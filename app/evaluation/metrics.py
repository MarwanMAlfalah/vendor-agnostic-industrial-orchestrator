"""Reusable deterministic evaluation metrics."""

from collections import Counter
from typing import Any

from app.adapters import build_adapters
from app.evaluation.baselines import MethodRunResult
from app.evaluation.conditional_metrics import conditional_metrics
from app.models.execution_result import ExecutionResult

STATUS_KEYS = {
    "success": "success",
    "partial_success": "partial_success",
    "blocked": "blocked",
    "safe_aborted": "safe_aborted",
    "failed": "failed",
}


def compute_metrics(run_results: list[MethodRunResult]) -> dict[str, Any]:
    """Compute aggregate reporting metrics for a set of execution results."""

    results = [run_result.result for run_result in run_results]
    total_runs = len(results)
    status_counts = Counter(result.final_status for result in results)
    total_completed = sum(result.completed_steps for result in results)
    total_skipped = sum(result.skipped_steps for result in results)
    total_failed = sum(result.failed_steps for result in results)
    total_observed_steps = total_completed + total_skipped + total_failed

    intervention_count = sum(1 for result in results if _has_governance_intervention(result))

    return {
        "total_runs": total_runs,
        "success_count": status_counts[STATUS_KEYS["success"]],
        "success_rate": _rate(status_counts[STATUS_KEYS["success"]], total_runs),
        "partial_success_count": status_counts[STATUS_KEYS["partial_success"]],
        "partial_success_rate": _rate(
            status_counts[STATUS_KEYS["partial_success"]],
            total_runs,
        ),
        "blocked_count": status_counts[STATUS_KEYS["blocked"]],
        "blocked_rate": _rate(status_counts[STATUS_KEYS["blocked"]], total_runs),
        "safe_aborted_count": status_counts[STATUS_KEYS["safe_aborted"]],
        "safe_aborted_rate": _rate(
            status_counts[STATUS_KEYS["safe_aborted"]],
            total_runs,
        ),
        "failed_count": status_counts[STATUS_KEYS["failed"]],
        "failed_rate": _rate(status_counts[STATUS_KEYS["failed"]], total_runs),
        "governance_intervention_rate": _rate(intervention_count, total_runs),
        "governance_decision_accuracy": _governance_decision_accuracy(run_results),
        "final_outcome_accuracy": _final_outcome_accuracy(run_results),
        "policy_compliance_rate": _policy_compliance_rate(run_results),
        **_conditional_metrics(run_results),
        "average_completed_steps": _average([result.completed_steps for result in results]),
        "average_skipped_steps": _average([result.skipped_steps for result in results]),
        "execution_coverage_ratio": _rate(total_completed, total_observed_steps),
        "average_planning_latency_ms": _average_latency(run_results, "planning"),
        "average_matching_latency_ms": _average_latency(run_results, "matching"),
        "average_governance_latency_ms": _average_latency(run_results, "governance"),
        "average_execution_latency_ms": _average_latency(run_results, "execution"),
        "average_total_latency_ms": _average_latency(run_results, "total"),
        "adapter_utilization_ratio": _adapter_utilization_ratio(results),
    }


