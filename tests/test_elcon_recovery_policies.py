"""Frozen protocol v1.0 §3 policies B0/B1/B2/P as pure functions, per information class.

Expected actions below are derived from the frozen pseudocode, not from runs.
"""

import dataclasses

import pytest

from app.integration.maintenance_effect_service import SimulatedClock
from app.integration.recovery_policies import (
    POLICIES,
    AckState,
    Action,
    CapabilityContract,
    DispatchState,
    Evidence,
    Observation,
    QueryEvidence,
    b0_blind_redispatch,
    b1_revalidate_then_redispatch,
    b2_idempotency_and_readback,
    drive_policy,
    p_capability_aware,
)

Q0 = CapabilityContract(False, True, "available", 0.0, 0.0, "attempt")
DEDUP = dataclasses.replace(Q0, deduplicates_by_operation_id=True)
UNVERIFIABLE = dataclasses.replace(Q0, outcome_query="unavailable", visibility_bound_s=None)
DEDUP_UNVERIFIABLE = dataclasses.replace(UNVERIFIABLE, deduplicates_by_operation_id=True)
LAG30 = dataclasses.replace(Q0, visibility_bound_s=30.0)
LAG_UNDECLARED = dataclasses.replace(Q0, visibility_bound_s=None)
LAG30_NO_COMPLETION = dataclasses.replace(LAG30, completion_bound_s=None)


def obs(contract, ack="missing", attempts=1):
    return Observation(
        workflow_id="wf",
        step_id="step-001",
        operation_id="wf:step-001",
        capability="create_maintenance_ticket",
        adapter="maintenance_effect_service",
        request={"machine_id": "M1"},
        dispatch=DispatchState(attempts, 1000.0),
        ack=AckState(ack, None, None),
        contract=contract,
        approval={"required": False, "status": "not_required"},
        preconditions={},
        resume_at=1010.0,
        horizon_end=1070.0,
    )


def ev(*queries, governance="ALLOW", now=1010.0):
    return Evidence(governance=governance, queries=tuple(queries), now=now)


FOUND = QueryEvidence("found", "MT-M1-000001", 1010.0)
NF_EARLY = QueryEvidence("not_found", None, 1010.0)
NF_AT_DEADLINE = QueryEvidence("not_found", None, 1030.0)


def kind(policy, o, e):
    return policy(o, e).kind


def test_registry_holds_exactly_the_four_frozen_policies():
    assert POLICIES == {
        "B0": b0_blind_redispatch,
        "B1": b1_revalidate_then_redispatch,
        "B2": b2_idempotency_and_readback,
        "P": p_capability_aware,
    }


@pytest.mark.parametrize("policy", [b1_revalidate_then_redispatch, b2_idempotency_and_readback, p_capability_aware])
def test_revalidation_comes_first_and_non_allow_holds(policy):
    assert kind(policy, obs(Q0), ev(governance=None)) == "REVALIDATE"
    assert kind(policy, obs(Q0), ev(governance="BLOCK")) == "HOLD"


def test_b0_always_redispatches_without_revalidation():
    for contract in (Q0, DEDUP, UNVERIFIABLE, LAG30, LAG_UNDECLARED):
        assert kind(b0_blind_redispatch, obs(contract), ev(governance=None)) == "REDISPATCH"


def test_b1_redispatches_after_allow_whatever_the_contract():
    for contract in (Q0, UNVERIFIABLE, LAG_UNDECLARED):
        assert kind(b1_revalidate_then_redispatch, obs(contract), ev()) == "REDISPATCH"


@pytest.mark.parametrize("policy", [b2_idempotency_and_readback, p_capability_aware])
def test_ic1_failure_reply_on_sole_attempt_redispatches(policy):
    assert kind(policy, obs(Q0, ack="failure_received"), ev()) == "REDISPATCH"
    # Not sole attempt: falls through to the query rules.
    assert kind(policy, obs(Q0, ack="failure_received", attempts=2), ev()) == "QUERY"


@pytest.mark.parametrize("policy", [b2_idempotency_and_readback, p_capability_aware])
def test_conflict_reply_holds(policy):
    assert kind(policy, obs(Q0, ack="conflict"), ev()) == "HOLD"


@pytest.mark.parametrize("policy", [b2_idempotency_and_readback, p_capability_aware])
@pytest.mark.parametrize("contract", [DEDUP, DEDUP_UNVERIFIABLE])
def test_ic3_ic5_ic8_dedup_contract_redispatches(policy, contract):
    assert kind(policy, obs(contract), ev()) == "REDISPATCH"


@pytest.mark.parametrize("policy", [b2_idempotency_and_readback, p_capability_aware])
def test_ic4_unverifiable_without_dedup_holds(policy):
    assert kind(policy, obs(UNVERIFIABLE), ev()) == "HOLD"


@pytest.mark.parametrize("policy", [b2_idempotency_and_readback, p_capability_aware])
def test_ic2_query_first_then_adopt_or_authoritative_redispatch(policy):
    assert kind(policy, obs(Q0), ev()) == "QUERY"
    adopt = policy(obs(Q0), ev(FOUND))
    assert (adopt.kind, adopt.ticket_id) == ("ADOPT", "MT-M1-000001")
    # Bounds 0 and 0: not_found at 1010 >= 1000 is authoritative for P.
    assert kind(policy, obs(Q0), ev(NF_EARLY)) == "REDISPATCH"


