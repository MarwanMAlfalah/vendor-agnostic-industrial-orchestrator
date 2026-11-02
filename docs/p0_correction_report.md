# P0 Factual and Evaluation Correction Report

Working base: `main`, commit `7f087e0`. The working tree was clean before edits. No commit or push was made. Scenario definitions, deterministic seed `20260523`, runtime execution semantics, and baseline implementations are unchanged. Original artifacts were preserved before regeneration; before values are also recoverable from Git HEAD.

## P0-A: reference approval behavior

`ExecutionAgent._run_steps` only breaks on `blocked` or `safe_aborted`. `REQUIRE_APPROVAL` produces an `approval_required` result and iteration continues; a later allowed executable step can run. Public documentation, capability profiles, and aligned expectation explanations now describe decision recording without workflow-wide pause/resume. Controlled approval interrupt/resume belongs to LangGraph. No runtime behavior was changed to rescue the old claim.

Alignment still expects partial success for reference approval cases, because the approval-required step is not executed; partial success does not prove workflow suspension. Those labels and all aligned outcome/compliance results remain unchanged. The previous narrative claiming a stop at an approval checkpoint was unsupported. The test explicitly verifies approval-required followed by allowed execution.

## P0-B: definitions, eligibility, and audit counts

- Unsafe execution = `unsafe_execution_count / unsafe_execution_eligible_count`; eligibility is gold `expected_governance_sequence` containing BLOCK or REQUIRE_APPROVAL. Valid approval cases stay eligible; actual validated approval excludes authorized execution from the numerator. SAFE_ABORT-only execution is a containment issue, outside this metric. Mixed approval/SAFE_ABORT sequences remain eligible.
- Approval bypass = `approval_bypass_count / approval_required_count`; eligibility is gold sequence membership of REQUIRE_APPROVAL, including valid-approval cases.
- Invalid-mapping containment = `invalid_mapping_contained_count / invalid_mapping_case_count`; eligibility is the existing failure-condition set: unsupported capability, invalid adapter mapping, unavailable capability, malformed payload, or safe abort condition.

The new eligibility fields are derived from those existing scenario fields and persisted in CSV/JSON. Aligned labels never redefine eligibility. Small canonical/mixed/post-approval comparisons use the case sequence (or expected decision when no sequence exists), with SAFE_ABORT defining their invalid-mapping cases. Actual validation is carried as evaluation metadata; gold approval permission alone no longer exempts baseline execution.

Incorrect all-run denominators existed in scaled unsafe/bypass summaries, aligned unsafe/bypass/containment summaries, error-audit factor/scope summaries, and ablation unsafe summaries. Statistical unsafe summaries and their Wilson intervals/effect sizes also used all runs. Statistical containment already selected the correct failure-condition subset and remains numerically unchanged. Small comparison rates already selected sensitive cases but excluded valid-approval cases entirely; they now include those cases and exclude only genuinely authorized execution from numerators. Their committed rate values remain unchanged.

Non-mapping rows previously contributed neutral `invalid_mapping_contained=True` to aggregate containment. They remain neutral for existing policy checks but are excluded from conditional containment counts. Scaled summaries now expose containment as well as the two safety rates. The all-pair difference has the distinct name `paired_unsafe_execution_incidence_difference`.

Zero eligibility is `None` / JSON `null` / blank CSV, and conditional Wilson limits are null. No schema requires a false 0.0. Implemented ablations use the same semantics; conceptual, unimplemented ablations retain their explicitly unavailable cells. Existing rounding precision is preserved (scaled/small comparison: four decimals; aligned/statistical/stratified/ablation: six).

## Journal profile: all five paths, before versus after

Each path has 240 runs. The corrected denominators are **140 unsafe-eligible, 120 approval-required, and 100 invalid-mapping cases**, rather than all 240 runs. Values below use the aligned six-decimal reporting layer.

