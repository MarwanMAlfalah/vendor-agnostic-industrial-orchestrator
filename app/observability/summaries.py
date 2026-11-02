"""Structured output summaries for trace visibility."""

from typing import Any

from app.models.execution_result import ExecutionResult


def execution_summary(result: ExecutionResult) -> dict[str, Any]:
    """Return compact execution outputs for traces."""

    return {
        "final_status": result.final_status,
        "completed_steps": result.completed_steps,
        "failed_steps": result.failed_steps,
        "skipped_steps": result.skipped_steps,
        "governance_summary": result.governance_summary,
    }


def comparison_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Return compact comparison outputs keyed by method/runtime id."""

    return {
        row.get("method_id")
        or row.get("runtime_id"): {
            key: row[key]
            for key in (
                "policy_compliance_rate",
                "unsafe_execution_rate",
                "final_outcome_accuracy",
                "approval_resume_correctness",
                "resume_success_rate",
                "checkpoint_resume_success_rate",
                "checkpoint_reopen_resume_success_rate",
            )
            if key in row
        }
        for row in rows
    }


def langgraph_run_summary(run: dict[str, Any]) -> dict[str, Any]:
    """Return compact LangGraph runtime outputs for traces."""

    result = run["result"]
    return {
        **execution_summary(result),
        "approval_state": run.get("approval_state"),
        "gated_step_executed": run.get("approval_execution_performed", False),
        "resume_success": bool(run.get("resumed")),
        "interrupted": bool(run.get("interrupted")),
        "trace": run.get("trace", []),
    }


def crash_restart_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Return compact crash/restart outputs for top-level trace visibility."""

    metrics = summary.get("metrics", {})
    return {
        "checkpoint_resume_success_rate": metrics.get("checkpoint_resume_success_rate"),
        "checkpoint_reopen_resume_success_rate": metrics.get(
            "checkpoint_reopen_resume_success_rate"
        ),
        "post_reopen_final_outcome_accuracy": metrics.get("post_reopen_final_outcome_accuracy"),
        "checkpoint_reopen_trace_completeness": metrics.get("checkpoint_reopen_trace_completeness"),
        "runs": [
            {
                "case_id": run["case_id"],
                "approval_state": run["approval_state"],
                "gated_step_executed": run["gated_step_executed"],
                "final_status": run["final_status"],
                "resumed_from_checkpoint": run["resumed_from_checkpoint"],
            }
            for run in summary.get("runs", [])
        ],
    }
