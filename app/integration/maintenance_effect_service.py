"""Stateful, fault-injectable maintenance effect service (ElCon-EE 2027, opt-in).

Simulator only. It is not wired into the planner, governance, execution agents,
LangGraph runtime, or existing adapters.

Three roles, kept separate on purpose:

* ``MaintenanceEffectService`` - harness side. Owns the SQLite database and the
  fault schedule. Policies must not receive it.
* ``MaintenanceClient`` - the caller's interface: ``submit`` and ``query``. It
  returns only what a real caller would see (an acknowledgment, an error
  response, a timeout, or a query result). In the recovery study the harness
  holds it; policies receive only an observation and harness-recorded evidence.
* ``EffectLedger`` - the oracle. A read-only view of what the service actually
  dispatched and committed. Experimental ground truth comes from here only.

Four things are recorded separately for each request:

* dispatched - a row in ``dispatch_log`` (the request reached the service);
* committed - a row in ``committed_effects`` (the external effect happened);
* acknowledged - ``dispatch_log.ack_delivered`` (the caller received the reply);
* observable - ``committed_effects.visible_at`` <= now (``query`` can see it).

A ``not_found`` query result therefore does not mean the operation never ran:
the effect may be committed but not yet visible.

``operation_id`` is the client-supplied idempotency key. Its first dispatch binds
it to a request fingerprint (``request_fingerprint``) in both configurations;
a later dispatch with the same ID and a different fingerprint is answered
``conflict`` and commits nothing. With ``deduplicate=True`` the service also
enforces at most one committed effect per ID. Each dispatch runs in one
``BEGIN IMMEDIATE`` transaction, in this order: consume the next fault, check
the fingerprint binding, look up an existing effect (deduplication only), then
apply the commit fault. A UNIQUE index on ``committed_effects.dedup_key`` is a
backstop.

All timestamps are simulated seconds from an injected ``SimulatedClock``; wall
clocks are rejected, so simulated and real time never mix in one database.

A ``SubmitResponse`` describes the current attempt only, not the logical
operation: ``failed`` means *this attempt* committed nothing; an earlier attempt
may have committed. ``deduplicated`` means this attempt committed nothing
because the operation already has an effect, whose ticket is returned.
"""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from collections.abc import Iterable, Mapping
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

