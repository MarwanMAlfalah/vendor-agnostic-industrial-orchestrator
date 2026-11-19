"""Recovery policies B0/B1/B2/P from the frozen ElCon-EE 2027 protocol v1.0 (§3).

Each policy is a pure, deterministic function ``(Observation, Evidence) -> Action``.
Policies see only the policy-visible observation (§1) and the evidence the
harness recorded for this resumer. They never see a case ID, fault schedule,
oracle row, expected result, service, client or ledger. Every policy receives
the same declared capability contract; they differ only in which rules they
apply.

``drive_policy`` is the single stepper shared by the service-level runner and
the opt-in RecoveryGuard. It executes REVALIDATE / QUERY / WAIT_UNTIL on the
policy's behalf, enforces the protocol's harness rules (QUERY rejected when the
contract says the query is unavailable; WAIT_UNTIL bounded by the horizon; a
20-step budget), and returns the terminal action with the evidence it was based
on. REVALIDATE runs whatever ``revalidate`` callable the caller supplies, and the
provenance it reports is recorded. A carried ALLOW is never labelled as a fresh
GovernanceAgent evaluation.
"""

from __future__ import annotations

import dataclasses
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from app.integration.maintenance_effect_service import QueryResult, SimulatedClock


@dataclass(frozen=True)
class CapabilityContract:
    """Declared capability contract (protocol v1.0 §1). None = undeclared."""

    deduplicates_by_operation_id: bool | None
    binds_request_fingerprint: bool | None
    outcome_query: str | None  # "available" | "unavailable" | None
    visibility_bound_s: float | None
    completion_bound_s: float | None
    failure_response_scope: str | None


@dataclass(frozen=True)
class DispatchState:
    attempts: int
    last_dispatch_at: float | None


@dataclass(frozen=True)
class AckState:
    state: str  # "received" | "failure_received" | "conflict" | "missing"
    status: str | None
    ticket_id: str | None


@dataclass(frozen=True)
class Observation:
    workflow_id: str
    step_id: str
    operation_id: str
    capability: str
    adapter: str
    request: Mapping[str, Any]
    dispatch: DispatchState
    ack: AckState
    contract: CapabilityContract
    approval: Mapping[str, Any]
    preconditions: Mapping[str, Any]
    resume_at: float
    horizon_end: float


@dataclass(frozen=True)
class QueryEvidence:
    status: str
    ticket_id: str | None
    query_time: float


@dataclass(frozen=True)
class Evidence:
    governance: str | None
    queries: tuple[QueryEvidence, ...]
    now: float


@dataclass(frozen=True)
class Action:
    kind: str  # REVALIDATE | QUERY | WAIT_UNTIL | ADOPT | REDISPATCH | HOLD
    basis: str = ""
    until: float | None = None
    ticket_id: str | None = None


TERMINAL = frozenset({"ADOPT", "REDISPATCH", "HOLD"})

# Journal reply status of the latest attempt -> policy-visible ack state.
ACK_STATES: dict[str | None, str] = {
    None: "missing",
    "committed": "received",
    "deduplicated": "received",
    "failed": "failure_received",
    "conflict": "conflict",
}


def b0_blind_redispatch(obs: Observation, ev: Evidence) -> Action:
    """B0: re-dispatch unconditionally; no query, no revalidation."""
    return Action("REDISPATCH", "blind")


def b1_revalidate_then_redispatch(obs: Observation, ev: Evidence) -> Action:
    """B1: governance/approval revalidation, then re-dispatch if ALLOW."""
    if ev.governance is None:
        return Action("REVALIDATE")
    if ev.governance != "ALLOW":
        return Action("HOLD", "governance_not_allow")
    return Action("REDISPATCH", "revalidated_allow")


def b2_idempotency_and_readback(obs: Observation, ev: Evidence) -> Action:
    """B2: idempotency key where declared; otherwise read back once, then retry.

    Treats any not_found as absence and ignores visibility/completion bounds.
    It is a common-practice control, not the strongest possible query-aware
    algorithm.
    """
    if ev.governance is None:
        return Action("REVALIDATE")
    if ev.governance != "ALLOW":
        return Action("HOLD", "governance_not_allow")
    if obs.ack.state == "conflict":
        return Action("HOLD", "conflict_reply")
    if obs.ack.state == "failure_received" and obs.dispatch.attempts == 1:
        return Action("REDISPATCH", "failure_response_sole_attempt")
    if obs.contract.deduplicates_by_operation_id is True:
        return Action("REDISPATCH", "dedup_contract")
    if obs.contract.outcome_query != "available":
        return Action("HOLD", "outcome_unverifiable")
    if not ev.queries:
        return Action("QUERY")
    latest = ev.queries[-1]
    if latest.status == "found":
        return Action("ADOPT", "query_found", ticket_id=latest.ticket_id)
    return Action("REDISPATCH", "not_found_read_as_absence")


