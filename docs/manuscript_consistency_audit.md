# Manuscript Consistency Audit

Historical audit snapshot: numeric checks below predate the P0 denominator correction. Current values and limitations are in [P0 correction report](p0_correction_report.md); the earlier audit is not a current numerical validation.

Audit date: 2026-05-24

Scope: IJTech and SEDM manuscript-facing documents only. This audit did not change code,
`data/results`, metrics, formulas, or result artifacts.

Audited documents:

- `docs/ijtech_manuscript_full_draft.md`
- `docs/ijtech_results_final_candidate.md`
- `docs/ijtech_methodology_final_candidate.md`
- `docs/ijtech_threats_to_validity_final_candidate.md`
- `docs/sedm_shortened_version_plan.md`
- `docs/ijtech_sedm_*.md`

Reference artifacts checked:

- `data/results/scaled_evaluation_summary_journal.json`
- `data/results/aligned_scaled_summary_journal.json`
- `data/results/scaled_evaluation_summary_extended.json`
- `data/results/containerized_integration_summary.json`
- `data/results/k8s_reproducibility_summary.json`
- `data/results/deployment_mode_comparison.csv`
- `data/results/langsmith_trace_manifest.csv`
- `data/results/RESULTS_MANIFEST.json`

## Executive Summary

No critical overclaiming was found in the current IJTech final candidate documents or SEDM
shortening plan. Docker Compose, Kubernetes kind, and LangSmith are generally framed correctly as
local reproducibility, service-boundary, and observability/debugging evidence rather than
production or industrial validation evidence.

The main scientific metric values used in the manuscript-facing text match the generated result
artifacts for policy compliance, unsafe execution, final outcome accuracy, approval bypass,
trace completeness, supported/stress scope values, and extended-profile headline values.

Edits are recommended before submission, but they are editorial consistency changes rather than
required corrections to runtime logic or metrics.

## 1. Overclaiming Audit

Status: pass, with minor wording caution.

The documents repeatedly state the correct non-claims:

- no production deployment claim;
- no live PLC integration claim;
- no certified safety or regulatory compliance claim;
- no industrial validation or field validation claim;
- Docker/Kubernetes are local reproducibility evidence only;
- LangSmith is observability/debugging evidence only.

No unqualified claim was found that the prototype is production deployed, certified safe, validated
on live PLCs, or industrially validated in the field.

Recommended changes:

1. In any future caption for Kubernetes screenshots, use "local kind reproducibility evidence" and
   avoid "deployment evidence" unless qualified as "local Kubernetes deployment packaging."
2. In any future LangSmith figure caption, use "trace observability evidence" and avoid
   "validation trace" or "industrial validation trace."

## 2. Metric Consistency Audit

Status: pass for manuscript headline values.

The following manuscript values match `data/results/aligned_scaled_summary_journal.json` and
`data/results/scaled_evaluation_summary_journal.json`:

| Metric claim | Manuscript value | Artifact value | Status |
| --- | ---: | ---: | --- |
| `reference_v1` original policy compliance, journal | 0.854167 | 0.854167 | Match |
| `reference_v1` original final outcome accuracy, journal | 0.875 | 0.875 | Match |
| `langgraph_runtime` original policy compliance, journal | 0.979167 | 0.979167 | Match |
| `langgraph_runtime` original final outcome accuracy, journal | 0.979167 | 0.979167 | Match |
| `reference_v1` aligned policy compliance, journal | 1.0 | 1.0 | Match |
| `langgraph_runtime` aligned policy compliance, journal | 1.0 | 1.0 | Match |
| Governance-aware unsafe execution, aligned journal | 0.0 | 0.0 | Match |
| Baseline A unsafe execution, aligned journal | 0.583333 | 0.583333 | Match |
| Baseline C unsafe execution, aligned journal | 0.583333 | 0.583333 | Match |
| Baseline B aligned policy compliance, journal | 0.083333 | 0.083333 | Match |
| Baseline A stress-scope unsafe execution | 0.636364 | 0.636364 | Match |
| Baseline C stress-scope unsafe execution | 0.777778 | 0.777778 | Match |
| Baseline C stress-scope aligned policy compliance | 0.222222 | 0.222222 | Match |

