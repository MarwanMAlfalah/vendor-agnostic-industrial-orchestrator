# Supported Scope Versus Stress Scope

Supported-scope scenarios represent behavior within the intended implemented
capability of the prototype. Stress-scope scenarios intentionally exercise
edge conditions: malformed payloads, unavailable capabilities, invalid
mappings, invalid or missing approvals, invalidated post-approval mappings,
and safe-abort paths.

Stress cases are retained and reported separately. They should not be hidden or
removed from aggregate results.

## Supported Scope

| runtime_id | scenario_count | policy_compliance_rate | unsafe_execution_rate | final_outcome_accuracy | trace_completeness | policy_compliance_wilson_95_low | policy_compliance_wilson_95_high |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_a_direct_without_governance | 70 | 0.0 | 0.714286 | 0.571429 | 0.0 | 0.0 | 0.052023 |
| baseline_b_single_stage_execution | 70 | 0.285714 | 0.0 | 0.571429 | 0.0 | 0.193222 | 0.400502 |
| baseline_c_without_policy_filtering | 70 | 0.285714 | 0.714286 | 0.571429 | 0.0 | 0.193222 | 0.400502 |
| langgraph_runtime | 70 | 0.928571 | 0.0 | 0.928571 | 1.0 | 0.843446 | 0.969106 |
| reference_v1 | 70 | 0.642857 | 0.0 | 0.714286 | 1.0 | 0.525884 | 0.744967 |

## Stress Scope

| runtime_id | scenario_count | policy_compliance_rate | unsafe_execution_rate | final_outcome_accuracy | trace_completeness | policy_compliance_wilson_95_low | policy_compliance_wilson_95_high |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_a_direct_without_governance | 170 | 0.0 | 0.529412 | 0.0 | 0.0 | 0.0 | 0.022097 |
| baseline_b_single_stage_execution | 170 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.022097 |
| baseline_c_without_policy_filtering | 170 | 0.588235 | 0.529412 | 0.588235 | 0.0 | 0.5131 | 0.659471 |
| langgraph_runtime | 170 | 1.0 | 0.0 | 1.0 | 1.0 | 0.977903 | 1.0 |
| reference_v1 | 170 | 0.941176 | 0.0 | 0.941176 | 1.0 | 0.895117 | 0.967738 |
