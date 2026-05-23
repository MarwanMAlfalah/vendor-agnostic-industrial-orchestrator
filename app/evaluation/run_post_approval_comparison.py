"""Evaluate LangGraph controlled post-approval continuation."""

import csv
import json
from pathlib import Path
from typing import Any

from app.evaluation.baselines import GovernanceAwareReference, MethodRunResult
from app.evaluation.metrics import compute_metrics
from app.evaluation.scenario_cases import (
    EvaluationCase,
    load_post_approval_evaluation_cases,
)
from app.langgraph_runtime import LangGraphRuntime
from app.observability.summaries import comparison_summary
from app.observability.tracing import trace_experiment

RESULTS_DIR = Path("data/results")
DOCS_DIR = Path("docs")
POST_APPROVAL_CSV = RESULTS_DIR / "post_approval_comparison_results.csv"
POST_APPROVAL_JSON = RESULTS_DIR / "post_approval_summary.json"
POST_APPROVAL_MD = DOCS_DIR / "post_approval_comparison_summary.md"
POST_APPROVAL_METRICS_MD = DOCS_DIR / "post_approval_metrics_definitions.md"

REQUIRED_APPROVAL_TRACE = [
    "planner_node",
    "matcher_node",
    "governance_node",
    "approval_interrupt",
    "approval_resume",
    "approval_validated",
    "final_result",
]


