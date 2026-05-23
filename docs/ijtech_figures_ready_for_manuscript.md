# IJTech Figures Ready For Manuscript

This file defines the figure package for the IJTech-first manuscript. Figures should be redrawn cleanly for submission and should not expose repository paths, user accounts, email addresses, LangSmith workspace identity, or machine-specific details.

## Figure 1. Graphical Abstract

Purpose: summarize the contribution in one visual.

Suggested content:

`Industrial goal -> deterministic planner -> capability matcher -> governance evaluator -> adapter-mediated execution -> trace evidence`

Include mock OPC UA, REST, and legacy adapter blocks. Include governance outcomes: `ALLOW`, `REQUIRE_APPROVAL`, `BLOCK`, and `SAFE_ABORT`.

Caption: Governance-aware vendor-agnostic orchestration flow used in the deterministic prototype. The adapters are mock implementations and the evaluation uses generated scenarios.

## Figure 2. Reference Architecture

Purpose: show system structure.

Suggested content:

- goal intake;
- deterministic planner;
- capability registry;
- capability matcher;
- governance evaluator;
- execution agent;
- mock OPC UA, REST, and legacy adapters;
- trace recorder;
- optional LangGraph runtime path.

Caption: Reference architecture for governance-aware industrial workflow orchestration. The architecture separates planning, matching, governance, execution, and tracing.

## Figure 3. Governance Decision Pipeline

Purpose: show why correct non-execution matters.

Suggested content:

- `ALLOW -> execute adapter step`;
- `REQUIRE_APPROVAL -> stop or interrupt until approval`;
- `BLOCK -> do not execute prohibited step`;
- `SAFE_ABORT -> stop workflow and contain invalid mapping or malformed payload`.

Caption: Governance decision pipeline. In governed workflows, blocking, approval-required stopping, and safe aborts can be correct outcomes.

## Figure 4. Policy Compliance Versus Unsafe Execution

Purpose: visualize the main empirical contrast.

Data source: `data/results/ijtech_figure_data_policy_vs_unsafe.csv` or `data/results/ijtech_table_2_main_results_aligned.csv`.

Suggested plot:

- grouped bars by runtime;
- aligned policy compliance and unsafe execution;
- highlight `reference_v1` and `langgraph_runtime`;
- keep baselines visible.

Caption: Aligned policy compliance and unsafe execution in the 240-scenario deterministic journal profile. Governance-aware runtimes avoid unsafe execution, while governance-ablated baselines reveal policy risk.

## Figure 5. Supported Versus Stress Scope

Purpose: show that edge cases are retained rather than hidden.

Data source: `data/results/ijtech_table_4_supported_vs_stress_aligned.csv`.

Suggested plot:

- small multiples by runtime;
- supported and stress scope on the x-axis;
- aligned policy compliance and unsafe execution as separate series.

Caption: Runtime-specific supported and stress scope results. Stress cases include malformed payloads, unavailable capabilities, invalid mappings, invalid or missing approvals, invalidated post-approval mappings, and safe-abort paths.

## Figure 6. LangGraph Approval Continuation Trace

Purpose: show continuation semantics.

Suggested content:

`planner_node -> matcher_node -> governance_node -> approval_interrupt -> approval_resume -> approval_validated -> approved_execution -> final_result`

Use LangSmith only if the screenshot can be fully anonymized. A redrawn schematic is safer for blind review.

Caption: LangGraph approval continuation path in the deterministic prototype. The trace demonstrates controlled interrupt/resume behavior after approval validation and revalidation.

## Figure 7. Crash/Restart Persistence Flow

Purpose: show local checkpoint recovery.

Suggested content:

`approval interrupt -> SQLite checkpoint -> simulated process stop -> runtime reopen -> resume with approval input -> final result`

Caption: Local crash/restart persistence demonstration using LangGraph checkpointing. This is prototype recovery evidence and not a production deployment claim.

## Figure 8. Latency Distribution

Purpose: report runtime overhead without overclaiming.

Data source: `data/results/ijtech_figure_data_latency_distribution.csv` or `data/results/ijtech_table_5_latency_summary.csv`.

Suggested plot:

- box or violin plot if row-level latency values are available;
- otherwise bar plot with mean and p95 latency;
- note that the LangGraph runtime has higher local overhead due to graph runtime structure.

Caption: Local deterministic latency distribution by runtime. These measurements are not real-time industrial timing guarantees.
