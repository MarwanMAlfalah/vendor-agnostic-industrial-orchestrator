# Result Metadata Gap Report

This audit scans generated result CSV/JSON artifacts under `data/results` and checks whether each file contains the metadata fields `run_id`, `git_sha`, `profile`, `deployment_mode`, `runtime_id`, and `timestamp`. The audit is structural only and does not modify result values.

## Summary

- Files scanned: `70`
- `run_id` present in `7` files and missing in `63` files.
- `git_sha` present in `10` files and missing in `60` files.
- `profile` present in `11` files and missing in `59` files.
- `deployment_mode` present in `9` files and missing in `61` files.
- `runtime_id` present in `40` files and missing in `30` files.
- `timestamp` present in `0` files and missing in `70` files.
- Files containing all checked fields: `0`

## Interpretation

- Historical raw artifacts may miss metadata because many were generated before deployment-mode and traceability fields were introduced.
- The raw result files should not be rewritten to hide provenance gaps or alter their original structure.
- Final evidence traceability is now provided through `data/results/RESULTS_MANIFEST.json`, `data/results/RESULTS_METADATA_INDEX.csv`, and `data/results/RESULTS_METADATA_INDEX.json`.
- Manuscript-facing normalized copies with explicit metadata are available at `data/results/final_manuscript_results_with_metadata.csv` and `data/results/deployment_mode_comparison_with_metadata.csv`.
- `timestamp_utc` in the metadata index records the indexing pass time; it is not backfilled into historical raw artifacts.
- `RESULTS_MANIFEST.json` and the `RESULTS_METADATA_INDEX.*` files are self-referential metadata artifacts; the metadata index excludes those files to avoid unstable self-hashes, while `RESULTS_MANIFEST.json` remains the authoritative hash manifest for current result files except itself.

## Field Presence Matrix

