"""Tests for the scaled deterministic empirical evaluation package."""

import csv
import hashlib
import json
from pathlib import Path

import pytest

from app.evaluation import run_ablation_study as ablation_module
from app.evaluation import run_aligned_scaled_evaluation as aligned_module
from app.evaluation import run_scaled_error_audit as error_audit_module
from app.evaluation import run_scaled_evaluation as scaled_module
from app.evaluation import runtime_expectations as runtime_expectations_module
from app.evaluation import scenario_generator as scenario_generator_module
from app.evaluation.runtime_expectations import (
    RUNTIME_CAPABILITY_PROFILES,
    runtime_expected_outcome,
)
from app.evaluation.scenario_generator import generate_scenarios, write_scenarios
from app.evaluation.scope_classifier import classify_runtime_scope
from app.evaluation.statistical_analysis import wilson_interval


@pytest.fixture(autouse=True)
def isolated_evaluation_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """Route evaluation test artifacts away from committed evidence files."""

    results_dir = tmp_path / "data" / "results"
    docs_dir = tmp_path / "docs"
    scenarios_dir = tmp_path / "data" / "scenarios"
    profile_files = {
        profile: scenarios_dir / path.name
        for profile, path in scenario_generator_module.PROFILE_FILES.items()
    }

    monkeypatch.setattr(scenario_generator_module, "SCENARIOS_DIR", scenarios_dir)
    monkeypatch.setattr(scenario_generator_module, "PROFILE_FILES", profile_files)

    monkeypatch.setattr(scaled_module, "RESULTS_DIR", results_dir)
    monkeypatch.setattr(ablation_module, "RESULTS_DIR", results_dir)
    monkeypatch.setattr(ablation_module, "DOCS_DIR", docs_dir)
    monkeypatch.setattr(error_audit_module, "RESULTS_DIR", results_dir)
    monkeypatch.setattr(error_audit_module, "DOCS_DIR", docs_dir)
    monkeypatch.setattr(aligned_module, "RESULTS_DIR", results_dir)
    monkeypatch.setattr(aligned_module, "DOCS_DIR", docs_dir)
    monkeypatch.setattr(runtime_expectations_module, "RESULTS_DIR", results_dir)

    return {"results": results_dir, "docs": docs_dir, "scenarios": scenarios_dir}


@pytest.fixture
def committed_result_hashes() -> dict[Path, str]:
    """Snapshot committed result CSV/JSON files to detect accidental test writes."""

    paths = sorted(Path("data/results").glob("*.csv")) + sorted(Path("data/results").glob("*.json"))
    return {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def assert_committed_result_hashes_unchanged(before: dict[Path, str]) -> None:
    after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in before}
    assert after == before


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


def test_write_scenarios_creates_default_and_journal_files(
    isolated_evaluation_outputs: dict[str, Path],
) -> None:
    default_path = write_scenarios("default")
    journal_path = write_scenarios("journal")
    assert default_path.exists()
    assert journal_path.exists()
    assert default_path.is_relative_to(isolated_evaluation_outputs["scenarios"])
    assert journal_path.is_relative_to(isolated_evaluation_outputs["scenarios"])
    assert len(json.loads(default_path.read_text(encoding="utf-8"))) == 120
    assert len(json.loads(journal_path.read_text(encoding="utf-8"))) == 240


def test_scaled_evaluation_produces_output_files(
    isolated_evaluation_outputs: dict[str, Path],
    committed_result_hashes: dict[Path, str],
) -> None:
    rows, summary = scaled_module.run_scaled_evaluation("default")
    assert summary["scenario_count"] == 120
    assert rows
    results_dir = isolated_evaluation_outputs["results"]
    assert (results_dir / "scaled_evaluation_results_default.csv").exists()
    assert (results_dir / "scaled_evaluation_results_default.json").exists()
    assert (results_dir / "scaled_evaluation_summary_default.json").exists()
    assert_committed_result_hashes_unchanged(committed_result_hashes)


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


def test_ablation_runner_produces_expected_artifacts(
    isolated_evaluation_outputs: dict[str, Path],
    committed_result_hashes: dict[Path, str],
) -> None:
    rows, summary = ablation_module.run_ablation_study()
    assert len(rows) == 6
    assert "full_system" in summary["variants"]
    results_dir = isolated_evaluation_outputs["results"]
    docs_dir = isolated_evaluation_outputs["docs"]
    assert (results_dir / "ablation_results.csv").exists()
    assert (results_dir / "ablation_summary.json").exists()
    assert (docs_dir / "ablation_study_report.md").exists()
    assert_committed_result_hashes_unchanged(committed_result_hashes)


