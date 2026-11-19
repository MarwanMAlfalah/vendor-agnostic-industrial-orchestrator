"""Deterministic external-effect simulator with genuine in-flight commits (extension v1).

Unlike the original ``MaintenanceEffectService`` (where a dispatch commits or fails inside the
submit call, so the completion bound is 0), this service separates four events:

* acceptance  - the request is recorded at dispatch time and may stay pending;
* commit      - the external effect happens, possibly after recovery has started;
* visibility  - the outcome query can see the committed effect (commit + visibility lag);
* acknowledgment - the reply to the caller, delivered or lost (lost replies raise
  ``AcknowledgmentLost`` exactly as in the original service).

Time semantics (documented in extension protocol §3):
* The shared ``SimulatedClock`` holds whole seconds in floats; all scheduled times in the
  extension matrix are integers, so comparisons are exact.
* Before any submit, query or drain at time t, every event scheduled at or before t is
  applied in order (time, priority, sequence) with priority commit/abort = 0, visible = 1.
  A query at t therefore observes events scheduled exactly at t (bounds are inclusive).
* Applying due events is bookkeeping of scheduled history: a query never causes a commit,
  and a re-dispatch never cancels or alters a pending request.
* Δ (completion bound) bounds commit_at - accepted_at; λ (visibility bound) bounds
  visible_at - committed_at. Faults may violate a *declared* bound (contract-violation set);
  the service itself only executes the fault schedule.

Authorization semantics (provider contract field ``auth_check``):
* ``none``       - the provider never checks authorization;
* ``acceptance`` - a request arriving while authorization is invalid is rejected with a
  delivered ``failed`` reply; an already accepted request still commits;
* ``commit``     - as ``acceptance``, and a pending request whose commit time falls while
  authorization is invalid is aborted at that time instead of committing.

Deduplication (``deduplicate=True``): a request whose operation ID already has an accepted,
non-aborted request is not accepted again; the reply is ``deduplicated`` with the existing
ticket. Under deduplication an accepted request is durable: the schedule must give it a commit
time (validated), so "accepted but never commits" cases are run without deduplication.

The ledger (SQLite, one database per run) records every committed effect independently of any
policy decision; ``events()`` returns the full ordered event log.
"""

from __future__ import annotations

import heapq
import json
import sqlite3
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.integration.maintenance_effect_service import (
    AcknowledgmentLost,
    QueryResult,
    SimulatedClock,
    SubmitResponse,
)

AUTH_CHECKS = ("none", "acceptance", "commit")
_PRIORITY = {"commit": 0, "abort": 0, "visible": 1}


