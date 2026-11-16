"""Extension v1: reference policy R_LI and variant P_A (originals B0/B1/B2/P are untouched)."""

from app.integration.inflight.policies import (
    EXT_POLICIES,
    p_adopt_under_non_allow,
    r_li_wait_then_verify,
)
from app.integration.recovery_policies import (
    POLICIES,
    AckState,
    CapabilityContract,
    DispatchState,
    Evidence,
    Observation,
    QueryEvidence,
)


def obs(cb=30.0, vb=0.0, dedup=False, query="available", horizon_end=1070.0):
    return Observation(
        workflow_id="wf", step_id="s1", operation_id="wf:s1", capability="create_maintenance_ticket",
        adapter="maintenance_effect_adapter", request={"machine_id": "M-1"},
        dispatch=DispatchState(1, 1000.0), ack=AckState("missing", None, None),
        contract=CapabilityContract(dedup, True, query, vb, cb, "attempt"),
        approval={}, preconditions={}, resume_at=1010.0, horizon_end=horizon_end,
    )


def test_original_policies_are_reused_unchanged():
    for pid in ("B0", "B1", "B2", "P"):
        assert EXT_POLICIES[pid] is POLICIES[pid]


def test_r_li_waits_before_its_first_query():
    o = obs()
    assert r_li_wait_then_verify(o, Evidence(None, (), 1010.0)).kind == "REVALIDATE"
    a = r_li_wait_then_verify(o, Evidence("ALLOW", (), 1010.0))
    assert (a.kind, a.until) == ("WAIT_UNTIL", 1030.0)
    assert r_li_wait_then_verify(o, Evidence("ALLOW", (), 1030.0)).kind == "QUERY"
    nf = Evidence("ALLOW", (QueryEvidence("not_found", None, 1030.0),), 1030.0)
    assert r_li_wait_then_verify(o, nf).kind == "REDISPATCH"
    found = Evidence("ALLOW", (QueryEvidence("found", "T-1", 1030.0),), 1030.0)
    assert r_li_wait_then_verify(o, found).kind == "ADOPT"


def test_r_li_holds_without_declared_bounds_or_beyond_horizon():
    assert r_li_wait_then_verify(obs(cb=None), Evidence("ALLOW", (), 1010.0)).kind == "HOLD"
    assert r_li_wait_then_verify(obs(cb=90.0), Evidence("ALLOW", (), 1010.0)).kind == "HOLD"


def test_p_a_adopts_visible_effect_under_non_allow_but_never_dispatches():
    o = obs()
    assert p_adopt_under_non_allow(o, Evidence("SAFE_ABORT", (), 1010.0)).kind == "QUERY"
    found = Evidence("SAFE_ABORT", (QueryEvidence("found", "T-1", 1010.0),), 1010.0)
    assert p_adopt_under_non_allow(o, found).kind == "ADOPT"
    nf = Evidence("SAFE_ABORT", (QueryEvidence("not_found", None, 1010.0),), 1010.0)
    assert p_adopt_under_non_allow(o, nf).kind == "HOLD"


def test_p_a_equals_p_when_governance_allows():
    o = obs()
    for ev in (Evidence(None, (), 1010.0), Evidence("ALLOW", (), 1010.0),
               Evidence("ALLOW", (QueryEvidence("not_found", None, 1010.0),), 1010.0)):
        assert p_adopt_under_non_allow(o, ev) == POLICIES["P"](o, ev)
