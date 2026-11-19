"""Internal-consistency checks for the pre-specified ElCon-EE 2027 oracle.

The oracle must be a function of policy-visible information only (rule R7):
valid actions are rebuilt here from the observation and declared contract,
never from hidden state. Hidden state is used only to derive eligibility
(which evidence is obtainable) and denominators.
"""

import json
from collections import defaultdict
from pathlib import Path

import pytest

from app.integration.maintenance_effect_service import (
    AcknowledgmentLost,
    EffectLedger,
    FaultSpec,
    MaintenanceEffectService,
    SimulatedClock,
)

CONTRACT_FIELDS = {
    "deduplicates_by_operation_id",
    "binds_request_fingerprint",
    "outcome_query",
    "visibility_bound_s",
    "completion_bound_s",
    "failure_response_scope",
}

ORACLE_PATH = (
    Path(__file__).resolve().parents[1] / "research" / "elcon2027" / "protocol" / "oracle_table.json"
)


@pytest.fixture(scope="module")
def oracle() -> dict:
    return json.loads(ORACLE_PATH.read_text())


def _all_cases(oracle):
    return oracle["cases"] + oracle["stress_cases"]


def _valid(case) -> set[tuple[str, str]]:
    entries = case.get("valid_actions", case.get("per_decision_valid_actions"))
    return {(e["action"], e["evidence"]) for e in entries}


def _visible(case):
    contract = case["declared_contract"]
    seen = case["visible_at_resume"]
    return {
        "dedup": contract["deduplicates_by_operation_id"] is True,
        "query": contract["outcome_query"] == "available",
        "bound": contract["visibility_bound_s"],
        "completion": contract["completion_bound_s"],
        "failure_sole": seen["ack_state"] == "failure_received" and seen["attempts"] == 1,
        "last_dispatch_at": seen["last_dispatch_at"],
    }


def _rule_valid_set(case) -> set[tuple[str, str]]:
    """R1-R6 applied to policy-visible information only."""
    v = _visible(case)
    valid = set()
    if v["query"]:
        valid.add(("ADOPT", "query_found"))  # R1
    if v["dedup"]:
        valid.add(("REDISPATCH", "dedup_contract"))  # R4
    if v["failure_sole"]:
        valid.add(("REDISPATCH", "failure_response_sole_attempt"))  # R2
    # A visibility bound alone never makes not_found authoritative: a request
    # could still commit later unless a completion bound is also declared.
    both_bounds = v["bound"] is not None and v["completion"] is not None
    if v["query"] and both_bounds:
        valid.add(("REDISPATCH", "query_not_found_authoritative"))  # R2
    if not v["dedup"] and not v["failure_sole"] and (not v["query"] or not both_bounds):
        valid.add(("HOLD", "any"))  # R6
    return valid


def _obtainable(case, horizon_end) -> dict[str, bool]:
    v = _visible(case)
    hidden = case["hidden_state"]
    effects = hidden["committed_effects_at_resume"]
    visible_from = hidden["visible_from"]
    return {
        "any": True,
        "dedup_contract": v["dedup"],
        "failure_response_sole_attempt": v["failure_sole"],
        "query_found": v["query"] and effects >= 1 and visible_from <= horizon_end,
        "query_not_found_authoritative": v["query"]
        and v["bound"] is not None
        and v["completion"] is not None
        and effects == 0
        and v["last_dispatch_at"] + v["completion"] + v["bound"] <= horizon_end,
    }


def test_case_ids_are_unique(oracle):
    ids = [c["id"] for c in _all_cases(oracle)]
    assert len(ids) == len(set(ids))


def test_vocabulary_is_closed(oracle):
    actions = set(oracle["actions"]["terminal"])
    predicates = set(oracle["evidence_predicates"]) - {"note"}
    for case in _all_cases(oracle):
        for action, evidence in _valid(case):
            assert action in actions, case["id"]
            assert evidence in predicates, case["id"]


def test_valid_actions_follow_rules_from_visible_information_only(oracle):
    for case in _all_cases(oracle):
        assert _valid(case) == _rule_valid_set(case), case["id"]


