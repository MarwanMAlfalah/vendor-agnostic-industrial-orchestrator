# Final Unified Evaluation Report

## Executive Summary

This repository implements a deterministic supervisory orchestration prototype
for vendor-agnostic industrial operations. The evaluation now covers a stable
custom reference runtime (`reference_v1`), deterministic baselines, an optional
LangGraph runtime, mixed multi-step workflows, controlled post-approval
continuation, same-process checkpoint reopen/resume, and optional hosted LangSmith
observability.

Across the canonical governance cases, the reference method achieves perfect
policy-centric correctness (`policy_compliance_rate = 1.0`,
`unsafe_execution_rate = 0.0`) while simple baselines achieve higher raw
execution coverage by bypassing governance. The LangGraph runtime preserves
policy correctness on canonical and mixed workflows while adding runtime-level
evidence for interrupt/resume, post-approval continuation, trace completeness,
and checkpoint recovery.

## Evaluation Inventory

| Layer | Cases | Main Artifact | Main Purpose |
| --- | ---: | --- | --- |
| Canonical baseline comparison | 12 | `data/results/comparison_results.csv` | Compare reference runtime against governance-ablated baselines. |
| LangGraph canonical comparison | 12 | `data/results/langgraph_comparison_results.csv` | Compare `reference_v1` and `langgraph_runtime` on policy correctness parity. |
| Mixed workflow comparison | 12 | `data/results/mixed_comparison_results.csv` | Evaluate multi-step combinations such as allow-then-block and approval-then-allow. |
| Post-approval continuation | 6 | `data/results/post_approval_comparison_results.csv` | Evaluate controlled execution of approval-gated steps after valid approval. |
| Checkpoint reopen/resume demo | 2 | `data/results/crash_restart_demo_summary.json` | Demonstrate checkpoint reopen/resume continuation from a persisted approval checkpoint. |
| LangSmith observability | N/A | `docs/langsmith_trace_examples.md` | Document trace categories and screenshot candidates. |

## Metric Summary

| Evaluation Layer | Subject | Policy Compliance | Unsafe Execution | Governance Accuracy | Final Outcome Accuracy | Trace / Recovery Evidence |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Canonical baseline | Reference governance-aware execution | 1.0 | 0.0 | 1.0 | 1.0 | Coverage 0.2; intervention 0.75 |
| Canonical baseline | Baseline A direct without governance | 0.25 | 1.0 | 0.0 | 0.25 | Coverage 0.6 |
| Canonical baseline | Baseline B single-stage execution | 0.25 | 1.0 | 0.25 | 0.25 | Coverage 1.0 |
| Canonical baseline | Baseline C without policy filtering | 0.5 | 1.0 | 0.5 | 0.5 | Coverage 0.6 |
| LangGraph canonical | reference_v1 | 1.0 | 0.0 | 1.0 | 1.0 | Trace completeness 1.0 |
| LangGraph canonical | langgraph_runtime | 1.0 | 0.0 | 1.0 | 1.0 | Trace completeness 1.0 |
| Mixed workflows | reference_v1 | 1.0 | 0.0 | 1.0 | 1.0 | Trace stage coverage 0.0 |
| Mixed workflows | langgraph_runtime | 1.0 | 0.0 | 1.0 | 1.0 | Trace stage coverage 1.0; interrupt quality 1.0 |
| Post-approval | reference_v1 | 0.3333 | 0.0 | 0.8333 | 0.3333 | No controlled continuation |
| Post-approval | langgraph_runtime | 1.0 | 0.0 | 1.0 | 1.0 | Approval validation, gated execution, trace completeness all 1.0 |
| Crash/restart | LangGraph SQLite checkpoint | N/A | N/A | N/A | N/A | Checkpoint resume, checkpoint reopen/resume, post-reopen outcome, trace completeness all 1.0 |

The complete machine-readable table is available in
`data/results/final_unified_metrics.csv` and
`data/results/final_unified_metrics.json`.

## Claim-Evidence Table