Extended-profile values in `docs/ijtech_results_final_candidate.md` match
`data/results/scaled_evaluation_summary_extended.json`:

| Metric claim | Manuscript value | Artifact value | Status |
| --- | ---: | ---: | --- |
| `reference_v1` extended policy compliance | 0.854 | 0.854 | Match |
| `reference_v1` extended final outcome accuracy | 0.876 | 0.876 | Match |
| `langgraph_runtime` extended policy compliance | 0.978 | 0.978 | Match |
| `langgraph_runtime` extended final outcome accuracy | 0.978 | 0.978 | Match |
| Baseline A extended unsafe execution | 0.586 | 0.586 | Match |
| Baseline C extended unsafe execution | 0.586 | 0.586 | Match |

Observation:

Some latency values differ across result artifacts. For example,
`scaled_evaluation_summary_journal.json` records journal p95 latency of `0.070464` for
`reference_v1` and `3.266788` for `langgraph_runtime`, while
`deployment_mode_comparison.csv` records `0.075116` and `3.815129`. The audited manuscript
candidate files do not currently foreground these p95 latency values, so this is not an active
manuscript inconsistency. If latency numbers are added to tables or captions, choose one
authoritative artifact and cite it explicitly.

Recommended changes:

1. If the IJTech manuscript includes a final latency table, source p95 latency values from one
   named artifact only, preferably `scaled_evaluation_summary_journal.json` for journal-runtime
   metrics and `k8s_reproducibility_summary.json` for Kubernetes evidence.
2. Add a note in any latency table caption that local timings are prototype measurements and not
   industrial real-time guarantees.

## 3. Terminology Consistency Audit

Status: mostly consistent.

Runtime terminology is generally consistent:

- `reference_v1` is the deterministic reference runtime without controlled post-approval
  continuation.
- `langgraph_runtime` is the graph runtime with controlled approval continuation and checkpoint
  evidence.
- Baseline A, B, and C are consistently described as deterministic governance-ablated baselines.

Evidence terminology is generally consistent:

- Docker Compose is local mock-service integration evidence.
- Kubernetes is actual local kind reproducibility evidence.
- LangSmith is optional observability/debugging evidence.

Minor terminology inconsistencies:

1. The documents alternate between "LangGraph runtime" and `langgraph_runtime`. This is acceptable
   when prose uses the display name and tables use the runtime identifier, but the first mention in
   each section should ideally state "`langgraph_runtime` (LangGraph runtime)".
2. The documents alternate between "Kubernetes local kind", "local Kubernetes kind", and "actual
   local kind". These are not contradictory, but the preferred manuscript phrase should be
   "actual local kind Kubernetes reproducibility evidence."
3. Docker evidence is sometimes called "Docker Compose integration" and sometimes "Dockerized
   integration." These are compatible, but "Docker Compose mock-service integration" is clearest.

Recommended changes:

1. Use `reference_v1` and `langgraph_runtime` in tables and metric claims.
2. Use "the LangGraph runtime" only as a prose display label after the identifier has been
   introduced.
3. Standardize Kubernetes wording to "actual local kind Kubernetes reproducibility evidence."
4. Standardize Docker wording to "Docker Compose mock-service integration evidence."

## 4. Docker, Kubernetes, And LangSmith Framing

Status: pass.

The framing is correct across the IJTech final candidate files and SEDM shortening plan:

