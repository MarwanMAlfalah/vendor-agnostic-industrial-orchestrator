"""Run deterministic baseline comparisons and write reporting artifacts."""

import csv
import json
from pathlib import Path
from typing import Any

from app.evaluation.baselines import EvaluationMethod, MethodRunResult, comparison_methods
from app.evaluation.metrics import compute_metrics, flatten_metrics
from app.evaluation.scenario_cases import EvaluationCase, load_evaluation_cases
from app.observability.summaries import comparison_summary
from app.observability.tracing import trace_experiment

RESULTS_DIR = Path("data/results")
DOCS_DIR = Path("docs")
COMPARISON_CSV = RESULTS_DIR / "comparison_results.csv"
BASELINE_SUMMARY_JSON = RESULTS_DIR / "baseline_summary.json"
COMPARISON_SUMMARY_MD = DOCS_DIR / "comparison_summary.md"


def run_comparison() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run all deterministic comparison methods and write artifacts."""

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    cases = load_evaluation_cases()
    aggregate_rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {
        "evaluation_design": {
            "case_count": len(cases),
            "case_ids": [case.case_id for case in cases],
            "gold_labels": [
                {
                    "case_id": case.case_id,
                    "expected_final_status": case.expected_final_status,
                    "expected_governance_decision": case.expected_governance_decision,
                    "expected_execution_allowed": case.expected_execution_allowed,
                }
                for case in cases
            ],
            "deterministic": True,
            "stochastic_llm_logic": False,
        },
        "methods": {},
    }

    with trace_experiment(
        "evaluation.run_comparison",
        inputs={"case_count": len(cases)},
        metadata={"runtime_id": "comparison_runner"},
        tags=["evaluation", "comparison"],
    ) as trace_handle:
        for method in comparison_methods():
            method_results = _run_method(method, cases)
            metrics = compute_metrics(method_results)
            aggregate_rows.append(
                {
                    "method_id": method.method_id,
                    "method_name": method.method_name,
                    **flatten_metrics(metrics),
                }
            )
            summary["methods"][method.method_id] = {
                "method_name": method.method_name,
                "description": method.description,
                "metrics": metrics,
                "case_results": [
                    _case_result_summary(method_result) for method_result in method_results
                ],
            }
        trace_handle.add_outputs(comparison_summary(aggregate_rows))

    _write_comparison_csv(COMPARISON_CSV, aggregate_rows)
    BASELINE_SUMMARY_JSON.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    COMPARISON_SUMMARY_MD.write_text(
        _comparison_markdown(aggregate_rows, summary),
        encoding="utf-8",
    )

    return aggregate_rows, summary


def _run_method(
    method: EvaluationMethod,
    cases: list[EvaluationCase],
) -> list[MethodRunResult]:
    return [method.run_with_timing(case) for case in cases]


def _case_result_summary(method_result: MethodRunResult) -> dict[str, Any]:
    case = method_result.case
    result = method_result.result
    return {
        "case_id": case.case_id,
        "scenario_category": case.scenario_category,
        "expected_final_status": case.expected_final_status,
        "expected_governance_decision": case.expected_governance_decision,
        "expected_execution_allowed": case.expected_execution_allowed,
        "goal_id": result.goal_id,
        "final_status": result.final_status,
        "completed_steps": result.completed_steps,
        "failed_steps": result.failed_steps,
        "skipped_steps": result.skipped_steps,
        "stage_latencies_ms": method_result.stage_latencies_ms,
        "executed_adapters": [
            step.adapter
            for step in result.step_results
            if step.status == "executed" and step.adapter is not None
        ],
    }


def _write_comparison_csv(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    fieldnames = [
        "method_id",
        "method_name",
        "total_runs",
        "success_count",
        "success_rate",
        "partial_success_count",
        "partial_success_rate",
        "blocked_count",
        "blocked_rate",
        "safe_aborted_count",
        "safe_aborted_rate",
        "failed_count",
        "failed_rate",
        "governance_intervention_rate",
        "governance_decision_accuracy",
        "final_outcome_accuracy",
        "policy_compliance_rate",
        "unsafe_execution_rate",
        "approval_bypass_rate",
        "invalid_mapping_containment_rate",
        "average_completed_steps",
        "average_skipped_steps",
        "execution_coverage_ratio",
        "average_planning_latency_ms",
        "average_matching_latency_ms",
        "average_governance_latency_ms",
        "average_execution_latency_ms",
        "average_total_latency_ms",
        "adapter_utilization_ratio.legacy_adapter",
        "adapter_utilization_ratio.opcua_adapter",
        "adapter_utilization_ratio.rest_adapter",
    ]
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _comparison_markdown(
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
) -> str:
    table = _markdown_table(
        rows,
        [
            ("Method", "method_name"),
            ("Success Rate", "success_rate"),
            ("Partial Rate", "partial_success_rate"),
            ("Blocked Rate", "blocked_rate"),
            ("Safe-Abort Rate", "safe_aborted_rate"),
            ("Failed Rate", "failed_rate"),
            ("Gov. Intervention", "governance_intervention_rate"),
            ("Coverage", "execution_coverage_ratio"),
        ],
    )
    policy_table = _markdown_table(
        rows,
        [
            ("Method", "method_name"),
            ("Gov. Decision Acc.", "governance_decision_accuracy"),
            ("Final Outcome Acc.", "final_outcome_accuracy"),
            ("Policy Compliance", "policy_compliance_rate"),
            ("Unsafe Exec.", "unsafe_execution_rate"),
            ("Approval Bypass", "approval_bypass_rate"),
            ("Invalid Mapping Containment", "invalid_mapping_containment_rate"),
        ],
    )
    latency_table = _markdown_table(
        rows,
        [
            ("Method", "method_name"),
            ("Planning ms", "average_planning_latency_ms"),
            ("Matching ms", "average_matching_latency_ms"),
            ("Governance ms", "average_governance_latency_ms"),
            ("Execution ms", "average_execution_latency_ms"),
            ("Total ms", "average_total_latency_ms"),
        ],
    )
    method_notes = "\n".join(
        f"- `{method_id}`: {method_data['description']}"
        for method_id, method_data in summary["methods"].items()
    )

    return f"""# Comparison Summary

