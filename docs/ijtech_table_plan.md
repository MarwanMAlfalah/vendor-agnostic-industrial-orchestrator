# IJTech Table Plan

## Table 1: Scenario Design

Source: `data/results/ijtech_table_1_scenario_design.csv`.

Purpose: summarize the deterministic scenario factors, including workflow
length, governance pattern, adapter mix, approval condition, failure condition,
and scenario count.

## Table 2: Main Aligned And Original Results

Source: `data/results/ijtech_table_2_main_results_aligned.csv`.

Purpose: report original policy compliance, aligned policy compliance, final
outcome accuracy, unsafe execution, approval bypass, trace completeness, and
latency by runtime.

## Table 3: Baseline Comparison

Source: `data/results/ijtech_table_3_baseline_comparison_aligned.csv`.

Purpose: compare proposed runtimes with deterministic governance-ablated
baselines using aligned policy compliance deltas and unsafe execution deltas.

## Table 4: Supported Versus Stress Scope

Source: `data/results/ijtech_table_4_supported_vs_stress_aligned.csv`.

Purpose: show runtime-specific supported-scope and stress-scope performance,
including containment and trace completeness.

## Table 5: Ablation Study

Source: `data/results/ijtech_table_4_ablation_results.csv`.

Purpose: report implemented and conceptual ablation variants, making clear
which ablations reuse existing baselines and which are not implemented.

## Table 6: Metric Definitions

Source: `docs/ijtech_mathematical_methodology.md`.

Purpose: define policy compliance, unsafe execution, approval bypass, trace
completeness, restart recovery, latency aggregation, effect sizes, Wilson
intervals, and paired comparisons.

## Formatting Notes

All tables should remain editable in the manuscript source. Avoid screenshots
of tables. Use consistent decimal precision and include notes explaining that
the benchmark is deterministic and synthetic.
