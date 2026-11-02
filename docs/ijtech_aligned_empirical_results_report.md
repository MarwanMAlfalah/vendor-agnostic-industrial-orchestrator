# IJTech Aligned Empirical Results Report

The aligned empirical results are deterministic and synthetic. Metrics are
scenario-distribution estimates over the generated journal profile, not
production reliability claims.

Runtime-specific expectations are used for fair comparison. Baselines remain
intentionally weak in governance to reveal policy risk. LangGraph value is
evaluated only for capabilities it actually supports, including controlled
approval continuation. `reference_v1` remains useful as a policy-correct
non-continuation runtime that records approval requirements without a workflow-wide pause.

## Main Runtime Results

| runtime_id | aligned_policy_compliance_rate | aligned_final_outcome_accuracy | unsafe_execution_rate | approval_bypass_rate | trace_completeness |
| --- | --- | --- | --- | --- | --- |
| baseline_a_direct_without_governance | 0.0 | 0.166667 | 1.0 | 1.0 | 0.0 |
| baseline_b_single_stage_execution | 0.083333 | 0.166667 | 0.0 | 0.0 | 0.0 |
| baseline_c_without_policy_filtering | 0.416667 | 0.583333 | 1.0 | 1.0 | 0.0 |
| langgraph_runtime | 1.0 | 1.0 | 0.0 | 0.0 | 1.0 |
| reference_v1 | 1.0 | 1.0 | 0.0 | 0.0 | 1.0 |

## Baseline Comparison

| proposed_runtime | baseline_runtime | delta_aligned_policy_compliance | delta_unsafe_execution |
| --- | --- | --- | --- |
| reference_v1 | baseline_a_direct_without_governance | 1.0 | 1.0 |
| reference_v1 | baseline_b_single_stage_execution | 0.916667 | 0.0 |
| reference_v1 | baseline_c_without_policy_filtering | 0.583333 | 1.0 |
| langgraph_runtime | baseline_a_direct_without_governance | 1.0 | 1.0 |
| langgraph_runtime | baseline_b_single_stage_execution | 0.916667 | 0.0 |
| langgraph_runtime | baseline_c_without_policy_filtering | 0.583333 | 1.0 |

## Interpretation

Alignment is not metric manipulation: original labels are retained, every rule
is documented, and unsafe execution remains non-compliant. The corrected view
separates runtime capability scope from actual policy violations.
