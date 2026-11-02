"""Behavioral checks for conditional rates across the actual reporting pipelines."""

from dataclasses import replace

import pytest

from app.agents.execution_agent import ExecutionAgent
from app.evaluation import run_ablation_study as ablation
from app.evaluation import run_aligned_scaled_evaluation as aligned
from app.evaluation import run_scaled_error_audit as audit
from app.evaluation import run_scaled_evaluation as scaled
from app.evaluation import statistical_analysis as statistics
from app.evaluation.baselines import DirectExecutionWithoutGovernanceBaseline
from app.evaluation.conditional_metrics import scenario_eligibility
from app.evaluation.metrics import compute_metrics
from app.evaluation.scenario_generator import generate_scenarios


def _row(**overrides):
    return {
        "runtime_id": "reference_v1",
        "scenario_family": "test",
        "latency_ms": 0.0,
        "policy_compliant": True,
        "final_outcome_correct": True,
        "governance_decision_correct": True,
        "trace_complete": True,
        "restart_recovered": False,
        "approval_validation_correct": True,
        "approval_condition": "no approval required",
        "original_policy_compliant": True,
        "aligned_policy_compliant": True,
        "original_final_outcome_correct": True,
        "aligned_final_outcome_correct": True,
        "unsafe_execution_eligible": False,
        "unsafe_execution": False,
        "approval_required": False,
        "approval_bypass": False,
        "invalid_mapping_case": False,
        "invalid_mapping_contained": True,
        **overrides,
    }


AGGREGATORS = [
    scaled._aggregate_rows,
    lambda rows: aligned._aggregate_rows("reference_v1", rows),
    lambda rows: audit._metric_row("reference_v1", "test", "test", rows),
    ablation._variant_metrics,
]


@pytest.mark.parametrize("aggregate", AGGREGATORS)
def test_aggregates_use_eligible_subsets_and_expose_counts(aggregate):
    # Ten runs: two approval bypasses, one blocked-action violation, two invalid mappings.
    rows = [_row() for _ in range(5)] + [
        _row(
            approval_required=True,
            unsafe_execution_eligible=True,
            unsafe_execution=True,
            approval_bypass=True,
        ),
        _row(
            approval_required=True,
            unsafe_execution_eligible=True,
            unsafe_execution=True,
            approval_bypass=True,
        ),
        _row(unsafe_execution_eligible=True, unsafe_execution=True),
        _row(invalid_mapping_case=True),
        _row(invalid_mapping_case=True, invalid_mapping_contained=False),
    ]
    metrics = aggregate(rows)
    assert metrics["approval_bypass_rate"] == 1.0  # 2 / 2, not 2 / 10
    assert metrics["unsafe_execution_rate"] == 1.0  # 3 / 3, not 3 / 10
    assert metrics["invalid_mapping_containment_rate"] == 0.5  # 1 / 2, not 9 / 10
    assert metrics["approval_required_count"] == metrics["approval_bypass_count"] == 2
    assert metrics["unsafe_execution_eligible_count"] == metrics["unsafe_execution_count"] == 3
    assert metrics["invalid_mapping_case_count"] == 2
    assert metrics["invalid_mapping_contained_count"] == 1
    summary = statistics._proportion_summary(rows)
    for metric, numerator, denominator in [
        ("approval_bypass_rate", 2, 2),
        ("unsafe_execution_rate", 3, 3),
        ("invalid_mapping_containment_rate", 1, 2),
    ]:
        result = next(r for r in summary if r["group_type"] == "runtime" and r["metric"] == metric)
        assert (result["numerator"], result["denominator"]) == (numerator, denominator)
        assert result["rate"] == metrics[metric]


@pytest.mark.parametrize("aggregate", AGGREGATORS)
@pytest.mark.parametrize("rows", [[], [_row()]])
def test_zero_eligibility_is_not_applicable(aggregate, rows):
    metrics = aggregate(rows)
    for metric in [
        "unsafe_execution_rate",
        "approval_bypass_rate",
        "invalid_mapping_containment_rate",
    ]:
        assert metrics[metric] is None
    assert metrics["unsafe_execution_eligible_count"] == 0
    if rows:
        for result in statistics._proportion_summary(rows):
            if result["metric"] in {
                "unsafe_execution_rate",
                "approval_bypass_rate",
                "invalid_mapping_containment_rate",
            }:
                assert result["rate"] is None
                assert result["wilson_95_low"] is result["wilson_95_high"] is None


def test_gold_sequence_controls_eligibility_even_when_dominant_label_is_safe_abort():
    scenario = next(
        s
        for s in generate_scenarios()
        if s["governance_pattern"] == "mixed_allow_approval_safe_abort"
    )
    assert scenario["expected_governance_decision"] == "SAFE_ABORT"
    assert scenario_eligibility(scenario) == {
        "unsafe_execution_eligible": True,
        "approval_required": True,
        "invalid_mapping_case": True,
    }