def test_same_information_class_means_same_observation_and_same_valid_actions(oracle):
    groups = defaultdict(list)
    for case in _all_cases(oracle):
        groups[case["information_class"]].append(case)
    assert set(groups) == set(oracle["information_classes"])
    for ic, members in groups.items():
        first = members[0]
        for other in members[1:]:
            assert other["declared_contract"] == first["declared_contract"], ic
            assert other["visible_at_resume"] == first["visible_at_resume"], ic
            assert _valid(other) == _valid(first), ic


def test_eligibility_is_derived_from_hidden_state_and_rules(oracle):
    horizon_end = oracle["time_model"]["horizon_end"]
    for case in oracle["cases"]:
        got = case["eligibility"]
        ok = _obtainable(case, horizon_end)
        valid = _valid(case)
        hold_valid = ("HOLD", "any") in valid
        effects = case["hidden_state"]["committed_effects_at_resume"]
        hindsight = effects == 0 or ok["query_found"] or ok["dedup_contract"]
        safely = any(ok[evidence] for action, evidence in valid if action != "HOLD")
        if not hold_valid:
            hold_class = "unnecessary"
        elif valid == {("HOLD", "any")}:
            hold_class = "information_forced" if hindsight else "required"
        else:
            hold_class = "acceptable"
        assert got == {
            "hindsight_recoverable": hindsight,
            "safely_recoverable": safely,
            "hold_valid": hold_valid,
            "hold_class": hold_class,
            "unnecessary_hold_eligible": not hold_valid,
        }, case["id"]


def test_denominators_match_case_table(oracle):
    cases = oracle["cases"]
    elig = [c["eligibility"] for c in cases]
    assert all("eligibility" not in c for c in oracle["stress_cases"])
    assert oracle["denominators"] == {
        "policies": 4,
        "primary_cases": len(cases),
        "stress_cases": len(oracle["stress_cases"]),
        "hindsight_recoverable_cases": sum(e["hindsight_recoverable"] for e in elig),
        "safely_recoverable_cases": sum(e["safely_recoverable"] for e in elig),
        "hold_required_cases": sum(e["hold_class"] in {"required", "information_forced"} for e in elig),
        "unnecessary_hold_eligible_cases": sum(e["unnecessary_hold_eligible"] for e in elig),
        "information_forced_hold_cases": sum(e["hold_class"] == "information_forced" for e in elig),
    }
    assert all(c["set"] == "primary" for c in cases)
    assert all(c["set"] == "stress" for c in oracle["stress_cases"])


def test_fault_schedules_are_implemented_and_contracts_truthful(oracle):
    t0 = oracle["time_model"]["initial_dispatch_at"]
    for case in _all_cases(oracle):
        harness = case["harness_only"]
        faults = [FaultSpec(**entry) for entry in harness["fault_schedule"]]
        contract = case["declared_contract"]
        assert contract["deduplicates_by_operation_id"] == harness["service_deduplicate"], case["id"]
        if contract["visibility_bound_s"] is not None:
            assert all(f.visibility_delay <= contract["visibility_bound_s"] for f in faults)
        if contract["outcome_query"] != "available":
            assert contract["visibility_bound_s"] is None, case["id"]
        # The simulator commits inside the dispatch transaction or never
        # (test_dispatch_is_terminal_when_submit_returns), so any declared
        # completion bound >= 0 is truthful; an undeclared one is allowed.
        completion = contract["completion_bound_s"]
        assert completion is None or completion >= 0, case["id"]
        first = faults[0]
        hidden = case["hidden_state"]
        assert hidden["committed_effects_at_resume"] == int(first.commit), case["id"]
        expected_visible = t0 + first.visibility_delay if first.commit else None
        assert hidden["visible_from"] == expected_visible, case["id"]
        if not first.ack_delivered:
            expected_ack = "missing"
        else:
            expected_ack = "received" if first.commit else "failure_received"
        assert case["visible_at_resume"]["ack_state"] == expected_ack, case["id"]


def test_every_contract_declares_every_field(oracle):
    # R5 (worst-case reading of missing fields) is a policy-time rule; the
    # pre-specified matrix itself must leave nothing implicit.
    for case in _all_cases(oracle):
        assert set(case["declared_contract"]) == CONTRACT_FIELDS, case["id"]


