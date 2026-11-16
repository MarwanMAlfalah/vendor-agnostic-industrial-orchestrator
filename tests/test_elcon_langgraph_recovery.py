"""ElCon-EE 2027: first recovery measurement through the original LangGraph graph.

Path under test (all original components except the substituted adapter):
build_graph() -> planner_node (no goal: plan supplied by the test) -> matcher_node
(CapabilityMatchingAgent) -> governance_node (GovernanceAgent) -> execution_node
(ExecutionAgent) -> MaintenanceEffectAdapter -> MaintenanceClient ->
MaintenanceEffectService.

The adapter that ExecutionAgent resolves for 'rest_adapter' is substituted by the
test (monkeypatch of app.agents.execution_agent.get_adapter). Default runtime and
default adapters are unchanged. Ground truth is read from EffectLedger only.

Recovery mechanism: after the execution node raises, the same thread is resumed
with graph.invoke(None, config), LangGraph's supported continuation from the
latest checkpoint. This is not Command(resume=...) (no interrupt is pending), not
time travel (no checkpoint_id is chosen), and not re-invoking a completed run.
"""

import sqlite3
from contextlib import closing
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver

import app.agents.execution_agent as execution_agent_module
from app.adapters import AdapterError, build_adapters, get_adapter
from app.agents import ExecutionAgent
from app.integration.maintenance_effect_adapter import (
    MaintenanceEffectAdapter,
    operation_id,
)
from app.integration.maintenance_effect_service import (
    AcknowledgmentLost,
    EffectLedger,
    FaultSpec,
    MaintenanceEffectService,
    SimulatedClock,
)
from app.langgraph_runtime.graph import build_graph
from app.models.governance import GovernanceEvaluation, GovernanceStepDecision
from app.models.plan import Plan, PlanStep

STEP_ID = "step-001"
MACHINE_ID = "M1"


def _plan() -> Plan:
    return Plan(
        goal_id="elcon-maintenance-goal",
        goal_type="maintenance_ticket",
        payload={"machine_id": MACHINE_ID, "summary": "Bearing temperature high"},
        steps=[
            PlanStep(
                step_id=STEP_ID,
                title="Create maintenance ticket",
                intent="Open a maintenance work order for the target machine.",
                required_capability="create_maintenance_ticket",
                expected_output="Maintenance ticket identifier.",
            )
        ],
    )


def _initial_state(case_id: str) -> dict:
    # Same keys as LangGraphRuntime._initial_state, except: no goal (no Planner
    # template produces create_maintenance_ticket), a test-supplied plan, and no
    # evaluation_governance_plan, so the real GovernanceAgent runs.
    return {
        "case_id": case_id,
        "goal": None,
        "plan": _plan().model_dump(),
        "evaluation_governance_plan": None,
        "trace": [],
        "stage_latencies_ms": {},
        "approval_required": False,
        "approval_resumed": False,
        "approval_payload": None,
        "approval_required_step_id": None,
        "approval_state": None,
        "approved_by": None,
        "approval_token": None,
        "resumed_from_interrupt": False,
        "approval_validation_error": None,
        "approval_execution_performed": False,
        "approval_resume_mutation": None,
        "controlled_approval_execution": False,
    }


def _substitute_adapter(monkeypatch, adapter: MaintenanceEffectAdapter) -> None:
    def resolve(adapter_name: str):
        return adapter if adapter_name == "rest_adapter" else get_adapter(adapter_name)

    monkeypatch.setattr(execution_agent_module, "get_adapter", resolve)


def _checkpoints(saver: SqliteSaver, config: dict) -> list:
    return list(saver.list(config))