def test_authorized_approval_is_eligible_without_being_unsafe():
    scenario = next(
        s for s in generate_scenarios() if s["governance_pattern"] == "post_approval_valid"
    )
    case = scaled.scenario_to_case(scenario)
    run = DirectExecutionWithoutGovernanceBaseline().run_with_timing(case)
    # Gold permission alone cannot excuse the baseline bypassing actual validation.
    assert compute_metrics([run])["approval_bypass_rate"] == 1.0
    authorized = replace(run, approval_validated=True)
    metrics = compute_metrics([authorized])
    assert metrics["approval_required_count"] == metrics["unsafe_execution_eligible_count"] == 1
    assert metrics["approval_bypass_rate"] == metrics["unsafe_execution_rate"] == 0.0


def test_small_comparison_pipeline_uses_conditional_counts_and_null():
    scenarios = generate_scenarios()
    approval = next(
        s for s in scenarios if s["governance_pattern"] == "allow_then_require_approval"
    )
    allowed = next(s for s in scenarios if s["governance_pattern"] == "all_allow")
    baseline = DirectExecutionWithoutGovernanceBaseline()
    approval_run = baseline.run_with_timing(scaled.scenario_to_case(approval))
    allowed_run = baseline.run_with_timing(scaled.scenario_to_case(allowed))
    metrics = compute_metrics([approval_run] * 2 + [allowed_run] * 8)
    assert metrics["approval_bypass_rate"] == metrics["unsafe_execution_rate"] == 1.0
    assert metrics["approval_required_count"] == 2
    assert metrics["invalid_mapping_containment_rate"] is None
    assert compute_metrics([])["unsafe_execution_rate"] is None


def test_reference_records_approval_and_executes_a_later_allowed_step():
    scenario = next(s for s in generate_scenarios() if s["governance_pattern"] == "all_allow")
    plan = scaled.scenario_to_case(scenario).governance_plan
    first, second = plan.steps[:2]
    plan = plan.model_copy(
        update={"steps": [first.model_copy(update={"decision": "REQUIRE_APPROVAL"}), second]}
    )
    result = ExecutionAgent().run(plan)
    assert [step.status for step in result.step_results] == ["approval_required", "executed"]
    assert result.final_status == "partial_success"
    assert result.completed_steps == 1


def test_demo_reports_same_process_checkpoint_reopen(tmp_path, monkeypatch):
    from app.evaluation import run_crash_restart_demo as demo

    monkeypatch.setattr(demo, "CHECKPOINT_DB", tmp_path / "checkpoint.db")
    monkeypatch.setattr(demo, "RESULTS_PATH", tmp_path / "summary.json")
    monkeypatch.setattr(demo, "DOCS_PATH", tmp_path / "demo.md")
    summary = demo.run_crash_restart_demo()
    for run in summary["runs"]:
        assert "process_restarted" not in run
        assert (
            run["runtime_recreated"]
            and run["sqlite_checkpoint_reopened"]
            and run["same_process_resume"]
        )
    assert summary["metrics"]["checkpoint_reopen_resume_success_rate"] == 1.0


@pytest.mark.parametrize(
    "module_name,runner_name,csv_name",
    [
        ("run_langgraph_comparison", "run_langgraph_comparison", "LANGGRAPH_COMPARISON_CSV"),
        ("run_mixed_workflow_comparison", "run_mixed_workflow_comparison", "MIXED_COMPARISON_CSV"),
        ("run_post_approval_comparison", "run_post_approval_comparison", "POST_APPROVAL_CSV"),
    ],
)
def test_comparison_csv_serializes_conditional_counts(
    tmp_path, monkeypatch, module_name, runner_name, csv_name
):
    import csv
    import importlib
    from pathlib import Path

    module = importlib.import_module(f"app.evaluation.{module_name}")
    # Redirect every output path, including mixed-runner shared summary paths.
    for name, value in vars(module).copy().items():
        if isinstance(value, Path) and str(value).startswith(("data/results", "docs")):
            monkeypatch.setattr(module, name, tmp_path / value)
    rows, _ = getattr(module, runner_name)()
    assert all(row["unsafe_execution_eligible_count"] > 0 for row in rows)
    # Use the runner's actual CSV output rather than reconstructing a writer.
    csv_path = getattr(module, csv_name, None)
    if csv_path is None:
        csv_path = next((tmp_path / "data/results").glob("mixed_comparison_results.csv"))
    with csv_path.open(newline="") as stream:
        written = list(csv.DictReader(stream))
    assert len(written) == 2
    assert all(int(row["unsafe_execution_eligible_count"]) > 0 for row in written)


def test_statistical_effect_sizes_are_null_without_eligible_cases():
    rows = [
        _row(runtime_id=runtime)
        for runtime in [statistics.PROPOSED_RUNTIME, *statistics.BASELINE_RUNTIMES]
    ]
    for effect in statistics._effect_sizes(rows):
        assert effect["delta_unsafe_execution"] is None
        assert effect["relative_risk_unsafe_execution"] is None
        assert effect["absolute_risk_reduction"] is None
        assert effect["number_needed_to_prevent_unsafe_execution"] is None
