# Crash/Restart Persistence Demo

This demo uses the optional LangGraph runtime with a SQLite checkpointer at
`data/langgraph/checkpoints.db`. It starts an approval-gated workflow, reaches an
approval interrupt, closes the runtime to simulate a process stop, reopens a new
runtime from the same checkpoint database, and resumes using the same
`thread_id`.

## Runs

- `CASE-POST-APPROVAL-VALID-001`: interrupt=True, checkpoint=True, resumed=True, approval_state=approved, final_status=success, gated_step_executed=True
- `CASE-POST-APPROVAL-INVALID-PAYLOAD-001`: interrupt=True, checkpoint=True, resumed=True, approval_state=approval_invalid, final_status=partial_success, gated_step_executed=False

## Metrics

- checkpoint_resume_success_rate: `1.0`
- restart_recovery_success_rate: `1.0`
- post_restart_final_outcome_accuracy: `1.0`
- restart_trace_completeness: `1.0`

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