def run_post_approval_comparison() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run post-approval continuation cases through both runtimes."""

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    cases = load_post_approval_evaluation_cases()
    with trace_experiment(
        "evaluation.run_post_approval_comparison",
        inputs={"case_count": len(cases)},
        metadata={"runtime_id": "post_approval_runner", "approval_case": True},
        tags=["evaluation", "post_approval"],
    ) as trace_handle:
        reference_runs = [GovernanceAwareReference().run_with_timing(case) for case in cases]
        langgraph_raw_runs = [
            LangGraphRuntime().run_case(
                case,
                approval_payload=case.approval_payload,
                controlled_approval_execution=True,
            )
            for case in cases
        ]
        langgraph_runs = [
            MethodRunResult(
                case=run["case"],
                result=run["result"],
                stage_latencies_ms=run["stage_latencies_ms"],
            )
            for run in langgraph_raw_runs
        ]

        reference_records = _reference_records(reference_runs)
        rows = [
            _runtime_row(
                "reference_v1",
                "Reference v1 custom deterministic orchestration",
                reference_runs,
                reference_records,
                graph_runtime=False,
            ),
            _runtime_row(
                "langgraph_runtime",
                "Experimental LangGraph controlled approval continuation",
                langgraph_runs,
                langgraph_raw_runs,
                graph_runtime=True,
            ),
        ]
        trace_handle.add_outputs(comparison_summary(rows))

    summary = {
        "evaluation_design": {
            "case_count": len(cases),
            "case_ids": [case.case_id for case in cases],
            "deterministic": True,
            "post_approval_continuation": True,
            "reference_v1_unchanged": True,
        },
        "cases": [_case_metadata(case) for case in cases],
        "runtimes": {
            "reference_v1": {
                "metrics": rows[0],
                "case_results": [_reference_case_summary(run) for run in reference_runs],
            },
            "langgraph_runtime": {
                "metrics": rows[1],
                "case_results": [_langgraph_case_summary(run) for run in langgraph_raw_runs],
            },
        },
    }

    _write_csv(POST_APPROVAL_CSV, rows)
    POST_APPROVAL_JSON.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    POST_APPROVAL_MD.write_text(
        _markdown_summary(rows, langgraph_raw_runs),
        encoding="utf-8",
    )
    POST_APPROVAL_METRICS_MD.write_text(_metrics_markdown(), encoding="utf-8")
    return rows, summary


def _runtime_row(
    runtime_id: str,
    runtime_name: str,
    run_results: list[MethodRunResult],
    trace_records: list[dict[str, Any]],
    graph_runtime: bool,
) -> dict[str, Any]:
    base_metrics = compute_metrics(run_results)
    return {
        "runtime_id": runtime_id,
        "runtime_name": runtime_name,
        "policy_compliance_rate": base_metrics["policy_compliance_rate"],
        "unsafe_execution_rate": base_metrics["unsafe_execution_rate"],
        "governance_decision_accuracy": base_metrics["governance_decision_accuracy"],
        "final_outcome_accuracy": _final_outcome_accuracy(trace_records),
        "average_total_latency_ms": base_metrics["average_total_latency_ms"],
        "average_execution_latency_ms": base_metrics["average_execution_latency_ms"],
        "approval_resume_correctness": _approval_resume_correctness(
            trace_records,
            graph_runtime,
        ),
        "approved_step_execution_rate": _approved_step_execution_rate(
            trace_records,
            graph_runtime,
        ),
        "approval_validation_accuracy": _approval_validation_accuracy(
            trace_records,
            graph_runtime,
        ),
        "post_resume_final_outcome_accuracy": _post_resume_final_outcome_accuracy(
            trace_records,
            graph_runtime,
        ),
        "gated_step_policy_compliance_rate": _gated_step_policy_compliance_rate(
            trace_records,
            graph_runtime,
        ),
        "resume_success_rate": _resume_success_rate(trace_records, graph_runtime),
        "approved_execution_trace_completeness": _approved_execution_trace_completeness(
            trace_records,
            graph_runtime,
        ),
    }


def _approval_resume_correctness(
    records: list[dict[str, Any]],
    graph_runtime: bool,
) -> float:
    if not graph_runtime:
        return 0.0
    correct = sum(
        1
        for record in records
        if record["interrupted"]
        and record["resumed"]
        and record["result"].final_status == record["case"].expected_post_resume_final_status
    )
    return _rate(correct, len(records))


def _approved_step_execution_rate(
    records: list[dict[str, Any]],
    graph_runtime: bool,
) -> float:
    valid_approved = [
        record
        for record in records
        if _approval_payload_is_valid(record["case"].approval_payload)
        and record["case"].expected_approval_execution_allowed
    ]
    if not graph_runtime:
        return 0.0
    executed = sum(1 for record in valid_approved if record["approval_execution_performed"])
    return _rate(executed, len(valid_approved))


def _approval_validation_accuracy(
    records: list[dict[str, Any]],
    graph_runtime: bool,
) -> float:
    if not graph_runtime:
        return 0.0
    correct = 0
    for record in records:
        expected_valid = _approval_payload_is_valid(record["case"].approval_payload)
        observed_valid = "approval_validated" in record["trace"]
        correct += int(expected_valid == observed_valid)

    return _rate(correct, len(records))


def _post_resume_final_outcome_accuracy(
    records: list[dict[str, Any]],
    graph_runtime: bool,
) -> float:
    if not graph_runtime:
        return 0.0
    correct = sum(
        1
        for record in records
        if record["resumed"]
        and record["result"].final_status == record["case"].expected_post_resume_final_status
    )
    return _rate(correct, len(records))


def _gated_step_policy_compliance_rate(
    records: list[dict[str, Any]],
    graph_runtime: bool,
) -> float:
    if not graph_runtime:
        return 0.0
    compliant = 0
    for record in records:
        expected_execute = bool(record["case"].expected_approval_execution_allowed)
        observed_execute = bool(record["approval_execution_performed"])
        final_status_matches = (
            record["result"].final_status == record["case"].expected_post_resume_final_status
        )
        compliant += int(expected_execute == observed_execute and final_status_matches)

    return _rate(compliant, len(records))


def _resume_success_rate(records: list[dict[str, Any]], graph_runtime: bool) -> float:
    if not graph_runtime:
        return 0.0
    resumed = sum(1 for record in records if record["resumed"])
    return _rate(resumed, len(records))


def _approved_execution_trace_completeness(
    records: list[dict[str, Any]],
    graph_runtime: bool,
) -> float:
    if not graph_runtime:
        return 0.0
    complete = 0
    for record in records:
        required_trace = [
            marker for marker in REQUIRED_APPROVAL_TRACE if marker != "approval_validated"
        ]
        has_validation_outcome = (
            "approval_validated" in record["trace"] or "approval_rejected" in record["trace"]
        )
        if record["case"].expected_approval_execution_allowed:
            required_trace.append("approved_execution")
        complete += int(
            has_validation_outcome and all(marker in record["trace"] for marker in required_trace)
        )

    return _rate(complete, len(records))


def _final_outcome_accuracy(records: list[dict[str, Any]]) -> float:
    correct = sum(
        1
        for record in records
        if record["result"].final_status == record["case"].expected_final_status
    )
    return _rate(correct, len(records))


def _reference_records(run_results: list[MethodRunResult]) -> list[dict[str, Any]]:
    return [
        {
            "case": run_result.case,
            "result": run_result.result,
            "trace": ["execution_agent"],
            "interrupted": False,
            "resumed": False,
            "approval_execution_performed": False,
        }
        for run_result in run_results
    ]


def _approval_payload_is_valid(payload: dict[str, object] | None) -> bool:
    if not payload:
        return False
    token = payload.get("approval_token")
    return (
        payload.get("approved") is True
        and isinstance(payload.get("approved_by"), str)
        and bool(payload.get("approved_by"))
        and isinstance(token, str)
        and token.startswith("APPROVED-")
    )


def _case_metadata(case: EvaluationCase) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "scenario_category": case.scenario_category,
        "expected_governance_sequence": case.expected_governance_sequence,
        "expected_final_status": case.expected_final_status,
        "expected_post_resume_final_status": case.expected_post_resume_final_status,
        "expected_approval_execution_allowed": case.expected_approval_execution_allowed,
        "approval_payload": case.approval_payload,
        "approval_resume_mutation": case.approval_resume_mutation,
        "industrial_context": case.industrial_context,
    }


def _reference_case_summary(run: MethodRunResult) -> dict[str, Any]:
    return {
        "case_id": run.case.case_id,
        "final_status": run.result.final_status,
        "completed_steps": run.result.completed_steps,
        "skipped_steps": run.result.skipped_steps,
        "trace": ["execution_agent"],
    }


def _langgraph_case_summary(run: dict[str, Any]) -> dict[str, Any]:
    result = run["result"]
    return {
        "case_id": run["case"].case_id,
        "final_status": result.final_status,
        "completed_steps": result.completed_steps,
        "skipped_steps": result.skipped_steps,
        "trace": run["trace"],
        "interrupted": run["interrupted"],
        "resumed": run["resumed"],
        "approval_state": run["approval_state"],
        "approval_validation_error": run["approval_validation_error"],
        "approval_execution_performed": run["approval_execution_performed"],
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
        "average_total_latency_ms",
        "average_execution_latency_ms",
        "approval_resume_correctness",
        "approved_step_execution_rate",
        "approval_validation_accuracy",
        "post_resume_final_outcome_accuracy",
        "gated_step_policy_compliance_rate",
        "resume_success_rate",
        "approved_execution_trace_completeness",
    ]
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _markdown_summary(
    rows: list[dict[str, Any]],
    langgraph_runs: list[dict[str, Any]],
) -> str:
    table = _markdown_table(
        rows,
        [
            ("Runtime", "runtime_name"),
            ("Final Outcome Acc.", "final_outcome_accuracy"),
            ("Resume Correctness", "approval_resume_correctness"),
            ("Approved Step Exec.", "approved_step_execution_rate"),
            ("Approval Validation Acc.", "approval_validation_accuracy"),
            ("Gated Policy Compliance", "gated_step_policy_compliance_rate"),
            ("Trace Completeness", "approved_execution_trace_completeness"),
        ],
    )
    valid_run = next(run for run in langgraph_runs if run["approval_execution_performed"])
    invalid_run = next(run for run in langgraph_runs if not run["approval_execution_performed"])

    return f"""# Post-Approval Continuation Comparison