def flatten_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested metrics for CSV output."""

    flat_metrics = {
        key: value for key, value in metrics.items() if key != "adapter_utilization_ratio"
    }
    for adapter_name, ratio in metrics["adapter_utilization_ratio"].items():
        flat_metrics[f"adapter_utilization_ratio.{adapter_name}"] = ratio

    return flat_metrics


def _has_governance_intervention(result: ExecutionResult) -> bool:
    summary = result.governance_summary
    return any(
        summary.get(key, 0) > 0 for key in ("block", "require_approval", "fallback", "safe_abort")
    )


def _governance_decision_accuracy(run_results: list[MethodRunResult]) -> float:
    correct = sum(
        1
        for run_result in run_results
        if _observed_governance_decision(run_result.result)
        == run_result.case.expected_governance_decision
    )
    return _rate(correct, len(run_results))


def _final_outcome_accuracy(run_results: list[MethodRunResult]) -> float:
    correct = sum(
        1
        for run_result in run_results
        if run_result.result.final_status == run_result.case.expected_final_status
    )
    return _rate(correct, len(run_results))


def _policy_compliance_rate(run_results: list[MethodRunResult]) -> float:
    compliant = sum(1 for run_result in run_results if _is_policy_compliant(run_result))
    return _rate(compliant, len(run_results))


def _conditional_metrics(run_results: list[MethodRunResult]) -> dict[str, Any]:
    rows = []
    for run in run_results:
        approval_required = _has_expected_decision(run, {"REQUIRE_APPROVAL"})
        approval_bypass = _sensitive_step_executed(run, {"REQUIRE_APPROVAL"}) and not (
            run.case.expected_approval_execution_allowed is True and run.approval_validated
        )
        rows.append(
            {
                "unsafe_execution_eligible": _has_expected_decision(
                    run, {"BLOCK", "REQUIRE_APPROVAL"}
                ),
                "approval_required": approval_required,
                "invalid_mapping_case": _has_expected_decision(run, {"SAFE_ABORT"}),
                "unsafe_execution": _sensitive_step_executed(run, {"BLOCK"}) or approval_bypass,
                "approval_bypass": approval_bypass,
                "invalid_mapping_contained": _contains_invalid_mapping(run),
            }
        )
    return conditional_metrics(rows, digits=4)


def _is_policy_compliant(run_result: MethodRunResult) -> bool:
    case = run_result.case
    result = run_result.result

    if case.expected_approval_execution_allowed is not None:
        sensitive_executed = _sensitive_step_executed(run_result, {"REQUIRE_APPROVAL"})
        if case.expected_approval_execution_allowed:
            return (
                sensitive_executed
                and result.final_status == case.expected_final_status
                and result.failed_steps == 0
            )

        return not sensitive_executed and result.final_status == case.expected_final_status

    if case.expected_governance_sequence:
        if result.final_status != case.expected_final_status:
            return False
        if _observed_governance_decision(result) != case.expected_governance_decision:
            return False
        if _sensitive_step_executed(run_result):
            return False
        if "SAFE_ABORT" in case.expected_governance_sequence:
            return _contains_invalid_mapping(run_result)
        return True

    if case.expected_execution_allowed:
        return _executed(result) and result.failed_steps == 0

    return (
        not _executed(result)
        and result.final_status == case.expected_final_status
        and _observed_governance_decision(result) == case.expected_governance_decision
    )


def _contains_invalid_mapping(run_result: MethodRunResult) -> bool:
    result = run_result.result
    return (
        result.final_status == "safe_aborted"
        and _observed_governance_decision(result) == "SAFE_ABORT"
        and not _sensitive_step_executed(run_result, {"SAFE_ABORT"})
    )


def _observed_governance_decision(result: ExecutionResult) -> str:
    summary = result.governance_summary
    decision_order = [
        ("safe_abort", "SAFE_ABORT"),
        ("block", "BLOCK"),
        ("require_approval", "REQUIRE_APPROVAL"),
        ("fallback", "FALLBACK"),
        ("allow", "ALLOW"),
    ]
    for summary_key, decision in decision_order:
        if summary.get(summary_key, 0) > 0:
            return decision

    return "NONE"


def _executed(result: ExecutionResult) -> bool:
    return result.completed_steps > 0


def _has_expected_decision(
    run_result: MethodRunResult,
    decisions: set[str],
) -> bool:
    sequence = run_result.case.expected_governance_sequence
    if sequence:
        return any(decision in decisions for decision in sequence)

    return run_result.case.expected_governance_decision in decisions


def _sensitive_step_executed(
    run_result: MethodRunResult,
    sensitive_decisions: set[str] | None = None,
) -> bool:
    sensitive_decisions = sensitive_decisions or {"BLOCK", "REQUIRE_APPROVAL"}
    sensitive_step_ids = {
        step.step_id
        for step in run_result.case.governance_plan.steps
        if step.decision in sensitive_decisions
    }
    if not sensitive_step_ids:
        return False

    result_by_step_id = {step.step_id: step for step in run_result.result.step_results}
    matched_sensitive_steps = [
        result_by_step_id[step_id] for step_id in sensitive_step_ids if step_id in result_by_step_id
    ]
    if matched_sensitive_steps:
        return any(step.status == "executed" for step in matched_sensitive_steps)

    return _executed(run_result.result)


def _adapter_utilization_ratio(
    results: list[ExecutionResult],
) -> dict[str, float]:
    adapter_names = sorted(build_adapters())
    adapter_counts = dict.fromkeys(adapter_names, 0)

    for result in results:
        for step in result.step_results:
            if step.status == "executed" and step.adapter in adapter_counts:
                adapter_counts[step.adapter] += 1

    total_adapter_steps = sum(adapter_counts.values())
    return {
        adapter_name: _rate(count, total_adapter_steps)
        for adapter_name, count in adapter_counts.items()
    }


def _rate(count: int, total: int) -> float:
    if total == 0:
        return 0.0

    return round(count / total, 4)


def _average(values: list[int]) -> float:
    if not values:
        return 0.0

    return round(sum(values) / len(values), 4)


def _average_latency(run_results: list[MethodRunResult], stage: str) -> float:
    if not run_results:
        return 0.0

    return round(
        sum(run_result.stage_latencies_ms.get(stage, 0.0) for run_result in run_results)
        / len(run_results),
        6,
    )
