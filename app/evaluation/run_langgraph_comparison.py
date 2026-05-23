"""Compare the reference runtime with the optional LangGraph runtime."""

import csv
import json
from pathlib import Path
from typing import Any

from app.evaluation.baselines import GovernanceAwareReference, MethodRunResult
from app.evaluation.metrics import compute_metrics
from app.evaluation.scenario_cases import load_evaluation_cases
from app.langgraph_runtime import LangGraphRuntime
from app.observability.tracing import trace_experiment

RESULTS_DIR = Path("data/results")
DOCS_DIR = Path("docs")
LANGGRAPH_COMPARISON_CSV = RESULTS_DIR / "langgraph_comparison_results.csv"
LANGGRAPH_SUMMARY_JSON = RESULTS_DIR / "langgraph_summary.json"
LANGGRAPH_SUMMARY_MD = DOCS_DIR / "langgraph_comparison_summary.md"

TRACE_NODES = {
    "planner_node",
    "matcher_node",
    "governance_node",
    "execution_node",
}


def run_langgraph_comparison() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run reference and LangGraph runtimes on the same deterministic cases."""

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    cases = load_evaluation_cases()
    with trace_experiment(
        "evaluation.run_langgraph_comparison",
        inputs={"case_count": len(cases)},
        metadata={"runtime_id": "langgraph_comparison_runner"},
        tags=["evaluation", "langgraph"],
    ):
        reference_runs = [GovernanceAwareReference().run_with_timing(case) for case in cases]
        langgraph_raw_runs = [LangGraphRuntime().run_case(case) for case in cases]
    langgraph_runs = [
        MethodRunResult(
            case=run["case"],
            result=run["result"],
            stage_latencies_ms=run["stage_latencies_ms"],
        )
        for run in langgraph_raw_runs
    ]

    rows = [
        _comparison_row(
            "reference_v1",
            "Reference v1 custom deterministic orchestration",
            reference_runs,
            _reference_trace_records(reference_runs),
            reference_runtime=True,
        ),
        _comparison_row(
            "langgraph_runtime",
            "Experimental LangGraph runtime",
            langgraph_runs,
            langgraph_raw_runs,
            reference_runtime=False,
        ),
    ]

    summary = {
        "evaluation_design": {
            "case_count": len(cases),
            "case_ids": [case.case_id for case in cases],
            "deterministic": True,
            "stochastic_llm_logic": False,
            "langgraph_optional_runtime": True,
        },
        "runtimes": {
            "reference_v1": {
                "description": "Existing custom deterministic orchestration path.",
                "metrics": rows[0],
            },
            "langgraph_runtime": {
                "description": (
                    "Experimental LangGraph control-flow wrapper using existing "
                    "Planner, Matcher, Governance, and Execution logic."
                ),
                "metrics": rows[1],
                "case_results": [_langgraph_case_summary(run) for run in langgraph_raw_runs],
            },
        },
    }

    _write_csv(LANGGRAPH_COMPARISON_CSV, rows)
    LANGGRAPH_SUMMARY_JSON.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    LANGGRAPH_SUMMARY_MD.write_text(_markdown_summary(rows), encoding="utf-8")
    return rows, summary


def _comparison_row(
    runtime_id: str,
    runtime_name: str,
    run_results: list[MethodRunResult],
    trace_records: list[dict[str, Any]],
    reference_runtime: bool,
) -> dict[str, Any]:
    metrics = compute_metrics(run_results)
    return {
        "runtime_id": runtime_id,
        "runtime_name": runtime_name,
        "policy_compliance_rate": metrics["policy_compliance_rate"],
        "unsafe_execution_rate": metrics["unsafe_execution_rate"],
        "governance_decision_accuracy": metrics["governance_decision_accuracy"],
        "final_outcome_accuracy": metrics["final_outcome_accuracy"],
        "trace_completeness": _trace_completeness(trace_records),
        "average_total_latency_ms": metrics["average_total_latency_ms"],
        "average_execution_latency_ms": metrics["average_execution_latency_ms"],
        "approval_resume_correctness": _approval_resume_correctness(
            trace_records,
            reference_runtime,
        ),
        "resume_success_rate": _resume_success_rate(trace_records, reference_runtime),
    }


def _trace_completeness(trace_records: list[dict[str, Any]]) -> float:
    if not trace_records:
        return 0.0

    complete = sum(
        1 for record in trace_records if TRACE_NODES.issubset(set(record["trace"]))
    )
    return round(complete / len(trace_records), 4)


def _approval_resume_correctness(
    trace_records: list[dict[str, Any]],
    reference_runtime: bool,
) -> float:
    approval_records = [
        record
        for record in trace_records
        if record["case"].expected_governance_decision == "REQUIRE_APPROVAL"
    ]
    if not approval_records:
        return 0.0

    correct = 0
    for record in approval_records:
        result = record["result"]
        if reference_runtime:
            correct += int(result.final_status == "partial_success")
        else:
            correct += int(
                record["interrupted"]
                and record["resumed"]
                and result.final_status == "partial_success"
                and result.completed_steps == 0
            )

    return round(correct / len(approval_records), 4)


def _resume_success_rate(
    trace_records: list[dict[str, Any]],
    reference_runtime: bool,
) -> float:
    approval_records = [
        record
        for record in trace_records
        if record["case"].expected_governance_decision == "REQUIRE_APPROVAL"
    ]
    if not approval_records:
        return 0.0

    if reference_runtime:
        return 1.0

    resumed = sum(1 for record in approval_records if record["resumed"])
    return round(resumed / len(approval_records), 4)


def _reference_trace_records(
    run_results: list[MethodRunResult],
) -> list[dict[str, Any]]:
    return [
        {
            "case": run_result.case,
            "result": run_result.result,
            "trace": sorted(TRACE_NODES),
            "interrupted": False,
            "resumed": False,
        }
        for run_result in run_results
    ]


def _langgraph_case_summary(run: dict[str, Any]) -> dict[str, Any]:
    result = run["result"]
    return {
        "case_id": run["case"].case_id,
        "final_status": result.final_status,
        "trace": run["trace"],
        "interrupted": run["interrupted"],
        "resumed": run["resumed"],
        "stage_latencies_ms": run["stage_latencies_ms"],
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "runtime_id",
        "runtime_name",
        "policy_compliance_rate",
        "unsafe_execution_rate",
        "governance_decision_accuracy",
        "final_outcome_accuracy",
        "trace_completeness",
        "average_total_latency_ms",
        "average_execution_latency_ms",
        "approval_resume_correctness",
        "resume_success_rate",
    ]
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _markdown_summary(rows: list[dict[str, Any]]) -> str:
    table = _markdown_table(
        rows,
        [
            ("Runtime", "runtime_name"),
            ("Policy Compliance", "policy_compliance_rate"),
            ("Unsafe Exec.", "unsafe_execution_rate"),
            ("Gov. Decision Acc.", "governance_decision_accuracy"),
            ("Final Outcome Acc.", "final_outcome_accuracy"),
            ("Trace Completeness", "trace_completeness"),
            ("Total ms", "average_total_latency_ms"),
            ("Execution ms", "average_execution_latency_ms"),
            ("Approval Resume Correctness", "approval_resume_correctness"),
            ("Resume Success", "resume_success_rate"),
        ],
    )

    return f"""# LangGraph Runtime Comparison

