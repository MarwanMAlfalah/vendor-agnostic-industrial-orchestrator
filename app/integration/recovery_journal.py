"""Durable per-operation recovery journal (ElCon-EE 2027, opt-in).

The journal records what the WORKFLOW knows locally: an operation's identity
and request fingerprint, each dispatch attempt it started, the replies it
received, and the recovery decisions it took. It is written before the
external call, so an attempt without a recorded reply is an uncertain outcome:
the request may or may not have committed.

It is NOT the committed-effect oracle. Ground truth lives only in the
service's EffectLedger; the journal and the ledger can disagree, and that is
exactly the situation recovery has to handle.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS operations (
    operation_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    capability TEXT NOT NULL,
    adapter TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    recorded_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS attempts (
    attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id TEXT NOT NULL REFERENCES operations(operation_id),
    dispatched_at REAL NOT NULL,
    reply_status TEXT,
    ticket_id TEXT,
    replied_at REAL
);
CREATE TABLE IF NOT EXISTS decisions (
    decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id TEXT NOT NULL REFERENCES operations(operation_id),
    decided_at REAL NOT NULL,
    action TEXT NOT NULL,
    basis TEXT NOT NULL,
    ticket_id TEXT
);
"""


class JournalConflict(Exception):
    """The operation ID is already journaled for a different request."""


@dataclass(frozen=True)
class AttemptRecord:
    attempt_id: int
    dispatched_at: float
    reply_status: str | None  # None: no reply recorded (outcome unknown)
    ticket_id: str | None


@dataclass(frozen=True)
class DecisionRecord:
    decided_at: float
    action: str
    basis: str
    ticket_id: str | None


class RecoveryJournal:
    """SQLite journal; one connection per call, so it survives runtime restarts."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def record_intent(
        self,
        *,
        operation_id: str,
        workflow_id: str,
        step_id: str,
        capability: str,
        adapter: str,
        fingerprint: str,
        now: float,
    ) -> None:
        """Persist identity + fingerprint once; reject a different request later."""
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    "SELECT fingerprint FROM operations WHERE operation_id = ?", (operation_id,)
                ).fetchone()
                if row is None:
                    conn.execute(
                        "INSERT INTO operations VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (operation_id, workflow_id, step_id, capability, adapter, fingerprint, now),
                    )
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        if row is not None and row[0] != fingerprint:
            raise JournalConflict(f"{operation_id} is journaled for a different request")

    def begin_attempt(self, operation_id: str, now: float) -> int:
        """Record a dispatch attempt BEFORE the external call is made."""
        with closing(self._connect()) as conn:
            cursor = conn.execute(
                "INSERT INTO attempts(operation_id, dispatched_at) VALUES (?, ?)",
                (operation_id, now),
            )
            return int(cursor.lastrowid)

    def record_reply(
        self, attempt_id: int, status: str, ticket_id: str | None, now: float
    ) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "UPDATE attempts SET reply_status = ?, ticket_id = ?, replied_at = ?"
                " WHERE attempt_id = ? AND reply_status IS NULL",
                (status, ticket_id, now, attempt_id),
            )

    def record_decision(
        self,
        operation_id: str,
        *,
        now: float,
        action: str,
        basis: str,
        ticket_id: str | None = None,
    ) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO decisions(operation_id, decided_at, action, basis, ticket_id)"
                " VALUES (?, ?, ?, ?, ?)",
                (operation_id, now, action, basis, ticket_id),
            )

    def attempts(self, operation_id: str) -> list[AttemptRecord]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT attempt_id, dispatched_at, reply_status, ticket_id FROM attempts"
                " WHERE operation_id = ? ORDER BY attempt_id",
                (operation_id,),
            ).fetchall()
        return [AttemptRecord(*row) for row in rows]

    def decisions(self, operation_id: str) -> list[DecisionRecord]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT decided_at, action, basis, ticket_id FROM decisions"
                " WHERE operation_id = ? ORDER BY decision_id",
                (operation_id,),
            ).fetchall()
        return [DecisionRecord(*row) for row in rows]
