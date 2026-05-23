# Evaluation Summary

The current evaluation uses 12 deterministic governance-aware execution runs.
The cases are predefined in code and executed through the same
`ExecutionAgent` used by the API. Results are exported to CSV and JSON under
`data/results/`.

## Evaluation Design

The evaluation covers four governance categories, with three cases per
category:

| Category | Runs | Meaning in the Prototype |
|---|---:|---|
| `ALLOW` | 3 | Governance permits the step. Adapter-backed steps execute, while non-executable reasoning or recording steps are skipped cleanly. |
| `REQUIRE_APPROVAL` | 3 | Governance identifies a sensitive vendor action. The step is not executed automatically and is marked `approval_required`. |
| `BLOCK` | 3 | Governance blocks a forbidden action such as `shutdown_line`. Execution stops without invoking the adapter. |
| `SAFE_ABORT` | 3 | Governance detects an invalid execution mapping and safely stops execution. |

The scenarios vary machine identifiers, action names, goal identifiers, notes,
and selected capabilities where appropriate. The evaluation is deterministic and
does not use random sampling, LLM reasoning, live equipment, or external
services.

## Interpretation

The evaluation is designed to test whether the prototype preserves structured
control over execution decisions. It does not measure industrial performance,
operator workload, model accuracy, or real-world safety. Instead, it verifies
that governance decisions are represented consistently in execution outputs and
that adapter calls occur only when explicitly allowed.
