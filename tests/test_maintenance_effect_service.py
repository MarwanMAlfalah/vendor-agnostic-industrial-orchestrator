"""Tests for the fault-injectable maintenance effect service (ElCon-EE 2027).

Ground truth is always read from EffectLedger (the service's committed-effect
ledger), never from what the client observed.
"""

import dataclasses
import hashlib
import os
import sqlite3
import subprocess
import sys
import textwrap
import threading
import time
from contextlib import closing
from pathlib import Path

import pytest

from app.integration.maintenance_effect_service import (
    AcknowledgmentLost,
    ClockRegression,
    EffectLedger,
    FaultSpec,
    MaintenanceClient,
    MaintenanceEffectService,
    QueryResult,
    SimulatedClock,
    SubmitResponse,
    request_fingerprint,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def clock() -> SimulatedClock:
    return SimulatedClock(1000.0)


def _service(tmp_path: Path, clock: SimulatedClock, deduplicate: bool = False):
    db = tmp_path / "effects.db"
    service = MaintenanceEffectService(db, deduplicate=deduplicate, clock=clock)
    return service, service.client(), EffectLedger(db)


# --- 1. successful commit -------------------------------------------------


def test_successful_commit_is_acknowledged_committed_and_queryable(tmp_path, clock):
    service, client, ledger = _service(tmp_path, clock)

    response = client.submit("op-1", machine_id="M1")

    assert response.status == "committed"
    assert response.ticket_id is not None
    assert ledger.dispatch_count("op-1") == 1
    assert ledger.committed_effect_count("op-1") == 1
    assert ledger.ack_delivered_count("op-1") == 1
    assert client.query("op-1") == QueryResult(status="found", ticket_id=response.ticket_id)


# --- 2. failure before commit ---------------------------------------------


def test_failure_before_commit_leaves_ledger_empty(tmp_path, clock):
    service, client, ledger = _service(tmp_path, clock)
    service.schedule_faults([FaultSpec(commit=False, ack_delivered=True)])

    response = client.submit("op-1", machine_id="M1")

    assert response.status == "failed"
    assert response.ticket_id is None
    assert ledger.dispatch_count("op-1") == 1
    assert ledger.committed_effect_count("op-1") == 0
    assert client.query("op-1") == QueryResult(status="not_found", ticket_id=None)


# --- 3. commit followed by lost acknowledgment ----------------------------


def test_commit_with_lost_ack_raises_but_effect_is_committed(tmp_path, clock):
    service, client, ledger = _service(tmp_path, clock)
    service.schedule_faults([FaultSpec(commit=True, ack_delivered=False)])

    with pytest.raises(AcknowledgmentLost):
        client.submit("op-1", machine_id="M1")

    assert ledger.dispatch_count("op-1") == 1
    assert ledger.committed_effect_count("op-1") == 1
    assert ledger.ack_delivered_count("op-1") == 0
    assert client.query("op-1").status == "found"


# --- 4. duplicate request without deduplication ---------------------------


def test_redispatch_without_deduplication_commits_duplicate_effect(tmp_path, clock):
    service, client, ledger = _service(tmp_path, clock, deduplicate=False)
    service.schedule_faults([FaultSpec(commit=True, ack_delivered=False)])

    with pytest.raises(AcknowledgmentLost):
        client.submit("op-1", machine_id="M1")
    second = client.submit("op-1", machine_id="M1")

    assert second.status == "committed"
    assert ledger.dispatch_count("op-1") == 2
    assert ledger.committed_effect_count("op-1") == 2


# --- 5. duplicate request with atomic service-enforced idempotency key ----


def test_redispatch_with_deduplication_commits_once(tmp_path, clock):
    service, client, ledger = _service(tmp_path, clock, deduplicate=True)
    service.schedule_faults([FaultSpec(commit=True, ack_delivered=False)])

    with pytest.raises(AcknowledgmentLost):
        client.submit("op-1", machine_id="M1")
    second = client.submit("op-1", machine_id="M1")

    assert second.status == "deduplicated"
    assert second.ticket_id == client.query("op-1").ticket_id
    assert ledger.dispatch_count("op-1") == 2
    assert ledger.committed_effect_count("op-1") == 1


def test_deduplication_is_atomic_under_concurrent_submits(tmp_path, clock):
    service, client, ledger = _service(tmp_path, clock, deduplicate=True)
    n_threads = 8
    barrier = threading.Barrier(n_threads, timeout=30)
    statuses: list[str] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def worker() -> None:
        try:
            own_client = MaintenanceEffectService(
                tmp_path / "effects.db", deduplicate=True, clock=clock
            ).client()
            barrier.wait()
            status = own_client.submit("op-1", machine_id="M1").status
        except BaseException as exc:  # surfaced in the main thread below
            barrier.abort()
            with lock:
                errors.append(exc)
            return
        with lock:
            statuses.append(status)

    threads = [threading.Thread(target=worker) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert not any(t.is_alive() for t in threads)
    assert errors == []
    assert sorted(statuses) == ["committed"] + ["deduplicated"] * (n_threads - 1)
    assert ledger.dispatch_count("op-1") == n_threads
    assert ledger.committed_effect_count("op-1") == 1


# --- 6. delayed outcome visibility ----------------------------------------


@pytest.mark.parametrize("deduplicate, expected_effects", [(False, 2), (True, 1)])
def test_delayed_visibility_query_cannot_rule_out_commit(
    tmp_path, clock, deduplicate, expected_effects
):
    service, client, ledger = _service(tmp_path, clock, deduplicate=deduplicate)
    service.schedule_faults(
        [FaultSpec(commit=True, ack_delivered=False, visibility_delay=30.0)]
    )

    with pytest.raises(AcknowledgmentLost):
        client.submit("op-1", machine_id="M1")

    clock.advance(10.0)  # read-back inside the visibility window
    assert client.query("op-1") == QueryResult(status="not_found", ticket_id=None)
    assert ledger.committed_effect_count("op-1") == 1  # already committed

    # A verification-only policy that trusts "not_found" re-dispatches.
    client.submit("op-1", machine_id="M1")
    assert ledger.committed_effect_count("op-1") == expected_effects

    clock.advance(30.0)
    assert client.query("op-1").status == "found"


def test_not_found_is_identical_for_uncommitted_and_invisible_commit(tmp_path, clock):
    """The observation alone cannot distinguish 'never executed' from 'pending'."""
    service_a, client_a, ledger_a = _service(tmp_path / "a", clock)
    service_b, client_b, ledger_b = _service(tmp_path / "b", clock)
    service_a.schedule_faults([FaultSpec(commit=False, ack_delivered=False)])
    service_b.schedule_faults(
        [FaultSpec(commit=True, ack_delivered=False, visibility_delay=30.0)]
    )

    with pytest.raises(AcknowledgmentLost) as exc_a:
        client_a.submit("op-1", machine_id="M1")
    with pytest.raises(AcknowledgmentLost) as exc_b:
        client_b.submit("op-1", machine_id="M1")

    assert str(exc_a.value) == str(exc_b.value)
    assert client_a.query("op-1") == client_b.query("op-1")
    assert ledger_a.committed_effect_count("op-1") == 0
    assert ledger_b.committed_effect_count("op-1") == 1


# --- 7. persistence across OS processes -----------------------------------


def _run_in_subprocess(script: str) -> str:
    env = {**os.environ, "LANGSMITH_TRACING": "false", "PYTHONDONTWRITEBYTECODE": "1"}
    completed = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(script)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.strip()


def test_ledger_and_fault_schedule_persist_across_processes(tmp_path):
    db = tmp_path / "effects.db"
    header = f"""
        import os
        from app.integration.maintenance_effect_service import (
            AcknowledgmentLost, EffectLedger, FaultSpec, MaintenanceEffectService,
            SimulatedClock,
        )
        # Each process has its own simulated clock: this test claims ledger and
        # fault-queue persistence only, not shared simulated time.
        service = MaintenanceEffectService(
            {str(db)!r}, deduplicate=True, clock=SimulatedClock(1000.0)
        )
    """
    pid_a = _run_in_subprocess(
        header
        + """
        service.schedule_faults([FaultSpec(commit=True, ack_delivered=False)])
        try:
            service.client().submit("op-1", machine_id="M1")
        except AcknowledgmentLost:
            pass
        print(os.getpid())
        """
    )
    output_b = _run_in_subprocess(
        header
        + """
        client = service.client()
        found = client.query("op-1").status
        resubmit = client.submit("op-1", machine_id="M1").status
        ledger = EffectLedger(service.db_path)
        print(os.getpid(), found, resubmit, ledger.committed_effect_count("op-1"),
              ledger.dispatch_count("op-1"))
        """
    )
    pid_b, found, resubmit, effects, dispatches = output_b.split()

    # Each step ran in its own child process; PIDs may be reused, so only
    # compare each child against this (parent) process.
    assert int(pid_a) != os.getpid()
    assert int(pid_b) != os.getpid()
    assert (found, resubmit, effects, dispatches) == ("found", "deduplicated", "1", "2")


def test_reopening_with_different_dedup_mode_is_rejected(tmp_path, clock):
    MaintenanceEffectService(tmp_path / "effects.db", deduplicate=True, clock=clock)
    with pytest.raises(ValueError, match="deduplicate"):
        MaintenanceEffectService(tmp_path / "effects.db", deduplicate=False, clock=clock)


# --- observation / oracle independence ------------------------------------


def test_client_observations_carry_no_oracle_information(tmp_path, clock):
    service, client, ledger = _service(tmp_path, clock)

    assert {f.name for f in dataclasses.fields(SubmitResponse)} == {
        "operation_id",
        "status",
        "ticket_id",
    }
    assert {f.name for f in dataclasses.fields(QueryResult)} == {"status", "ticket_id"}
    public = {name for name in dir(client) if not name.startswith("_")}
    assert public == {"submit", "query"}
    assert isinstance(client, MaintenanceClient)


def test_ledger_is_read_only(tmp_path, clock):
    service, client, ledger = _service(tmp_path, clock)
    client.submit("op-1", machine_id="M1")

    with closing(ledger._connect()) as conn:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute("DELETE FROM committed_effects")
    assert ledger.committed_effect_count("op-1") == 1


# --- S1: a failed attempt reports the attempt, not the operation ----------


def test_dedup_retry_with_fail_before_commit_fault_reports_existing_effect(tmp_path, clock):
    service, client, ledger = _service(tmp_path, clock, deduplicate=True)
    service.schedule_faults(
        [FaultSpec(commit=True, ack_delivered=False), FaultSpec(commit=False)]
    )
    with pytest.raises(AcknowledgmentLost):
        client.submit("op-1", machine_id="M1")

    retry = client.submit("op-1", machine_id="M1")

    # The existing-operation lookup precedes the commit fault: an already
    # committed operation is answered from the idempotency store.
    assert retry.status == "deduplicated"
    assert retry.ticket_id == client.query("op-1").ticket_id
    assert ledger.committed_effect_count("op-1") == 1
    assert ledger.dispatch_outcomes("op-1") == ["committed", "deduplicated"]


def test_non_dedup_failed_retry_reports_the_attempt_only(tmp_path, clock):
    service, client, ledger = _service(tmp_path, clock, deduplicate=False)
    first = client.submit("op-1", machine_id="M1")
    service.schedule_faults([FaultSpec(commit=False)])

    retry = client.submit("op-1", machine_id="M1")

    assert retry.status == "failed"  # this attempt committed nothing ...
    assert ledger.committed_effect_count("op-1") == 1  # ... the operation did
    assert client.query("op-1").ticket_id == first.ticket_id
    assert ledger.dispatch_outcomes("op-1") == ["committed", "failed"]


# --- S2: operation ID bound to a request fingerprint ----------------------


def test_request_fingerprint_is_canonical_sha256():
    expected = hashlib.sha256(
        b'{"capability":"create_maintenance_ticket","parameters":{"machine_id":"M1","priority":"high"}}'
    ).hexdigest()
    a = request_fingerprint("create_maintenance_ticket", {"machine_id": "M1", "priority": "high"})
    b = request_fingerprint("create_maintenance_ticket", {"priority": "high", "machine_id": "M1"})
    assert a == b == expected
    assert a != request_fingerprint("create_maintenance_ticket", {"machine_id": "M2", "priority": "high"})


@pytest.mark.parametrize(
    "deduplicate, second_status, effects",
    [(False, "committed", 2), (True, "deduplicated", 1)],
)
def test_identical_request_is_not_a_conflict(tmp_path, clock, deduplicate, second_status, effects):
    service, client, ledger = _service(tmp_path, clock, deduplicate=deduplicate)
    client.submit("op-1", machine_id="M1")

    assert client.submit("op-1", machine_id="M1").status == second_status
    assert ledger.committed_effect_count("op-1") == effects


@pytest.mark.parametrize("deduplicate", [False, True])
def test_conflicting_request_is_rejected_without_effect(tmp_path, clock, deduplicate):
    service, client, ledger = _service(tmp_path, clock, deduplicate=deduplicate)
    first = client.submit("op-1", machine_id="M1")

    conflict = client.submit("op-1", machine_id="M2")

    assert conflict == SubmitResponse(operation_id="op-1", status="conflict", ticket_id=None)
    assert ledger.committed_effect_count("op-1") == 1
    assert ledger.dispatch_outcomes("op-1") == ["committed", "conflict"]
    assert client.query("op-1").ticket_id == first.ticket_id


@pytest.mark.parametrize("deduplicate", [False, True])
def test_operation_binding_is_set_by_first_dispatch_even_if_it_failed(
    tmp_path, clock, deduplicate
):
    service, client, ledger = _service(tmp_path, clock, deduplicate=deduplicate)
    service.schedule_faults([FaultSpec(commit=False)])
    assert client.submit("op-1", machine_id="M1").status == "failed"

    assert client.submit("op-1", machine_id="M2").status == "conflict"
    assert client.submit("op-1", machine_id="M1").status == "committed"
    assert ledger.committed_effect_count("op-1") == 1


# --- S8: fault-spec validation ---------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"visibility_delay": float("nan")},
        {"visibility_delay": float("inf")},
        {"visibility_delay": -1.0},
        {"visibility_delay": "5"},
        {"visibility_delay": True},
        {"commit": "false"},
        {"commit": 0},
        {"ack_delivered": 1},
        {"commit": False, "visibility_delay": 5.0},
    ],
)
def test_invalid_fault_spec_is_rejected(kwargs):
    with pytest.raises((TypeError, ValueError)):
        FaultSpec(**kwargs)