| Runtime | Unsafe execution before → after | Approval bypass before → after | Mapping containment before → after | Aligned compliance (unchanged) | Aligned final accuracy (unchanged) | Trace (unchanged) |
| --- | --- | --- | --- | --- | --- | --- |
| reference_v1 | 0.0 → 0.0 | 0.0 → 0.0 | 1.0 → 1.0 | 1.0 | 1.0 | 1.0 |
| langgraph_runtime | 0.0 → 0.0 | 0.0 → 0.0 | 1.0 → 1.0 | 1.0 | 1.0 | 1.0 |
| baseline_a_direct_without_governance | 0.583333 → 1.0 | 0.5 → 1.0 | 0.583333 → 0.0 | 0.0 | 0.166667 | 0.0 |
| baseline_b_single_stage_execution | 0.0 → 0.0 | 0.0 → 0.0 | 0.583333 → 0.0 | 0.083333 | 0.166667 | 0.0 |
| baseline_c_without_policy_filtering | 0.583333 → 1.0 | 0.5 → 1.0 | 1.0 → 1.0 | 0.416667 | 0.583333 | 0.0 |

For A/C unsafe execution, the count stays 140 but the denominator changes 240 → 140. Approval bypass stays 120 with denominator 240 → 120. A/B containment previously counted 140 neutral non-mapping rows as contained out of 240; it is now 0 genuine contained mappings out of 100. Reference/LangGraph/C containment changes 240/240 → 100/100, leaving the rate 1.0.

Original (unaligned) policy compliance and final accuracy are unchanged: reference 0.8542 / 0.875; LangGraph 0.9792 / 0.9792; A 0.0 / 0.1667; B 0.0833 / 0.1667; C 0.5 / 0.5833. Governance-decision accuracy and trace completeness are unchanged. Repeated wall-clock latency values changed, as expected for local measurements; they are not deterministic numeric guarantees. All pre-existing scaled row fields except `latency_ms` are identical before/after in default, journal, and extended profiles.

## Extended, baseline, and ablation impact

The 500-scenario extended profile has 293 unsafe-eligible, 251 approval-required, and 207 invalid-mapping cases per path. A/C unsafe execution changes 0.586 → 1.0 (293/293), and bypass 0.502 → 1.0 (251/251). Extended factor aggregation of containment for A/B now excludes 293 neutral non-mapping cases and reports 0/207 = 0.0; reference/LangGraph/C report 207/207 = 1.0. Other final-outcome, governance, policy, and trace scores remain unchanged.

The 120-scenario default profile and implemented ablations have denominators 70 unsafe-eligible, 60 approval-required, and 50 mapping cases. The without-governance ablation unsafe rate changes 0.583333 → 1.0; full reference and single-stage ablation unsafe rates stay 0.0. Conceptual ablations remain unimplemented. Canonical baseline A/B/C conditional unsafe rates remain 1.0, with reference 0.0. Baseline B remains unsafe in the canonical set but has zero sensitive execution in the prepared-plan scaled set; zero unsafe execution does not mean it preserves the workflow or contains invalid mappings.

The proposed runtime conclusions retain their measured aligned policy/outcome parity and zero unsafe/bypass rates in this deterministic scope. Baseline weaknesses become more pronounced under the corrected conditional definitions. B's mapping containment is now correctly exposed as zero. No stronger planning, workflow-wide reference approval gating, OS process recovery, or industrial safety conclusion follows.

## P0-C: checkpoint evidence

The demo closes the runtime/checkpointer and recreates a SQLite-backed runtime within the same Python process. It does not spawn or crash an OS process. `process_restarted: true` was removed and replaced by `runtime_recreated`, `sqlite_checkpoint_reopened`, and `same_process_resume`. The artifact records the evidence scope explicitly.

Misleading metric keys were migrated to `checkpoint_reopen_resume_success_rate`, `post_reopen_final_outcome_accuracy`, and `checkpoint_reopen_trace_completeness`. Both valid and invalid approval checkpoint cases pass; these three rates and checkpoint creation/resume rate are 1.0. Observability and Kubernetes-summary consumers use the new keys. Consolidated tables and manuscript-support reports use the corrected vocabulary. Historical script/job/file identifiers remain compatible.