def test_scaled_error_audit_produces_diagnostic_artifacts(
    isolated_evaluation_outputs: dict[str, Path],
    committed_result_hashes: dict[Path, str],
) -> None:
    summary = error_audit_module.run_scaled_error_audit("journal")
    assert summary["scenario_count"] == 240
    assert summary["error_case_count"] > 0
    results_dir = isolated_evaluation_outputs["results"]
    assert (results_dir / "scaled_error_cases_journal.csv").exists()
    assert (results_dir / "confusion_matrix_final_status_journal.csv").exists()
    assert (results_dir / "confusion_matrix_governance_decision_journal.csv").exists()
    assert_committed_result_hashes_unchanged(committed_result_hashes)


def test_supported_stress_split_and_factor_balance_are_generated(
    isolated_evaluation_outputs: dict[str, Path],
) -> None:
    error_audit_module.run_scaled_error_audit("journal")
    results_dir = isolated_evaluation_outputs["results"]
    docs_dir = isolated_evaluation_outputs["docs"]
    assert (results_dir / "supported_scope_metrics_journal.csv").exists()
    assert (results_dir / "stress_scope_metrics_journal.csv").exists()
    assert (results_dir / "scenario_factor_balance_journal.csv").exists()
    assert (docs_dir / "supported_vs_stress_scope_report.md").exists()
    assert (docs_dir / "scenario_generator_quality_audit.md").exists()


def test_error_audit_does_not_modify_runtime_source_files() -> None:
    runtime_files = [
        *Path("app/adapters").rglob("*.py"),
        *Path("app/agents").rglob("*.py"),
        *Path("app/langgraph_runtime").rglob("*.py"),
        *Path("app/services").rglob("*.py"),
    ]
    before = {path: path.stat().st_mtime_ns for path in runtime_files}
    error_audit_module.run_scaled_error_audit("journal")
    after = {path: path.stat().st_mtime_ns for path in runtime_files}
    assert after == before


def test_runtime_capability_profiles_load_correctly() -> None:
    assert "reference_v1" in RUNTIME_CAPABILITY_PROFILES
    assert "langgraph_runtime" in RUNTIME_CAPABILITY_PROFILES
    assert (
        "controlled post-approval execution"
        in RUNTIME_CAPABILITY_PROFILES["reference_v1"]["does_not_support"]
    )
    assert (
        "controlled post-approval continuation"
        in RUNTIME_CAPABILITY_PROFILES["langgraph_runtime"]["supports"]
    )


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


def test_aligned_evaluation_output_files_are_generated(
    isolated_evaluation_outputs: dict[str, Path],
    committed_result_hashes: dict[Path, str],
) -> None:
    summary = aligned_module.run_aligned_scaled_evaluation("journal")
    assert summary["scenario_count"] == 240
    results_dir = isolated_evaluation_outputs["results"]
    assert (results_dir / "aligned_scaled_results_journal.csv").exists()
    assert (results_dir / "aligned_scaled_summary_journal.json").exists()
    assert (results_dir / "aligned_scaled_metrics_by_runtime.csv").exists()
    assert (results_dir / "aligned_scaled_metrics_by_scope.csv").exists()
    assert_committed_result_hashes_unchanged(committed_result_hashes)


def test_aligned_metrics_do_not_hide_unsafe_execution(
    isolated_evaluation_outputs: dict[str, Path],
) -> None:
    aligned_module.run_aligned_scaled_evaluation("journal")
    with (isolated_evaluation_outputs["results"] / "aligned_scaled_metrics_by_runtime.csv").open(
        newline="",
        encoding="utf-8",
    ) as csv_file:
        rows = {row["runtime_id"]: row for row in csv.DictReader(csv_file)}
    assert float(rows["reference_v1"]["unsafe_execution_rate"]) == 0.0
    assert float(rows["langgraph_runtime"]["unsafe_execution_rate"]) == 0.0
    assert float(rows["baseline_a_direct_without_governance"]["unsafe_execution_rate"]) > 0
    assert (
        float(rows["baseline_a_direct_without_governance"]["aligned_policy_compliance_rate"]) == 0.0
    )


def test_baselines_still_show_policy_violations_after_alignment(
    isolated_evaluation_outputs: dict[str, Path],
) -> None:
    aligned_module.run_aligned_scaled_evaluation("journal")
    with (isolated_evaluation_outputs["results"] / "aligned_error_cases_journal.csv").open(
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
    aligned_module.run_aligned_scaled_evaluation("journal")
    after = {path: path.stat().st_mtime_ns for path in runtime_files}
    assert after == before