This experiment extends the optional LangGraph runtime from simple
pause/resume semantics to controlled post-approval continuation. A
`REQUIRE_APPROVAL` step now pauses, persists graph state, resumes with an
explicit approval payload, revalidates policy eligibility and adapter mapping,
and executes the gated step only when approval and mapping checks pass.

## Results

{table}

## Valid Approval Example

- Case: `{valid_run['case'].case_id}`
- Approval state: `{valid_run['approval_state']}`
- Final status: `{valid_run['result'].final_status}`
- Gated step executed: `{valid_run['approval_execution_performed']}`
- Trace: `{valid_run['trace']}`

## Invalid Or Missing Approval Example

- Case: `{invalid_run['case'].case_id}`
- Approval state: `{invalid_run['approval_state']}`
- Validation error: `{invalid_run['approval_validation_error']}`
- Final status: `{invalid_run['result'].final_status}`
- Gated step executed: `{invalid_run['approval_execution_performed']}`

## What This Adds Beyond Parity

The reference runtime remains policy-correct but does not execute approval-gated
steps after resume. The LangGraph runtime now demonstrates graph-native
checkpointing plus controlled continuation: approval validation, revalidation of
adapter/capability mapping, approved execution, safe rejection, and complete
approval traces.
"""


def _metrics_markdown() -> str:
    return """# Post-Approval Metrics Definitions