| Evidence type | Current framing | Status |
| --- | --- | --- |
| Docker Compose | Local service-boundary run against separate mock OPC UA-style, REST, and legacy service containers | Correct |
| Kubernetes kind | Actual local kind run with `orchestrator` Deployment, `orchestrator-api` Service, completed jobs, PVC, health response, and logs | Correct |
| LangSmith | Trace observability, debugging, auditability, and figure preparation only | Correct |
| `RESULTS_MANIFEST.json` | Frozen evidence integrity manifest | Correct |

The obsolete zero-byte `orchestrator-api.log` is correctly explained as a Service-name versus
Deployment-name evidence collection mismatch and is not treated as application log evidence.

Recommended changes:

1. Keep Docker/Kubernetes/LangSmith in a separate "Reproducibility and Observability Evidence"
   subsection rather than merging them into the main empirical metric table.
2. For screenshots, use captions such as:
   - "Local kind Kubernetes reproducibility evidence: pods, jobs, and health response."
   - "Redacted LangSmith observability trace for deterministic governance workflow."
   - "Docker Compose mock-service topology for local integration evidence."

## 5. IJTech Versus SEDM Differentiation

Status: pass for the current plan; watch the SEDM draft assembly.

The IJTech draft is clearly stronger and more extended than the SEDM shortened version plan:

- IJTech includes the full 240-scenario journal profile and 500-scenario extended profile.
- IJTech includes original-versus-aligned methodology.
- IJTech includes Docker/Kubernetes/LangSmith evidence integration.
- IJTech includes expanded threats to validity.
- IJTech includes detailed reproducibility and manifest validation framing.

The SEDM shortened version plan correctly instructs the shorter version to retain only the core
architecture, compact results, brief reproducibility paragraph, and concise limitations.

Potential issue:

The older `docs/ijtech_sedm_*.md` draft fragments still contain some detailed journal-profile
language. That is acceptable as source material, but if they are assembled into a final SEDM paper,
they should be compressed according to `docs/sedm_shortened_version_plan.md`.

Recommended changes:

1. When producing the final SEDM manuscript, keep at most one compact paragraph on Docker,
   Kubernetes, and LangSmith evidence.
2. Do not include the full Docker/Kubernetes/LangSmith table in the SEDM version; reserve it for
   IJTech or supplementary material.
3. Keep the SEDM version focused on architecture, policy-centric metrics, and headline aligned
   results.

## 6. Exact Recommended Edits Not Applied

No edits were applied by this audit. Recommended future edits are:

1. `docs/ijtech_results_final_candidate.md`
   - The "Original And Aligned Journal Metrics" section repeats the original-label metric sentence
     in two adjacent paragraphs. Delete one occurrence or merge the two paragraphs for smoother
     paper-ready flow.

2. `docs/ijtech_manuscript_full_draft.md`
   - The evidence table is introduced as "Table 2" without a formal table caption. Add a caption
     in the final manuscript layout, or avoid numbering until all tables are finalized.

3. `docs/ijtech_methodology_final_candidate.md`
   - Keep the validation sentence, but if the execution environment uses `python3` instead of
     `python`, phrase it as "`python -m pytest` or the environment-equivalent `python3 -m pytest`"
     in the reproducibility appendix.

4. `docs/sedm_shortened_version_plan.md`
   - No immediate correction needed. When drafting the final SEDM paper, ensure the reproducibility
     paragraph remains compact and does not import the full IJTech evidence table.

5. All manuscript files
   - If adding latency values later, choose one authoritative source artifact per table and avoid
     mixing p95 values from `deployment_mode_comparison.csv` with values from
     `scaled_evaluation_summary_journal.json`.

## Final Audit Conclusion

The manuscript package is consistent with the current evidence boundary. It does not overclaim
production deployment, live PLC integration, certified safety, or industrial validation. Headline
policy, safety, accuracy, and aligned metric values match the generated artifacts. Docker Compose,
Kubernetes kind, and LangSmith are framed correctly as reproducibility and observability support.
The IJTech draft is positioned as the stronger, extended manuscript, while the SEDM plan remains a
shortened derivative.
