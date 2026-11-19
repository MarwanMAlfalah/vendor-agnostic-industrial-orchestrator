"""ElCon-EE 2027: opt-in capability-aware RecoveryGuard on the original LangGraph path.

Same path as test_elcon_langgraph_recovery.py (original graph, real Matcher,
real GovernanceAgent, real ExecutionAgent, test-substituted adapter), with a
RecoveryGuard consulted before every dispatch. Three separate SQLite files:
LangGraph checkpoints, the recovery journal (workflow-side records), and the
service ledger (independent oracle, read only by these assertions).

Evidence category: opt-in capability-aware recovery integration. This is not the
frozen service-level B0/B1/B2/P matrix.
"""

import dataclasses
import inspect
from pathlib import Path

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from test_elcon_langgraph_recovery import (
    STEP_ID,
    _initial_state,
    _substitute_adapter,
    run_ack_loss_recovery,
)

from app.integration.maintenance_effect_adapter import (
    MAX_HOLD_ROUNDS,
    MaintenanceEffectAdapter,
    RecoveryHoldUnresolved,
    operation_id,
)
from app.integration.maintenance_effect_service import (
    AcknowledgmentLost,
    EffectLedger,
    FaultSpec,
    MaintenanceEffectService,
    SimulatedClock,
)
from app.integration.recovery_guard import (
    CapabilityContract,
    Evidence,
    GuardDecision,
    Observation,
    RecoveryGuard,
    capability_aware_next_action,
)
from app.integration.recovery_journal import RecoveryJournal
from app.langgraph_runtime.graph import build_graph

QUERYABLE = CapabilityContract(
    deduplicates_by_operation_id=False,
    binds_request_fingerprint=True,
    outcome_query="available",
    visibility_bound_s=0.0,
    completion_bound_s=0.0,
    failure_response_scope="attempt",
)
DEDUPLICATING = dataclasses.replace(QUERYABLE, deduplicates_by_operation_id=True)
UNVERIFIABLE = dataclasses.replace(QUERYABLE, outcome_query="unavailable", visibility_bound_s=None)
LAGGING = dataclasses.replace(QUERYABLE, visibility_bound_s=30.0)
LAGGING_NO_COMPLETION_BOUND = dataclasses.replace(LAGGING, completion_bound_s=None)

ACK_LOST = FaultSpec(commit=True, ack_delivered=False)


def run_guarded(
    tmp_path: Path,
    monkeypatch,
    *,
    contract: CapabilityContract,
    fault: FaultSpec | None,
    resume_after_s: float = 10.0,
) -> dict:
    """First attempt, then (if it failed) recovery via invoke(None) with the guard."""
    clock = SimulatedClock(1000.0)
    service = MaintenanceEffectService(
        tmp_path / "effects.db",
        deduplicate=bool(contract.deduplicates_by_operation_id),
        clock=clock,
    )
    if fault is not None:
        service.schedule_faults([fault])
    client = service.client()
    journal = RecoveryJournal(tmp_path / "journal.db")
    guard = RecoveryGuard(journal, contract, clock)
    _substitute_adapter(monkeypatch, MaintenanceEffectAdapter(client, guard=guard))
    ledger = EffectLedger(service.db_path)

    workflow_id = "elcon-guarded-wf"
    config = {"configurable": {"thread_id": workflow_id}}
    op_id = operation_id(workflow_id, STEP_ID)
    checkpoint_db = str(tmp_path / "checkpoints.db")
    record: dict = {"operation_id": op_id}

    with SqliteSaver.from_conn_string(checkpoint_db) as saver:
        graph = build_graph().compile(checkpointer=saver)
        try:
            final = graph.invoke(_initial_state("elcon-guarded"), config=config)
            record["first_attempt"] = "completed"
        except AcknowledgmentLost:
            record["first_attempt"] = "AcknowledgmentLost"
            final = None
    record["after_first_attempt"] = _counts(ledger, op_id)
    record["journal_after_first_attempt"] = [
        (a.reply_status, a.ticket_id) for a in journal.attempts(op_id)
    ]

    if final is None:
        clock.advance(resume_after_s)
        with SqliteSaver.from_conn_string(checkpoint_db) as saver:
            graph = build_graph().compile(checkpointer=saver)
            final = graph.invoke(None, config=config)
            record["state_after_recovery"] = _state(graph, config, final)
    else:
        with SqliteSaver.from_conn_string(checkpoint_db) as saver:
            graph = build_graph().compile(checkpointer=saver)
            record["state_after_recovery"] = _state(graph, config, final)

    record["after_recovery"] = _counts(ledger, op_id)
    record["decisions"] = [d.action for d in journal.decisions(op_id)]
    record["decision_bases"] = [d.basis for d in journal.decisions(op_id)]
    record["clock"] = clock()
    record["service_query_ticket_id"] = client.query(op_id).ticket_id
    record["_resume"] = (checkpoint_db, config)
    record["_ledger"] = ledger
    return record