def run_ack_loss_recovery(tmp_path: Path, monkeypatch, *, deduplicate: bool) -> dict:
    """Run one workflow, lose the ack after commit, recover, and record everything."""
    clock = SimulatedClock(1000.0)
    service = MaintenanceEffectService(
        tmp_path / "effects.db", deduplicate=deduplicate, clock=clock
    )
    service.schedule_faults([FaultSpec(commit=True, ack_delivered=False)])
    client = service.client()
    _substitute_adapter(monkeypatch, MaintenanceEffectAdapter(client))
    ledger = EffectLedger(service.db_path)

    workflow_id = f"elcon-wf-dedup-{deduplicate}".lower()
    config = {"configurable": {"thread_id": workflow_id}}
    op_id = operation_id(workflow_id, STEP_ID)
    checkpoint_db = str(tmp_path / "checkpoints.db")
    record: dict = {"workflow_id": workflow_id, "operation_id": op_id}

    # Attempt 1: original graph; the service commits, then the ack is lost.
    with SqliteSaver.from_conn_string(checkpoint_db) as saver:
        graph = build_graph().compile(checkpointer=saver)
        with pytest.raises(AcknowledgmentLost) as raised:
            graph.invoke(_initial_state("elcon-ack-loss"), config=config)
        record["first_attempt_exception"] = type(raised.value).__name__
        record["checkpoints_after_failure"] = len(_checkpoints(saver, config))

    record["after_attempt_1"] = {
        "dispatches": ledger.dispatch_count(op_id),
        "committed_effects": ledger.committed_effect_count(op_id),
        "acks_delivered": ledger.ack_delivered_count(op_id),
        "outcomes": ledger.dispatch_outcomes(op_id),
    }

    # Recovery: a fresh saver connection and a freshly compiled graph on the same
    # checkpoint file (a new runtime object, same OS process).
    with SqliteSaver.from_conn_string(checkpoint_db) as saver:
        graph = build_graph().compile(checkpointer=saver)
        before = graph.get_state(config)
        record["state_before_recovery"] = {
            "next": list(before.next),
            "pending_task_names": [t.name for t in before.tasks],
            "pending_task_errors": [t.error for t in before.tasks],
            "has_execution_result": "execution_result" in before.values,
            "governance_decisions": [
                s["decision"] for s in before.values["governance_plan"]["steps"]
            ],
            "approval_required": before.values.get("approval_required"),
            "trace": list(before.values.get("trace", [])),
        }
        final = graph.invoke(None, config=config)
        after = graph.get_state(config)
        record["checkpoints_after_recovery"] = len(_checkpoints(saver, config))

    result = final["execution_result"]
    record["after_recovery"] = {
        "dispatches": ledger.dispatch_count(op_id),
        "committed_effects": ledger.committed_effect_count(op_id),
        "acks_delivered": ledger.ack_delivered_count(op_id),
        "outcomes": ledger.dispatch_outcomes(op_id),
    }
    record["final_graph"] = {
        "next": list(after.next),
        "final_status": result["final_status"],
        "step_status": result["step_results"][0]["status"],
        "workflow_ticket_id": result["output"][STEP_ID]["result"]["ticket_id"],
        "service_query_ticket_id": client.query(op_id).ticket_id,
        "interrupted": "__interrupt__" in final,
        "trace": list(final.get("trace", [])),
    }
    return record


def _assert_failure_left_execution_incomplete(record: dict) -> None:
    assert record["first_attempt_exception"] == "AcknowledgmentLost"
    # input checkpoint + one per completed superstep (planner, matcher,
    # governance) + the checkpoint whose pending task is execution.
    assert record["checkpoints_after_failure"] == 5
    assert record["checkpoints_after_recovery"] == 6
    # The effect was committed before the execution node failed.
    assert record["after_attempt_1"] == {
        "dispatches": 1,
        "committed_effects": 1,
        "acks_delivered": 0,
        "outcomes": ["committed"],
    }
    before = record["state_before_recovery"]
    assert before["next"] == ["execution"]
    assert before["pending_task_names"] == ["execution"]
    assert before["has_execution_result"] is False
    assert before["governance_decisions"] == ["ALLOW"]
    assert before["approval_required"] is False
    assert before["trace"] == ["planner_node", "matcher_node", "governance_node"]
    # Recovery re-ran only the pending execution task, once.
    assert record["final_graph"]["trace"] == [
        "planner_node",
        "matcher_node",
        "governance_node",
        "execution_node",
        "final_result",
    ]


