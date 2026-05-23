"""Run mixed workflow comparison for reference and LangGraph runtimes."""

import csv
import json
from pathlib import Path
from typing import Any

from app.evaluation.baselines import GovernanceAwareReference, MethodRunResult
from app.evaluation.metrics import compute_metrics
from app.evaluation.scenario_cases import EvaluationCase, load_mixed_evaluation_cases
from app.langgraph_runtime import LangGraphRuntime
from app.observability.summaries import comparison_summary
from app.observability.tracing import trace_experiment

RESULTS_DIR = Path("data/results")
DOCS_DIR = Path("docs")
MIXED_COMPARISON_CSV = RESULTS_DIR / "mixed_comparison_results.csv"
LANGGRAPH_SUMMARY_JSON = RESULTS_DIR / "langgraph_summary.json"
MIXED_SUMMARY_MD = DOCS_DIR / "mixed_workflow_comparison_summary.md"

GRAPH_STAGE_TRACE = ["planner_node", "matcher_node", "governance_node", "execution_node"]


def run_mixed_workflow_comparison() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run deterministic mixed workflows through both runtimes."""

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    cases = load_mixed_evaluation_cases()
    with trace_experiment(
        "evaluation.run_mixed_workflow_comparison",
        inputs={"case_count": len(cases)},
        metadata={"runtime_id": "mixed_workflow_runner", "mixed_workflow": True},
        tags=["evaluation", "mixed_workflow"],
    ) as trace_handle:
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

        reference_trace_records = _reference_trace_records(reference_runs)
        rows = [
            _comparison_row(
                "reference_v1",
                "Reference v1 custom deterministic orchestration",
                reference_runs,
                reference_trace_records,
                graph_native_interrupts=False,
            ),
            _comparison_row(
                "langgraph_runtime",
                "Experimental LangGraph runtime",
                langgraph_runs,
                langgraph_raw_runs,
                graph_native_interrupts=True,
            ),
        ]
        trace_handle.add_outputs(comparison_summary(rows))

    summary = {
        "evaluation_design": {
            "case_count": len(cases),
            "case_ids": [case.case_id for case in cases],
            "deterministic": True,
            "mixed_workflows": True,
            "langgraph_optional_runtime": True,
        },
        "mixed_cases": [_case_metadata(case) for case in cases],
        "runtimes": {
            "reference_v1": {
                "description": "Existing custom deterministic governance-aware runtime.",
                "metrics": rows[0],
                "case_results": [_reference_case_summary(run) for run in reference_runs],
            },
            "langgraph_runtime": {
                "description": (
                    "Experimental LangGraph runtime with persisted interrupt/resume "
                    "checkpoints for approval-required mixed workflows."
                ),
                "metrics": rows[1],
                "case_results": [_langgraph_case_summary(run) for run in langgraph_raw_runs],
            },
        },
    }

    _write_csv(MIXED_COMPARISON_CSV, rows)
    LANGGRAPH_SUMMARY_JSON.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    MIXED_SUMMARY_MD.write_text(
        _markdown_summary(rows, cases, langgraph_raw_runs), encoding="utf-8"
    )
    return rows, summary


def _comparison_row(
    runtime_id: str,
    runtime_name: str,
    run_results: list[MethodRunResult],
    trace_records: list[dict[str, Any]],
    graph_native_interrupts: bool,
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
        "trace_stage_coverage": _trace_stage_coverage(trace_records),
        "interrupt_trace_quality": _interrupt_trace_quality(
            trace_records,
            graph_native_interrupts,
        ),
        "average_total_latency_ms": metrics["average_total_latency_ms"],
        "average_execution_latency_ms": metrics["average_execution_latency_ms"],
        "approval_resume_correctness": _approval_resume_correctness(
            trace_records,
            graph_native_interrupts,
        ),
        "resume_success_rate": _resume_success_rate(trace_records, graph_native_interrupts),
        "post_resume_final_outcome_accuracy": _post_resume_final_outcome_accuracy(
            trace_records,
            graph_native_interrupts,
        ),
    }


def _trace_completeness(trace_records: list[dict[str, Any]]) -> float:
    if not trace_records:
        return 0.0

    complete = sum(
        1
        for record in trace_records
        if set(GRAPH_STAGE_TRACE).issubset(set(record.get("trace", [])))
    )
    return round(complete / len(trace_records), 4)


def _trace_stage_coverage(trace_records: list[dict[str, Any]]) -> float:
    if not trace_records:
        return 0.0

    ratios = []
    for record in trace_records:
        trace = set(record.get("trace", []))
        ratios.append(
            sum(1 for stage in GRAPH_STAGE_TRACE if stage in trace) / len(GRAPH_STAGE_TRACE)
        )

    return round(sum(ratios) / len(ratios), 4)


def _interrupt_trace_quality(
    trace_records: list[dict[str, Any]],
    graph_native_interrupts: bool,
) -> float:
    approval_records = _approval_records(trace_records)
    if not approval_records:
        return 0.0

    if not graph_native_interrupts:
        return 0.0

    quality_count = sum(
        1
        for record in approval_records
        if record["interrupted"]
        and record["resumed"]
        and "approval_interrupt" in record["trace"]
        and "approval_resume" in record["trace"]
        and record["trace"].index("approval_interrupt")
        < record["trace"].index("approval_resume")
        < record["trace"].index("execution_node")
    )
    return round(quality_count / len(approval_records), 4)


def _approval_resume_correctness(
    trace_records: list[dict[str, Any]],
    graph_native_interrupts: bool,
) -> float:
    approval_records = _approval_records(trace_records)
    if not approval_records:
        return 0.0

    if not graph_native_interrupts:
        return 0.0

    correct = sum(
        1
        for record in approval_records
        if record["interrupted"]
        and record["resumed"]
        and record["result"].final_status
        == (
            record["case"].expected_post_resume_final_status or record["case"].expected_final_status
        )
    )
    return round(correct / len(approval_records), 4)


def _resume_success_rate(
    trace_records: list[dict[str, Any]],
    graph_native_interrupts: bool,
) -> float:
    approval_records = _approval_records(trace_records)
    if not approval_records:
        return 0.0
    if not graph_native_interrupts:
        return 0.0

    resumed = sum(1 for record in approval_records if record["resumed"])
    return round(resumed / len(approval_records), 4)


def _post_resume_final_outcome_accuracy(
    trace_records: list[dict[str, Any]],
    graph_native_interrupts: bool,
) -> float:
    approval_records = _approval_records(trace_records)
    if not approval_records:
        return 0.0
    if not graph_native_interrupts:
        return 0.0

    correct = sum(
        1
        for record in approval_records
        if record["resumed"]
        and record["result"].final_status
        == (
            record["case"].expected_post_resume_final_status or record["case"].expected_final_status
        )
    )
    return round(correct / len(approval_records), 4)


def _approval_records(trace_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        record
        for record in trace_records
        if "REQUIRE_APPROVAL" in (record["case"].expected_governance_sequence or [])
    ]


def _reference_trace_records(
    run_results: list[MethodRunResult],
) -> list[dict[str, Any]]:
    return [
        {
            "case": run_result.case,
            "result": run_result.result,
            "trace": ["execution_agent"],
            "interrupted": False,
            "resumed": False,
        }
        for run_result in run_results
    ]


def _reference_case_summary(run: MethodRunResult) -> dict[str, Any]:
    return {
        "case_id": run.case.case_id,
        "scenario_category": run.case.scenario_category,
        "final_status": run.result.final_status,
        "completed_steps": run.result.completed_steps,
        "skipped_steps": run.result.skipped_steps,
        "trace": ["execution_agent"],
    }


def _langgraph_case_summary(run: dict[str, Any]) -> dict[str, Any]:
    result = run["result"]
    return {
        "case_id": run["case"].case_id,
        "scenario_category": run["case"].scenario_category,
        "final_status": result.final_status,
        "completed_steps": result.completed_steps,
        "skipped_steps": result.skipped_steps,
        "trace": run["trace"],
        "interrupted": run["interrupted"],
        "resumed": run["resumed"],
        "stage_latencies_ms": run["stage_latencies_ms"],
    }


def _case_metadata(case: EvaluationCase) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "scenario_category": case.scenario_category,
        "expected_final_status": case.expected_final_status,
        "expected_governance_sequence": case.expected_governance_sequence,
        "expected_post_resume_final_status": case.expected_post_resume_final_status,
        "industrial_context": case.industrial_context,
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
        "trace_stage_coverage",
        "interrupt_trace_quality",
        "average_total_latency_ms",
        "average_execution_latency_ms",
        "approval_resume_correctness",
        "resume_success_rate",
        "post_resume_final_outcome_accuracy",
    ]
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _markdown_summary(
    rows: list[dict[str, Any]],
    cases: list[EvaluationCase],
    langgraph_runs: list[dict[str, Any]],
) -> str:
    table = _markdown_table(
        rows,
        [
            ("Runtime", "runtime_name"),
            ("Policy Compliance", "policy_compliance_rate"),
            ("Unsafe Exec.", "unsafe_execution_rate"),
            ("Gov. Decision Acc.", "governance_decision_accuracy"),
            ("Final Outcome Acc.", "final_outcome_accuracy"),
            ("Trace Completeness", "trace_completeness"),
            ("Stage Coverage", "trace_stage_coverage"),
            ("Interrupt Trace Quality", "interrupt_trace_quality"),
            ("Resume Success", "resume_success_rate"),
            ("Post-Resume Outcome Acc.", "post_resume_final_outcome_accuracy"),
        ],
    )
    sample_case = cases[0]
    sample_interrupt = next(run for run in langgraph_runs if run["interrupted"])

    return f"""# Mixed Workflow Comparison Summary

