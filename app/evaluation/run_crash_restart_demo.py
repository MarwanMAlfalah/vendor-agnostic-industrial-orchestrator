"""Demonstrate same-process SQLite checkpoint reopen/resume."""

import json
from pathlib import Path
from time import perf_counter
from typing import Any

from app.evaluation.scenario_cases import (
    EvaluationCase,
    load_post_approval_evaluation_cases,
)
from app.langgraph_runtime import LangGraphRuntime
from app.observability.summaries import crash_restart_summary
from app.observability.tracing import run_metadata, trace_experiment

CHECKPOINT_DB = Path("data/langgraph/checkpoints.db")
RESULTS_PATH = Path("data/results/crash_restart_demo_summary.json")
DOCS_PATH = Path("docs/crash_restart_demo.md")

REQUIRED_TRACE_MARKERS = {
    "planner_node",
    "matcher_node",
    "governance_node",
    "approval_interrupt",
    "approval_resume",
    "execution_node",
    "final_result",
}


def run_crash_restart_demo() -> dict[str, Any]:
    """Run a deterministic checkpoint reopen/resume demo for valid and invalid approval."""

    CHECKPOINT_DB.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOCS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if CHECKPOINT_DB.exists():
        CHECKPOINT_DB.unlink()

    with trace_experiment(
        "evaluation.run_crash_restart_demo",
        inputs={"checkpoint_db": str(CHECKPOINT_DB)},
        metadata={"runtime_id": "crash_restart_demo", "approval_case": True},
        tags=["evaluation", "crash-restart"],
    ) as trace_handle:
        cases = [
            _case("CASE-POST-APPROVAL-VALID-001"),
            _case("CASE-POST-APPROVAL-INVALID-PAYLOAD-001"),
        ]
        runs = [_run_restart_case(case) for case in cases]
        summary = {
            "checkpoint_db": str(CHECKPOINT_DB),
            "deterministic": True,
            "evidence_scope": "same-process SQLite checkpoint reopen/resume; no OS process crash or restart",
            "runs": runs,
            "metrics": _metrics(runs),
        }
        trace_handle.add_outputs(crash_restart_summary(summary))

    RESULTS_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    DOCS_PATH.write_text(_markdown(summary), encoding="utf-8")
    return summary


def _run_restart_case(case: EvaluationCase) -> dict[str, Any]:
    thread_id = f"crash-restart-{case.case_id}"
    total_start = perf_counter()

    with trace_experiment(
        "langgraph_runtime.crash_restart_demo",
        inputs={"case_id": case.case_id, "thread_id": thread_id},
        metadata=run_metadata(
            runtime_id="langgraph_runtime",
            case_id=case.case_id,
            goal_type=case.governance_plan.goal_type,
            governance_category=case.scenario_category,
            mixed_workflow=True,
            approval_case=True,
        ),
        tags=["langgraph", "checkpoint", "crash-restart"],
    ) as trace_handle:
        runtime = LangGraphRuntime.with_sqlite_checkpointer(str(CHECKPOINT_DB))
        try:
            interrupted_state = runtime.start_case(
                case,
                thread_id=thread_id,
                controlled_approval_execution=True,
            )
            interrupt_reached = "__interrupt__" in interrupted_state
        finally:
            runtime.close()

        checkpoint_saved = CHECKPOINT_DB.exists() and CHECKPOINT_DB.stat().st_size > 0
        restarted_runtime = LangGraphRuntime.with_sqlite_checkpointer(str(CHECKPOINT_DB))
        try:
            resumed_state = restarted_runtime.resume_case(
                thread_id=thread_id,
                approval_payload=case.approval_payload,
            )
            output = restarted_runtime._run_output(
                case=case,
                state=resumed_state,
                total_start=total_start,
                interrupted=interrupt_reached,
                resumed=True,
                thread_id=thread_id,
            )
        finally:
            restarted_runtime.close()

        result = output["result"]
    run_summary = {
        "case_id": case.case_id,
        "thread_id": thread_id,
        "interrupt_reached": interrupt_reached,
        "checkpoint_saved": checkpoint_saved,
        "runtime_recreated": True,
        "sqlite_checkpoint_reopened": checkpoint_saved,
        "same_process_resume": True,
        "resumed_from_checkpoint": output["resumed"],
        "approval_state": output["approval_state"],
        "approval_validation_error": output["approval_validation_error"],
        "approval_validated": "approval_validated" in output["trace"],
        "gated_step_executed": output["approval_execution_performed"],
        "final_status": result.final_status,
        "expected_final_status": case.expected_post_resume_final_status,
        "trace": output["trace"],
    }
    trace_handle.add_outputs(
        {
            "case_id": run_summary["case_id"],
            "approval_state": run_summary["approval_state"],
            "gated_step_executed": run_summary["gated_step_executed"],
            "final_status": run_summary["final_status"],
            "resumed_from_checkpoint": run_summary["resumed_from_checkpoint"],
        }
    )
    return run_summary


