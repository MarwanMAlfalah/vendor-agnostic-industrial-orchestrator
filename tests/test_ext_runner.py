"""Extension v1 development tests: runner and replay harness on selected protocol cases.

These are simulator-development checks, separate from the formal evaluation run.
"""

import json
from pathlib import Path

import pytest

from app.integration.inflight.runner import run_ext_trial

CASES = Path(__file__).resolve().parents[1] / "research/elcon2027/extension_v1/protocol/cases.json"


@pytest.fixture(scope="module")
def doc():
    return json.loads(CASES.read_text())


def case(doc, cid):
    return next(c for c in doc["cases"] + doc.get("replay_cases", []) if c["id"] == cid)


def test_eager_query_redispatch_creates_late_duplicate_while_bound_aware_policy_adopts(doc, tmp_path):
    b2 = run_ext_trial(case(doc, "E02"), "B2", tmp_path / "b2")["assessment"]
    p = run_ext_trial(case(doc, "E02"), "P", tmp_path / "p")
    assert b2["duplicate_eventual"] and b2["late_duplicate"] and b2["effects_at_decision"] == 1
    assert p["final"] == "ADOPT" and p["assessment"]["completed_single_effect"]
    assert p["simulated_wait_s"] == 20.0


def test_policies_never_receive_fault_schedule_or_ledger(doc, tmp_path):
    r = run_ext_trial(case(doc, "E02"), "P", tmp_path / "p")
    assert {q["status"] for q in r["queries_by_policy"]} == {"not_found", "found"}
    assert r["revalidations"][0]["decision"] == "ALLOW"


def test_never_committing_twin_is_redispatched_after_the_bound(doc, tmp_path):
    r = run_ext_trial(case(doc, "E04"), "P", tmp_path / "p")
    assert r["final"] == "REDISPATCH" and r["assessment"]["eventual_effects"] == 1


def test_assessment_continues_after_hold(doc, tmp_path):
    r = run_ext_trial(case(doc, "E11"), "P", tmp_path / "p")
    assert r["final"] == "HOLD" and r["assessment"]["commits_after_hold"] == 1


def test_real_governance_agent_returns_safe_abort_after_the_change(doc, tmp_path):
    r = run_ext_trial(case(doc, "G01"), "P", tmp_path / "p")
    assert r["revalidations"][0]["decision"] == "SAFE_ABORT"
    assert "capability_unavailable" in r["revalidations"][0]["provenance"]
    assert r["final"] == "HOLD"
    pa = run_ext_trial(case(doc, "G01"), "P_A", tmp_path / "pa")
    assert pa["final"] == "ADOPT" and pa["assessment"]["dispatches_while_invalid"] == 0


def test_provider_commit_check_aborts_pending_request(doc, tmp_path):
    r = run_ext_trial(case(doc, "G03"), "P", tmp_path / "p")
    assert r["assessment"]["eventual_effects"] == 0


def test_two_step_unprotected_replay_repeats_completed_step(doc, tmp_path):
    from app.integration.inflight.pipeline_replay import run_replay_trial

    r = run_replay_trial(case(doc, "R01"), "UNPROTECTED", tmp_path / "u")
    assert r["first_invocation"] == "AcknowledgmentLost"
    assert r["steps"]["s1"]["assessment"]["eventual_effects"] == 2
    g = run_replay_trial(case(doc, "R01"), "P", tmp_path / "g")
    assert g["steps"]["s1"]["guard_recovery_decisions"] == [("ADOPT", "acknowledged_reply")]
    assert g["steps"]["s1"]["assessment"]["eventual_effects"] == 1
    assert g["operation_ids_before_resume"] == g["operation_ids_after_resume"]
