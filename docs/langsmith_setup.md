# Hosted LangSmith Setup

LangSmith is used here only for optional experiment observability. It does not
change planning, matching, governance, execution, policy decisions, or
evaluation metrics.

## Environment

Copy `.env.example` to `.env` or export the variables directly:

```bash
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=<your-langsmith-api-key>
export LANGSMITH_PROJECT=vendor-agnostic-industrial-orchestrator
```

`LANGSMITH_ENDPOINT` is optional. Hosted LangSmith users normally leave it
unset. Set it only when you explicitly need a non-default endpoint.

## Run With Tracing

```bash
.venv/bin/python -m app.evaluation.run_comparison
.venv/bin/python -m app.evaluation.run_langgraph_comparison
.venv/bin/python -m app.evaluation.run_mixed_workflow_comparison
.venv/bin/python -m app.evaluation.run_post_approval_comparison
.venv/bin/python -m app.evaluation.run_crash_restart_demo
```

Traces include metadata such as `runtime_id`, `case_id`, `goal_type`,
`governance_category`, `mixed_workflow`, and `approval_case`.

## Disabled Mode

If `LANGSMITH_TRACING` is unset or false, or if `LANGSMITH_API_KEY` is missing,
the project runs normally without tracing.