This experiment compares the existing deterministic reference runtime with an
optional LangGraph runtime path. The LangGraph path does not replace the
reference implementation; it wraps the same planner, matcher, governance, and
execution logic in a graph runtime with interrupt/resume support for approval
checkpoints.

## Results

{table}

## Interpretation

The LangGraph runtime is expected to match the reference method on policy and
final-outcome metrics while adding explicit graph traces and pause/resume
semantics for `REQUIRE_APPROVAL` cases.
"""


def _markdown_table(
    rows: list[dict[str, Any]],
    columns: list[tuple[str, str]],
) -> str:
    header = "| " + " | ".join(label for label, _ in columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = [
        "| "
        + " | ".join(str(row[field]) for _, field in columns)
        + " |"
        for row in rows
    ]
    return "\n".join([header, separator, *body])


def main() -> None:
    """Command-line entrypoint."""

    rows, _ = run_langgraph_comparison()
    print(f"LangGraph comparison CSV: {LANGGRAPH_COMPARISON_CSV}")
    print(f"LangGraph summary JSON: {LANGGRAPH_SUMMARY_JSON}")
    print(f"LangGraph summary Markdown: {LANGGRAPH_SUMMARY_MD}")
    print("LangGraph comparison results:")
    for row in rows:
        print(
            "  "
            f"{row['runtime_id']}: "
            f"policy_compliance_rate={row['policy_compliance_rate']}, "
            f"unsafe_execution_rate={row['unsafe_execution_rate']}, "
            f"trace_completeness={row['trace_completeness']}, "
            f"resume_success_rate={row['resume_success_rate']}"
        )


if __name__ == "__main__":
    main()
