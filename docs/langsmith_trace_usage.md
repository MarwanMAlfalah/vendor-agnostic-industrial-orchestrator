# LangSmith Trace Usage

LangSmith traces are intended for experiment inspection and paper figures. They
show runtime execution structure, case metadata, and approval-checkpoint events.

## What To Inspect

- `reference_v1.run_case`: custom deterministic reference execution.
- `langgraph_runtime.run_case`: experimental graph runtime execution.
- `langgraph_runtime.crash_restart_demo`: SQLite-checkpoint restart demo.

Useful metadata:

- `runtime_id`
- `case_id`
- `goal_type`
- `governance_category`
- `mixed_workflow`
- `approval_case`

## What Tracing Does Not Do

Tracing does not participate in policy decisions. Missing LangSmith credentials
do not affect deterministic results or generated artifacts.

## Suggested Figure Evidence

For approval workflows, inspect traces that include:

- `approval_interrupt`
- `approval_resume`
- `approval_validated`
- `approved_execution`
- `final_result`

For the crash/restart demo, compare the trace metadata with
`data/results/crash_restart_demo_summary.json`.