def _counts(ledger: EffectLedger, op_id: str) -> dict:
    return {
        "dispatches": ledger.dispatch_count(op_id),
        "committed_effects": ledger.committed_effect_count(op_id),
        "acks_delivered": ledger.ack_delivered_count(op_id),
    }


def _state(graph, config, final: dict) -> dict:
    snapshot = graph.get_state(config)
    result = final.get("execution_result")
    interrupts = [i.value for i in final.get("__interrupt__", [])]
    return {
        "next": list(snapshot.next),
        "has_execution_result": "execution_result" in snapshot.values,
        "interrupts": interrupts,
        "final_status": result["final_status"] if result else None,
        "step_result": (result["output"].get(STEP_ID) if result else None),
    }


# --- 1. confirmed previous effect: ADOPT, no second dispatch ---------------


def test_guard_adopts_confirmed_effect_where_unprotected_replay_duplicates(tmp_path, monkeypatch):
    unprotected = run_ack_loss_recovery(tmp_path / "unprotected", monkeypatch, deduplicate=False)
    guarded = run_guarded(tmp_path / "guarded", monkeypatch, contract=QUERYABLE, fault=ACK_LOST)

    # Same fault, same request: the only difference is the guard.
    assert unprotected["after_recovery"]["committed_effects"] == 2
    assert guarded["first_attempt"] == "AcknowledgmentLost"
    assert guarded["after_first_attempt"] == {
        "dispatches": 1,
        "committed_effects": 1,
        "acks_delivered": 0,
    }
    # The journal records an attempt whose outcome is unknown to the workflow,
    # even though the ledger shows it committed: the journal is not the oracle.
    assert guarded["journal_after_first_attempt"] == [(None, None)]
    assert guarded["decisions"] == ["DISPATCH", "ADOPT"]
    assert guarded["after_recovery"] == {"dispatches": 1, "committed_effects": 1, "acks_delivered": 0}
    state = guarded["state_after_recovery"]
    assert state["next"] == []
    assert state["final_status"] == "success"
    assert state["step_result"]["recovery_action"] == "ADOPT"
    assert state["step_result"]["result"]["ticket_id"] == guarded["service_query_ticket_id"]


# --- 2. deduplicating service: REDISPATCH under the contract ---------------


def test_guard_redispatches_under_dedup_contract_with_one_effect(tmp_path, monkeypatch):
    record = run_guarded(tmp_path, monkeypatch, contract=DEDUPLICATING, fault=ACK_LOST)

    assert record["decisions"] == ["DISPATCH", "REDISPATCH"]
    assert record["decision_bases"][1] == "dedup_contract"
    assert record["after_recovery"] == {"dispatches": 2, "committed_effects": 1, "acks_delivered": 1}
    state = record["state_after_recovery"]
    assert state["final_status"] == "success"
    assert state["step_result"]["result"]["status"] == "deduplicated"


# --- 3. unverifiable outcome: HOLD, not success, no retry ------------------


