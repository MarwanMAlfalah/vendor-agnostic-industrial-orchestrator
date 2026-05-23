# Aligned Scaled Evaluation Report

This report recomputes the `journal` scaled metrics using
runtime-specific expectations. Original global labels remain present in
`data/results/aligned_scaled_results_journal.csv`; aligned labels are added as
separate columns.

## Metrics By Runtime

| runtime_id | count | original_policy_compliance_rate | aligned_policy_compliance_rate | aligned_final_outcome_accuracy | unsafe_execution_rate | approval_bypass_rate | trace_completeness | alignment_delta_policy_compliance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_a_direct_without_governance | 240 | 0.0 | 0.0 | 0.166667 | 0.583333 | 0.5 | 0.0 | 0.0 |
| baseline_b_single_stage_execution | 240 | 0.083333 | 0.083333 | 0.166667 | 0.0 | 0.0 | 0.0 | 0.0 |
| baseline_c_without_policy_filtering | 240 | 0.5 | 0.416667 | 0.583333 | 0.583333 | 0.5 | 0.0 | -0.083333 |
| langgraph_runtime | 240 | 0.979167 | 1.0 | 1.0 | 0.0 | 0.0 | 1.0 | 0.020833 |
| reference_v1 | 240 | 0.854167 | 1.0 | 1.0 | 0.0 | 0.0 | 1.0 | 0.145833 |

## Why Original And Aligned Metrics Differ

The original metric used one global expected final status per scenario. The
aligned metric compares each runtime against documented capabilities. For
example, `reference_v1` is expected to stop at approval-required checkpoints,
while `langgraph_runtime` may reach `success` after valid controlled approval
continuation. Unsafe execution and approval bypass are never excused by
alignment.
