# LangSmith Trace Examples

This project uses LangSmith only for optional observability. The traces are
useful for inspecting deterministic experiment structure and collecting
paper/presentation screenshots.

## Recommended Screenshot Traces

| Trace | What It Demonstrates | Good Screenshot Target |
| --- | --- | --- |
| `evaluation.run_comparison` | Baseline comparison with policy-centric output metrics. | Top-level output table showing `policy_compliance_rate` and `unsafe_execution_rate`. |
| `evaluation.run_langgraph_comparison` | Runtime parity between `reference_v1` and `langgraph_runtime`. | Top-level outputs for both runtimes. |
| `evaluation.run_mixed_workflow_comparison` | LangGraph trace value beyond correctness parity. | Outputs showing `trace_stage_coverage` and `interrupt_trace_quality`. |
| `evaluation.run_post_approval_comparison` | Controlled post-approval continuation. | Outputs showing `approved_step_execution_rate`, `approval_validation_accuracy`, and `gated_step_policy_compliance_rate`. |
| `evaluation.run_crash_restart_demo` | SQLite checkpoint restart-safe approval continuation. | Outputs showing checkpoint and restart metrics. |
| `langgraph_runtime.run_case` | One graph execution with approval state and final result. | Child span tree with approval markers. |

## Approval Trace Shape

Paper-friendly approval traces use these span names:

```text
planner_node
matcher_node
governance_node
approval_interrupt
approval_resume
approval_validated
approved_execution
execution_node
final_result
```

For rejected approval cases, `approval_rejected` replaces
`approval_validated` and `approved_execution`.

## Sample Top-Level Output

```json
{
  "langgraph_runtime": {
    "policy_compliance_rate": 1.0,
    "unsafe_execution_rate": 0.0,
    "final_outcome_accuracy": 1.0,
    "approval_resume_correctness": 1.0,
    "resume_success_rate": 1.0
  }
}
```

## Sample Approval Run Output

```json
{
  "final_status": "success",
  "approval_state": "approved",
  "gated_step_executed": true,
  "resume_success": true,
  "trace": [
    "planner_node",
    "matcher_node",
    "governance_node",
    "approval_interrupt",
    "approval_resume",
    "approval_validated",
    "approved_execution",
    "execution_node",
    "final_result"
  ]
}
```