# --- S10: files stay inside the designated temporary directory ------------


def _snapshot(root: Path) -> dict[str, tuple[int, int]]:
    """Path -> (size, mtime_ns): detects new files and in-place rewrites."""
    skip = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache"}
    found = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for name in filenames:
            path = os.path.join(dirpath, name)
            stat = os.stat(path)
            found[os.path.relpath(path, root)] = (stat.st_size, stat.st_mtime_ns)
    return found


def test_service_files_stay_inside_temporary_directory(tmp_path, clock, monkeypatch):
    workdir = tmp_path / "cwd"
    workdir.mkdir()
    monkeypatch.chdir(workdir)  # a relative-path write would land here
    repo_before = _snapshot(REPO_ROOT)
    db = tmp_path / "svc" / "effects.db"

    service = MaintenanceEffectService(db, deduplicate=True, clock=clock)
    service.schedule_faults(
        [FaultSpec(commit=True, ack_delivered=False, visibility_delay=5.0), FaultSpec(commit=False)]
    )
    client = service.client()
    with pytest.raises(AcknowledgmentLost):
        client.submit("op-1", machine_id="M1")
    client.submit("op-1", machine_id="M1")
    client.submit("op-1", machine_id="M2")
    client.query("op-1")
    EffectLedger(db).committed_effect_count("op-1")

    assert set(_snapshot(tmp_path)) == {os.path.join("svc", "effects.db")}
    assert _snapshot(REPO_ROOT) == repo_before