CAPABILITY = "create_maintenance_ticket"
SCHEMA_VERSION = "2"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS service_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS operations (
    operation_id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    first_seen_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS fault_schedule (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    commit_effect INTEGER NOT NULL,
    ack_delivered INTEGER NOT NULL,
    visibility_delay REAL NOT NULL,
    consumed INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS committed_effects (
    effect_id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id TEXT NOT NULL,
    machine_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    ticket_id TEXT,
    committed_at REAL NOT NULL,
    visible_at REAL NOT NULL,
    dedup_key TEXT UNIQUE
);
CREATE TABLE IF NOT EXISTS dispatch_log (
    dispatch_id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id TEXT NOT NULL,
    machine_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    received_at REAL NOT NULL,
    outcome TEXT NOT NULL,
    ack_delivered INTEGER NOT NULL,
    effect_id INTEGER REFERENCES committed_effects(effect_id)
);
"""


class SimulatedClock:
    """Explicit simulated time in seconds. All service timestamps use it.

    Share one instance between every service/client of a trial. Separate OS
    processes cannot share an instance, so simulated-time behaviour across
    processes is out of scope. ``ClockRegression`` detects a clock that is
    behind the latest recorded *dispatch* time; query times are not recorded,
    so a clock behind an earlier query is not detected. One shared clock per
    trial is therefore required, not merely checked.
    """

    def __init__(self, start: float = 0.0) -> None:
        if isinstance(start, bool) or not isinstance(start, (int, float)):
            raise TypeError("start must be a real number")
        if not math.isfinite(start):
            raise ValueError("start must be finite")
        self._now = float(start)

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
            raise TypeError("seconds must be a real number")
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError("seconds must be finite and >= 0")
        self._now += float(seconds)


class ClockRegression(ValueError):
    """The caller's clock is behind simulated time already recorded."""


class AcknowledgmentLost(Exception):
    """The caller got no reply (e.g. a timeout).

    The message is the same whatever happened inside the service, so it carries
    no information about whether the effect was committed.
    """

    def __init__(self, operation_id: str) -> None:
        super().__init__(f"no acknowledgment received for operation {operation_id}")
        self.operation_id = operation_id


@dataclass(frozen=True)
class FaultSpec:
    """Fault applied to one dispatch, in schedule order.

    commit: whether the external effect is committed.
    ack_delivered: whether the caller receives the reply.
    visibility_delay: seconds (on the injected clock) before ``query`` can see
        a committed effect.
    """

    commit: bool = True
    ack_delivered: bool = True
    visibility_delay: float = 0.0

    def __post_init__(self) -> None:
        for name in ("commit", "ack_delivered"):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be a bool")
        delay = self.visibility_delay
        if isinstance(delay, bool) or not isinstance(delay, (int, float)):
            raise TypeError("visibility_delay must be a real number")
        if not math.isfinite(delay) or delay < 0:
            raise ValueError("visibility_delay must be finite and >= 0")
        if not self.commit and delay != 0:
            raise ValueError("visibility_delay applies only to a committing fault")
        object.__setattr__(self, "visibility_delay", float(delay))


def request_fingerprint(capability: str, parameters: Mapping[str, object]) -> str:
    """SHA-256 of the canonical JSON of the capability and its parameters."""
    canonical = json.dumps(
        {"capability": capability, "parameters": dict(parameters)},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SubmitResponse:
    """Delivered reply for the current attempt.

    status: 'committed' | 'deduplicated' | 'failed' | 'conflict'.
    """

    operation_id: str
    status: str
    ticket_id: str | None


@dataclass(frozen=True)
class QueryResult:
    """status: 'found' | 'not_found'. 'not_found' is not proof of absence."""

    status: str
    ticket_id: str | None


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30.0, isolation_level=None)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


class MaintenanceEffectService:
    """Harness-side service. Each call opens its own connection, so separate
    instances, threads, and OS processes can share one database file."""

    def __init__(
        self,
        db_path: str | Path,
        *,
        deduplicate: bool,
        clock: SimulatedClock,
    ) -> None:
        if not isinstance(clock, SimulatedClock):
            raise TypeError("clock must be a SimulatedClock; wall-clock time is not supported")
        if not isinstance(deduplicate, bool):
            raise TypeError("deduplicate must be a bool")
        self.db_path = Path(db_path)
        self.deduplicate = deduplicate
        self._clock = clock
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(_connect(self.db_path)) as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                self._open_or_create(conn, deduplicate)
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")  # also undoes any DDL: nothing is stamped
                raise

    @staticmethod
    def _open_or_create(conn: sqlite3.Connection, deduplicate: bool) -> None:
        tables = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        if not tables:
            for statement in _SCHEMA.split(";"):
                if statement.strip():
                    conn.execute(statement)
            conn.executemany(
                "INSERT INTO service_config(key, value) VALUES (?, ?)",
                [("deduplicate", str(int(deduplicate))), ("schema_version", SCHEMA_VERSION)],
            )
            return
        if "service_config" not in tables:
            raise ValueError("not a maintenance effect service database")
        config = dict(conn.execute("SELECT key, value FROM service_config"))
        if config.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(
                f"database schema_version={config.get('schema_version')}, expected {SCHEMA_VERSION}"
            )
        stored = config.get("deduplicate")
        if stored != str(int(deduplicate)):
            raise ValueError(
                f"database was created with deduplicate={stored == '1'}; "
                f"refusing to reopen with deduplicate={deduplicate}"
            )

    def client(self) -> MaintenanceClient:
        return MaintenanceClient(self)

    def schedule_faults(self, faults: Iterable[FaultSpec]) -> None:
        """Queue faults; dispatch n consumes the n-th unconsumed entry.
        Dispatches with no entry left behave as FaultSpec() (normal success)."""
        with closing(_connect(self.db_path)) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.executemany(
                "INSERT INTO fault_schedule(commit_effect, ack_delivered, visibility_delay)"
                " VALUES (?, ?, ?)",
                [(int(f.commit), int(f.ack_delivered), f.visibility_delay) for f in faults],
            )
            conn.execute("COMMIT")

    def _submit(self, operation_id: str, machine_id: str) -> SubmitResponse:
        with closing(_connect(self.db_path)) as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                now = self._now(conn)  # read under the write lock
                fault = self._consume_fault(conn)
                fingerprint = request_fingerprint(CAPABILITY, {"machine_id": machine_id})
                effect_id: int | None = None
                ticket_id: str | None = None
                bound = conn.execute(
                    "SELECT fingerprint FROM operations WHERE operation_id = ?", (operation_id,)
                ).fetchone()
                if bound is None:
                    conn.execute(
                        "INSERT INTO operations(operation_id, fingerprint, first_seen_at)"
                        " VALUES (?, ?, ?)",
                        (operation_id, fingerprint, now),
                    )
                existing = None
                if self.deduplicate:
                    existing = conn.execute(
                        "SELECT effect_id, ticket_id FROM committed_effects WHERE dedup_key = ?",
                        (operation_id,),
                    ).fetchone()
                if bound is not None and bound[0] != fingerprint:
                    outcome = "conflict"
                elif existing is not None:
                    outcome = "deduplicated"
                    effect_id, ticket_id = existing
                elif not fault.commit:
                    outcome = "failed"
                else:
                    cursor = conn.execute(
                        "INSERT INTO committed_effects(operation_id, machine_id, fingerprint,"
                        " committed_at, visible_at, dedup_key) VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            operation_id,
                            machine_id,
                            fingerprint,
                            now,
                            now + fault.visibility_delay,
                            operation_id if self.deduplicate else None,
                        ),
                    )
                    outcome = "committed"
                    effect_id = cursor.lastrowid
                    ticket_id = f"MT-{machine_id}-{effect_id:06d}"
                    conn.execute(
                        "UPDATE committed_effects SET ticket_id = ? WHERE effect_id = ?",
                        (ticket_id, effect_id),
                    )
                conn.execute(
                    "INSERT INTO dispatch_log(operation_id, machine_id, fingerprint, received_at,"
                    " outcome, ack_delivered, effect_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        operation_id,
                        machine_id,
                        fingerprint,
                        now,
                        outcome,
                        int(fault.ack_delivered),
                        effect_id,
                    ),
                )
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        if not fault.ack_delivered:
            raise AcknowledgmentLost(operation_id)
        return SubmitResponse(operation_id=operation_id, status=outcome, ticket_id=ticket_id)

    @staticmethod
    def _consume_fault(conn: sqlite3.Connection) -> FaultSpec:
        row = conn.execute(
            "SELECT seq, commit_effect, ack_delivered, visibility_delay FROM fault_schedule"
            " WHERE consumed = 0 ORDER BY seq LIMIT 1"
        ).fetchone()
        if row is None:
            return FaultSpec()
        seq, commit_effect, ack_delivered, visibility_delay = row
        conn.execute("UPDATE fault_schedule SET consumed = 1 WHERE seq = ?", (seq,))
        return FaultSpec(bool(commit_effect), bool(ack_delivered), visibility_delay)

    def _now(self, conn: sqlite3.Connection) -> float:
        now = self._clock()
        latest = conn.execute("SELECT MAX(received_at) FROM dispatch_log").fetchone()[0]
        if latest is not None and now < latest:
            raise ClockRegression(
                f"clock reads {now} but the database already records time {latest}"
            )
        return now

    def _query(self, operation_id: str) -> QueryResult:
        with closing(_connect(self.db_path)) as conn:
            row = conn.execute(
                "SELECT ticket_id FROM committed_effects"
                " WHERE operation_id = ? AND visible_at <= ? ORDER BY effect_id LIMIT 1",
                (operation_id, self._now(conn)),
            ).fetchone()
        if row is None:
            return QueryResult(status="not_found", ticket_id=None)
        return QueryResult(status="found", ticket_id=row[0])