def test_each_schedule_has_one_fault_for_the_initial_dispatch(oracle):
    # The service's fault queue is global FIFO (S7). With exactly one entry,
    # consumed by the initial dispatch, no recovery dispatch can receive it.
    for case in _all_cases(oracle):
        assert len(case["harness_only"]["fault_schedule"]) == 1, case["id"]


def test_hidden_state_matches_the_service_ledger(oracle, tmp_path):
    """Ground truth comes from executing the schedule, not from the JSON alone."""
    t0 = oracle["time_model"]["initial_dispatch_at"]
    resume = oracle["time_model"]["resume_at"]
    for case in _all_cases(oracle):
        harness = case["harness_only"]
        db = tmp_path / f"{case['id']}.db"
        clock = SimulatedClock(t0)
        service = MaintenanceEffectService(
            db, deduplicate=harness["service_deduplicate"], clock=clock
        )
        service.schedule_faults([FaultSpec(**f) for f in harness["fault_schedule"]])
        client = service.client()
        try:
            reply = client.submit("wf:step", machine_id=oracle["operation"]["machine_id"])
            ack_state = "received" if reply.status == "committed" else "failure_received"
        except AcknowledgmentLost:
            ack_state = "missing"
        ledger = EffectLedger(db)
        hidden = case["hidden_state"]
        assert ack_state == case["visible_at_resume"]["ack_state"], case["id"]
        assert ledger.committed_effect_count("wf:step") == hidden["committed_effects_at_resume"]
        assert ledger.dispatch_count("wf:step") == case["visible_at_resume"]["attempts"]
        clock.advance(resume - t0)
        visible_from = hidden["visible_from"]
        expected_at_resume = (
            "found" if visible_from is not None and visible_from <= resume else "not_found"
        )
        assert client.query("wf:step").status == expected_at_resume, case["id"]
        if visible_from is not None and visible_from > resume:
            clock.advance(visible_from - resume - 0.001)
            assert client.query("wf:step").status == "not_found", case["id"]
            clock.advance(0.001)
            assert client.query("wf:step").status == "found", case["id"]


def test_unimplemented_faults_are_declared_deferred(oracle):
    classes = {c["fault_class"] for c in _all_cases(oracle)}
    assert not any(c.startswith(("F5c", "F7", "F8")) for c in classes)
    assert {"F5c-late-commit", "F7", "F8"} <= set(oracle["deferred_not_implemented"])


def test_protocol_is_frozen_v1(oracle):
    assert oracle["protocol_version"] == "1.0"
    assert oracle["status"].startswith("FROZEN")
    assert oracle["evidence_label"] == "In-repository, service-level deterministic simulation"


def test_primary_trial_count_and_metric_eligibility(oracle):
    d = oracle["denominators"]
    m = oracle["metrics"]
    k = d["policies"]
    assert d["primary_cases"] * k == m["primary_trials"] == 52
    expected = {
        "duplicate_effect_rate": d["primary_cases"],
        "correct_recovery_decision_rate": d["primary_cases"],
        "recovery_completion_rate": d["safely_recoverable_cases"],
        "hindsight_completion_rate": d["hindsight_recoverable_cases"],
        "unnecessary_hold_rate": d["unnecessary_hold_eligible_cases"],
        "required_hold_compliance": d["hold_required_cases"],
        "information_forced_holds": d["information_forced_hold_cases"],
    }
    for name, cases_per_policy in expected.items():
        assert m["denominators_per_policy"][name] == cases_per_policy, name
    unauthorized = m["unauthorized_effect_rate"]
    assert unauthorized["eligible_trials"] == 0
    assert unauthorized["report_as"] == "not evaluated"
    assert m["replays"]["k"] == 5
    assert m["replays"]["are_independent_samples"] is False


def test_c05_and_c06_are_observationally_indistinguishable(oracle):
    c05, c06 = (next(c for c in oracle["cases"] if c["id"] == i) for i in ("C05", "C06"))
    assert c05["information_class"] == c06["information_class"]
    assert c05["declared_contract"] == c06["declared_contract"]
    assert c05["visible_at_resume"] == c06["visible_at_resume"]
    assert _valid(c05) == _valid(c06) == {("HOLD", "any")}
    assert c05["hidden_state"] != c06["hidden_state"]
