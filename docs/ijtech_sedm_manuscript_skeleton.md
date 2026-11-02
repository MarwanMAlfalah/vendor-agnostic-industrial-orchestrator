# Title

Governance-Aware Vendor-Agnostic Orchestration for Industrial Workflows: A Deterministic Prototype and Scaled Empirical Evaluation

## Abstract

Draft in `docs/ijtech_sedm_abstract_draft.md`.

## Keywords

Industrial orchestration; governance-aware agents; vendor-agnostic integration; LangGraph; policy compliance; deterministic evaluation; RAMI 4.0; industrial interoperability.

## 1. Introduction

- Motivate industrial heterogeneity across OPC UA, REST, and legacy interfaces.
- Explain why raw automation success is insufficient when workflows include approval gates, blocked actions, invalid mappings, and safe-abort conditions.
- Position agentic orchestration as a supervisory coordination opportunity rather than an autonomous plant-control claim.
- State contributions:
  - a governance-aware reference architecture;
  - a deterministic prototype with mock OPC UA, REST, and legacy adapters;
  - a LangGraph runtime variant for approval continuation, tracing, and checkpoint recovery;
  - a scaled deterministic evaluation with 240 journal scenarios and 500 extended scenarios;
  - an aligned evaluation methodology using runtime-specific capability profiles.
- Summarize key evidence:
  - canonical reference policy compliance 1.0 and unsafe execution 0.0;
  - aligned journal policy compliance 1.0 and unsafe execution 0.0 for `reference_v1` and `langgraph_runtime`;
  - baselines expose policy risk, with conditional unsafe execution up to 1.0 in the aligned journal table.

## 2. Related Work / Background

- Industrial interoperability and vendor heterogeneity.
- Supervisory control and governance constraints.
- Agentic workflows and orchestration runtimes.
- Policy-aware evaluation versus task-success evaluation.
- Observability and trace inspection for reproducible prototype studies.

## 3. Proposed Reference Architecture

- Goal intake and deterministic planning.
- Capability matching against a registry.
- Governance evaluation with `ALLOW`, `REQUIRE_APPROVAL`, `BLOCK`, and `SAFE_ABORT`.
- Governance-aware execution through mock adapters.
- Observability and trace records.
- Optional graph runtime for stateful approval continuation.

## 4. Prototype Implementation

- `reference_v1` runtime.
- Mock OPC UA, REST, and legacy adapters.
- Deterministic baselines:
  - direct execution without governance;
  - single-stage execution;
  - execution without policy filtering.
- `langgraph_runtime` for graph-native interrupt/resume and controlled approval continuation.
- Checkpoint reopen/resume demo using SQLite checkpointing.
- LangSmith trace examples as observability evidence only.

## 5. Empirical Evaluation Methodology

- Canonical 12-case comparison.
- Mixed workflow evaluation.
- Post-approval continuation evaluation.
- Checkpoint reopen/resume demo.
- Scaled deterministic scenario generator:
  - default profile: 120 scenarios;
  - journal profile: 240 scenarios;
  - extended profile: 500 scenarios.
- Runtime-specific expectation alignment.
- Supported-scope versus stress-scope classification.
- Metrics:
  - policy compliance;
  - unsafe execution;
  - approval bypass;
  - final outcome accuracy;
  - invalid mapping containment;
  - trace completeness;
  - latency summaries;
  - Wilson confidence intervals as scenario-distribution intervals.

## 6. Results

- Canonical comparison.
- Scaled aligned journal profile.
- Baseline comparison.
- Supported versus stress scope.
- LangGraph approval continuation.
- Crash/restart persistence.
- LangSmith observability evidence.

## 7. Discussion

- Raw success rate is insufficient.
- Policy-centric metrics better capture governed industrial workflows.
- LangGraph adds runtime-level value beyond correctness parity.
- Runtime-specific alignment is methodologically fair when capability profiles differ.
- The study remains a deterministic prototype evaluation with mock adapters.

## 8. Threats to Validity

- Synthetic deterministic scenarios.
- Mock adapters rather than live PLCs or industrial devices.
- Local latency measurement.
- Runtime-specific expectation alignment risks.
- Limited unsafe-action space.
- LangSmith traces are observability evidence, not deployment evidence.

## 9. Reproducibility

- Fixed scenario generator seed.
- Machine-readable CSV and JSON artifacts.
- Commands for scenario generation, scaled evaluation, aligned evaluation, statistical analysis, and tests.
- Editable tables and figure-data CSVs.

## 10. Conclusion

- Summarize feasibility and empirical evidence.
- Emphasize prototype-level contribution.
- Identify next steps toward journal-level validation.