def test_guard_holds_unverifiable_outcome_without_completing(tmp_path, monkeypatch):
    record = run_guarded(tmp_path, monkeypatch, contract=UNVERIFIABLE, fault=ACK_LOST)

    assert record["decisions"] == ["DISPATCH", "HOLD"]
    assert record["after_recovery"] == {"dispatches": 1, "committed_effects": 1, "acks_delivered": 0}
    state = record["state_after_recovery"]
    assert state["next"] == ["execution"]  # step not complete
    assert state["has_execution_result"] is False  # not checkpointed as success
    assert state["final_status"] is None
    assert len(state["interrupts"]) == 1
    hold = state["interrupts"][0]
    assert hold["reason"] == "RECOVERY_HOLD"  # distinct from REQUIRE_APPROVAL
    assert hold["operation_id"] == record["operation_id"]
    assert hold["basis"] == "outcome_unverifiable"

    # An operator resume re-evaluates; it does not force a dispatch.
    checkpoint_db, config = record["_resume"]
    with SqliteSaver.from_conn_string(checkpoint_db) as saver:
        graph = build_graph().compile(checkpointer=saver)
        resumed = graph.invoke(Command(resume={"resolution": "re-evaluate"}), config=config)
        snapshot = graph.get_state(config)
    assert [i.value["reason"] for i in resumed["__interrupt__"]] == ["RECOVERY_HOLD"]
    # Still held: the execution task is pending with a live interrupt and no result.
    assert [i.value["reason"] for i in snapshot.interrupts] == ["RECOVERY_HOLD"]
    assert [t.name for t in snapshot.tasks] == ["execution"]
    assert "execution_result" not in snapshot.values
    # LangGraph 1.2.1 omits a task from StateSnapshot.next once it carries a
    # __resume__ write (pregel/main.py: next = tasks without non-error,
    # non-interrupt writes). So next == () here does NOT mean completion.
    assert snapshot.next == ()
    assert record["_ledger"].dispatch_count(record["operation_id"]) == 1


# --- 4. no known prior dispatch: normal execution --------------------------


def test_first_authorized_dispatch_executes_normally(tmp_path, monkeypatch):
    record = run_guarded(tmp_path, monkeypatch, contract=QUERYABLE, fault=None)

    assert record["first_attempt"] == "completed"
    assert record["decisions"] == ["DISPATCH"]
    assert record["journal_after_first_attempt"] == [
        ("committed", record["service_query_ticket_id"])
    ]
    assert record["after_recovery"] == {"dispatches": 1, "committed_effects": 1, "acks_delivered": 1}
    assert record["state_after_recovery"]["final_status"] == "success"


# --- 5. early negative query is not conclusive -----------------------------


def test_early_not_found_waits_for_both_bounds_then_adopts(tmp_path, monkeypatch):
    lagging_ack_lost = FaultSpec(commit=True, ack_delivered=False, visibility_delay=30.0)
    record = run_guarded(tmp_path, monkeypatch, contract=LAGGING, fault=lagging_ack_lost)

    # Resume at 1010: not_found; deadline 1000 + completion 0 + visibility 30.
    assert record["decisions"] == ["DISPATCH", "ADOPT"]
    assert record["clock"] == 1030.0
    assert record["after_recovery"] == {"dispatches": 1, "committed_effects": 1, "acks_delivered": 0}
    assert record["state_after_recovery"]["final_status"] == "success"


def test_visibility_bound_without_completion_bound_holds(tmp_path, monkeypatch):
    lagging_ack_lost = FaultSpec(commit=True, ack_delivered=False, visibility_delay=30.0)
    record = run_guarded(
        tmp_path, monkeypatch, contract=LAGGING_NO_COMPLETION_BOUND, fault=lagging_ack_lost
    )

    assert record["decisions"] == ["DISPATCH", "HOLD"]
    assert record["decision_bases"][1] == "not_found_not_authoritative"
    assert record["after_recovery"]["dispatches"] == 1
    assert record["state_after_recovery"]["next"] == ["execution"]


def test_authoritative_absence_after_both_bounds_permits_redispatch(tmp_path, monkeypatch):
    no_commit_no_reply = FaultSpec(commit=False, ack_delivered=False)
    record = run_guarded(tmp_path, monkeypatch, contract=LAGGING, fault=no_commit_no_reply)

    assert record["after_first_attempt"]["committed_effects"] == 0
    assert record["decisions"] == ["DISPATCH", "REDISPATCH"]
    assert record["decision_bases"][1] == "authoritative_absence"
    assert record["clock"] == 1030.0  # waited for the deadline before redispatch
    assert record["after_recovery"] == {"dispatches": 2, "committed_effects": 1, "acks_delivered": 1}
    assert record["state_after_recovery"]["final_status"] == "success"


# --- request identity: a changed request under the same operation ID -------


