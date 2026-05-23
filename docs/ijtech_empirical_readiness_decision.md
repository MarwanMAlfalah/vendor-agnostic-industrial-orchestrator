# IJTech Empirical Readiness Decision

## Decision

The scaled evaluation is stronger than the previous 12-case evaluation because
it adds deterministic scenario scaling, factor stratification, confidence
intervals over the scenario distribution, confusion matrices, and explicit
stress-scope diagnostics.

It is suitable for a conference paper as empirical prototype evidence. It is a
promising foundation for an IJTech extension, but journal submission should
include this audit, a clear supported-versus-stress framing, and a hardening
plan for unsupported or ambiguous cases.

## What To Emphasize

- Scaled deterministic coverage across governance patterns and adapter mixes.
- Zero unsafe execution for the reference/full-system rows in the audited
  aggregate.
- Stronger empirical depth than the initial 12-case package.
- Honest stress testing rather than only curated success cases.

## What To Frame As Limitations

- Synthetic scenarios and mock adapters.
- `reference_v1` does not represent approved post-approval continuation.
- Stress cases expose robustness limits and label/runtime-scope mismatches.
- LangSmith traces are observability evidence, not deployment evidence.

## Strong Claims

- The prototype can be evaluated reproducibly across hundreds of deterministic
  governance scenarios.
- Governance-removing baselines show substantially higher unsafe execution.
- The audit exposes where aggregate metrics decline rather than hiding those
  cases.

## Preliminary Claims

- Industrial readiness, certified safety, and live PLC behavior remain
  preliminary and unsupported by this artifact set.

## Failure Category Snapshot

| failure_category | count |
| --- | --- |
| unsupported_scenario_scope | 320 |
| true_runtime_limitation | 280 |
| trace_instrumentation_gap | 120 |
| label_runtime_mismatch | 20 |
| unknown_needs_review | 20 |
