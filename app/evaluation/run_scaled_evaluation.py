"""Run deterministic scaled empirical evaluations across runtime paths."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any

from app.evaluation.baselines import (
    DirectExecutionWithoutGovernanceBaseline,
    GovernanceAwareReference,
    MethodRunResult,
    NoGovernancePolicyFilteringBaseline,
    SingleStageExecutionBaseline,
)
from app.evaluation.scenario_cases import EvaluationCase
from app.evaluation.scenario_generator import PROFILE_COUNTS, load_or_generate_scenarios
from app.langgraph_runtime import LangGraphRuntime
from app.models.execution_result import ExecutionResult
from app.models.governance import GovernanceEvaluation

RESULTS_DIR = Path("data/results")

RUNTIME_LABELS = {
    "reference_v1": "Reference v1 deterministic governance-aware runtime",
    "langgraph_runtime": "LangGraph deterministic approval/persistence runtime",
    "baseline_a_direct_without_governance": "Baseline A: direct execution without governance",
    "baseline_b_single_stage_execution": "Baseline B: single-stage execution",
    "baseline_c_without_policy_filtering": "Baseline C: without policy filtering",
}

ROW_FIELDS = [
    "scenario_id",
    "runtime_id",
    "scenario_family",
    "workflow_length",
    "workflow_step_count",
    "governance_pattern",
    "adapter_mix",
    "approval_condition",
    "failure_condition",
    "expected_governance_decision",
    "observed_governance_decision",
    "governance_decision_correct",
    "expected_final_status",
    "observed_final_status",
    "policy_compliant",
    "unsafe_execution",
    "approval_bypass",
    "approval_validation_correct",
    "invalid_mapping_contained",
    "trace_complete",
    "restart_recovered",
    "final_outcome_correct",
    "completed_steps",
    "skipped_steps",
    "failed_steps",
    "latency_ms",
    "latency_group_runtime_id",
    "latency_group_scenario_family",
]


def run_scaled_evaluation(profile: str = "default") -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run all applicable runtimes for a generated scenario profile."""

    if profile not in PROFILE_COUNTS:
        raise ValueError(f"Unknown profile '{profile}'. Expected one of {sorted(PROFILE_COUNTS)}.")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    scenarios = load_or_generate_scenarios(profile)
    rows: list[dict[str, Any]] = []
    runtime_cache = _runtime_cache()

    for scenario in scenarios:
        case = scenario_to_case(scenario)
        for runtime_id in scenario["runtime_applicability"]:
            raw_run = _run_runtime(runtime_id, case, scenario, runtime_cache)
            rows.append(_result_row(scenario, runtime_id, raw_run))

    summary = _summary(profile, scenarios, rows)
    _write_outputs(profile, rows, summary)
    return rows, summary


def scenario_to_case(scenario: dict[str, Any]) -> EvaluationCase:
    """Convert a generated scenario record into the existing evaluation contract."""

    return EvaluationCase(
        case_id=scenario["scenario_id"],
        scenario_category=scenario["scenario_family"],
        governance_plan=GovernanceEvaluation.model_validate(scenario["governance_plan"]),
        expected_final_status=scenario["expected_final_status"],
        expected_governance_decision=scenario["expected_governance_decision"],
        expected_execution_allowed=bool(scenario["expected_execution_allowed"]),
        expected_governance_sequence=list(scenario["expected_governance_sequence"]),
        expected_post_resume_final_status=scenario["expected_final_status"],
        expected_approval_execution_allowed=scenario.get("expected_approval_execution_allowed"),
        approval_payload=scenario.get("approval_payload"),
        approval_resume_mutation=scenario.get("approval_resume_mutation"),
        industrial_context=scenario.get("industrial_context", {}),
        source_goal=None,
    )


def _runtime_cache() -> dict[str, Any]:
    return {
        "reference_v1": GovernanceAwareReference(),
        "langgraph_runtime": LangGraphRuntime(),
        "baseline_a_direct_without_governance": DirectExecutionWithoutGovernanceBaseline(),
        "baseline_b_single_stage_execution": SingleStageExecutionBaseline(),
        "baseline_c_without_policy_filtering": NoGovernancePolicyFilteringBaseline(),
    }


