# Stratified Scaled Results

The stratified metrics table groups results by runtime and each experimental
factor: scenario family, workflow length, governance pattern, adapter mix,
approval condition, and failure condition.

## Reference Runtime By Scenario Family

| factor_value | count | policy_compliance_rate | unsafe_execution_rate | final_outcome_accuracy | trace_completeness | p95_latency_ms |
| --- | --- | --- | --- | --- | --- | --- |
| all_allow | 20 | 1.0 | 0.0 | 1.0 | 1.0 | 0.053471 |
| allow_then_block | 20 | 1.0 | 0.0 | 1.0 | 1.0 | 0.071121 |
| allow_then_require_approval | 20 | 0.5 | 0.0 | 0.75 | 1.0 | 0.066084 |
| allow_then_safe_abort | 20 | 1.0 | 0.0 | 1.0 | 1.0 | 0.048996 |
| invalid_mapping | 20 | 1.0 | 0.0 | 1.0 | 1.0 | 0.052908 |
| malformed_payload | 20 | 1.0 | 0.0 | 1.0 | 1.0 | 1.686885 |
| mixed_allow_approval_block | 20 | 0.75 | 0.0 | 0.75 | 1.0 | 0.058614 |
| mixed_allow_approval_safe_abort | 20 | 1.0 | 0.0 | 1.0 | 1.0 | 0.0951 |
| post_approval_invalid | 20 | 1.0 | 0.0 | 1.0 | 1.0 | 0.063732 |
| post_approval_missing | 20 | 1.0 | 0.0 | 1.0 | 1.0 | 0.070171 |
| post_approval_valid | 20 | 0.0 | 0.0 | 0.0 | 1.0 | 0.059263 |
| unavailable_capability | 20 | 1.0 | 0.0 | 1.0 | 1.0 | 0.055875 |

These rows are intended for empirical depth in a journal manuscript. They make
clear where aggregate metrics are strong and where stress or scope mismatches
lower the overall compliance rate.