| File | Format | Shape/records | run_id | git_sha | profile | deployment_mode | runtime_id | timestamp | Missing fields |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `data/results/RESULTS_MANIFEST.json` | json | object; object | missing | present | missing | missing | missing | missing | run_id, profile, deployment_mode, runtime_id, timestamp |
| `data/results/RESULTS_METADATA_INDEX.csv` | csv | csv; 68 rows | present | present | present | present | missing | missing | runtime_id, timestamp |
| `data/results/RESULTS_METADATA_INDEX.json` | json | object; object | present | present | present | present | missing | missing | runtime_id, timestamp |
| `data/results/ablation_results.csv` | csv | csv; 6 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/ablation_summary.json` | json | object; object | missing | missing | present | missing | present | missing | run_id, git_sha, deployment_mode, timestamp |
| `data/results/aligned_confusion_matrix_final_status_journal.csv` | csv | csv; 72 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/aligned_error_cases_journal.csv` | csv | csv; 720 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/aligned_scaled_metrics_by_runtime.csv` | csv | csv; 5 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/aligned_scaled_metrics_by_scope.csv` | csv | csv; 10 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/aligned_scaled_results_journal.csv` | csv | csv; 1200 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/aligned_scaled_summary_journal.json` | json | object; object | missing | missing | present | missing | present | missing | run_id, git_sha, deployment_mode, timestamp |
| `data/results/baseline_summary.json` | json | object; object | missing | missing | missing | missing | missing | missing | run_id, git_sha, profile, deployment_mode, runtime_id, timestamp |
| `data/results/comparison_results.csv` | csv | csv; 4 rows | missing | missing | missing | missing | missing | missing | run_id, git_sha, profile, deployment_mode, runtime_id, timestamp |
| `data/results/confusion_matrix_final_status_journal.csv` | csv | csv; 71 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/confusion_matrix_governance_decision_journal.csv` | csv | csv; 70 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/containerized_integration_results.csv` | csv | csv; 5 rows | missing | missing | missing | missing | missing | missing | run_id, git_sha, profile, deployment_mode, runtime_id, timestamp |
| `data/results/containerized_integration_summary.json` | json | object; object | missing | present | missing | present | missing | missing | run_id, profile, runtime_id, timestamp |
| `data/results/crash_restart_demo_summary.json` | json | object; object | missing | missing | missing | missing | missing | missing | run_id, git_sha, profile, deployment_mode, runtime_id, timestamp |
| `data/results/deployment_mode_comparison.csv` | csv | csv; 6 rows | missing | missing | missing | present | missing | missing | run_id, git_sha, profile, runtime_id, timestamp |
| `data/results/deployment_mode_comparison_with_metadata.csv` | csv | csv; 6 rows | present | present | present | present | missing | missing | runtime_id, timestamp |
| `data/results/evaluation_results_20260513T023524Z.csv` | csv | csv; 4 rows | missing | missing | missing | missing | missing | missing | run_id, git_sha, profile, deployment_mode, runtime_id, timestamp |
| `data/results/evaluation_results_20260513T023524Z.json` | json | list; 4 | present | missing | missing | missing | missing | missing | git_sha, profile, deployment_mode, runtime_id, timestamp |
| `data/results/evaluation_results_20260513T024206Z.csv` | csv | csv; 12 rows | missing | missing | missing | missing | missing | missing | run_id, git_sha, profile, deployment_mode, runtime_id, timestamp |
| `data/results/evaluation_results_20260513T024206Z.json` | json | list; 12 | present | missing | missing | missing | missing | missing | git_sha, profile, deployment_mode, runtime_id, timestamp |
| `data/results/evaluation_summary_20260513T024206Z.json` | json | object; object | missing | missing | missing | missing | missing | missing | run_id, git_sha, profile, deployment_mode, runtime_id, timestamp |
| `data/results/evidence_manifest.json` | json | object; object | missing | present | missing | missing | missing | missing | run_id, profile, deployment_mode, runtime_id, timestamp |
| `data/results/final_manuscript_results_with_metadata.csv` | csv | csv; 11 rows | present | present | present | present | missing | missing | runtime_id, timestamp |
| `data/results/final_results_table.csv` | csv | csv; 15 rows | missing | missing | missing | missing | missing | missing | run_id, git_sha, profile, deployment_mode, runtime_id, timestamp |
| `data/results/final_unified_metrics.csv` | csv | csv; 11 rows | missing | missing | missing | missing | missing | missing | run_id, git_sha, profile, deployment_mode, runtime_id, timestamp |
| `data/results/final_unified_metrics.json` | json | object; object | missing | missing | missing | missing | missing | missing | run_id, git_sha, profile, deployment_mode, runtime_id, timestamp |
| `data/results/ijtech_figure_data_latency_distribution.csv` | csv | csv; 1200 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/ijtech_figure_data_policy_vs_unsafe.csv` | csv | csv; 5 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/ijtech_figure_data_trace_recovery.csv` | csv | csv; 5 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/ijtech_table_1_scenario_design.csv` | csv | csv; 130 rows | missing | missing | missing | missing | missing | missing | run_id, git_sha, profile, deployment_mode, runtime_id, timestamp |
| `data/results/ijtech_table_2_main_results.csv` | csv | csv; 35 rows | missing | missing | missing | missing | missing | missing | run_id, git_sha, profile, deployment_mode, runtime_id, timestamp |
| `data/results/ijtech_table_2_main_results_aligned.csv` | csv | csv; 5 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/ijtech_table_3_baseline_comparison.csv` | csv | csv; 3 rows | missing | missing | missing | missing | missing | missing | run_id, git_sha, profile, deployment_mode, runtime_id, timestamp |
| `data/results/ijtech_table_3_baseline_comparison_aligned.csv` | csv | csv; 6 rows | missing | missing | missing | missing | missing | missing | run_id, git_sha, profile, deployment_mode, runtime_id, timestamp |
| `data/results/ijtech_table_4_ablation_results.csv` | csv | csv; 6 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/ijtech_table_4_supported_vs_stress_aligned.csv` | csv | csv; 10 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/ijtech_table_5_latency_summary.csv` | csv | csv; 65 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/k8s_reproducibility_results.csv` | csv | csv; 1 rows | missing | present | missing | present | missing | missing | run_id, profile, runtime_id, timestamp |
| `data/results/k8s_reproducibility_summary.json` | json | object; object | missing | present | present | present | missing | missing | run_id, runtime_id, timestamp |
| `data/results/langgraph_comparison_results.csv` | csv | csv; 2 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/langgraph_summary.json` | json | object; object | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/langsmith_trace_manifest.csv` | csv | csv; 7 rows | present | present | missing | present | present | missing | profile, timestamp |
| `data/results/mixed_comparison_results.csv` | csv | csv; 2 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/post_approval_comparison_results.csv` | csv | csv; 2 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/post_approval_summary.json` | json | object; object | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/runtime_capability_profiles.json` | json | object; object | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/scaled_error_cases_extended.csv` | csv | csv; 1584 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/scaled_error_cases_journal.csv` | csv | csv; 760 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/scaled_evaluation_results_default.csv` | csv | csv; 600 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/scaled_evaluation_results_default.json` | json | list; 600 | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/scaled_evaluation_results_extended.csv` | csv | csv; 2500 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/scaled_evaluation_results_extended.json` | json | list; 2500 | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/scaled_evaluation_results_journal.csv` | csv | csv; 1200 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/scaled_evaluation_results_journal.json` | json | list; 1200 | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/scaled_evaluation_summary_default.json` | json | object; object | missing | missing | present | missing | missing | missing | run_id, git_sha, deployment_mode, runtime_id, timestamp |
| `data/results/scaled_evaluation_summary_extended.json` | json | object; object | missing | missing | present | missing | missing | missing | run_id, git_sha, deployment_mode, runtime_id, timestamp |
| `data/results/scaled_evaluation_summary_journal.json` | json | object; object | missing | missing | present | missing | missing | missing | run_id, git_sha, deployment_mode, runtime_id, timestamp |
| `data/results/scaled_metrics_by_factor_extended.csv` | csv | csv; 230 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/scaled_metrics_by_factor_journal.csv` | csv | csv; 230 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/scaled_statistical_summary_journal.csv` | csv | csv; 190 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/scaled_statistical_summary_journal.json` | json | object; object | missing | missing | present | missing | present | missing | run_id, git_sha, deployment_mode, timestamp |
| `data/results/scenario_factor_balance_journal.csv` | csv | csv; 34 rows | missing | missing | missing | missing | missing | missing | run_id, git_sha, profile, deployment_mode, runtime_id, timestamp |
| `data/results/stress_scope_metrics_aligned_journal.csv` | csv | csv; 5 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/stress_scope_metrics_journal.csv` | csv | csv; 5 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/supported_scope_metrics_aligned_journal.csv` | csv | csv; 5 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |
| `data/results/supported_scope_metrics_journal.csv` | csv | csv; 5 rows | missing | missing | missing | missing | present | missing | run_id, git_sha, profile, deployment_mode, timestamp |

## Notes

- Several legacy evaluation artifacts predate deployment metadata and therefore omit `git_sha`, `deployment_mode`, and `timestamp`.
- Some aggregate summaries include `profile` but not per-run identifiers such as `run_id`.
- Deployment-focused artifacts such as Docker, Kubernetes, evidence, and LangSmith manifests are more likely to include `git_sha` and `deployment_mode`.
- Missing fields are reported as gaps only; this report does not infer or backfill metadata.