# --- S6: simulated clock ---------------------------------------------------


@pytest.mark.parametrize("bad", [-1.0, float("nan"), float("inf")])
def test_simulated_clock_rejects_invalid_advance(bad):
    clock = SimulatedClock(1000.0)
    with pytest.raises(ValueError):
        clock.advance(bad)
    assert clock() == 1000.0


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), "1000", True])
def test_simulated_clock_rejects_invalid_start(bad):
    with pytest.raises((TypeError, ValueError)):
        SimulatedClock(bad)


@pytest.mark.parametrize("wall_clock", [time.time, time.monotonic, lambda: 1000.0])
def test_service_rejects_non_simulated_clock(tmp_path, wall_clock):
    with pytest.raises(TypeError, match="SimulatedClock"):
        MaintenanceEffectService(tmp_path / "effects.db", deduplicate=False, clock=wall_clock)


def test_clock_behind_recorded_time_is_rejected(tmp_path, clock):
    db = tmp_path / "effects.db"
    ahead = MaintenanceEffectService(db, deduplicate=False, clock=clock).client()
    ahead.submit("op-1", machine_id="M1")
    behind = MaintenanceEffectService(db, deduplicate=False, clock=SimulatedClock(900.0)).client()

    with pytest.raises(ClockRegression):
        behind.submit("op-2", machine_id="M1")
    with pytest.raises(ClockRegression):
        behind.query("op-1")
    assert EffectLedger(db).dispatch_count("op-2") == 0