def _metrics(runs: list[dict[str, Any]]) -> dict[str, float]:
    total = len(runs)
    return {
        "checkpoint_resume_success_rate": _rate(
            sum(1 for run in runs if run["interrupt_reached"] and run["checkpoint_saved"]),
            total,
        ),
        "checkpoint_reopen_resume_success_rate": _rate(
            sum(
                1
                for run in runs
                if run["runtime_recreated"]
                and run["sqlite_checkpoint_reopened"]
                and run["resumed_from_checkpoint"]
            ),
            total,
        ),
        "post_reopen_final_outcome_accuracy": _rate(
            sum(1 for run in runs if run["final_status"] == run["expected_final_status"]),
            total,
        ),
        "checkpoint_reopen_trace_completeness": _rate(
            sum(1 for run in runs if REQUIRED_TRACE_MARKERS.issubset(set(run["trace"]))),
            total,
        ),
    }


def _case(case_id: str) -> EvaluationCase:
    return next(case for case in load_post_approval_evaluation_cases() if case.case_id == case_id)


def _markdown(summary: dict[str, Any]) -> str:
    run_lines = "\n".join(
        "- "
        f"`{run['case_id']}`: interrupt={run['interrupt_reached']}, "
        f"checkpoint={run['checkpoint_saved']}, resumed={run['resumed_from_checkpoint']}, "
        f"approval_state={run['approval_state']}, final_status={run['final_status']}, "
        f"gated_step_executed={run['gated_step_executed']}"
        for run in summary["runs"]
    )
    metrics = summary["metrics"]
    return f"""# SQLite Checkpoint Reopen/Resume Demo

This demo uses the optional LangGraph runtime with a SQLite checkpointer at
`{summary['checkpoint_db']}`. It starts an approval-gated workflow, reaches an
approval interrupt, closes the initial runtime/checkpointer, reopens a new
SQLite-backed runtime, and resumes using the same `thread_id`, all within one
Python process. It demonstrates checkpoint reopen/resume behavior, not recovery
after an operating-system process crash.

## Runs

{run_lines}

## Metrics

- checkpoint_resume_success_rate: `{metrics['checkpoint_resume_success_rate']}`
- checkpoint_reopen_resume_success_rate: `{metrics['checkpoint_reopen_resume_success_rate']}`
- post_reopen_final_outcome_accuracy: `{metrics['post_reopen_final_outcome_accuracy']}`
- checkpoint_reopen_trace_completeness: `{metrics['checkpoint_reopen_trace_completeness']}`

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
"""


def _rate(count: int, total: int) -> float:
    if total == 0:
        return 0.0

    return round(count / total, 4)


def main() -> None:
    """Command-line entrypoint."""

    summary = run_crash_restart_demo()
    print(f"Checkpoint DB: {CHECKPOINT_DB}")
    print(f"Checkpoint reopen/resume summary JSON: {RESULTS_PATH}")
    print(f"Checkpoint reopen/resume docs: {DOCS_PATH}")
    print("Checkpoint reopen/resume metrics:")
    for key, value in summary["metrics"].items():
        print(f"  {key}: {value}")
    for run in summary["runs"]:
        print(
            "  "
            f"{run['case_id']}: "
            f"interrupt={run['interrupt_reached']}, "
            f"checkpoint={run['checkpoint_saved']}, "
            f"resumed={run['resumed_from_checkpoint']}, "
            f"approval_state={run['approval_state']}, "
            f"gated_step_executed={run['gated_step_executed']}, "
            f"final_status={run['final_status']}"
        )


if __name__ == "__main__":
    main()