class MaintenanceClient:
    """The only interface a recovery policy may hold."""

    def __init__(self, service: MaintenanceEffectService) -> None:
        self._service = service

    def submit(self, operation_id: str, machine_id: str) -> SubmitResponse:
        """Dispatch a create-ticket request. Raises AcknowledgmentLost if no reply."""
        return self._service._submit(operation_id, machine_id)

    def query(self, operation_id: str) -> QueryResult:
        """Look up an operation's outcome. Visibility may lag the commit."""
        return self._service._query(operation_id)


class EffectLedger:
    """Read-only oracle over the service database. Never give it to a policy."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(f"{self.db_path.resolve().as_uri()}?mode=ro", uri=True)

    def _count(self, sql: str, operation_id: str) -> int:
        with closing(self._connect()) as conn:
            return conn.execute(sql, (operation_id,)).fetchone()[0]

    def dispatch_count(self, operation_id: str) -> int:
        return self._count("SELECT COUNT(*) FROM dispatch_log WHERE operation_id = ?", operation_id)

    def committed_effect_count(self, operation_id: str) -> int:
        return self._count(
            "SELECT COUNT(*) FROM committed_effects WHERE operation_id = ?", operation_id
        )

    def dispatch_outcomes(self, operation_id: str) -> list[str]:
        """Per-dispatch outcomes in arrival order."""
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT outcome FROM dispatch_log WHERE operation_id = ? ORDER BY dispatch_id",
                (operation_id,),
            ).fetchall()
        return [row[0] for row in rows]

    def ack_delivered_count(self, operation_id: str) -> int:
        return self._count(
            "SELECT COUNT(*) FROM dispatch_log WHERE operation_id = ? AND ack_delivered = 1",
            operation_id,
        )