def test_changed_request_under_same_operation_id_holds(tmp_path):
    clock = SimulatedClock(1000.0)
    guard = RecoveryGuard(RecoveryJournal(tmp_path / "journal.db"), QUERYABLE, clock)
    common = dict(
        operation_id="wf:step-001",
        workflow_id="wf",
        step_id="step-001",
        capability="create_maintenance_ticket",
        adapter="maintenance_effect_adapter",
        query=lambda op: pytest.fail("no query expected"),
    )
    first = guard.decide(request={"machine_id": "M1", "summary": "a"}, **common)
    changed = guard.decide(request={"machine_id": "M1", "summary": "b"}, **common)

    assert first.action == "DISPATCH"
    assert (changed.action, changed.basis) == ("HOLD", "request_fingerprint_mismatch")


# --- 6. isolation: the policy sees an Observation and Evidence only --------


def test_policy_input_contains_no_oracle_or_case_information():
    assert list(inspect.signature(capability_aware_next_action).parameters) == ["obs", "ev"]
    forbidden = {"case", "case_id", "fault", "fault_schedule", "ledger", "oracle", "expected"}
    obs_fields = {f.name for f in dataclasses.fields(Observation)}
    ev_fields = {f.name for f in dataclasses.fields(Evidence)}
    assert not obs_fields & forbidden
    assert not ev_fields & forbidden
    assert obs_fields == {
        "workflow_id",
        "step_id",
        "operation_id",
        "capability",
        "adapter",
        "request",
        "dispatch",
        "ack",
        "contract",
        "approval",
        "preconditions",
        "resume_at",
        "horizon_end",
    }
    assert ev_fields == {"governance", "queries", "now"}
    guard_params = set(inspect.signature(RecoveryGuard).parameters)
    assert not guard_params & {"service", "ledger", "client", "fault_schedule"}


# --- 7. compatibility: without a guard the adapter is the unprotected path -


def test_adapter_without_guard_is_unchanged_unprotected_replay(tmp_path, monkeypatch):
    record = run_ack_loss_recovery(tmp_path, monkeypatch, deduplicate=False)
    assert record["after_recovery"]["dispatches"] == 2
    assert record["after_recovery"]["committed_effects"] == 2


def test_hold_that_does_not_pause_is_bounded_and_never_dispatches(tmp_path):
    clock = SimulatedClock(1000.0)
    service = MaintenanceEffectService(tmp_path / "effects.db", deduplicate=False, clock=clock)
    service.schedule_faults([ACK_LOST])
    guard = RecoveryGuard(RecoveryJournal(tmp_path / "journal.db"), UNVERIFIABLE, clock)
    holds: list[dict] = []
    adapter = MaintenanceEffectAdapter(
        service.client(), workflow_id_provider=lambda: "wf", guard=guard, hold=holds.append
    )
    payload = {"machine_id": "M1"}
    with pytest.raises(AcknowledgmentLost):
        adapter.invoke_step("create_maintenance_ticket", payload, step_id=STEP_ID)

    with pytest.raises(RecoveryHoldUnresolved):
        adapter.invoke_step("create_maintenance_ticket", payload, step_id=STEP_ID)

    assert len(holds) == MAX_HOLD_ROUNDS
    assert EffectLedger(service.db_path).dispatch_count(operation_id("wf", STEP_ID)) == 1


class _ScriptedGuard:
    """Returns HOLD n times, then a resolving decision (review finding 1)."""

    def __init__(self, holds: int, final: GuardDecision) -> None:
        self._decisions = [GuardDecision("HOLD", "outcome_unverifiable")] * holds + [final]

    def decide(self, **_):
        return self._decisions.pop(0)


def test_hold_resolved_on_the_last_permitted_round_is_not_reported_unresolved(tmp_path):
    service = MaintenanceEffectService(
        tmp_path / "effects.db", deduplicate=False, clock=SimulatedClock(1000.0)
    )
    guard = _ScriptedGuard(MAX_HOLD_ROUNDS, GuardDecision("ADOPT", "query_found", "MT-1"))
    holds: list[dict] = []
    adapter = MaintenanceEffectAdapter(
        service.client(), workflow_id_provider=lambda: "wf", guard=guard, hold=holds.append
    )

    result = adapter.invoke_step("create_maintenance_ticket", {"machine_id": "M1"}, step_id=STEP_ID)

    assert len(holds) == MAX_HOLD_ROUNDS
    assert result["recovery_action"] == "ADOPT"
    assert EffectLedger(service.db_path).dispatch_count(operation_id("wf", STEP_ID)) == 0
