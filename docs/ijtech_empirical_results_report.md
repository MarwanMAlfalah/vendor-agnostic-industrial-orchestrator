# IJTech Empirical Results Report

This report summarizes the `journal` deterministic scaled evaluation package
over 240 generated scenarios. The evaluation is prototype-level
and does not claim production deployment, live PLC validation, certified
safety, or stochastic LLM performance.

## Scenario Scaling Summary

The generated set balances workflow length, governance pattern, adapter mix,
approval condition, containment condition, and runtime coverage. Scenario
records include expected governance sequences, final statuses, policy labels,
trace markers, industrial context, RAMI alignment, and interoperability role.

## Main Empirical Findings

| group_id | metric | rate | wilson_95_low | wilson_95_high |
| --- | --- | --- | --- | --- |
| baseline_a_direct_without_governance | policy_compliance_rate | 0.0 | 0.0 | 0.015754 |
| baseline_a_direct_without_governance | unsafe_execution_rate | 0.583333 | 0.520127 | 0.643914 |
| baseline_a_direct_without_governance | final_outcome_accuracy | 0.166667 | 0.124848 | 0.218988 |
| baseline_b_single_stage_execution | policy_compliance_rate | 0.083333 | 0.054591 | 0.125203 |
| baseline_b_single_stage_execution | unsafe_execution_rate | 0.0 | 0.0 | 0.015754 |
| baseline_b_single_stage_execution | final_outcome_accuracy | 0.166667 | 0.124848 | 0.218988 |
| baseline_c_without_policy_filtering | policy_compliance_rate | 0.5 | 0.437243 | 0.562757 |
| baseline_c_without_policy_filtering | unsafe_execution_rate | 0.583333 | 0.520127 | 0.643914 |
| baseline_c_without_policy_filtering | final_outcome_accuracy | 0.583333 | 0.520127 | 0.643914 |
| langgraph_runtime | policy_compliance_rate | 0.979167 | 0.952167 | 0.991069 |
| langgraph_runtime | unsafe_execution_rate | 0.0 | 0.0 | 0.015754 |
| langgraph_runtime | final_outcome_accuracy | 0.979167 | 0.952167 | 0.991069 |
| reference_v1 | policy_compliance_rate | 0.854167 | 0.803938 | 0.893236 |
| reference_v1 | unsafe_execution_rate | 0.0 | 0.0 | 0.015754 |
| reference_v1 | final_outcome_accuracy | 0.875 | 0.827164 | 0.911021 |

## Baseline Comparison

| comparison | delta_policy_compliance | delta_unsafe_execution | relative_risk_unsafe_execution | absolute_risk_reduction | number_needed_to_prevent_unsafe_execution |
| --- | --- | --- | --- | --- | --- |
| reference_v1_vs_baseline_a_direct_without_governance | 0.854167 | 0.583333 | 0.0 | 0.583333 | 1.714287 |
| reference_v1_vs_baseline_b_single_stage_execution | 0.770834 | 0.0 | None | 0.0 | None |
| reference_v1_vs_baseline_c_without_policy_filtering | 0.354167 | 0.583333 | 0.0 | 0.583333 | 1.714287 |

## Ablation Interpretation

The ablation runner writes `data/results/ijtech_table_4_ablation_results.csv`.
Implemented ablations reuse deterministic baselines where they directly
correspond to removed governance or matching stages. Conceptual ablations are
marked as not implemented rather than simulated.

## Limitations

The scenarios are synthetic and deterministic. They exercise mock adapters and
fixed governance labels, not live industrial equipment. Latency values are
local runtime measurements and should not be interpreted as deployment
benchmarks. LangSmith traces provide observability evidence only.

## Journal Extension Value

The package strengthens a journal extension by adding scaled scenario coverage,
confidence intervals over the scenario distribution, baseline effect sizes,
paired deterministic comparisons, ablation reporting, and table/figure data
that can be audited from reproducible artifacts.