@dataclass(frozen=True)
class RequestFault:
    """Fate of one accepted request. Consumed in submit order; later submits use the default.

    commit_after: seconds after acceptance at which the effect commits; None = never commits.
    abort_after: for a request that never commits, seconds after acceptance at which the
        provider resolves it as aborted; None = unresolved (censored at the assessment horizon).
    visibility_after: seconds after commit at which a query can see the effect.
    ack_delivered: whether the caller receives a reply for this submit.
    """

    commit_after: float | None = 0.0
    visibility_after: float = 0.0
    ack_delivered: bool = True
    abort_after: float | None = None

    def __post_init__(self) -> None:
        for name in ("commit_after", "abort_after"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ValueError(f"{name} must be >= 0")
        if self.visibility_after < 0:
            raise ValueError("visibility_after must be >= 0")
        if self.commit_after is not None and self.abort_after is not None:
            raise ValueError("a request either commits or aborts")
        if self.ack_delivered and self.commit_after != 0.0:
            raise ValueError("a delivered acknowledgment requires an immediate commit")


DEFAULT_FAULT = RequestFault()


@dataclass(frozen=True)
class AuthorizationTimeline:
    """World authorization/precondition state: valid until ``invalid_from`` (exclusive)."""

    invalid_from: float | None = None

    def valid(self, t: float) -> bool:
        return self.invalid_from is None or t < self.invalid_from


@dataclass(frozen=True)
class Event:
    seq: int
    time: float
    kind: str
    operation_id: str
    request_seq: int | None = None
    ticket_id: str | None = None
    detail: str = ""


@dataclass(frozen=True)
class Effect:
    operation_id: str
    ticket_id: str
    request_seq: int
    committed_at: float
    visible_at: float
    authorized_at_commit: bool


@dataclass
class DrainReport:
    until: float
    pending_at_horizon: list[str] = field(default_factory=list)


class InFlightEffectService:
    def __init__(
        self,
        db_path: str | Path,
        *,
        clock: SimulatedClock,
        deduplicate: bool = False,
        auth_check: str = "none",
        authorization: AuthorizationTimeline | None = None,
    ) -> None:
        if auth_check not in AUTH_CHECKS:
            raise ValueError(f"auth_check must be one of {AUTH_CHECKS}")
        self.db_path = Path(db_path)
        if self.db_path.exists():
            raise FileExistsError("use a fresh database per run")
        self._clock = clock
        self.deduplicate = deduplicate
        self.auth_check = auth_check
        self.authorization = authorization or AuthorizationTimeline()
        self._faults: list[RequestFault] = []
        self._queue: list[tuple[float, int, int, str, int]] = []  # (time, prio, seq, kind, request_seq)
        self._events: list[Event] = []
        self._requests: dict[int, dict] = {}
        self._bound_machine: dict[str, str] = {}
        self._seq = 0
        self._processed_until = -float("inf")
        self._conn = sqlite3.connect(self.db_path)
        self._conn.executescript(
            """
            CREATE TABLE effects (operation_id TEXT, ticket_id TEXT, request_seq INTEGER,
                                  committed_at REAL, visible_at REAL, authorized_at_commit INTEGER);
            CREATE TABLE requests (request_seq INTEGER PRIMARY KEY, operation_id TEXT,
                                   machine_id TEXT, accepted_at REAL, fault TEXT, status TEXT);
            """
        )

    # --- public API -------------------------------------------------------------------------
    def schedule(self, faults: Iterable[RequestFault]) -> None:
        self._faults.extend(faults)

    def client(self) -> InFlightClient:
        return InFlightClient(self)

    def events(self) -> list[Event]:
        return list(self._events)

    def effects(self, operation_id: str | None = None) -> list[Effect]:
        sql = "SELECT operation_id, ticket_id, request_seq, committed_at, visible_at, authorized_at_commit FROM effects"
        args: tuple = ()
        if operation_id is not None:
            sql += " WHERE operation_id = ?"
            args = (operation_id,)
        rows = self._conn.execute(sql + " ORDER BY committed_at, request_seq", args).fetchall()
        return [Effect(r[0], r[1], r[2], r[3], r[4], bool(r[5])) for r in rows]

    def drain(self, *, until: float) -> DrainReport:
        """Apply every scheduled event up to the assessment horizon ``until`` (clock unchanged)."""
        self._apply_due(until)
        pending = sorted(
            {r["operation_id"] for r in self._requests.values() if r["status"] == "pending"}
        )
        return DrainReport(until=until, pending_at_horizon=pending)

    # --- internals --------------------------------------------------------------------------
    def _log(self, time: float, kind: str, op: str, request_seq: int | None = None,
             ticket: str | None = None, detail: str = "") -> None:
        self._events.append(Event(len(self._events), time, kind, op, request_seq, ticket, detail))

    def _push(self, time: float, kind: str, request_seq: int) -> None:
        self._seq += 1
        heapq.heappush(self._queue, (time, _PRIORITY[kind], self._seq, kind, request_seq))

    def _apply_due(self, t: float) -> None:
        while self._queue and self._queue[0][0] <= t:
            time, _, _, kind, rseq = heapq.heappop(self._queue)
            req = self._requests[rseq]
            op = req["operation_id"]
            if kind == "commit":
                authorized = self.authorization.valid(time)
                if self.auth_check == "commit" and not authorized:
                    req["status"] = "aborted"
                    self._log(time, "abort_unauthorized_at_commit", op, rseq, req["ticket_id"])
                    continue
                req["status"] = "committed"
                fault: RequestFault = req["fault"]
                visible_at = time + fault.visibility_after
                self._conn.execute(
                    "INSERT INTO effects VALUES (?,?,?,?,?,?)",
                    (op, req["ticket_id"], rseq, time, visible_at, int(authorized)),
                )
                self._log(time, "commit", op, rseq, req["ticket_id"],
                          "" if authorized else "authorization_invalid_at_commit")
                self._push(visible_at, "visible", rseq)
            elif kind == "abort":
                req["status"] = "aborted"
                self._log(time, "abort", op, rseq, req["ticket_id"])
            elif kind == "visible":
                req["visible"] = True
                self._log(time, "visible", op, rseq, req["ticket_id"])
        self._processed_until = max(self._processed_until, t)
        self._conn.commit()

    def _submit(self, operation_id: str, machine_id: str) -> SubmitResponse:
        now = self._clock()
        self._apply_due(now)
        fault = self._faults.pop(0) if self._faults else DEFAULT_FAULT
        bound = self._bound_machine.setdefault(operation_id, machine_id)
        self._log(now, "submit", operation_id, detail=json.dumps(asdict(fault), sort_keys=True))
        if bound != machine_id:
            return self._reply(fault, now, operation_id, "conflict", None)
        if self.auth_check in ("acceptance", "commit") and not self.authorization.valid(now):
            self._log(now, "reject_unauthorized_at_acceptance", operation_id)
            return self._reply(fault, now, operation_id, "failed", None)
        if self.deduplicate:
            live = [r for r in self._requests.values()
                    if r["operation_id"] == operation_id and r["status"] in ("pending", "committed")]
            if live:
                ticket = live[0]["ticket_id"]
                self._log(now, "deduplicated", operation_id, live[0]["seq"], ticket)
                return self._reply(fault, now, operation_id, "deduplicated", ticket)
            if fault.commit_after is None:
                raise ValueError("under deduplication an accepted request must commit (protocol §3)")
        rseq = len(self._requests) + 1
        ticket = f"T-{rseq:04d}"
        self._requests[rseq] = {"seq": rseq, "operation_id": operation_id, "ticket_id": ticket,
                                "fault": fault, "status": "pending", "visible": False}
        self._conn.execute("INSERT INTO requests VALUES (?,?,?,?,?,?)",
                           (rseq, operation_id, machine_id, now, json.dumps(asdict(fault)), "accepted"))
        self._log(now, "accept", operation_id, rseq, ticket,
                  "" if self.authorization.valid(now) else "authorization_invalid_at_acceptance")
        if fault.commit_after is not None:
            self._push(now + fault.commit_after, "commit", rseq)
        elif fault.abort_after is not None:
            self._push(now + fault.abort_after, "abort", rseq)
        self._apply_due(now)  # an immediate commit happens inside the submit call
        return self._reply(fault, now, operation_id, "committed", ticket)

    def _reply(self, fault: RequestFault, now: float, op: str, status: str, ticket: str | None) -> SubmitResponse:
        if not fault.ack_delivered:
            self._log(now, "ack_lost", op, ticket=ticket, detail=status)
            raise AcknowledgmentLost(op)
        self._log(now, "ack", op, ticket=ticket, detail=status)
        return SubmitResponse(op, status, ticket)

    def _query(self, operation_id: str) -> QueryResult:
        now = self._clock()
        self._apply_due(now)
        row = self._conn.execute(
            "SELECT ticket_id FROM effects WHERE operation_id = ? AND visible_at <= ? "
            "ORDER BY committed_at, request_seq LIMIT 1", (operation_id, now)).fetchone()
        status = "found" if row else "not_found"
        self._log(now, "query", operation_id, ticket=row[0] if row else None, detail=status)
        return QueryResult(status, row[0] if row else None)


class InFlightClient:
    """Same interface as ``MaintenanceClient``: submit (may raise AcknowledgmentLost) and query."""

    def __init__(self, service: InFlightEffectService) -> None:
        self._service = service

    def submit(self, operation_id: str, machine_id: str) -> SubmitResponse:
        return self._service._submit(operation_id, machine_id)

    def query(self, operation_id: str) -> QueryResult:
        return self._service._query(operation_id)
