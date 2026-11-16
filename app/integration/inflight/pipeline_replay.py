"""Extension v1, RQ3: whole-node replay of a two-step plan through the original LangGraph graph.

Disclosed harness elements (same as the original pipeline cross-check): the two-step plan is
supplied by the harness (the planner has no template for it); the opt-in maintenance adapter is
injected for ``rest_adapter`` by patching ``execution_agent.get_adapter``. Everything else is the
original graph: capability matcher node, GovernanceAgent node (real evaluation, ALLOW for both
steps), the single execution node, and a SQLite checkpointer. The external service is the
extension's ``InFlightEffectService``.

Sequence: step s1 commits and its acknowledgment is delivered; step s2's acknowledgment is lost
(its effect committed at dispatch, or pending and committing later). The exception leaves the
execution node without a completion checkpoint. The same thread is resumed, so LangGraph
re-runs the whole execution node, i.e. both steps. ``UNPROTECTED`` uses the adapter without a
guard; a policy ID uses the unchanged RecoveryGuard with that policy for every step.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any
from unittest import mock

from app.integration.inflight.assessor import assess
from app.integration.inflight.policies import EXT_POLICIES
from app.integration.inflight.runner import governance_revalidation_at
from app.integration.inflight.service import (
    AuthorizationTimeline,
    InFlightEffectService,
    RequestFault,
)
from app.integration.maintenance_effect_service import AcknowledgmentLost, SimulatedClock
from app.integration.recovery_experiment import CAPABILITY
from app.integration.recovery_journal import RecoveryJournal
from app.integration.recovery_policies import CapabilityContract
from app.models.plan import Plan, PlanStep

STEPS = ("s1", "s2")


def two_step_plan(machine_id: str) -> Plan:
    return Plan(
        goal_id="elcon-ext-two-step",
        goal_type="maintenance_ticket",
        payload={"machine_id": machine_id, "summary": "Bearing temperature high"},
        steps=[
            PlanStep(step_id=sid, title=f"Create maintenance ticket ({sid})",
                     intent="Open a maintenance work order for the target machine.",
                     required_capability=CAPABILITY, expected_output="Maintenance ticket identifier.")
            for sid in STEPS
        ],
    )


def _initial_state(case_id: str, plan: Plan) -> dict[str, Any]:
    return {
        "case_id": case_id, "goal": None, "plan": plan.model_dump(), "evaluation_governance_plan": None,
        "trace": [], "stage_latencies_ms": {}, "approval_required": False, "approval_resumed": False,
        "approval_payload": None, "approval_required_step_id": None, "approval_state": None,
        "approved_by": None, "approval_token": None, "resumed_from_interrupt": False,
        "approval_validation_error": None, "approval_execution_performed": False,
        "approval_resume_mutation": None, "controlled_approval_execution": False,
    }


def run_replay_trial(case: dict[str, Any], mode: str, workdir: Path, *, machine_id: str = "M-1",
                     replay: int = 0, provenance: dict[str, Any] | None = None) -> dict[str, Any]:
    from langgraph.checkpoint.sqlite import SqliteSaver

    import app.agents.execution_agent as execution_agent_module
    from app.adapters import get_adapter
    from app.integration.maintenance_effect_adapter import MaintenanceEffectAdapter
    from app.integration.recovery_guard import RecoveryGuard
    from app.langgraph_runtime.graph import build_graph

    workdir.mkdir(parents=True, exist_ok=False)
    t = case["times"]
    clock = SimulatedClock(t["dispatch_at"])
    timeline = AuthorizationTimeline(None)
    svc = InFlightEffectService(workdir / "effects.db", clock=clock,
                                deduplicate=case["provider"]["deduplicate"], auth_check="none",
                                authorization=timeline)
    svc.schedule([RequestFault(), RequestFault(**case["step2_fault"])])  # s1 acked; s2 ack lost
    client = svc.client()
    journal = RecoveryJournal(workdir / "journal.db")
    guard = None
    if mode != "UNPROTECTED":
        guard = RecoveryGuard(journal, CapabilityContract(**case["declared_contract"]), clock,
                              policy=EXT_POLICIES[mode],
                              revalidate=governance_revalidation_at(machine_id, timeline, clock),
                              horizon_s=t["horizon_s"])
    adapter = MaintenanceEffectAdapter(client, guard=guard)

    def resolve(name: str):
        return adapter if name == "rest_adapter" else get_adapter(name)

    thread_id = f"elcon-ext-replay-{case['id']}-{mode}-r{replay}"
    config = {"configurable": {"thread_id": thread_id}}
    checkpoint_db = str(workdir / "checkpoints.db")
    first = "completed"
    with mock.patch.object(execution_agent_module, "get_adapter", resolve):
        with SqliteSaver.from_conn_string(checkpoint_db) as saver:
            graph = build_graph().compile(checkpointer=saver)
            try:
                graph.invoke(_initial_state(case["id"], two_step_plan(machine_id)), config=config)
            except AcknowledgmentLost:
                first = "AcknowledgmentLost"
        ops_before = sorted({e.operation_id for e in svc.events()})
        clock.advance(t["resume_at"] - t["dispatch_at"])
        with SqliteSaver.from_conn_string(checkpoint_db) as saver:
            graph = build_graph().compile(checkpointer=saver)
            final = graph.invoke(None, config=config)
            snapshot = graph.get_state(config)
    resume_end = clock()
    drain = svc.drain(until=t["assessment_until"])
    events = [dataclasses.asdict(e) for e in svc.events()]
    effects = [dataclasses.asdict(e) for e in svc.effects()]
    result = final.get("execution_result")
    interrupts = [i.value for i in final.get("__interrupt__", [])]
    graph_outcome = ("graph_success" if result is not None and result["final_status"] == "success"
                     else "interrupted_hold" if interrupts else "other")
    step_results = {s["step_id"]: s for s in (result or {}).get("step_results", [])}
    per_step = {}
    for sid in STEPS:
        op = f"{thread_id}:{sid}"
        decisions = [dataclasses.asdict(d) for d in journal.decisions(op)] if guard else []
        recovery = [d for d in decisions if d["action"] != "DISPATCH"]
        out = (step_results.get(sid) or {}).get("result") or {}
        ticket = (out.get("result") or {}).get("ticket_id") if isinstance(out, dict) else None
        final_action = (recovery[-1]["action"] if recovery else
                        ("REDISPATCH" if step_results.get(sid, {}).get("status") == "executed" else "HOLD"))
        per_step[sid] = {
            "operation_id": op,
            "guard_recovery_decisions": [(d["action"], d["basis"]) for d in recovery],
            "step_status": step_results.get(sid, {}).get("status"),
            "recorded_ticket": ticket,
            "assessment": assess(operation_id=op, effects=effects, events=events,
                                 outcome={"final": final_action if graph_outcome == "graph_success" else "HOLD",
                                          "ticket_id": ticket},
                                 decision_time=resume_end, invalid_from=None,
                                 pending_at_horizon=drain.pending_at_horizon),
        }
    return {
        "case_id": case["id"], "set": "pipeline_replay", "rq": "RQ3", "mode": mode, "replay": replay,
        "provenance": provenance or {}, "declared_contract": case["declared_contract"],
        "provider": case["provider"], "step2_fault": case["step2_fault"], "times": t,
        "first_invocation": first, "operation_ids_before_resume": ops_before,
        "operation_ids_after_resume": sorted({e["operation_id"] for e in events}),
        "graph_outcome": graph_outcome, "hold_reasons": [i.get("reason") for i in interrupts],
        "pending_tasks": [task.name for task in snapshot.tasks],
        "steps": per_step, "events": events, "effects": effects,
        "pending_at_horizon": drain.pending_at_horizon,
    }