Captured Docker/kind/LangSmith evidence and job logs are historical observations and were not rerun or rewritten. Old labels in those captured logs do not provide OS process-restart evidence. Local reruns do not establish current Kubernetes deployment status or hosted trace validity.

## README, trace, presentation, and stale documents

The README now distinguishes REQUIRE_APPROVAL behavior by runtime, explains same-process SQLite reopen/resume, links journal/extended/aligned/baseline/ablation evidence, names five evaluated paths, and states the prepared-plan boundary (`source_goal=None`). The main introduction describes an in-progress manuscript without publication or journal-ranking claims. Python badge is 3.11+, matching package metadata. MIT and generic LLM-AI badges were removed; no license was invented.

Author formatting uses Marwan M. Al-Falah, MSc Researcher in Intelligent Systems, Peter the Great St. Petersburg Polytechnic University. Elena S. Gebel uses the conservative co-author / academic collaborator role. `prototype_overview.md` is explicitly historical and points to current runtime/deployment capabilities. Earlier numerical audit snapshots are marked historical. Directly affected manuscript narratives/tables and restart evidence descriptions are corrected.

Trace completeness criteria did not change. Scaled reference checks a synthetic execution-result marker; LangGraph checks scenario-specific expected graph markers, while baselines have no such trace. Canonical/mixed layers have their own marker criteria and synthetic reference records. A 1.0 in both runtimes is not evidence of identical stage coverage. These distinctions are documented.

## Portfolio claim check

The claims listed in the handoff remain supported by the corrected evidence, within the stated boundaries:

| Supplied portfolio claim | Result |
| --- | --- |
| 240-scenario deterministic journal profile | Supported: 240 scenarios, five paths, 1,200 result rows; prepared plans, not an end-to-end planning benchmark. |
| Aligned final-outcome accuracy 1.0 for reference/LangGraph | Supported and unchanged under runtime-specific expectations. |
| Aligned policy compliance 1.0 for reference/LangGraph | Supported and unchanged within the deterministic mock-adapter scope. |
| Unsafe execution 0.0 for reference/LangGraph | Supported and unchanged; now auditable as 0/140 each. Baseline A/C values must change to conditional 1.0 if quoted. |
| Trace completeness 1.0 for reference/LangGraph | Numerically supported and unchanged; must disclose runtime-specific marker criteria, not imply identical trace coverage. |

This verifies the claims supplied in the handoff against repository evidence. The current published portfolio page/version was not independently identified; local portfolio candidates did not contain these numerical claims. No portfolio files were edited.

## Validation and integrity

Baseline before edits: 45 tests passed, lint passed, all 84 original manifest hashes valid. Focused tests now cover actual aggregate functions, 2/2 versus 2/10 approval bypass, unsafe and mapping eligibility, mixed dominant SAFE_ABORT cases, actual versus expected approval validation, zero-subset rates and intervals, CSV serialization, reference iteration semantics, and same-process demo metadata.

Deterministic reruns: default, journal, extended scaled profiles; journal alignment; journal/extended error audits; journal statistics and Wilson/effect-size evidence; ablations; canonical, LangGraph, mixed, and post-approval comparisons; SQLite checkpoint demo. No stochastic LLM evaluation was introduced. Existing generator warnings remain: 240-profile duplicate signatures = 62 and block-status consistency warnings = 5; 500-profile duplicates = 112 and block-status warnings = 10. Scenarios were not changed to eliminate them.

Final validation: 67 tests pass (21 focused metric/demo cases and a metadata-index integrity check), lint passes, and `git diff --check` passes. All 85 current manifest entries validate, including the correction report (84 original entries plus this report). Both metadata-index formats retain matching artifact hashes. The original metadata index incorrectly included its own CSV/JSON despite its explicit self-exclusion convention; the refresh removes those two stale self-hashes, leaving 82 auditable index entries. The authoritative manifest still hashes both index files. CSV writers now emit LF so generated tables pass Git whitespace checks. No pre-existing test or lint failures were found; the existing scenario-generator warnings above remain visible.