# --- terminal dispatch: the service's completion bound is 0 ---------------


@pytest.mark.parametrize(
    "fault",
    [
        FaultSpec(),
        FaultSpec(commit=False),
        FaultSpec(commit=False, ack_delivered=False),
        FaultSpec(ack_delivered=False),
        FaultSpec(ack_delivered=False, visibility_delay=30.0),
    ],
)
def test_dispatch_is_terminal_when_submit_returns(tmp_path, clock, fault):
    """Contract the protocol declares as completion_bound_s = 0: a dispatch
    commits inside submit() or never. Later time changes visibility only;
    no deferred (late) commit exists in this simulator (F5c not modelled)."""
    service, client, ledger = _service(tmp_path, clock)
    service.schedule_faults([fault])
    try:
        client.submit("op-1", machine_id="M1")
    except AcknowledgmentLost:
        pass
    effects = ledger.committed_effect_count("op-1")
    outcomes = ledger.dispatch_outcomes("op-1")
    assert effects == int(fault.commit)

    for _ in range(3):
        clock.advance(100.0)
        client.query("op-1")
        assert ledger.committed_effect_count("op-1") == effects
        assert ledger.dispatch_outcomes("op-1") == outcomes


# --- database initialisation guards ---------------------------------------


def test_unrelated_existing_database_is_rejected_untouched(tmp_path, clock):
    db = tmp_path / "other.db"
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("CREATE TABLE checkpoints (id INTEGER)")
        conn.commit()

    with pytest.raises(ValueError, match="not a maintenance effect service database"):
        MaintenanceEffectService(db, deduplicate=False, clock=clock)

    with closing(sqlite3.connect(db)) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert tables == {"checkpoints"}


def test_database_without_schema_version_is_rejected(tmp_path, clock):
    db = tmp_path / "old.db"
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("CREATE TABLE service_config (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("INSERT INTO service_config VALUES ('deduplicate', '0')")
        conn.commit()

    with pytest.raises(ValueError, match="schema_version"):
        MaintenanceEffectService(db, deduplicate=False, clock=clock)


@pytest.mark.parametrize("bad", [2, "false", None, 1])
def test_deduplicate_must_be_bool(tmp_path, clock, bad):
    with pytest.raises(TypeError, match="deduplicate"):
        MaintenanceEffectService(tmp_path / "effects.db", deduplicate=bad, clock=clock)