def _run_runtime(
    runtime_id: str,
    case: EvaluationCase,
    scenario: dict[str, Any],
    runtime_cache: dict[str, Any],
) -> dict[str, Any]:
    if runtime_id == "langgraph_runtime":
        run = runtime_cache[runtime_id].run_case(
            case,
            approval_payload=case.approval_payload,
            controlled_approval_execution=_requires_controlled_approval(scenario),
        )
        return {
            "result": run["result"],
            "stage_latencies_ms": run["stage_latencies_ms"],
            "trace": run["trace"],
            "approval_state": run.get("approval_state"),
            "approval_validation_error": run.get("approval_validation_error"),
            "approval_execution_performed": run.get("approval_execution_performed", False),
            "interrupted": run.get("interrupted", False),
            "resumed": run.get("resumed", False),
            "restart_recovered": False,
        }

    method_run: MethodRunResult = runtime_cache[runtime_id].run_with_timing(case)
    trace = ["reference_v1.execution_result"] if runtime_id == "reference_v1" else []
    return {
        "result": method_run.result,
        "stage_latencies_ms": method_run.stage_latencies_ms,
        "trace": trace,
        "approval_state": "not_supported" if _requires_controlled_approval(scenario) else "not_required",
        "approval_validation_error": None,
        "approval_execution_performed": False,
        "interrupted": False,
        "resumed": False,
        "restart_recovered": False,
    }


def _result_row(
    scenario: dict[str, Any],
    runtime_id: str,
    raw_run: dict[str, Any],
) -> dict[str, Any]:
    result: ExecutionResult = raw_run["result"]
    observed_decision = _observed_governance_decision(result)
    trace = raw_run.get("trace", [])
    final_outcome_correct = result.final_status == scenario["expected_final_status"]
    governance_decision_correct = observed_decision == scenario["expected_governance_decision"]
    policy_compliant = _policy_compliant(
        scenario=scenario,
        runtime_id=runtime_id,
        result=result,
        observed_decision=observed_decision,
        trace=trace,
        approval_execution_performed=bool(raw_run.get("approval_execution_performed")),
    )
    unsafe_execution = _unsafe_execution(
        scenario=scenario,
        runtime_id=runtime_id,
        result=result,
        trace=trace,
    )
    approval_bypass = _approval_bypass(
        scenario=scenario,
        runtime_id=runtime_id,
        result=result,
        trace=trace,
    )

    return {
        "scenario_id": scenario["scenario_id"],
        "runtime_id": runtime_id,
        "scenario_family": scenario["scenario_family"],
        "workflow_length": scenario["workflow_length"],
        "workflow_step_count": scenario["workflow_step_count"],
        "governance_pattern": scenario["governance_pattern"],
        "adapter_mix": scenario["adapter_mix"],
        "approval_condition": scenario["approval_condition"],
        "failure_condition": scenario["failure_condition"],
        "expected_governance_decision": scenario["expected_governance_decision"],
        "observed_governance_decision": observed_decision,
        "governance_decision_correct": governance_decision_correct,
        "expected_final_status": scenario["expected_final_status"],
        "observed_final_status": result.final_status,
        "policy_compliant": policy_compliant,
        "unsafe_execution": unsafe_execution,
        "approval_bypass": approval_bypass,
        "approval_validation_correct": _approval_validation_correct(
            scenario,
            runtime_id,
            trace,
            raw_run.get("approval_state"),
        ),
        "invalid_mapping_contained": _invalid_mapping_contained(scenario, result),
        "trace_complete": _trace_complete(scenario, runtime_id, trace),
        "restart_recovered": bool(raw_run.get("restart_recovered", False)),
        "final_outcome_correct": final_outcome_correct,
        "completed_steps": result.completed_steps,
        "skipped_steps": result.skipped_steps,
        "failed_steps": result.failed_steps,
        "latency_ms": round(raw_run["stage_latencies_ms"].get("total", result.total_latency_ms or 0.0), 6),
        "latency_group_runtime_id": runtime_id,
        "latency_group_scenario_family": scenario["scenario_family"],
    }


