# Stratified Scaled Results

The stratified metrics table groups results by runtime and each experimental
factor: scenario family, workflow length, governance pattern, adapter mix,
approval condition, and failure condition.

## Reference Runtime By Scenario Family

| factor_value | count | policy_compliance_rate | unsafe_execution_rate | final_outcome_accuracy | trace_completeness | p95_latency_ms |
| --- | --- | --- | --- | --- | --- | --- |
| all_allow | 20 | 1.0 | None | 1.0 | 1.0 | 0.014307 |
| allow_then_block | 20 | 1.0 | 0.0 | 1.0 | 1.0 | 0.031131 |
| allow_then_require_approval | 20 | 0.5 | 0.0 | 0.75 | 1.0 | 0.021898 |
| allow_then_safe_abort | 20 | 1.0 | None | 1.0 | 1.0 | 0.014825 |
| invalid_mapping | 20 | 1.0 | None | 1.0 | 1.0 | 0.013339 |
| malformed_payload | 20 | 1.0 | None | 1.0 | 1.0 | 0.037396 |
| mixed_allow_approval_block | 20 | 0.75 | 0.0 | 0.75 | 1.0 | 0.02124 |
| mixed_allow_approval_safe_abort | 20 | 1.0 | 0.0 | 1.0 | 1.0 | 0.028454 |
| post_approval_invalid | 20 | 1.0 | 0.0 | 1.0 | 1.0 | 0.02079 |
| post_approval_missing | 20 | 1.0 | 0.0 | 1.0 | 1.0 | 0.026702 |
| post_approval_valid | 20 | 0.0 | 0.0 | 0.0 | 1.0 | 0.014872 |
| unavailable_capability | 20 | 1.0 | None | 1.0 | 1.0 | 0.018069 |

These rows are intended for empirical depth in a journal manuscript. They make
clear where aggregate metrics are strong and where stress or scope mismatches
lower the overall compliance rate.