def test_unprotected_replay_after_lost_ack_commits_a_second_effect(tmp_path, monkeypatch):
    record = run_ack_loss_recovery(tmp_path, monkeypatch, deduplicate=False)

    _assert_failure_left_execution_incomplete(record)
    assert record["after_recovery"] == {
        "dispatches": 2,
        "committed_effects": 2,
        "acks_delivered": 1,
        "outcomes": ["committed", "committed"],
    }
    final = record["final_graph"]
    assert final["next"] == []
    assert final["final_status"] == "success"
    assert final["step_status"] == "executed"
    assert final["interrupted"] is False
    # The workflow records the second ticket; the first remains committed but
    # unreferenced by the workflow.
    assert final["workflow_ticket_id"] != final["service_query_ticket_id"]


def test_deduplicating_service_keeps_one_effect_across_replay(tmp_path, monkeypatch):
    record = run_ack_loss_recovery(tmp_path, monkeypatch, deduplicate=True)

    _assert_failure_left_execution_incomplete(record)
    assert record["after_recovery"] == {
        "dispatches": 2,
        "committed_effects": 1,
        "acks_delivered": 1,
        "outcomes": ["committed", "deduplicated"],
    }
    final = record["final_graph"]
    assert final["next"] == []
    assert final["final_status"] == "success"
    assert final["step_status"] == "executed"
    assert final["workflow_ticket_id"] == final["service_query_ticket_id"]


def test_operation_identity_is_per_workflow_instance_not_per_machine(tmp_path, monkeypatch):
    service = MaintenanceEffectService(
        tmp_path / "effects.db", deduplicate=True, clock=SimulatedClock(1000.0)
    )
    _substitute_adapter(monkeypatch, MaintenanceEffectAdapter(service.client()))
    ledger = EffectLedger(service.db_path)
    with SqliteSaver.from_conn_string(str(tmp_path / "checkpoints.db")) as saver:
        graph = build_graph().compile(checkpointer=saver)
        for workflow_id in ("elcon-wf-a", "elcon-wf-b"):
            config = {"configurable": {"thread_id": workflow_id}}
            graph.invoke(_initial_state(workflow_id), config=config)

    op_a, op_b = operation_id("elcon-wf-a", STEP_ID), operation_id("elcon-wf-b", STEP_ID)
    assert op_a != op_b
    # Same machine, same request: under deduplication a machine-keyed identity
    # would collapse these into one effect. Each instance commits its own.
    assert ledger.committed_effect_count(op_a) == 1
    assert ledger.committed_effect_count(op_b) == 1


# --- adapter guards: no dispatch without identity or a valid request -------


def _unit_adapter(tmp_path, workflow_id_provider=lambda: "wf-unit"):
    service = MaintenanceEffectService(
        tmp_path / "effects.db", deduplicate=False, clock=SimulatedClock(1000.0)
    )
    adapter = MaintenanceEffectAdapter(service.client(), workflow_id_provider=workflow_id_provider)
    return service, adapter, EffectLedger(service.db_path)


def test_plain_invoke_without_step_identity_does_not_dispatch(tmp_path):
    service, adapter, ledger = _unit_adapter(tmp_path)
    with pytest.raises(AdapterError, match="step identity"):
        adapter.invoke("create_maintenance_ticket", {"machine_id": MACHINE_ID})
    assert ledger.dispatch_count(operation_id("wf-unit", STEP_ID)) == 0


