"""Extension v1 (ElCon-EE 2027): semantics of the in-flight effect simulator.

Acceptance, commit, acknowledgment and query visibility are distinct events.
Times are whole simulated seconds held in floats (exact for these values).
"""

import pytest

from app.integration.inflight.service import (
    AuthorizationTimeline,
    InFlightEffectService,
    RequestFault,
)
from app.integration.maintenance_effect_service import AcknowledgmentLost, SimulatedClock

OP = "wf-1:step-1"


def make(tmp_path, *faults, dedup=False, auth_check="none", invalid_from=None, start=1000.0):
    clock = SimulatedClock(start)
    svc = InFlightEffectService(
        tmp_path / "effects.db",
        clock=clock,
        deduplicate=dedup,
        auth_check=auth_check,
        authorization=AuthorizationTimeline(invalid_from=invalid_from),
    )
    svc.schedule(list(faults))
    return clock, svc, svc.client()


def lost(commit_after, visibility_after=0.0):
    return RequestFault(commit_after=commit_after, visibility_after=visibility_after, ack_delivered=False)


def test_pending_request_commits_after_recovery_starts(tmp_path):
    clock, svc, client = make(tmp_path, lost(20.0))
    with pytest.raises(AcknowledgmentLost):
        client.submit(OP, "M-1")
    clock.advance(10.0)  # 1010: resume, still pending
    assert client.query(OP).status == "not_found"
    assert svc.effects(OP) == []
    clock.advance(10.0)  # 1020: commit event is due
    assert client.query(OP).status == "found"
    assert [e.committed_at for e in svc.effects(OP)] == [1020.0]


def test_query_does_not_cause_commit_and_boundaries_are_inclusive(tmp_path):
    clock, svc, client = make(tmp_path, lost(20.0, visibility_after=10.0))
    with pytest.raises(AcknowledgmentLost):
        client.submit(OP, "M-1")
    clock.advance(19.0)  # 1019
    assert client.query(OP).status == "not_found"
    clock.advance(1.0)  # 1020: committed but invisible until 1030
    assert client.query(OP).status == "not_found"
    assert len(svc.effects(OP)) == 1
    clock.advance(9.0)  # 1029
    assert client.query(OP).status == "not_found"
    clock.advance(1.0)  # 1030 = commit + lambda: a query at this instant sees it
    assert client.query(OP).status == "found"


def test_redispatch_does_not_cancel_pending_original(tmp_path):
    clock, svc, client = make(tmp_path, lost(20.0))
    with pytest.raises(AcknowledgmentLost):
        client.submit(OP, "M-1")
    clock.advance(10.0)
    reply = client.submit(OP, "M-1")  # default fault for later attempts: commit now, ack delivered
    assert reply.status == "committed"
    svc.drain(until=2000.0)
    assert len(svc.effects(OP)) == 2  # the original still commits at 1020


def test_accepted_request_that_never_commits(tmp_path):
    clock, svc, client = make(tmp_path, RequestFault(commit_after=None, abort_after=30.0, ack_delivered=False))
    with pytest.raises(AcknowledgmentLost):
        client.submit(OP, "M-1")
    report = svc.drain(until=2000.0)
    assert svc.effects(OP) == []
    assert report.pending_at_horizon == []
    assert [e.kind for e in svc.events() if e.kind == "abort"] == ["abort"]


def test_unresolved_request_is_censored_not_absent(tmp_path):
    clock, svc, client = make(tmp_path, RequestFault(commit_after=None, abort_after=None, ack_delivered=False))
    with pytest.raises(AcknowledgmentLost):
        client.submit(OP, "M-1")
    report = svc.drain(until=1600.0)
    assert report.pending_at_horizon == [OP]


def test_deduplication_suppresses_retry_of_pending_request(tmp_path):
    clock, svc, client = make(tmp_path, lost(20.0), dedup=True)
    with pytest.raises(AcknowledgmentLost):
        client.submit(OP, "M-1")
    clock.advance(10.0)
    reply = client.submit(OP, "M-1")
    assert reply.status == "deduplicated"
    svc.drain(until=2000.0)
    assert len(svc.effects(OP)) == 1


def test_authorization_checked_at_commit_aborts_pending_request(tmp_path):
    clock, svc, client = make(tmp_path, lost(20.0), auth_check="commit", invalid_from=1005.0)
    with pytest.raises(AcknowledgmentLost):
        client.submit(OP, "M-1")
    svc.drain(until=2000.0)
    assert svc.effects(OP) == []
    assert any(e.kind == "abort_unauthorized_at_commit" for e in svc.events())


def test_authorization_checked_only_at_acceptance_lets_pending_request_commit(tmp_path):
    clock, svc, client = make(tmp_path, lost(20.0), auth_check="acceptance", invalid_from=1005.0)
    with pytest.raises(AcknowledgmentLost):
        client.submit(OP, "M-1")
    clock.advance(10.0)
    assert client.submit(OP, "M-1").status == "failed"  # new request rejected at acceptance
    svc.drain(until=2000.0)
    assert [e.committed_at for e in svc.effects(OP)] == [1020.0]
    assert [e.authorized_at_commit for e in svc.effects(OP)] == [False]


def test_no_provider_check_accepts_new_request_while_invalid(tmp_path):
    clock, svc, client = make(tmp_path, lost(0.0), auth_check="none", invalid_from=1005.0)
    with pytest.raises(AcknowledgmentLost):
        client.submit(OP, "M-1")
    clock.advance(10.0)
    assert client.submit(OP, "M-1").status == "committed"
    assert [e.authorized_at_commit for e in svc.effects(OP)] == [True, False]


def test_request_fingerprint_conflict(tmp_path):
    clock, svc, client = make(tmp_path, lost(0.0))
    with pytest.raises(AcknowledgmentLost):
        client.submit(OP, "M-1")
    assert client.submit(OP, "M-2").status == "conflict"


def test_event_log_orders_same_timestamp_commit_before_visibility(tmp_path):
    clock, svc, client = make(tmp_path, lost(20.0, visibility_after=0.0))
    with pytest.raises(AcknowledgmentLost):
        client.submit(OP, "M-1")
    svc.drain(until=2000.0)
    kinds = [e.kind for e in svc.events() if e.time == 1020.0]
    assert kinds == ["commit", "visible"]


def test_fault_validation_rejects_delivered_ack_for_pending_request():
    with pytest.raises(ValueError):
        RequestFault(commit_after=5.0, ack_delivered=True)
