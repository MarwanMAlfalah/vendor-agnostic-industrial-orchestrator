"""Extension v1 service-level runner (RQ1 in-flight commits, RQ2 changing governance).

One execution = one case x one policy with fresh SQLite databases:
1. at dispatch_at the guard journals the first attempt and the request is submitted; the
   case's first-dispatch fault decides when (or whether) it commits; its acknowledgment is lost;
2. the clock advances to resume_at; the unchanged ``RecoveryGuard`` builds the policy-visible
   observation from its journal and the declared contract and runs the policy through the
   unchanged ``drive_policy`` (REVALIDATE / QUERY / WAIT_UNTIL executed on its behalf);
3. the terminal decision is executed (REDISPATCH submits with the same operation ID; ADOPT
   records the ticket; HOLD stops);
4. the service drains every scheduled event up to the assessment horizon, and the independent
   assessor evaluates the ledger and event log.

Policies see only the guard's observation, query replies and governance decisions. They never
see the fault schedule, the authorization timeline, the ledger or the case ID.

Governance revalidation runs the real ``CapabilityMatchingAgent`` and ``GovernanceAgent`` on
the harness one-step plan. The only substituted input is the capability registry snapshot: a
copy of the shipped registry in which ``create_maintenance_ticket.availability`` equals the
simulated precondition/authorization state at the current simulated time. GovernanceAgent
returns ALLOW while it is available and SAFE_ABORT (capability_unavailable) otherwise. With no
transition this is identical to the original study's revalidation.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.agents.capability_matcher import CapabilityMatchingAgent
from app.agents.governance_agent import GovernanceAgent
from app.integration.inflight.assessor import assess
from app.integration.inflight.policies import EXT_POLICIES
from app.integration.inflight.service import (
    AuthorizationTimeline,
    InFlightEffectService,
    RequestFault,
)
from app.integration.maintenance_effect_service import AcknowledgmentLost, SimulatedClock
from app.integration.recovery_experiment import CAPABILITY, STEP_ID, harness_plan
from app.integration.recovery_guard import RecoveryGuard
from app.integration.recovery_journal import RecoveryJournal
from app.integration.recovery_policies import CapabilityContract
from app.registry.loader import load_capabilities

ADAPTER = "maintenance_effect_adapter"


def governance_revalidation_at(machine_id: str, timeline: AuthorizationTimeline,
                               clock: SimulatedClock) -> Callable[[], tuple[str, str]]:
    def revalidate() -> tuple[str, str]:
        available = timeline.valid(clock())
        snapshot = [
            c.model_copy(update={"availability": available}) if c.capability_name == CAPABILITY else c
            for c in load_capabilities()
        ]
        mapped = CapabilityMatchingAgent(capabilities=snapshot).match_plan(harness_plan(machine_id))
        evaluation = GovernanceAgent(capabilities=snapshot).evaluate(mapped)
        step = next(s for s in evaluation.steps if s.step_id == STEP_ID)
        return step.decision, (
            "GovernanceAgent re-run (read-only) on the harness plan; registry snapshot "
            f"availability={available}; reason={step.reason}"
        )

    return revalidate


def run_ext_trial(case: dict[str, Any], policy_id: str, workdir: Path, *, machine_id: str = "M-1",
                  replay: int = 0, provenance: dict[str, Any] | None = None) -> dict[str, Any]:
    workdir.mkdir(parents=True, exist_ok=False)
    t = case["times"]
    clock = SimulatedClock(t["dispatch_at"])
    timeline = AuthorizationTimeline(case.get("authorization", {}).get("invalid_from"))
    svc = InFlightEffectService(workdir / "effects.db", clock=clock,
                                deduplicate=case["provider"]["deduplicate"],
                                auth_check=case["provider"]["auth_check"], authorization=timeline)
    svc.schedule([RequestFault(**case["first_dispatch_fault"])])
    client = svc.client()
    contract = CapabilityContract(**case["declared_contract"])
    revalidations: list[dict[str, Any]] = []
    base_revalidate = governance_revalidation_at(machine_id, timeline, clock)

    def revalidate() -> tuple[str, str]:
        decision, prov = base_revalidate()
        revalidations.append({"time": clock(), "decision": decision, "provenance": prov})
        return decision, prov

    journal = RecoveryJournal(workdir / "journal.db")
    guard = RecoveryGuard(journal, contract, clock, policy=EXT_POLICIES[policy_id],
                          revalidate=revalidate, horizon_s=t["horizon_s"])
    workflow_id = f"ext-{case['id']}-{policy_id}-r{replay}"
    op = f"{workflow_id}:{STEP_ID}"
    request = {"machine_id": machine_id, "summary": "Bearing temperature high"}

    def decide():
        return guard.decide(operation_id=op, workflow_id=workflow_id, step_id=STEP_ID,
                            capability=CAPABILITY, adapter=ADAPTER, request=request, query=client.query)

    first = decide()
    assert first.action == "DISPATCH", first
    attempt = guard.begin_attempt(op)
    first_reply = "ack_lost"
    try:
        reply = client.submit(op, machine_id)
        guard.record_reply(attempt, reply.status, reply.ticket_id)
        first_reply = reply.status
    except AcknowledgmentLost:
        pass
    clock.advance(t["resume_at"] - t["dispatch_at"])
    decision = decide()
    decision_time = clock()
    final = decision.action
    ticket = decision.ticket_id if decision.action == "ADOPT" else None
    redispatch_reply = None
    if decision.action == "REDISPATCH":
        attempt = guard.begin_attempt(op)
        try:
            reply = client.submit(op, machine_id)
            guard.record_reply(attempt, reply.status, reply.ticket_id)
            redispatch_reply = reply.status
            if reply.status in ("committed", "deduplicated"):
                ticket = reply.ticket_id
            else:
                final = "REDISPATCH_REJECTED"
        except AcknowledgmentLost:
            redispatch_reply = "ack_lost"
            final = "REDISPATCH_ACK_LOST"
    drain = svc.drain(until=t["assessment_until"])
    events = [dataclasses.asdict(e) for e in svc.events()]
    effects = [dataclasses.asdict(e) for e in svc.effects()]
    outcome = decision.outcome
    record = {
        "case_id": case["id"], "set": case["set"], "rq": case["rq"], "policy": policy_id, "replay": replay,
        "provenance": provenance or {},
        "declared_contract": case["declared_contract"], "provider": case["provider"],
        "first_dispatch_fault": case["first_dispatch_fault"], "times": t,
        "authorization": case.get("authorization", {}),
        "first_reply": first_reply,
        "decision": decision.action, "decision_basis": decision.basis, "decision_time": decision_time,
        "decision_path": ">".join(a.kind for a in outcome.steps) if outcome else decision.action,
        "queries_by_policy": [dataclasses.asdict(q) for q in outcome.evidence.queries] if outcome else [],
        "simulated_wait_s": outcome.simulated_wait_s if outcome else 0.0,
        "policy_error": outcome.error if outcome else None,
        "revalidations": revalidations,
        "redispatch_reply": redispatch_reply,
        "final": final, "recorded_ticket": ticket,
        "events": events, "effects": effects, "pending_at_horizon": drain.pending_at_horizon,
    }
    record["assessment"] = assess(
        operation_id=op, effects=effects, events=events,
        outcome={"final": final, "ticket_id": ticket}, decision_time=decision_time,
        invalid_from=timeline.invalid_from, pending_at_horizon=drain.pending_at_horizon,
    )
    return record
