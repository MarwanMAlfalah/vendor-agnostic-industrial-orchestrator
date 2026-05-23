# Scaled Statistical Analysis

Profile: `journal`.

The scaled evaluation is deterministic. Wilson 95% confidence intervals are
reported as scenario-distribution intervals: they summarize uncertainty from
the finite generated scenario set, not stochastic LLM sampling uncertainty.

## Runtime Proportion Metrics

| group_id | metric | numerator | denominator | rate | wilson_95_low | wilson_95_high |
| --- | --- | --- | --- | --- | --- | --- |
| baseline_a_direct_without_governance | policy_compliance_rate | 0 | 240 | 0.0 | 0.0 | 0.015754 |
| baseline_a_direct_without_governance | unsafe_execution_rate | 140 | 240 | 0.583333 | 0.520127 | 0.643914 |
| baseline_a_direct_without_governance | final_outcome_accuracy | 40 | 240 | 0.166667 | 0.124848 | 0.218988 |
| baseline_b_single_stage_execution | policy_compliance_rate | 20 | 240 | 0.083333 | 0.054591 | 0.125203 |
| baseline_b_single_stage_execution | unsafe_execution_rate | 0 | 240 | 0.0 | 0.0 | 0.015754 |
| baseline_b_single_stage_execution | final_outcome_accuracy | 40 | 240 | 0.166667 | 0.124848 | 0.218988 |
| baseline_c_without_policy_filtering | policy_compliance_rate | 120 | 240 | 0.5 | 0.437243 | 0.562757 |
| baseline_c_without_policy_filtering | unsafe_execution_rate | 140 | 240 | 0.583333 | 0.520127 | 0.643914 |
| baseline_c_without_policy_filtering | final_outcome_accuracy | 140 | 240 | 0.583333 | 0.520127 | 0.643914 |
| langgraph_runtime | policy_compliance_rate | 235 | 240 | 0.979167 | 0.952167 | 0.991069 |
| langgraph_runtime | unsafe_execution_rate | 0 | 240 | 0.0 | 0.0 | 0.015754 |
| langgraph_runtime | final_outcome_accuracy | 235 | 240 | 0.979167 | 0.952167 | 0.991069 |
| reference_v1 | policy_compliance_rate | 205 | 240 | 0.854167 | 0.803938 | 0.893236 |
| reference_v1 | unsafe_execution_rate | 0 | 240 | 0.0 | 0.0 | 0.015754 |
| reference_v1 | final_outcome_accuracy | 210 | 240 | 0.875 | 0.827164 | 0.911021 |

## Effect Sizes

Effect sizes compare `reference_v1` with deterministic baselines. Relative
risk and number-needed-to-prevent values are omitted where the denominator is
zero or the absolute risk reduction is not positive.

## Latency

Latency summaries are grouped by runtime and scenario family and include mean,
median, p50, p95, min, max, and standard deviation.

## Paired Comparisons

Paired differences compare outcomes scenario-by-scenario where `reference_v1`
and a baseline both executed the same generated case. These are descriptive
deterministic comparisons rather than claims of stochastic statistical
significance.
