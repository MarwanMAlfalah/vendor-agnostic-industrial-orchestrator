# Results Table

The tables below summarize the latest evaluation run:

- CSV: `data/results/evaluation_results_20260513T024206Z.csv`
- Summary JSON: `data/results/evaluation_summary_20260513T024206Z.json`

## Outcome Counts

| Outcome | Count | Rate |
|---|---:|---:|
| Success | 3 | 0.25 |
| Partial Success | 3 | 0.25 |
| Blocked | 3 | 0.25 |
| Safe Aborted | 3 | 0.25 |
| Failed | 0 | 0.00 |

## Derived Metrics

| Metric | Value |
|---|---:|
| total_runs | 12 |
| governance_intervention_rate | 0.75 |
| average_completed_steps | 0.25 |
| average_skipped_steps | 1.00 |
| unexpected_failure_rate | 0.00 |

The governance intervention rate counts runs with at least one
`REQUIRE_APPROVAL`, `BLOCK`, `SAFE_ABORT`, or `FALLBACK` governance decision.
The unexpected failure rate corresponds to the observed failed execution rate.
