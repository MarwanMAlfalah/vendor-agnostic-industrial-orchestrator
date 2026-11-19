"""Extension v1: the independent assessor detects deliberately faulty traces.

The assessor reads only service events, ledger effects, the declared authorization timeline
and the workflow's reported outcome. It never imports or calls a recovery policy.
"""

from app.integration.inflight.assessor import assess


def effect(ticket, at, authorized=True, op="wf:s1"):
    return {"operation_id": op, "ticket_id": ticket, "committed_at": at, "authorized_at_commit": authorized}


def ev(kind, t, op="wf:s1", ticket=None, detail=""):
    return {"kind": kind, "time": t, "operation_id": op, "ticket_id": ticket, "detail": detail}


BASE = dict(operation_id="wf:s1", decision_time=1010.0, invalid_from=None, pending_at_horizon=[])


def test_clean_adoption():
    r = assess(effects=[effect("T-0001", 1005.0)], events=[ev("submit", 1000.0), ev("query", 1010.0, ticket="T-0001")],
               outcome={"final": "ADOPT", "ticket_id": "T-0001"}, **BASE)
    assert r["eventual_effects"] == 1 and not r["duplicate_eventual"]
    assert r["completed_single_effect"] and r["adoption_consistent"]


def test_detects_late_duplicate_not_visible_at_decision():
    r = assess(effects=[effect("T-0002", 1010.0), effect("T-0001", 1020.0)],
               events=[ev("submit", 1000.0), ev("submit", 1010.0)],
               outcome={"final": "REDISPATCH", "ticket_id": "T-0002"}, **BASE)
    assert r["effects_at_decision"] == 1
    assert r["duplicate_eventual"] and r["late_duplicate"]
    assert not r["completed_single_effect"]


def test_detects_missing_effect_when_workflow_claims_completion():
    r = assess(effects=[], events=[ev("submit", 1000.0)], outcome={"final": "ADOPT", "ticket_id": "T-0001"}, **BASE)
    assert r["missing_effect"] and not r["adoption_consistent"] and not r["completed_single_effect"]


def test_detects_incorrect_adoption_ticket():
    r = assess(effects=[effect("T-0001", 1005.0)], events=[ev("submit", 1000.0)],
               outcome={"final": "ADOPT", "ticket_id": "T-9999"}, **BASE)
    assert not r["adoption_consistent"] and not r["completed_single_effect"]


def test_detects_dispatch_after_authorization_became_invalid():
    base = dict(BASE, invalid_from=1005.0)
    r = assess(effects=[effect("T-0001", 1000.0), effect("T-0002", 1010.0, authorized=False)],
               events=[ev("submit", 1000.0), ev("submit", 1010.0)],
               outcome={"final": "REDISPATCH", "ticket_id": "T-0002"}, **base)
    assert r["dispatches_while_invalid"] == 1
    assert r["effects_while_invalid"] == 1


def test_detects_commit_after_hold_and_censoring():
    base = dict(BASE, pending_at_horizon=["wf:s1"])
    r = assess(effects=[effect("T-0001", 1040.0)], events=[ev("submit", 1000.0)],
               outcome={"final": "HOLD", "ticket_id": None}, **base)
    assert r["commits_after_hold"] == 1
    assert r["censored"] and r["eventual_status"] == "censored"
    assert r["workflow_outcome"] == "held"