## approval_resume_correctness
Fraction of approval-gated cases that interrupt, resume, and end with the gold
post-resume final status.

Formula: `correct_resumed_approval_cases / approval_gated_cases`

## approved_step_execution_rate
Fraction of validly approved gated steps that actually execute.

Formula: `executed_valid_approved_gated_steps / valid_approved_gated_steps`

## approval_validation_accuracy
Fraction of approval decisions correctly accepted or rejected according to the
approval payload.

Formula: `correct_approval_validation_decisions / approval_gated_cases`

## post_resume_final_outcome_accuracy
Fraction of resumed workflows whose final status matches the gold post-resume
status.

Formula: `post_resume_status_matches / approval_gated_cases`

## gated_step_policy_compliance_rate
Fraction of gated steps handled according to expected policy before and after
resume.

Formula: `policy_compliant_gated_step_runs / approval_gated_cases`

## resume_success_rate
Fraction of approval-gated cases where the graph resumes after interrupt.

Formula: `resumed_approval_cases / approval_gated_cases`

## approved_execution_trace_completeness
Fraction of approval-resumed runs whose traces contain all required approval
markers. A complete trace includes either `approval_validated` or
`approval_rejected`; runs expected to execute must also contain
`approved_execution`.

Formula: `complete_approval_traces / approval_gated_cases`
"""


def _markdown_table(
    rows: list[dict[str, Any]],
    columns: list[tuple[str, str]],
) -> str:
    header = "| " + " | ".join(label for label, _ in columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = ["| " + " | ".join(str(row[field]) for _, field in columns) + " |" for row in rows]
    return "\n".join([header, separator, *body])


def _rate(count: int, total: int) -> float:
    if total == 0:
        return 0.0

    return round(count / total, 4)


def main() -> None:
    """Command-line entrypoint."""

    rows, _ = run_post_approval_comparison()
    print(f"Post-approval comparison CSV: {POST_APPROVAL_CSV}")
    print(f"Post-approval summary JSON: {POST_APPROVAL_JSON}")
    print(f"Post-approval summary Markdown: {POST_APPROVAL_MD}")
    print(f"Post-approval metrics Markdown: {POST_APPROVAL_METRICS_MD}")
    print("Post-approval comparison results:")
    for row in rows:
        print(
            "  "
            f"{row['runtime_id']}: "
            f"approval_resume_correctness={row['approval_resume_correctness']}, "
            f"approved_step_execution_rate={row['approved_step_execution_rate']}, "
            f"approval_validation_accuracy={row['approval_validation_accuracy']}, "
            f"gated_step_policy_compliance_rate={row['gated_step_policy_compliance_rate']}"
        )


if __name__ == "__main__":
    main()
