"""Tests for the scaled deterministic empirical evaluation package."""

import json
import csv
from pathlib import Path

from app.evaluation.run_ablation_study import run_ablation_study
from app.evaluation.run_aligned_scaled_evaluation import run_aligned_scaled_evaluation
from app.evaluation.run_scaled_error_audit import run_scaled_error_audit
from app.evaluation.run_scaled_evaluation import run_scaled_evaluation
from app.evaluation.runtime_expectations import (
    RUNTIME_CAPABILITY_PROFILES,
    runtime_expected_outcome,
)
from app.evaluation.scenario_generator import generate_scenarios, write_scenarios
from app.evaluation.scope_classifier import classify_runtime_scope
from app.evaluation.statistical_analysis import wilson_interval


def test_scenario_generator_is_deterministic() -> None:
    assert generate_scenarios("default") == generate_scenarios("default")


def test_generated_scenario_counts_for_default_and_journal() -> None:
    assert len(generate_scenarios("default")) == 120
    assert len(generate_scenarios("journal")) == 240


def test_required_fields_exist_in_generated_scenarios() -> None:
    scenario = generate_scenarios("default")[0]
    required_fields = {
        "scenario_id",
        "scenario_family",
        "workflow_length",
        "governance_pattern",
        "adapter_mix",
        "approval_condition",
        "failure_condition",
        "runtime_applicability",
        "input_goal",
        "input_payload",
        "expected_governance_sequence",
        "expected_final_status",
        "expected_execution_allowed",
        "expected_policy_compliance",
        "expected_trace_markers",
        "industrial_context",
        "rami_alignment",
        "interoperability_role",
    }
    assert required_fields.issubset(scenario)


def test_write_scenarios_creates_default_and_journal_files() -> None:
    default_path = write_scenarios("default")
    journal_path = write_scenarios("journal")
    assert default_path.exists()
    assert journal_path.exists()
    assert len(json.loads(default_path.read_text(encoding="utf-8"))) == 120
    assert len(json.loads(journal_path.read_text(encoding="utf-8"))) == 240


def test_scaled_evaluation_produces_output_files() -> None:
    rows, summary = run_scaled_evaluation("default")
    assert summary["scenario_count"] == 120
    assert rows
    assert Path("data/results/scaled_evaluation_results_default.csv").exists()
    assert Path("data/results/scaled_evaluation_results_default.json").exists()
    assert Path("data/results/scaled_evaluation_summary_default.json").exists()


def test_statistical_analysis_handles_zero_unsafe_execution_safely() -> None:
    low, high = wilson_interval(0, 0)
    assert (low, high) == (0.0, 0.0)
    low, high = wilson_interval(0, 10)
    assert low == 0.0
    assert 0.0 < high < 1.0


def test_wilson_interval_calculation() -> None:
    low, high = wilson_interval(50, 100)
    assert 0.4 < low < 0.5
    assert 0.5 < high < 0.6


def test_ablation_runner_produces_expected_artifacts() -> None:
    rows, summary = run_ablation_study()
    assert len(rows) == 6
    assert "full_system" in summary["variants"]
    assert Path("data/results/ablation_results.csv").exists()
    assert Path("data/results/ablation_summary.json").exists()
    assert Path("docs/ablation_study_report.md").exists()


def test_scaled_error_audit_produces_diagnostic_artifacts() -> None:
    summary = run_scaled_error_audit("journal")
    assert summary["scenario_count"] == 240
    assert summary["error_case_count"] > 0
    assert Path("data/results/scaled_error_cases_journal.csv").exists()
    assert Path("data/results/confusion_matrix_final_status_journal.csv").exists()
    assert Path("data/results/confusion_matrix_governance_decision_journal.csv").exists()


def test_supported_stress_split_and_factor_balance_are_generated() -> None:
    run_scaled_error_audit("journal")
    assert Path("data/results/supported_scope_metrics_journal.csv").exists()
    assert Path("data/results/stress_scope_metrics_journal.csv").exists()
    assert Path("data/results/scenario_factor_balance_journal.csv").exists()
    assert Path("docs/supported_vs_stress_scope_report.md").exists()
    assert Path("docs/scenario_generator_quality_audit.md").exists()


