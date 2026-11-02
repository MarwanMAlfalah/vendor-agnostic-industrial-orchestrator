# IJTech Tables Ready For Manuscript

All tables should remain editable in the manuscript source. Do not use screenshots of tables. Values below come from the current deterministic project evidence and should not be changed unless the underlying generated results are intentionally regenerated.

## Table 1. Scenario Design

Source: `data/results/ijtech_table_1_scenario_design.csv` and `data/results/scaled_evaluation_summary_journal.json`.

| Factor | Journal profile design |
| --- | --- |
| Scenario count | 240 |
| Workflow length | 80 short, 80 medium, 80 long |
| Governance patterns | 12 patterns, 20 scenarios each |
| Adapter mix | OPC UA only; REST only; legacy only; OPC UA + REST; OPC UA + legacy; REST + legacy; OPC UA + REST + legacy |
| Approval conditions | no approval required; missing approval; invalid approval; valid approval; approval with invalidated mapping |
| Failure or containment conditions | none; blocked action condition; safe-abort condition; invalid adapter mapping; malformed payload; unavailable capability; unsupported capability |
| Extended profile | 500 scenarios using the same factor structure |

Suggested caption: Deterministic scenario design for the IJTech journal profile. The profile uses mock adapters and generated scenarios; it is not field deployment data.

## Table 2. Main Original And Aligned Results

Source: `data/results/ijtech_table_2_main_results_aligned.csv`.

| Runtime | Original policy compliance | Aligned policy compliance | Aligned final outcome accuracy | Unsafe execution | Approval bypass | Invalid mapping containment | Trace completeness |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `baseline_a_direct_without_governance` | 0.0 | 0.0 | 0.166667 | 1.0 | 1.0 | 0.0 | 0.0 |
| `baseline_b_single_stage_execution` | 0.083333 | 0.083333 | 0.166667 | 0.0 | 0.0 | 0.0 | 0.0 |
| `baseline_c_without_policy_filtering` | 0.5 | 0.416667 | 0.583333 | 1.0 | 1.0 | 1.0 | 0.0 |
| `langgraph_runtime` | 0.979167 | 1.0 | 1.0 | 0.0 | 0.0 | 1.0 | 1.0 |
| `reference_v1` | 0.854167 | 1.0 | 1.0 | 0.0 | 0.0 | 1.0 | 1.0 |

Suggested caption: Main deterministic journal-profile results with original labels and runtime-aligned expectations. Alignment preserves original labels and keeps unsafe execution and approval bypass non-compliant for all runtimes.

## Table 3. Baseline Comparison

Source: `data/results/ijtech_table_3_baseline_comparison_aligned.csv`.

| Proposed runtime | Baseline runtime | Delta aligned policy compliance | Delta unsafe execution |
| --- | --- | ---: | ---: |
| `reference_v1` | `baseline_a_direct_without_governance` | 1.0 | 1.0 |
| `reference_v1` | `baseline_b_single_stage_execution` | 0.916667 | 0.0 |
| `reference_v1` | `baseline_c_without_policy_filtering` | 0.583333 | 1.0 |
| `langgraph_runtime` | `baseline_a_direct_without_governance` | 1.0 | 1.0 |
| `langgraph_runtime` | `baseline_b_single_stage_execution` | 0.916667 | 0.0 |
| `langgraph_runtime` | `baseline_c_without_policy_filtering` | 0.583333 | 1.0 |

Suggested caption: Aligned policy-compliance improvement and unsafe-execution reduction relative to deterministic governance-ablated baselines.

## Table 4. Supported Versus Stress Scope

Source: `data/results/ijtech_table_4_supported_vs_stress_aligned.csv`.

| Runtime | Scope | Scenario count | Aligned policy compliance | Aligned final outcome accuracy | Unsafe execution | Trace completeness |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `baseline_a_direct_without_governance` | stress | 220 | 0.0 | 0.090909 | 1.0 | 0.0 |
| `baseline_b_single_stage_execution` | stress | 220 | 0.0 | 0.090909 | 0.0 | 0.0 |
| `baseline_c_without_policy_filtering` | stress | 180 | 0.222222 | 0.444444 | 1.0 | 0.0 |
| `langgraph_runtime` | stress | 110 | 1.0 | 1.0 | 0.0 | 1.0 |
| `reference_v1` | stress | 115 | 1.0 | 1.0 | 0.0 | 1.0 |
| `baseline_a_direct_without_governance` | supported | 20 | 0.0 | 1.0 | N/A | 0.0 |
| `baseline_b_single_stage_execution` | supported | 20 | 1.0 | 1.0 | N/A | 0.0 |
| `baseline_c_without_policy_filtering` | supported | 60 | 1.0 | 1.0 | N/A | 0.0 |
| `langgraph_runtime` | supported | 130 | 1.0 | 1.0 | 0.0 | 1.0 |
| `reference_v1` | supported | 125 | 1.0 | 1.0 | 0.0 | 1.0 |

Suggested caption: Runtime-specific supported and stress scope results. Scenario counts differ because scope is defined relative to each runtime's capability profile.

## Table 5. Latency Summary

Source: `data/results/ijtech_table_5_latency_summary.csv`.

| Runtime | n | Mean latency ms | Median latency ms | p95 latency ms |
| --- | ---: | ---: | ---: | ---: |
| `baseline_a_direct_without_governance` | 240 | 0.016961 | 0.016583 | 0.026089 |
| `baseline_b_single_stage_execution` | 240 | 0.009832 | 0.009583 | 0.011291 |
| `baseline_c_without_policy_filtering` | 240 | 0.018756 | 0.019208 | 0.028513 |
| `langgraph_runtime` | 240 | 1.269167 | 1.322417 | 1.493592 |
| `reference_v1` | 240 | 0.019837 | 0.018750 | 0.029968 |

Suggested caption: Local deterministic runtime latency. These values are implementation measurements in the test environment and are not real-time industrial control guarantees.

## Table 6. Ablation Summary

Source: `data/results/ijtech_table_4_ablation_results.csv`.

| Variant | Implemented | Runtime | Policy compliance | Unsafe execution | Trace completeness | Note |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `full_system` | True | `reference_v1` | 0.858333 | 0.0 | 1.0 | Reference deterministic governance-aware runtime on default profile |
| `without_governance` | True | `baseline_a_direct_without_governance` | 0.0 | 1.0 | 0.0 | Existing direct execution baseline |
| `without_capability_matching` | True | `baseline_b_single_stage_execution` | 0.083333 | 0.0 | 0.0 | Existing single-stage baseline |
| `without_approval_revalidation` | False | n/a | N/A | N/A | N/A | Conceptual only |
| `without_langgraph_persistence` | False | n/a | N/A | N/A | N/A | Conceptual only |
| `without_trace_observability` | False | n/a | N/A | N/A | N/A | Conceptual only |

Suggested caption: Implemented and conceptual ablation variants. Conceptual variants should not be reported as executed experiments.