This experiment adds 12 deterministic mixed multi-step workflows and compares
the existing reference runtime with the optional LangGraph runtime.

## Aggregate Results

{table}

## Sample Mixed Case

- Case: `{sample_case.case_id}`
- Category: `{sample_case.scenario_category}`
- Expected governance sequence: `{sample_case.expected_governance_sequence}`
- Industrial context: `{sample_case.industrial_context}`

## Sample Interrupt/Resume Case

- Case: `{sample_interrupt['case'].case_id}`
- Interrupted: `{sample_interrupt['interrupted']}`
- Resumed: `{sample_interrupt['resumed']}`
- Final status: `{sample_interrupt['result'].final_status}`
- Trace: `{sample_interrupt['trace']}`

## Interpretation

The reference runtime preserves policy correctness. The LangGraph runtime is
evaluated for additional runtime-level value: persisted approval checkpoints,
explicit resume behavior, and stage-level graph traces.
"""


def _markdown_table(
    rows: list[dict[str, Any]],
    columns: list[tuple[str, str]],
) -> str:
    header = "| " + " | ".join(label for label, _ in columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = ["| " + " | ".join(str(row[field]) for _, field in columns) + " |" for row in rows]
    return "\n".join([header, separator, *body])


def main() -> None:
    """Command-line entrypoint."""

    rows, _ = run_mixed_workflow_comparison()
    print(f"Mixed comparison CSV: {MIXED_COMPARISON_CSV}")
    print(f"LangGraph summary JSON: {LANGGRAPH_SUMMARY_JSON}")
    print(f"Mixed comparison Markdown: {MIXED_SUMMARY_MD}")
    print("Mixed workflow comparison results:")
    for row in rows:
        print(
            "  "
            f"{row['runtime_id']}: "
            f"policy_compliance_rate={row['policy_compliance_rate']}, "
            f"trace_stage_coverage={row['trace_stage_coverage']}, "
            f"interrupt_trace_quality={row['interrupt_trace_quality']}, "
            f"resume_success_rate={row['resume_success_rate']}"
        )


if __name__ == "__main__":
    main()
