# SQLite Checkpoint Reopen/Resume Demo

This demo uses the optional LangGraph runtime with a SQLite checkpointer at
`data/langgraph/checkpoints.db`. It starts an approval-gated workflow, reaches an
approval interrupt, closes the initial runtime/checkpointer, reopens a new
SQLite-backed runtime, and resumes using the same `thread_id`, all within one
Python process. It demonstrates checkpoint reopen/resume behavior, not recovery
after an operating-system process crash.

## Runs

- `CASE-POST-APPROVAL-VALID-001`: interrupt=True, checkpoint=True, resumed=True, approval_state=approved, final_status=success, gated_step_executed=True
- `CASE-POST-APPROVAL-INVALID-PAYLOAD-001`: interrupt=True, checkpoint=True, resumed=True, approval_state=approval_invalid, final_status=partial_success, gated_step_executed=False

## Metrics

- checkpoint_resume_success_rate: `1.0`
- checkpoint_reopen_resume_success_rate: `1.0`
- post_reopen_final_outcome_accuracy: `1.0`
- checkpoint_reopen_trace_completeness: `1.0`

## Trace Evidence

The successful approval run includes `approval_interrupt`, `approval_resume`,
`approval_validated`, `approved_execution`, and `final_result`. The invalid
approval run resumes from the same kind of checkpoint but remains policy-correct
by rejecting approval and avoiding gated execution.

## Commands

Run locally:

```bash
.venv/bin/python -m app.evaluation.run_crash_restart_demo
```

Run with optional Docker support:

```bash
docker compose -f docker-compose.demo.yml up --build
```

The Docker demo mounts `./data` and `./docs`, so the checkpoint database and
generated summary files remain on the host.