This comparison evaluates the governance-aware reference method against three
deterministic baselines over the same 12 predefined cases.

## Methods

{method_notes}

## Aggregate Results

{table}

## Policy-Centric Results

{policy_table}

## Timing Results

{latency_table}

## Interpretation Notes

The reference method preserves governance interventions for approval-required,
blocked, and safe-abort cases. The baselines intentionally remove one or more
architectural protections, so higher execution coverage can correspond to
unsafe or policy-insensitive execution rather than better supervisory behavior.

The policy-centric metrics compare each run against explicit gold labels:
expected final status, expected governance decision, and whether automatic
execution is allowed.

All outputs are deterministic and derived from the local scenario cases in
`app/evaluation/scenario_cases.py`.
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

    rows, _ = run_comparison()
    print(f"Comparison CSV: {COMPARISON_CSV}")
    print(f"Baseline summary JSON: {BASELINE_SUMMARY_JSON}")
    print(f"Comparison summary Markdown: {COMPARISON_SUMMARY_MD}")
    print("Comparison results:")
    for row in rows:
        print(
            "  "
            f"{row['method_id']}: "
            f"success_rate={row['success_rate']}, "
            f"coverage={row['execution_coverage_ratio']}, "
            f"governance_intervention_rate={row['governance_intervention_rate']}, "
            f"policy_compliance_rate={row['policy_compliance_rate']}, "
            f"unsafe_execution_rate={row['unsafe_execution_rate']}"
        )


if __name__ == "__main__":
    main()