| Claim | Evidence | Interpretation |
| --- | --- | --- |
| Policy-aware execution is achieved in controlled cases. | Canonical reference row: policy compliance 1.0, unsafe execution 0.0. | Strong prototype-level evidence for deterministic governed scenarios. |
| Raw execution success alone is misleading. | Baseline B has success rate 1.0 and coverage 1.0 but policy compliance 0.25 and unsafe execution 1.0. | Safety-oriented metrics are required. |
| LangGraph preserves policy correctness. | LangGraph canonical and mixed rows show policy compliance 1.0 and unsafe execution 0.0. | Strong within current deterministic cases. |
| LangGraph adds runtime-level value. | Mixed and post-approval rows show trace stage coverage, interrupt quality, approval validation, and controlled continuation. | Strong for runtime semantics, not industrial deployment. |
| Restart-safe continuation is demonstrated. | Crash/restart demo metrics are 1.0 across checkpoint resume, checkpoint reopen/resume, post-reopen outcome, and trace completeness. | Strong demonstration at approval-checkpoint level. |
| Observability supports inspection. | LangSmith docs and trace outputs define structured top-level outputs and child spans. | Useful for debugging and paper figures. |

## Canonical Governance Comparison

The canonical comparison uses 12 deterministic cases spanning `ALLOW`,
`REQUIRE_APPROVAL`, `BLOCK`, and `SAFE_ABORT`. The reference governance-aware
method achieves perfect policy-centric correctness. The baselines intentionally
remove planner/matcher separation, governance, or policy filtering. Their higher
success and coverage values therefore reflect uncontrolled execution rather than
superior supervisory behavior.

## Mixed Workflow Evaluation

The mixed evaluation adds 12 multi-step cases covering:

- `MIXED_ALLOW_REQUIRE_APPROVAL`
- `MIXED_ALLOW_BLOCK`
- `MIXED_ALLOW_SAFE_ABORT`
- `MIXED_REQUIRE_APPROVAL_RESUME_ALLOW`
- `MIXED_ALLOW_ALLOW_BLOCK`

Both runtime paths remain policy-correct on these cases. The difference is
runtime evidence: `langgraph_runtime` exposes full graph stage coverage and
approval interrupt trace quality, while `reference_v1` remains a simpler custom
executor without graph-native checkpoint traces.

## Post-Approval Continuation

The post-approval experiment distinguishes simple pause/resume from controlled
continuation. Valid approval payloads allow the LangGraph runtime to revalidate
policy eligibility and adapter/capability mapping before executing the gated
step. Invalid, missing, or mapping-invalid cases remain policy-correct and do
not execute the gated step. In this experiment, `langgraph_runtime` achieves
1.0 for approved step execution, approval validation accuracy, post-resume final
outcome accuracy, gated step policy compliance, and approved execution trace
completeness.

## SQLite Checkpoint Reopen/Resume Demo

The crash/restart demo uses a SQLite LangGraph checkpointer at
`data/langgraph/checkpoints.db`. It demonstrates recovery at the approval
checkpoint level: the workflow reaches `approval_interrupt`, saves a checkpoint,
closes the runtime/checkpointer within the same Python process, reopens the runtime using the
same checkpoint database and `thread_id`, resumes with approval input, and
produces the expected final result. The demo includes both a valid approval and
an invalid approval case.

## LangSmith Observability

Hosted LangSmith tracing is optional and configured through environment
variables. The traces are not part of the control logic. They provide structured
outputs for experiment-level runs and child spans for graph stages:
`planner_node`, `matcher_node`, `governance_node`, `approval_interrupt`,
`approval_resume`, `approval_validated`, `approved_execution`,
`execution_node`, and `final_result`.

Recommended screenshot traces are documented in
`docs/langsmith_trace_examples.md`.

## Paper-Ready Narrative

This prototype demonstrates that a structured supervisory orchestration stack
can separate planning, capability matching, governance, execution, and
evaluation while maintaining deterministic, inspectable control over industrial
adapter calls. The quantitative results show that policy-centric metrics are
necessary: baseline methods can increase execution coverage while also
increasing unsafe execution. The governance-aware reference method prevents
unsafe execution in the controlled case set, and the LangGraph runtime preserves
this correctness while adding stateful runtime capabilities such as
interrupt/resume, controlled post-approval continuation, and checkpoint-based
reopen/resume within one process.

The evidence should be framed as prototype-level and deterministic. It supports
claims about feasibility, architecture, evaluation methodology, and runtime
semantics. It does not yet establish production safety, real plant performance,
operator workload effects, or generalization to diverse industrial facilities.

## Limitations

- The evaluation uses deterministic mock adapters, not live equipment.
- The case set is intentionally small and curated.
- Timing values are local runtime measurements, not industrial latency
  benchmarks.
- LangSmith traces improve inspection but do not validate safety by themselves.
- Standards alignment is descriptive and requires deeper mapping for a journal
  empirical paper.
- External industry/research comparisons require formal citation gathering.