def test_outside_langgraph_run_there_is_no_durable_identity_and_no_dispatch(tmp_path):
    service = MaintenanceEffectService(
        tmp_path / "effects.db", deduplicate=False, clock=SimulatedClock(1000.0)
    )
    adapter = MaintenanceEffectAdapter(service.client())  # default: LangGraph thread_id
    with pytest.raises(AdapterError, match="durable workflow identity"):
        adapter.invoke_step("create_maintenance_ticket", {"machine_id": MACHINE_ID}, step_id=STEP_ID)
    with closing(sqlite3.connect(service.db_path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM dispatch_log").fetchone()[0] == 0


def test_missing_machine_id_does_not_dispatch(tmp_path):
    service, adapter, ledger = _unit_adapter(tmp_path)
    with pytest.raises(AdapterError, match="machine_id"):
        adapter.invoke_step("create_maintenance_ticket", {}, step_id=STEP_ID)
    assert ledger.dispatch_count(operation_id("wf-unit", STEP_ID)) == 0


def test_lost_ack_propagates_and_is_not_converted_to_adapter_error(tmp_path):
    service, adapter, ledger = _unit_adapter(tmp_path)
    service.schedule_faults([FaultSpec(commit=True, ack_delivered=False)])
    with pytest.raises(AcknowledgmentLost) as raised:
        adapter.invoke_step("create_maintenance_ticket", {"machine_id": MACHINE_ID}, step_id=STEP_ID)
    assert not isinstance(raised.value, AdapterError)
    assert ledger.committed_effect_count(operation_id("wf-unit", STEP_ID)) == 1


def test_failed_attempt_reply_is_an_adapter_error(tmp_path):
    service, adapter, ledger = _unit_adapter(tmp_path)
    service.schedule_faults([FaultSpec(commit=False)])
    with pytest.raises(AdapterError, match="failed"):
        adapter.invoke_step("create_maintenance_ticket", {"machine_id": MACHINE_ID}, step_id=STEP_ID)
    assert ledger.committed_effect_count(operation_id("wf-unit", STEP_ID)) == 0


@pytest.mark.parametrize(
    "workflow_id, step_id",
    [("", STEP_ID), ("wf", ""), (None, STEP_ID), ("wf:a", "s"), ("wf", "a:s")],
)
def test_operation_id_rejects_missing_or_ambiguous_identity(workflow_id, step_id):
    # AdapterError: ExecutionAgent records a refused dispatch instead of the
    # node crashing on every replay.
    with pytest.raises(AdapterError):
        operation_id(workflow_id, step_id)


def test_empty_workflow_identity_is_refused_before_dispatch(tmp_path):
    service, adapter, ledger = _unit_adapter(tmp_path, workflow_id_provider=lambda: "")
    with pytest.raises(AdapterError):
        adapter.invoke_step("create_maintenance_ticket", {"machine_id": MACHINE_ID}, step_id=STEP_ID)
    with closing(sqlite3.connect(service.db_path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM dispatch_log").fetchone()[0] == 0


# --- finding 9: step identity is an explicit opt-in, not duck typing -------


class _DuckAdapter:
    """Third-party-style adapter that happens to define invoke_step."""

    adapter_name = "rest_adapter"
    supported_capabilities = {"create_maintenance_ticket"}

    def __init__(self) -> None:
        self.calls: list[str] = []

    def invoke(self, capability_name, payload):
        self.calls.append("invoke")
        return {"result": {"ticket_id": "T-1"}}

    def invoke_step(self, capability_name, payload, *, step_id):
        self.calls.append("invoke_step")
        return {"result": {"ticket_id": "T-1"}}


def _allow_plan() -> GovernanceEvaluation:
    return GovernanceEvaluation(
        goal_id="g",
        goal_type="maintenance_ticket",
        payload={"machine_id": MACHINE_ID},
        steps=[
            GovernanceStepDecision(
                step_id=STEP_ID,
                title="Create maintenance ticket",
                decision="ALLOW",
                reason="no_blocking_policy",
                selected_adapter="rest_adapter",
                selected_capability="create_maintenance_ticket",
            )
        ],
    )


@pytest.mark.parametrize("adapter_factory", [_DuckAdapter, MagicMock])
def test_adapters_without_the_opt_in_flag_keep_plain_invoke(monkeypatch, adapter_factory):
    adapter = adapter_factory()
    if isinstance(adapter, MagicMock):
        adapter.invoke.return_value = {"result": {"ticket_id": "T-1"}}
    monkeypatch.setattr(execution_agent_module, "get_adapter", lambda name: adapter)

    ExecutionAgent().run(_allow_plan())

    if isinstance(adapter, MagicMock):
        adapter.invoke.assert_called_once()
        adapter.invoke_step.assert_not_called()
    else:
        assert adapter.calls == ["invoke"]


def test_default_adapters_do_not_opt_in():
    assert all(
        getattr(type(a), "requires_step_identity", False) is False
        for a in build_adapters().values()
    )
    assert MaintenanceEffectAdapter.requires_step_identity is True