No reusable manifest/index refresh generator existed in the starting tree; only the hash-verification test was retained. `python3 -m app.evaluation.refresh_evidence_artifacts` now copies generated source metrics into existing consolidated CSV/JSON and manuscript tables, computes actual SHA-256 hashes, and refreshes the existing manifest/index schemas. Original index provenance is retained with refresh notes; normalized regenerated rows identify the base SHA and uncommitted worktree. No hashes or generated result values were manually fabricated.

## Modified files and review state

Concise diff summary: 116 files changed, 30906 insertions(+), 17097 deletions(-). Git diff statistics exclude 4 new files: `app/evaluation/conditional_metrics.py`, `app/evaluation/refresh_evidence_artifacts.py`, `docs/p0_correction_report.md`, `tests/test_conditional_metric_denominators.py`. The large evidence diff comes primarily from regenerated raw rows, explicit eligibility fields, measured latency, and refreshed hashes; no scenario definitions or seeds changed.

Every modified/new file is listed below in the exact `git status --short` output:

```text
 M README.md
 M app/evaluation/baselines.py
 M app/evaluation/metrics.py
 M app/evaluation/run_ablation_study.py
 M app/evaluation/run_aligned_scaled_evaluation.py
 M app/evaluation/run_comparison.py
 M app/evaluation/run_crash_restart_demo.py
 M app/evaluation/run_k8s_reproducibility_summary.py
 M app/evaluation/run_langgraph_comparison.py
 M app/evaluation/run_mixed_workflow_comparison.py
 M app/evaluation/run_post_approval_comparison.py
 M app/evaluation/run_scaled_error_audit.py
 M app/evaluation/run_scaled_evaluation.py
 M app/evaluation/runtime_expectations.py
 M app/evaluation/statistical_analysis.py
 M app/observability/summaries.py
 M data/results/RESULTS_MANIFEST.json
 M data/results/RESULTS_METADATA_INDEX.csv
 M data/results/RESULTS_METADATA_INDEX.json
 M data/results/ablation_results.csv
 M data/results/ablation_summary.json
 M data/results/aligned_confusion_matrix_final_status_journal.csv
 M data/results/aligned_error_cases_journal.csv
 M data/results/aligned_scaled_metrics_by_runtime.csv
 M data/results/aligned_scaled_metrics_by_scope.csv
 M data/results/aligned_scaled_results_journal.csv
 M data/results/aligned_scaled_summary_journal.json
 M data/results/baseline_summary.json
 M data/results/comparison_results.csv
 M data/results/confusion_matrix_final_status_journal.csv
 M data/results/confusion_matrix_governance_decision_journal.csv
 M data/results/crash_restart_demo_summary.json
 M data/results/deployment_mode_comparison.csv
 M data/results/deployment_mode_comparison_with_metadata.csv
 M data/results/final_manuscript_results_with_metadata.csv
 M data/results/final_unified_metrics.csv
 M data/results/final_unified_metrics.json
 M data/results/ijtech_figure_data_latency_distribution.csv
 M data/results/ijtech_figure_data_policy_vs_unsafe.csv
 M data/results/ijtech_figure_data_trace_recovery.csv
 M data/results/ijtech_table_1_scenario_design.csv
 M data/results/ijtech_table_2_main_results.csv
 M data/results/ijtech_table_2_main_results_aligned.csv
 M data/results/ijtech_table_3_baseline_comparison.csv
 M data/results/ijtech_table_3_baseline_comparison_aligned.csv
 M data/results/ijtech_table_4_ablation_results.csv
 M data/results/ijtech_table_4_supported_vs_stress_aligned.csv
 M data/results/ijtech_table_5_latency_summary.csv
 M data/results/langgraph_comparison_results.csv
 M data/results/langgraph_summary.json
 M data/results/mixed_comparison_results.csv
 M data/results/post_approval_comparison_results.csv
 M data/results/post_approval_summary.json
 M data/results/runtime_capability_profiles.json
 M data/results/scaled_error_cases_extended.csv
 M data/results/scaled_error_cases_journal.csv
 M data/results/scaled_evaluation_results_default.csv
 M data/results/scaled_evaluation_results_default.json
 M data/results/scaled_evaluation_results_extended.csv
 M data/results/scaled_evaluation_results_extended.json
 M data/results/scaled_evaluation_results_journal.csv
 M data/results/scaled_evaluation_results_journal.json
 M data/results/scaled_evaluation_summary_default.json
 M data/results/scaled_evaluation_summary_extended.json
 M data/results/scaled_evaluation_summary_journal.json
 M data/results/scaled_metrics_by_factor_extended.csv
 M data/results/scaled_metrics_by_factor_journal.csv
 M data/results/scaled_statistical_summary_journal.csv
 M data/results/scaled_statistical_summary_journal.json
 M data/results/scenario_factor_balance_journal.csv
 M data/results/stress_scope_metrics_aligned_journal.csv
 M data/results/stress_scope_metrics_journal.csv
 M data/results/supported_scope_metrics_aligned_journal.csv
 M data/results/supported_scope_metrics_journal.csv
 M docs/ablation_study_report.md
 M docs/aligned_scaled_evaluation_report.md
 M docs/comparison_summary.md
 M docs/crash_restart_demo.md
 M docs/final_experiment_inventory.md
 M docs/final_unified_evaluation_report.md
 M docs/ijtech_abstract_final_candidate.md
 M docs/ijtech_aligned_empirical_results_report.md
 M docs/ijtech_blind_review_package_checklist.md
 M docs/ijtech_discussion_final_candidate.md
 M docs/ijtech_empirical_results_report.md
 M docs/ijtech_figure_plan.md
 M docs/ijtech_figures_ready_for_manuscript.md
 M docs/ijtech_introduction_final_candidate.md
 M docs/ijtech_manuscript_full_draft.md
 M docs/ijtech_methodology_final_candidate.md
 M docs/ijtech_results_final_candidate.md
 M docs/ijtech_revision_notes.md
 M docs/ijtech_sedm_abstract_draft.md
 M docs/ijtech_sedm_discussion_draft.md
 M docs/ijtech_sedm_introduction_draft.md
 M docs/ijtech_sedm_manuscript_skeleton.md
 M docs/ijtech_sedm_methodology_draft.md
 M docs/ijtech_sedm_results_draft.md
 M docs/ijtech_tables_ready_for_manuscript.md
 M docs/ijtech_threats_to_validity_final_candidate.md
 M docs/kubernetes_reproducibility_demo.md
 M docs/langgraph_comparison_summary.md
 M docs/langsmith_trace_examples.md
 M docs/manuscript_consistency_audit.md
 M docs/mathematical_metrics_appendix.md
 M docs/metrics_definitions.md
 M docs/prototype_overview.md
 M docs/repository_quality_audit.md
 M docs/reproducibility_commands.md
 M docs/runtime_capability_profiles.md
 M docs/runtime_specific_expectation_rules.md
 M docs/scaled_statistical_analysis.md
 M docs/sedm_shortened_version_plan.md
 M docs/stratified_scaled_results.md
 M docs/supported_vs_stress_scope_report.md
 M tests/test_evidence_artifact_integrity.py
?? app/evaluation/conditional_metrics.py
?? app/evaluation/refresh_evidence_artifacts.py
?? docs/p0_correction_report.md
?? tests/test_conditional_metric_denominators.py
```