def test_ic6_b2_redispatches_on_early_not_found_p_waits():
    assert kind(b2_idempotency_and_readback, obs(LAG30), ev(NF_EARLY)) == "REDISPATCH"
    wait = p_capability_aware(obs(LAG30), ev(NF_EARLY))
    assert (wait.kind, wait.until) == ("WAIT_UNTIL", 1030.0)
    assert kind(p_capability_aware, obs(LAG30), ev(NF_EARLY, now=1030.0)) == "QUERY"
    assert kind(p_capability_aware, obs(LAG30), ev(NF_EARLY, NF_AT_DEADLINE, now=1030.0)) == "REDISPATCH"
    assert kind(p_capability_aware, obs(LAG30), ev(NF_EARLY, FOUND, now=1030.0)) == "ADOPT"


def test_ic7_undeclared_visibility_bound_b2_redispatches_p_holds_or_adopts():
    assert kind(b2_idempotency_and_readback, obs(LAG_UNDECLARED), ev(NF_EARLY)) == "REDISPATCH"
    assert kind(p_capability_aware, obs(LAG_UNDECLARED), ev(NF_EARLY)) == "HOLD"
    assert kind(p_capability_aware, obs(LAG_UNDECLARED), ev(FOUND)) == "ADOPT"


def test_v1_correction_visibility_bound_alone_is_not_authoritative():
    assert kind(p_capability_aware, obs(LAG30_NO_COMPLETION), ev(NF_AT_DEADLINE, now=1030.0)) == "HOLD"


def test_p_holds_when_deadline_is_beyond_horizon():
    late = dataclasses.replace(Q0, visibility_bound_s=100.0)
    assert kind(p_capability_aware, obs(late), ev(NF_EARLY)) == "HOLD"


@pytest.mark.parametrize("policy", list(POLICIES.values()))
def test_policies_are_deterministic_pure_functions(policy):
    o, e = obs(LAG30), ev(NF_EARLY)
    assert policy(o, e) == policy(o, e)


# --- drive_policy: the shared harness/guard stepper ------------------------


def _drive(policy, observation, query_results, *, revalidate=("ALLOW", "test")):
    clock = SimulatedClock(1010.0)
    results = iter(query_results)
    return drive_policy(
        policy,
        observation,
        query=lambda: next(results),
        revalidate=lambda: revalidate,
        clock=clock,
    ), clock


def test_driver_executes_wait_and_query_and_records_evidence():
    from app.integration.maintenance_effect_service import QueryResult

    outcome, clock = _drive(
        p_capability_aware,
        obs(LAG30),
        [QueryResult("not_found", None), QueryResult("found", "MT-M1-000001")],
    )
    assert outcome.action == Action("ADOPT", "query_found", ticket_id="MT-M1-000001")
    assert [s.kind for s in outcome.steps] == ["REVALIDATE", "QUERY", "WAIT_UNTIL", "QUERY", "ADOPT"]
    assert outcome.evidence.queries == (
        QueryEvidence("not_found", None, 1010.0),
        QueryEvidence("found", "MT-M1-000001", 1030.0),
    )
    assert outcome.simulated_wait_s == 20.0
    assert outcome.revalidation_provenance == "test"
    assert outcome.error is None
    assert clock() == 1030.0


def test_driver_rejects_query_when_contract_says_unavailable():
    def always_query(o, e):
        return Action("QUERY")

    outcome, _ = _drive(always_query, obs(UNVERIFIABLE), [])
    assert outcome.action.kind == "HOLD"
    assert outcome.error == "query_rejected_unavailable"


def test_driver_rejects_wait_beyond_horizon():
    def wait_forever(o, e):
        return Action("WAIT_UNTIL", until=5000.0)

    outcome, _ = _drive(wait_forever, obs(Q0), [])
    assert outcome.error == "wait_beyond_horizon"


def test_driver_step_budget_is_an_error_not_a_decision():
    def revalidate_forever(o, e):
        return Action("REVALIDATE")

    outcome, _ = _drive(revalidate_forever, obs(Q0), [])
    assert outcome.error == "step_budget_exhausted"


def test_wait_that_does_not_advance_the_clock_is_an_error():
    def wait_once(o, e):
        return Action("WAIT_UNTIL", until=1030.0)

    clock = SimulatedClock(1010.0)
    outcome = drive_policy(
        wait_once,
        obs(Q0),
        query=lambda: None,
        revalidate=lambda: ("ALLOW", "test"),
        clock=clock,
        wait=lambda seconds: None,  # does not move simulated time
    )
    assert outcome.error == "wait_did_not_advance"
    assert outcome.simulated_wait_s == 0.0


_PREFIX_CASES = [
    (Q0, "missing", 1, ev(governance=None)),
    (Q0, "missing", 1, ev(governance="BLOCK")),
    (Q0, "conflict", 1, ev()),
    (Q0, "failure_received", 1, ev()),
    (DEDUP, "missing", 1, ev()),
    (UNVERIFIABLE, "missing", 1, ev()),
    (LAG30, "missing", 1, ev()),
    (LAG_UNDECLARED, "missing", 1, ev(FOUND)),
    (LAG30, "missing", 2, ev(FOUND)),
]


@pytest.mark.parametrize("contract, ack, attempts, evidence", _PREFIX_CASES)
def test_p_equals_b2_up_to_and_including_the_first_query_result(contract, ack, attempts, evidence):
    o = obs(contract, ack=ack, attempts=attempts)
    assert p_capability_aware(o, evidence) == b2_idempotency_and_readback(o, evidence)
