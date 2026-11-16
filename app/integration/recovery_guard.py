"""Opt-in RecoveryGuard (ElCon-EE 2027).

The guard sits in front of every external dispatch made by an opt-in adapter.
It builds a policy-visible ``Observation`` (protocol v1.0 §1) from the recovery
journal and the declared capability contract, runs an injectable recovery
policy through the shared ``drive_policy`` stepper, journals the terminal
decision, and returns it. The default policy is P (``p_capability_aware``);
B0/B1/B2 can be injected with identical inputs.

Two integration rules apply to EVERY policy before it is consulted (they are
outside the frozen §3 pseudocode, which covers only interrupted attempts):

* no journaled attempt -> DISPATCH (the first authorised execution);
* the latest attempt has a recorded committed/deduplicated reply -> ADOPT that
  ticket (a delivered reply is confirmed commitment, protocol §1).

Governance provenance: the guard runs only inside an adapter invocation, and
ExecutionAgent invokes adapters only for steps whose decision in the executed
plan is ALLOW. Where that plan came from (the real GovernanceAgent, or a
pre-authored evaluation plan) is decided by the caller, not by the guard. By
default REVALIDATE is answered with that carried ALLOW and recorded with
provenance ``carried_allow_not_reevaluated``. It is not a fresh GovernanceAgent
evaluation or approval check. A caller can inject ``revalidate`` to actually
re-run governance.

Not claimed: exactly-once execution, safety under commits later than the
declared completion bound, or concurrent resumers (no lease exists).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from app.integration.maintenance_effect_service import (
    QueryResult,
    SimulatedClock,
    request_fingerprint,
)
from app.integration.recovery_journal import JournalConflict, RecoveryJournal
from app.integration.recovery_policies import (
    ACK_STATES,
    AckState,
    Action,
    CapabilityContract,
    DispatchState,
    DriveOutcome,
    Evidence,
    Observation,
    Policy,
    QueryEvidence,
    drive_policy,
    p_capability_aware,
)

__all__ = [
    "AckState",
    "Action",
    "CapabilityContract",
    "DispatchState",
    "Evidence",
    "GuardDecision",
    "Observation",
    "QueryEvidence",
    "RecoveryGuard",
    "capability_aware_next_action",
    "carried_allow",
]

capability_aware_next_action = p_capability_aware  # backwards-compatible name


def carried_allow() -> tuple[str, str]:
    """Default REVALIDATE answer: the plan's ALLOW, explicitly not re-evaluated."""
    return "ALLOW", "carried_allow_not_reevaluated"


@dataclass(frozen=True)
class GuardDecision:
    action: str  # DISPATCH | REDISPATCH | ADOPT | HOLD
    basis: str
    ticket_id: str | None = None
    outcome: DriveOutcome | None = None  # present when a policy was consulted


class RecoveryGuard:
    """Consulted by an opt-in adapter before every external dispatch."""

    def __init__(
        self,
        journal: RecoveryJournal,
        contract: CapabilityContract,
        clock: SimulatedClock,
        *,
        policy: Policy = p_capability_aware,
        revalidate: Callable[[], tuple[str, str]] = carried_allow,
        wait: Callable[[float], None] | None = None,
        horizon_s: float = 60.0,
        step_budget: int = 20,
        approval: Mapping[str, Any] | None = None,
    ) -> None:
        self.journal = journal
        self.contract = contract
        self._clock = clock
        self._policy = policy
        self._revalidate = revalidate
        self._wait = wait
        self._horizon_s = horizon_s
        self._step_budget = step_budget
        # Capability-level declaration for create_maintenance_ticket; approval
        # binding (F7) is not implemented.
        self._approval = dict(approval or {"required": False, "status": "not_required"})

    def decide(
        self,
        *,
        operation_id: str,
        workflow_id: str,
        step_id: str,
        capability: str,
        adapter: str,
        request: Mapping[str, Any],
        query: Callable[[str], QueryResult],
    ) -> GuardDecision:
        try:
            self.journal.record_intent(
                operation_id=operation_id,
                workflow_id=workflow_id,
                step_id=step_id,
                capability=capability,
                adapter=adapter,
                fingerprint=request_fingerprint(capability, request),
                now=self._clock(),
            )
        except JournalConflict:
            return self._journaled(operation_id, GuardDecision("HOLD", "request_fingerprint_mismatch"))

        attempts = self.journal.attempts(operation_id)
        if not attempts:
            return self._journaled(operation_id, GuardDecision("DISPATCH", "no_prior_dispatch"))
        latest = attempts[-1]
        if latest.reply_status in {"committed", "deduplicated"}:
            return self._journaled(
                operation_id, GuardDecision("ADOPT", "acknowledged_reply", latest.ticket_id)
            )

        now = self._clock()
        obs = Observation(
            workflow_id=workflow_id,
            step_id=step_id,
            operation_id=operation_id,
            capability=capability,
            adapter=adapter,
            request=dict(request),
            dispatch=DispatchState(len(attempts), latest.dispatched_at),
            ack=AckState(ACK_STATES[latest.reply_status], latest.reply_status, latest.ticket_id),
            contract=self.contract,
            approval=dict(self._approval),
            preconditions={
                "governance_revalidation": (
                    "carried_allow_not_reevaluated"
                    if self._revalidate is carried_allow
                    else "injected_revalidation"
                ),
                "equipment_state": "not_modelled",
            },
            resume_at=now,
            horizon_end=now + self._horizon_s,
        )
        outcome = drive_policy(
            self._policy,
            obs,
            query=lambda: query(operation_id),
            revalidate=self._revalidate,
            clock=self._clock,
            wait=self._wait,
            step_budget=self._step_budget,
        )
        action = outcome.action
        decision = GuardDecision(action.kind, action.basis, action.ticket_id, outcome)
        return self._journaled(operation_id, decision)

    def begin_attempt(self, operation_id: str) -> int:
        return self.journal.begin_attempt(operation_id, self._clock())

    def record_reply(self, attempt_id: int, status: str, ticket_id: str | None) -> None:
        self.journal.record_reply(attempt_id, status, ticket_id, self._clock())

    def _journaled(self, operation_id: str, decision: GuardDecision) -> GuardDecision:
        self.journal.record_decision(
            operation_id,
            now=self._clock(),
            action=decision.action,
            basis=decision.basis,
            ticket_id=decision.ticket_id,
        )
        return decision