def test_error_audit_does_not_modify_runtime_source_files() -> None:
    runtime_files = [
        *Path("app/adapters").rglob("*.py"),
        *Path("app/agents").rglob("*.py"),
        *Path("app/langgraph_runtime").rglob("*.py"),
        *Path("app/services").rglob("*.py"),
    ]
    before = {path: path.stat().st_mtime_ns for path in runtime_files}
    run_scaled_error_audit("journal")
    after = {path: path.stat().st_mtime_ns for path in runtime_files}
    assert after == before


def test_runtime_capability_profiles_load_correctly() -> None:
    assert "reference_v1" in RUNTIME_CAPABILITY_PROFILES
    assert "langgraph_runtime" in RUNTIME_CAPABILITY_PROFILES
    assert "controlled post-approval execution" in RUNTIME_CAPABILITY_PROFILES[
        "reference_v1"
    ]["does_not_support"]
    assert "controlled post-approval continuation" in RUNTIME_CAPABILITY_PROFILES[
        "langgraph_runtime"
    ]["supports"]


def test_runtime_specific_expected_outcomes_are_applied() -> None:
    scenario = next(
        scenario
        for scenario in generate_scenarios("journal")
        if scenario["governance_pattern"] == "post_approval_valid"
    )
    reference_expectation = runtime_expected_outcome(scenario, "reference_v1")
    langgraph_expectation = runtime_expected_outcome(scenario, "langgraph_runtime")
    assert reference_expectation["aligned_expected_final_status"] == "partial_success"
    assert langgraph_expectation["aligned_expected_final_status"] == "success"


def test_supported_stress_scope_classification_is_runtime_specific() -> None:
    scenario = next(
        scenario
        for scenario in generate_scenarios("journal")
        if scenario["governance_pattern"] == "post_approval_valid"
    )
    assert classify_runtime_scope(scenario, "reference_v1")["scope"] == "stress_scope"
    assert classify_runtime_scope(scenario, "langgraph_runtime")["scope"] == "supported_scope"


def test_aligned_evaluation_output_files_are_generated() -> None:
    summary = run_aligned_scaled_evaluation("journal")
    assert summary["scenario_count"] == 240
    assert Path("data/results/aligned_scaled_results_journal.csv").exists()
    assert Path("data/results/aligned_scaled_summary_journal.json").exists()
    assert Path("data/results/aligned_scaled_metrics_by_runtime.csv").exists()
    assert Path("data/results/aligned_scaled_metrics_by_scope.csv").exists()


def test_aligned_metrics_do_not_hide_unsafe_execution() -> None:
    run_aligned_scaled_evaluation("journal")
    with Path("data/results/aligned_scaled_metrics_by_runtime.csv").open(
        newline="",
        encoding="utf-8",
    ) as csv_file:
        rows = {row["runtime_id"]: row for row in csv.DictReader(csv_file)}
    assert float(rows["reference_v1"]["unsafe_execution_rate"]) == 0.0
    assert float(rows["langgraph_runtime"]["unsafe_execution_rate"]) == 0.0
    assert float(rows["baseline_a_direct_without_governance"]["unsafe_execution_rate"]) > 0
    assert (
        float(rows["baseline_a_direct_without_governance"]["aligned_policy_compliance_rate"])
        == 0.0
    )


def test_baselines_still_show_policy_violations_after_alignment() -> None:
    run_aligned_scaled_evaluation("journal")
    with Path("data/results/aligned_error_cases_journal.csv").open(
        newline="",
        encoding="utf-8",
    ) as csv_file:
        rows = list(csv.DictReader(csv_file))
    assert any(
        row["runtime_id"] == "baseline_a_direct_without_governance"
        and row["failure_category"] == "true_policy_violation"
        for row in rows
    )


def test_aligned_evaluation_does_not_modify_runtime_source_files() -> None:
    runtime_files = [
        *Path("app/adapters").rglob("*.py"),
        *Path("app/agents").rglob("*.py"),
        *Path("app/langgraph_runtime").rglob("*.py"),
        *Path("app/services").rglob("*.py"),
    ]
    before = {path: path.stat().st_mtime_ns for path in runtime_files}
    run_aligned_scaled_evaluation("journal")
    after = {path: path.stat().st_mtime_ns for path in runtime_files}
    assert after == before
