# Comparison Summary

This comparison evaluates the governance-aware reference method against three
deterministic baselines over the same 12 predefined cases.

## Methods

- `reference_governance_aware`: Existing Governance -> Execution behavior.
- `baseline_a_direct_without_governance`: Executes mapped adapter calls directly and records malformed executable mappings as failures instead of governance safe aborts.
- `baseline_b_single_stage_execution`: Selects one deterministic adapter capability directly from the case payload, bypassing separate planning and matching stages.
- `baseline_c_without_policy_filtering`: Keeps mapped adapter selections but converts policy BLOCK and REQUIRE_APPROVAL decisions into ALLOW decisions.

## Aggregate Results

| Method | Success Rate | Partial Rate | Blocked Rate | Safe-Abort Rate | Failed Rate | Gov. Intervention | Coverage |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Reference: governance-aware execution | 0.25 | 0.25 | 0.25 | 0.25 | 0.0 | 0.75 | 0.2 |
| Baseline A: direct execution without governance | 0.75 | 0.0 | 0.0 | 0.0 | 0.25 | 0.0 | 0.6 |
| Baseline B: single-stage execution | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 |
| Baseline C: without governance-aware policy filtering | 0.75 | 0.0 | 0.0 | 0.25 | 0.0 | 0.25 | 0.6 |

## Policy-Centric Results

| Method | Gov. Decision Acc. | Final Outcome Acc. | Policy Compliance | Unsafe Exec. | Approval Bypass | Invalid Mapping Containment |
| --- | --- | --- | --- | --- | --- | --- |
| Reference: governance-aware execution | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 | 1.0 |
| Baseline A: direct execution without governance | 0.0 | 0.25 | 0.25 | 1.0 | 1.0 | 0.0 |
| Baseline B: single-stage execution | 0.25 | 0.25 | 0.25 | 1.0 | 1.0 | 0.0 |
| Baseline C: without governance-aware policy filtering | 0.5 | 0.5 | 0.5 | 1.0 | 1.0 | 1.0 |

## Timing Results

| Method | Planning ms | Matching ms | Governance ms | Execution ms | Total ms |
| --- | --- | --- | --- | --- | --- |
| Reference: governance-aware execution | 0.006274 | 2.406382 | 2.370497 | 0.011601 | 4.870121 |
| Baseline A: direct execution without governance | 0.0 | 0.0 | 0.0 | 0.003754 | 0.007274 |
| Baseline B: single-stage execution | 0.002368 | 0.0 | 0.0 | 0.005104 | 0.007917 |
| Baseline C: without governance-aware policy filtering | 0.0 | 0.0 | 0.003295 | 0.005167 | 0.008913 |

## Interpretation Notes

The reference method preserves governance interventions for approval-required,
blocked, and safe-abort cases. The baselines intentionally remove one or more
architectural protections, so higher execution coverage can correspond to
unsafe or policy-insensitive execution rather than better supervisory behavior.

The policy-centric metrics compare each run against explicit gold labels:
expected final status, expected governance decision, and whether automatic
execution is allowed.

All outputs are deterministic and derived from the local scenario cases in
`app/evaluation/scenario_cases.py`.
