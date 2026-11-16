"""Extension v1 policies: the original B0/B1/B2/P (imported, unchanged) plus two named additions.

R_LI (reference): a transparent single-operation implementation of the bounded-wait principle
stated by Li (arXiv:2609.29095v1, §3 and the "wait Δ" harness policy of §5/§6.3): wait until
t_d + Δ + λ after the last dispatch, then read back once; adopt a found effect, re-issue only on
an authoritative not_found. Scope and assumptions: it needs both bounds declared and trusts them
(Li's remedy assumes a known bound); it does not reproduce Li's benchmark, models or harness.
To give every policy the same governance inputs it applies the same governance/conflict checks,
failure-reply rule and deduplication rule as B2/P, which are not part of Li's policy.
R_LI differs from P only in that P queries once before waiting (and may adopt early).

P_A (variant of P): identical to P except when revalidation is not ALLOW. P then holds; P_A
first queries (if a query exists) and adopts an effect that is already visible, otherwise holds.
P_A never dispatches under a non-ALLOW decision. Adopting records an existing external effect;
it is not a new request (protocol §5 distinguishes these permissions).
"""

from __future__ import annotations

from app.integration.recovery_policies import (
    POLICIES,
    Action,
    Evidence,
    Observation,
    p_capability_aware,
)


def r_li_wait_then_verify(obs: Observation, ev: Evidence) -> Action:
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
    vb, cb = contract.visibility_bound_s, contract.completion_bound_s
    if vb is None or cb is None or obs.dispatch.last_dispatch_at is None:
        return Action("HOLD", "bound_undeclared")
    deadline = obs.dispatch.last_dispatch_at + cb + vb
    if deadline > obs.horizon_end:
        return Action("HOLD", "deadline_beyond_horizon")
    after = [q for q in ev.queries if q.query_time >= deadline]
    if not after:
        if ev.now < deadline:
            return Action("WAIT_UNTIL", until=deadline)
        return Action("QUERY")
    latest = after[-1]
    if latest.status == "found":
        return Action("ADOPT", "query_found_after_bound", ticket_id=latest.ticket_id)
    return Action("REDISPATCH", "authoritative_absence")


def p_adopt_under_non_allow(obs: Observation, ev: Evidence) -> Action:
    if ev.governance is not None and ev.governance != "ALLOW":
        if obs.contract.outcome_query != "available":
            return Action("HOLD", "governance_not_allow")
        if not ev.queries:
            return Action("QUERY")
        latest = ev.queries[-1]
        if latest.status == "found":
            return Action("ADOPT", "adopt_observed_effect_under_non_allow", ticket_id=latest.ticket_id)
        return Action("HOLD", "governance_not_allow")
    return p_capability_aware(obs, ev)


EXT_POLICIES = {**POLICIES, "R_LI": r_li_wait_then_verify, "P_A": p_adopt_under_non_allow}