def _requires_controlled_approval(scenario: dict[str, Any]) -> bool:
    return (
        "REQUIRE_APPROVAL" in scenario["expected_governance_sequence"]
        or scenario["approval_condition"] != "no approval required"
    )


def _observed_governance_decision(result: ExecutionResult) -> str:
    for summary_key, decision in [
        ("safe_abort", "SAFE_ABORT"),
        ("block", "BLOCK"),
        ("require_approval", "REQUIRE_APPROVAL"),
        ("fallback", "FALLBACK"),
        ("allow", "ALLOW"),
    ]:
        if result.governance_summary.get(summary_key, 0) > 0:
            return decision
    return "NONE"


def _policy_compliant(
    *,
    scenario: dict[str, Any],
    runtime_id: str,
    result: ExecutionResult,
    observed_decision: str,
    trace: list[str],
    approval_execution_performed: bool,
) -> bool:
    expected_sequence = scenario["expected_governance_sequence"]
    approval_condition = scenario["approval_condition"]

    if scenario["expected_final_status"] != result.final_status:
        return False
    if observed_decision != scenario["expected_governance_decision"]:
        return False
    if "SAFE_ABORT" in expected_sequence:
        return _invalid_mapping_contained(scenario, result)
    if "BLOCK" in expected_sequence:
        return not _sensitive_step_executed(scenario, result, {"BLOCK"})
    if "REQUIRE_APPROVAL" in expected_sequence:
        if approval_condition == "valid approval":
            if runtime_id != "langgraph_runtime":
                return False
            return approval_execution_performed and "approval_validated" in trace
        return not _sensitive_step_executed(scenario, result, {"REQUIRE_APPROVAL"})
    return result.failed_steps == 0 and result.completed_steps > 0


def _unsafe_execution(
    *,
    scenario: dict[str, Any],
    runtime_id: str,
    result: ExecutionResult,
    trace: list[str],
) -> bool:
    expected_sequence = scenario["expected_governance_sequence"]
    if "BLOCK" in expected_sequence and _sensitive_step_executed(scenario, result, {"BLOCK"}):
        return True
    if "REQUIRE_APPROVAL" in expected_sequence and _sensitive_step_executed(
        scenario,
        result,
        {"REQUIRE_APPROVAL"},
    ):
        return not (
            runtime_id == "langgraph_runtime"
            and scenario["approval_condition"] == "valid approval"
            and "approval_validated" in trace
        )
    if "SAFE_ABORT" in expected_sequence:
        return _sensitive_step_executed(scenario, result, {"SAFE_ABORT"})
    return False


def _approval_bypass(
    *,
    scenario: dict[str, Any],
    runtime_id: str,
    result: ExecutionResult,
    trace: list[str],
) -> bool:
    if "REQUIRE_APPROVAL" not in scenario["expected_governance_sequence"]:
        return False
    if not _sensitive_step_executed(scenario, result, {"REQUIRE_APPROVAL"}):
        return False
    return not (runtime_id == "langgraph_runtime" and "approval_validated" in trace)


def _approval_validation_correct(
    scenario: dict[str, Any],
    runtime_id: str,
    trace: list[str],
    approval_state: Any,
) -> bool:
    if "REQUIRE_APPROVAL" not in scenario["expected_governance_sequence"]:
        return True
    if runtime_id != "langgraph_runtime":
        return False
    expected_valid = scenario["approval_condition"] in {
        "valid approval",
        "approval with invalidated mapping",
    }
    observed_valid = "approval_validated" in trace or approval_state == "approved"
    return expected_valid == observed_valid


def _invalid_mapping_contained(scenario: dict[str, Any], result: ExecutionResult) -> bool:
    containment_conditions = {
        "unsupported capability",
        "invalid adapter mapping",
        "unavailable capability",
        "malformed payload",
        "safe abort condition",
    }
    if scenario["failure_condition"] not in containment_conditions:
        return True
    return result.final_status == "safe_aborted" and not _sensitive_step_executed(
        scenario,
        result,
        {"SAFE_ABORT"},
    )


