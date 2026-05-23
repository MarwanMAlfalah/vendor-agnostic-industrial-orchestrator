"""Run deterministic governance-aware execution experiments."""

import csv
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.agents import ExecutionAgent
from app.evaluation.scenario_cases import EvaluationCase, load_evaluation_cases
from app.models.execution_result import ExecutionResult

RESULTS_DIR = Path("data/results")
CSV_FIELDS = [
    "case_id",
    "goal_id",
    "goal_type",
    "final_status",
    "completed_steps",
    "failed_steps",
    "skipped_steps",
    "allow_count",
    "block_count",
    "require_approval_count",
    "fallback_count",
    "safe_abort_count",
]


def run_experiments() -> tuple[list[dict[str, Any]], dict[str, Any], Path, Path, Path]:
    """Execute all evaluation cases and save CSV and JSON outputs."""

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    csv_path = RESULTS_DIR / f"evaluation_results_{timestamp}.csv"
    json_path = RESULTS_DIR / f"evaluation_results_{timestamp}.json"
    summary_path = RESULTS_DIR / f"evaluation_summary_{timestamp}.json"

    execution_agent = ExecutionAgent()
    rows: list[dict[str, Any]] = []
    full_results: list[dict[str, Any]] = []

    for case in load_evaluation_cases():
        result = execution_agent.run(case.governance_plan)
        rows.append(_result_row(case, result))
        full_results.append(
            {
                "case_id": case.case_id,
                "scenario_category": case.scenario_category,
                "governance_plan": case.governance_plan.model_dump(),
                "execution_result": result.model_dump(),
            }
        )

    _write_csv(csv_path, rows)
    json_path.write_text(
        json.dumps(full_results, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    summary = _summary(rows)
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return rows, summary, csv_path, json_path, summary_path


def _result_row(case: EvaluationCase, result: ExecutionResult) -> dict[str, Any]:
    governance_summary = result.governance_summary
    return {
        "case_id": case.case_id,
        "goal_id": result.goal_id,
        "goal_type": case.governance_plan.goal_type,
        "final_status": result.final_status,
        "completed_steps": result.completed_steps,
        "failed_steps": result.failed_steps,
        "skipped_steps": result.skipped_steps,
        "allow_count": governance_summary.get("allow", 0),
        "block_count": governance_summary.get("block", 0),
        "require_approval_count": governance_summary.get("require_approval", 0),
        "fallback_count": governance_summary.get("fallback", 0),
        "safe_abort_count": governance_summary.get("safe_abort", 0),
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = Counter(row["final_status"] for row in rows)
    total_runs = len(rows)
    intervention_count = sum(
        1
        for row in rows
        if row["require_approval_count"] > 0
        or row["block_count"] > 0
        or row["safe_abort_count"] > 0
        or row["fallback_count"] > 0
    )

    return {
        "total_runs": total_runs,
        "success_count": status_counts["success"],
        "partial_success_count": status_counts["partial_success"],
        "blocked_count": status_counts["blocked"],
        "safe_aborted_count": status_counts["safe_aborted"],
        "failed_count": status_counts["failed"],
        "success_rate": _rate(status_counts["success"], total_runs),
        "partial_success_rate": _rate(status_counts["partial_success"], total_runs),
        "blocked_rate": _rate(status_counts["blocked"], total_runs),
        "safe_aborted_rate": _rate(status_counts["safe_aborted"], total_runs),
        "failed_rate": _rate(status_counts["failed"], total_runs),
        "governance_intervention_rate": _rate(intervention_count, total_runs),
        "average_completed_steps": _average(rows, "completed_steps"),
        "average_skipped_steps": _average(rows, "skipped_steps"),
    }


def _rate(count: int, total: int) -> float:
    if total == 0:
        return 0.0

    return round(count / total, 4)


def _average(rows: list[dict[str, Any]], field: str) -> float:
    if not rows:
        return 0.0

    return round(sum(row[field] for row in rows) / len(rows), 4)


def main() -> None:
    """Command-line entrypoint."""

    _, summary, csv_path, json_path, summary_path = run_experiments()
    print(f"CSV results: {csv_path}")
    print(f"JSON results: {json_path}")
    print(f"Summary JSON: {summary_path}")
    print("Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
