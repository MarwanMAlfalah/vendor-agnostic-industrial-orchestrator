# IJTech Figure Plan

## Figure 1: Graphical Abstract

Show a high-level flow from industrial goal to planner, capability matcher,
governance layer, adapter execution, and trace evidence. Include OPC UA, REST,
and legacy adapter icons or blocks. Caption should state that the prototype
uses mock adapters and deterministic scenarios.

## Figure 2: Reference Architecture Diagram

Adapt the architecture diagram to show:

- goal intake;
- deterministic planner;
- capability registry and matcher;
- governance evaluator;
- execution agent;
- mock adapters;
- observability layer;
- optional LangGraph runtime path.

## Figure 3: Workflow Pipeline

Show the decision pipeline for `ALLOW`, `REQUIRE_APPROVAL`, `BLOCK`, and
`SAFE_ABORT`. Include examples of correct non-execution for blocked and
approval-required steps.

## Figure 4: Policy Compliance Versus Unsafe Execution

Use `data/results/ijtech_table_2_main_results_aligned.csv` or the existing
policy figure data. Plot aligned policy compliance and unsafe execution by
runtime. Emphasize that baselines expose policy risk.

## Figure 5: Approval Continuation Trace

Show the LangGraph approval path:

`planner_node -> matcher_node -> governance_node -> approval_interrupt -> approval_resume -> approval_validated -> approved_execution -> final_result`.

Use LangSmith only as observability evidence. Remove any personal account,
email, or project-identifying details before blind review.

## Figure 6: Crash/Restart Persistence Flow

Show checkpoint creation at approval interrupt, simulated process stop,
runtime reopening with SQLite checkpoint state, approval resume, and final
result. Caption should frame this as local checkpoint recovery evidence.