def p_capability_aware(obs: Observation, ev: Evidence) -> Action:
    """P: identical to B2 up to the first query result; differs only in when
    not_found counts as absence (both declared bounds must have elapsed)."""
    if ev.governance is None:
        return Action("REVALIDATE")
    if ev.governance != "ALLOW":
        return Action("HOLD", "governance_not_allow")
    if obs.ack.state == "conflict":
        return Action("HOLD", "conflict_reply")
    if obs.ack.state == "failure_received" and obs.dispatch.attempts == 1:
        return Action("REDISPATCH", "failure_response_sole_attempt")
    contract = obs.contract
    if contract.deduplicates_by_operation_id is True:
        return Action("REDISPATCH", "dedup_contract")
    if contract.outcome_query != "available":
        return Action("HOLD", "outcome_unverifiable")
    if not ev.queries:
        return Action("QUERY")
    latest = ev.queries[-1]
    if latest.status == "found":
        return Action("ADOPT", "query_found", ticket_id=latest.ticket_id)
    vb, cb = contract.visibility_bound_s, contract.completion_bound_s
    if vb is None or cb is None or obs.dispatch.last_dispatch_at is None:
        return Action("HOLD", "not_found_not_authoritative")
    deadline = obs.dispatch.last_dispatch_at + cb + vb
    if latest.query_time >= deadline:
        return Action("REDISPATCH", "authoritative_absence")
    if ev.now < deadline <= obs.horizon_end:
        return Action("WAIT_UNTIL", until=deadline)
    if ev.now >= deadline:
        return Action("QUERY")
    return Action("HOLD", "deadline_beyond_horizon")


Policy = Callable[[Observation, Evidence], Action]

POLICIES: dict[str, Policy] = {
    "B0": b0_blind_redispatch,
    "B1": b1_revalidate_then_redispatch,
    "B2": b2_idempotency_and_readback,
    "P": p_capability_aware,
}


@dataclass(frozen=True)
class DriveOutcome:
    action: Action  # terminal; HOLD with basis == error when the policy erred
    steps: tuple[Action, ...]
    evidence: Evidence  # evidence at the terminal decision
    simulated_wait_s: float
    latency_ns: int  # wall clock spent inside policy calls only
    revalidation_provenance: str | None
    error: str | None = None  # protocol rule violated -> decision is invalid
    extra: Mapping[str, Any] = field(default_factory=dict)


def drive_policy(
    policy: Policy,
    obs: Observation,
    *,
    query: Callable[[], QueryResult],
    revalidate: Callable[[], tuple[str, str]],
    clock: SimulatedClock,
    wait: Callable[[float], None] | None = None,
    step_budget: int = 20,
) -> DriveOutcome:
    """Run a policy to its terminal action, executing non-terminal steps."""
    wait = wait if wait is not None else clock.advance
    ev = Evidence(governance=None, queries=(), now=clock())
    steps: list[Action] = []
    waited = 0.0
    latency_ns = 0
    provenance: str | None = None

    def finish(action: Action, error: str | None = None) -> DriveOutcome:
        return DriveOutcome(
            action=action,
            steps=tuple(steps),
            evidence=ev,
            simulated_wait_s=waited,
            latency_ns=latency_ns,
            revalidation_provenance=provenance,
            error=error,
        )

    for _ in range(step_budget):
        started = time.perf_counter_ns()
        action = policy(obs, ev)
        latency_ns += time.perf_counter_ns() - started
        steps.append(action)
        if action.kind in TERMINAL:
            return finish(action)
        if action.kind == "REVALIDATE":
            decision, provenance = revalidate()
            ev = dataclasses.replace(ev, governance=decision)
        elif action.kind == "QUERY":
            if obs.contract.outcome_query != "available":
                return finish(Action("HOLD", "query_rejected_unavailable"), "query_rejected_unavailable")
            result = query()
            record = QueryEvidence(result.status, result.ticket_id, clock())
            ev = dataclasses.replace(ev, queries=(*ev.queries, record), now=clock())
        elif action.kind == "WAIT_UNTIL":
            if action.until is None or action.until > obs.horizon_end:
                return finish(Action("HOLD", "wait_beyond_horizon"), "wait_beyond_horizon")
            before = clock()
            wait(max(0.0, action.until - before))
            if clock() < action.until:
                return finish(Action("HOLD", "wait_did_not_advance"), "wait_did_not_advance")
            waited += clock() - before
            ev = dataclasses.replace(ev, now=clock())
        else:
            return finish(Action("HOLD", "unknown_action"), "unknown_action")
    return finish(Action("HOLD", "step_budget_exhausted"), "step_budget_exhausted")