def _trace_complete(scenario: dict[str, Any], runtime_id: str, trace: list[str]) -> bool:
    if runtime_id == "reference_v1":
        return "reference_v1.execution_result" in trace
    if runtime_id != "langgraph_runtime":
        return False
    return set(scenario["expected_trace_markers"]).issubset(set(trace))


def _sensitive_step_executed(
    scenario: dict[str, Any],
    result: ExecutionResult,
    sensitive_decisions: set[str],
) -> bool:
    sensitive_step_ids = {
        step["step_id"]
        for step in scenario["governance_plan"]["steps"]
        if step["decision"] in sensitive_decisions
    }
    if not sensitive_step_ids:
        return False
    result_by_step_id = {step.step_id: step for step in result.step_results}
    return any(
        result_by_step_id[step_id].status == "executed"
        for step_id in sensitive_step_ids
        if step_id in result_by_step_id
    )


def _summary(
    profile: str,
    scenarios: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    runtime_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    family_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        runtime_groups[row["runtime_id"]].append(row)
        family_groups[row["scenario_family"]].append(row)

    return {
        "profile": profile,
        "scenario_count": len(scenarios),
        "result_row_count": len(rows),
        "deterministic": True,
        "stochastic_llm_logic": False,
        "scenario_design": {
            "workflow_length_counts": dict(Counter(s["workflow_length"] for s in scenarios)),
            "governance_pattern_counts": dict(Counter(s["governance_pattern"] for s in scenarios)),
            "adapter_mix_counts": dict(Counter(s["adapter_mix"] for s in scenarios)),
            "approval_condition_counts": dict(Counter(s["approval_condition"] for s in scenarios)),
            "failure_condition_counts": dict(Counter(s["failure_condition"] for s in scenarios)),
        },
        "runtime_summary": {
            runtime_id: _aggregate_rows(group_rows)
            for runtime_id, group_rows in sorted(runtime_groups.items())
        },
        "scenario_family_summary": {
            family: _aggregate_rows(group_rows)
            for family, group_rows in sorted(family_groups.items())
        },
    }


def _aggregate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [float(row["latency_ms"]) for row in rows]
    return {
        "runs": len(rows),
        "policy_compliance_rate": _rate(sum(row["policy_compliant"] for row in rows), len(rows)),
        "unsafe_execution_rate": _rate(sum(row["unsafe_execution"] for row in rows), len(rows)),
        "approval_bypass_rate": _rate(sum(row["approval_bypass"] for row in rows), len(rows)),
        "final_outcome_accuracy": _rate(sum(row["final_outcome_correct"] for row in rows), len(rows)),
        "governance_decision_accuracy": _rate(
            sum(row["governance_decision_correct"] for row in rows),
            len(rows),
        ),
        "trace_completeness": _rate(sum(row["trace_complete"] for row in rows), len(rows)),
        "mean_latency_ms": round(sum(latencies) / len(latencies), 6) if latencies else 0.0,
        "median_latency_ms": round(median(latencies), 6) if latencies else 0.0,
        "p50_latency_ms": _percentile(latencies, 50),
        "p95_latency_ms": _percentile(latencies, 95),
    }


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = (len(ordered) - 1) * percentile / 100
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return round(ordered[lower] * (1 - weight) + ordered[upper] * weight, 6)


def _write_outputs(profile: str, rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    csv_path = RESULTS_DIR / f"scaled_evaluation_results_{profile}.csv"
    json_path = RESULTS_DIR / f"scaled_evaluation_results_{profile}.json"
    summary_path = RESULTS_DIR / f"scaled_evaluation_summary_{profile}.json"

    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=ROW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, indent=2, sort_keys=True), encoding="utf-8")
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run deterministic scaled evaluation.")
    parser.add_argument("--profile", choices=sorted(PROFILE_COUNTS), default="default")
    args = parser.parse_args()

    rows, summary = run_scaled_evaluation(args.profile)
    print(
        json.dumps(
            {
                "profile": args.profile,
                "scenario_count": summary["scenario_count"],
                "result_row_count": len(rows),
                "summary_path": str(RESULTS_DIR / f"scaled_evaluation_summary_{args.profile}.json"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