`git diff --check` passes with no output:

```text
$ git diff --check
(exit 0; no output)
```

Tracked-file diff summary:

```text
 README.md                                          |    59 +-
 app/evaluation/baselines.py                        |     1 +
 app/evaluation/metrics.py                          |    61 +-
 app/evaluation/run_ablation_study.py               |    12 +-
 app/evaluation/run_aligned_scaled_evaluation.py    |    22 +-
 app/evaluation/run_comparison.py                   |     8 +-
 app/evaluation/run_crash_restart_demo.py           |    44 +-
 app/evaluation/run_k8s_reproducibility_summary.py  |    12 +-
 app/evaluation/run_langgraph_comparison.py         |    11 +-
 app/evaluation/run_mixed_workflow_comparison.py    |    11 +-
 app/evaluation/run_post_approval_comparison.py     |    11 +-
 app/evaluation/run_scaled_error_audit.py           |    33 +-
 app/evaluation/run_scaled_evaluation.py            |    24 +-
 app/evaluation/runtime_expectations.py             |    15 +-
 app/evaluation/statistical_analysis.py             |    89 +-
 app/observability/summaries.py                     |    10 +-
 data/results/RESULTS_MANIFEST.json                 |   251 +-
 data/results/RESULTS_METADATA_INDEX.csv            |   114 +-
 data/results/RESULTS_METADATA_INDEX.json           |   255 +-
 data/results/ablation_results.csv                  |    14 +-
 data/results/ablation_summary.json                 |    32 +-
 ...igned_confusion_matrix_final_status_journal.csv |   146 +-
 data/results/aligned_error_cases_journal.csv       |  1442 +--
 data/results/aligned_scaled_metrics_by_runtime.csv |    12 +-
 data/results/aligned_scaled_metrics_by_scope.csv   |    22 +-
 data/results/aligned_scaled_results_journal.csv    |  2402 ++--
 data/results/aligned_scaled_summary_journal.json   |   222 +-
 data/results/baseline_summary.json                 |   336 +-
 data/results/comparison_results.csv                |    10 +-
 .../confusion_matrix_final_status_journal.csv      |   144 +-
 ...onfusion_matrix_governance_decision_journal.csv |   142 +-
 data/results/crash_restart_demo_summary.json       |    15 +-
 data/results/deployment_mode_comparison.csv        |     4 +-
 .../deployment_mode_comparison_with_metadata.csv   |     4 +-
 .../final_manuscript_results_with_metadata.csv     |    24 +-
 data/results/final_unified_metrics.csv             |    24 +-
 data/results/final_unified_metrics.json            |    73 +-
 .../ijtech_figure_data_latency_distribution.csv    |  2402 ++--
 .../ijtech_figure_data_policy_vs_unsafe.csv        |    12 +-
 data/results/ijtech_figure_data_trace_recovery.csv |    12 +-
 data/results/ijtech_table_1_scenario_design.csv    |   262 +-
 data/results/ijtech_table_2_main_results.csv       |    77 +-
 .../ijtech_table_2_main_results_aligned.csv        |    12 +-
 .../results/ijtech_table_3_baseline_comparison.csv |     8 +-
 .../ijtech_table_3_baseline_comparison_aligned.csv |    14 +-
 data/results/ijtech_table_4_ablation_results.csv   |    14 +-
 .../ijtech_table_4_supported_vs_stress_aligned.csv |    22 +-
 data/results/ijtech_table_5_latency_summary.csv    |   132 +-
 data/results/langgraph_comparison_results.csv      |     6 +-
 data/results/langgraph_summary.json                |   140 +-
 data/results/mixed_comparison_results.csv          |     6 +-
 data/results/post_approval_comparison_results.csv  |     6 +-
 data/results/post_approval_summary.json            |    80 +-
 data/results/runtime_capability_profiles.json      |     9 +-
 data/results/scaled_error_cases_extended.csv       |  3170 ++---
 data/results/scaled_error_cases_journal.csv        |  1522 +--
 data/results/scaled_evaluation_results_default.csv |  1202 +-
 .../results/scaled_evaluation_results_default.json |  3000 ++++-
 .../results/scaled_evaluation_results_extended.csv |  5002 ++++----
 .../scaled_evaluation_results_extended.json        | 12454 +++++++++++++++----
 data/results/scaled_evaluation_results_journal.csv |  2402 ++--
 .../results/scaled_evaluation_results_journal.json |  5992 +++++++--
 .../results/scaled_evaluation_summary_default.json |   285 +-
 .../scaled_evaluation_summary_extended.json        |   285 +-
 .../results/scaled_evaluation_summary_journal.json |   285 +-
 data/results/scaled_metrics_by_factor_extended.csv |   462 +-
 data/results/scaled_metrics_by_factor_journal.csv  |   462 +-
 .../results/scaled_statistical_summary_journal.csv |   399 +-
 .../scaled_statistical_summary_journal.json        |  1192 +-
 data/results/scenario_factor_balance_journal.csv   |    70 +-
 .../stress_scope_metrics_aligned_journal.csv       |    12 +-
 data/results/stress_scope_metrics_journal.csv      |    12 +-
 .../supported_scope_metrics_aligned_journal.csv    |    12 +-
 data/results/supported_scope_metrics_journal.csv   |    12 +-
 docs/ablation_study_report.md                      |     6 +-
 docs/aligned_scaled_evaluation_report.md           |     6 +-
 docs/comparison_summary.md                         |     8 +-
 docs/crash_restart_demo.md                         |    15 +-
 docs/final_experiment_inventory.md                 |     2 +-
 docs/final_unified_evaluation_report.md            |    14 +-
 docs/ijtech_abstract_final_candidate.md            |     2 +-
 docs/ijtech_aligned_empirical_results_report.md    |    14 +-
 docs/ijtech_blind_review_package_checklist.md      |     2 +-
 docs/ijtech_discussion_final_candidate.md          |     6 +-
 docs/ijtech_empirical_results_report.md            |    14 +-
 docs/ijtech_figure_plan.md                         |     2 +-
 docs/ijtech_figures_ready_for_manuscript.md        |     8 +-
 docs/ijtech_introduction_final_candidate.md        |     6 +-
 docs/ijtech_manuscript_full_draft.md               |    40 +-
 docs/ijtech_methodology_final_candidate.md         |    12 +-
 docs/ijtech_results_final_candidate.md             |    16 +-
 docs/ijtech_revision_notes.md                      |     2 +-
 docs/ijtech_sedm_abstract_draft.md                 |     2 +-
 docs/ijtech_sedm_discussion_draft.md               |     4 +-
 docs/ijtech_sedm_introduction_draft.md             |     6 +-
 docs/ijtech_sedm_manuscript_skeleton.md            |     6 +-
 docs/ijtech_sedm_methodology_draft.md              |    10 +-
 docs/ijtech_sedm_results_draft.md                  |     8 +-
 docs/ijtech_tables_ready_for_manuscript.md         |    32 +-
 docs/ijtech_threats_to_validity_final_candidate.md |     2 +-
 docs/kubernetes_reproducibility_demo.md            |     6 +-
 docs/langgraph_comparison_summary.md               |     4 +-
 docs/langsmith_trace_examples.md                   |     2 +-
 docs/manuscript_consistency_audit.md               |     2 +
 docs/mathematical_metrics_appendix.md              |    16 +-
 docs/metrics_definitions.md                        |    57 +-
 docs/prototype_overview.md                         |     7 +-
 docs/repository_quality_audit.md                   |     4 +-
 docs/reproducibility_commands.md                   |    34 +
 docs/runtime_capability_profiles.md                |     4 +-
 docs/runtime_specific_expectation_rules.md         |     2 +-
 docs/scaled_statistical_analysis.md                |    10 +-
 docs/sedm_shortened_version_plan.md                |     2 +-
 docs/stratified_scaled_results.md                  |    24 +-
 docs/supported_vs_stress_scope_report.md           |     8 +-
 tests/test_evidence_artifact_integrity.py          |    19 +-
 116 files changed, 30906 insertions(+), 17097 deletions(-)
```

Stopped for review. No commit or push.
