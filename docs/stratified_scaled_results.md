# Stratified Scaled Results

The stratified metrics table groups results by runtime and each experimental
factor: scenario family, workflow length, governance pattern, adapter mix,
approval condition, and failure condition.

## Reference Runtime By Scenario Family

| factor_value | count | policy_compliance_rate | unsafe_execution_rate | final_outcome_accuracy | trace_completeness | p95_latency_ms |
| --- | --- | --- | --- | --- | --- | --- |
| all_allow | 20 | 1.0 | 0.0 | 1.0 | 1.0 | 0.014716 |
| allow_then_block | 20 | 1.0 | 0.0 | 1.0 | 1.0 | 0.030319 |
| allow_then_require_approval | 20 | 0.5 | 0.0 | 0.75 | 1.0 | 0.020748 |
| allow_then_safe_abort | 20 | 1.0 | 0.0 | 1.0 | 1.0 | 0.017334 |
| invalid_mapping | 20 | 1.0 | 0.0 | 1.0 | 1.0 | 0.01322 |
| malformed_payload | 20 | 1.0 | 0.0 | 1.0 | 1.0 | 0.038515 |
| mixed_allow_approval_block | 20 | 0.75 | 0.0 | 0.75 | 1.0 | 0.018161 |
| mixed_allow_approval_safe_abort | 20 | 1.0 | 0.0 | 1.0 | 1.0 | 0.03054 |
| post_approval_invalid | 20 | 1.0 | 0.0 | 1.0 | 1.0 | 0.021593 |
| post_approval_missing | 20 | 1.0 | 0.0 | 1.0 | 1.0 | 0.027135 |
| post_approval_valid | 20 | 0.0 | 0.0 | 0.0 | 1.0 | 0.013855 |
| unavailable_capability | 20 | 1.0 | 0.0 | 1.0 | 1.0 | 0.01809 |

These rows are intended for empirical depth in a journal manuscript. They make
clear where aggregate metrics are strong and where stress or scope mismatches
lower the overall compliance rate.
