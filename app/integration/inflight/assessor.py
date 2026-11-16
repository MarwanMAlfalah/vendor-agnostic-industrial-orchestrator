"""Independent assessor for extension v1 runs.

Inputs are records produced by the simulated service (event log and committed-effect
ledger), the declared authorization timeline of the case, and the outcome the workflow
reported. The assessor imports no policy, guard, oracle or runner code, and it does not
know which policy produced the trace.

Definitions (extension protocol §6):
* effects_at_decision: ledger effects committed at or before the terminal recovery decision.
* eventual_effects: ledger effects committed by the assessment horizon (all finite events
  drained). If any request is still pending at the horizon the run is ``censored`` and
  duplicate freedom is NOT established.
* duplicate_eventual: eventual_effects > 1; late_duplicate: duplicate that did not exist at
  the decision time (it would be missed by an assessment that stops at the decision).
* completed_single_effect: the workflow reported completion (ADOPT or a delivered
  committed/deduplicated reply after REDISPATCH), exactly one eventual effect exists, the run is
  not censored, and the ticket the workflow recorded is that effect's ticket.
* missing_effect: the workflow reported completion but no effect exists eventually.
* adoption_consistent: for ADOPT, the adopted ticket is a committed effect in the ledger.
* dispatches_while_invalid: submit events at times when the declared authorization/precondition
  state is invalid (simulated; not an industrial safety measure).
* effects_while_invalid: committed effects whose commit time falls while it is invalid.
* commits_after_hold: effects committed after a HOLD decision.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def _invalid(t: float, invalid_from: float | None) -> bool:
    return invalid_from is not None and t >= invalid_from


def assess(
    *,
    operation_id: str,
    effects: Sequence[Mapping[str, Any]],
    events: Sequence[Mapping[str, Any]],
    outcome: Mapping[str, Any],
    decision_time: float,
    invalid_from: float | None,
    pending_at_horizon: Sequence[str],
) -> dict[str, Any]:
    mine = [e for e in effects if e["operation_id"] == operation_id]
    evs = [e for e in events if e["operation_id"] == operation_id]
    tickets = {e["ticket_id"] for e in mine}
    final = outcome.get("final")
    recorded = outcome.get("ticket_id")
    censored = operation_id in pending_at_horizon
    eventual = len(mine)
    at_decision = sum(1 for e in mine if e["committed_at"] <= decision_time)
    completed = final in ("ADOPT", "REDISPATCH") and recorded is not None
    single = completed and eventual == 1 and not censored and recorded in tickets
    if censored:
        status = "censored"
    elif eventual > 1:
        status = "duplicate"
    elif eventual == 1:
        status = "one_effect"
    else:
        status = "no_effect"
    return {
        "effects_at_decision": at_decision,
        "eventual_effects": eventual,
        "duplicate_at_decision": at_decision > 1,
        "duplicate_eventual": eventual > 1,
        "late_duplicate": eventual > 1 and at_decision <= 1,
        "censored": censored,
        "eventual_status": status,
        "workflow_outcome": "completed" if completed else ("held" if final == "HOLD" else "not_completed"),
        "completed_single_effect": single,
        "missing_effect": completed and eventual == 0,
        "adoption_consistent": (recorded in tickets) if final == "ADOPT" else None,
        "dispatches": sum(1 for e in evs if e["kind"] == "submit"),
        "queries": sum(1 for e in evs if e["kind"] == "query"),
        "dispatches_while_invalid": sum(1 for e in evs if e["kind"] == "submit" and _invalid(e["time"], invalid_from)),
        "effects_while_invalid": sum(1 for e in mine if _invalid(e["committed_at"], invalid_from)),
        "provider_flagged_unauthorized_effects": sum(1 for e in mine if not e.get("authorized_at_commit", True)),
        "commits_after_hold": sum(1 for e in mine if final == "HOLD" and e["committed_at"] > decision_time),
    }
