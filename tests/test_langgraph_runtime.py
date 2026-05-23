"""Minimal tests for the optional LangGraph runtime path."""

from app.evaluation.baselines import GovernanceAwareReference
from app.evaluation.scenario_cases import (
    load_evaluation_cases,
    load_mixed_evaluation_cases,
    load_post_approval_evaluation_cases,
)
from app.langgraph_runtime import LangGraphRuntime


def test_langgraph_runtime_completes_allow_case() -> None:
    case = next(case for case in load_evaluation_cases() if case.scenario_category == "ALLOW")

    run = LangGraphRuntime().run_case(case)

    assert run["result"].final_status == case.expected_final_status
    assert run["interrupted"] is False
    assert set(run["trace"]) == {
        "planner_node",
        "matcher_node",
        "governance_node",
        "execution_node",
        "final_result",
    }


def test_langgraph_runtime_interrupts_and_resumes_approval_case() -> None:
    case = next(
        case for case in load_evaluation_cases() if case.scenario_category == "REQUIRE_APPROVAL"
    )

    run = LangGraphRuntime().run_case(case)

    assert run["interrupted"] is True
    assert run["resumed"] is True
    assert run["result"].final_status == "partial_success"
    assert run["result"].completed_steps == 0
    assert run["result"].step_results[0].status == "approval_required"


def test_mixed_evaluation_set_contains_twelve_labeled_cases() -> None:
    cases = load_mixed_evaluation_cases()

    assert len(cases) == 12
    assert all(case.expected_governance_sequence for case in cases)
    assert {
        "MIXED_ALLOW_REQUIRE_APPROVAL",
        "MIXED_ALLOW_BLOCK",
        "MIXED_ALLOW_SAFE_ABORT",
        "MIXED_REQUIRE_APPROVAL_RESUME_ALLOW",
        "MIXED_ALLOW_ALLOW_BLOCK",
    }.issubset({case.scenario_category for case in cases})


def test_langgraph_mixed_approval_trace_records_interrupt_and_resume() -> None:
    case = next(
        case
        for case in load_mixed_evaluation_cases()
        if case.scenario_category == "MIXED_REQUIRE_APPROVAL_RESUME_ALLOW"
    )

    run = LangGraphRuntime().run_case(case)

    assert run["interrupted"] is True
    assert run["resumed"] is True
    assert run["result"].final_status == case.expected_post_resume_final_status
    assert "approval_interrupt" in run["trace"]
    assert "approval_resume" in run["trace"]
    assert run["trace"].index("approval_interrupt") < run["trace"].index("approval_resume")


def test_valid_approval_leads_to_controlled_continuation() -> None:
    case = _post_approval_case("CASE-POST-APPROVAL-VALID-002")

    run = LangGraphRuntime().run_case(
        case,
        approval_payload=case.approval_payload,
        controlled_approval_execution=True,
    )

    assert run["approval_state"] == "approved"
    assert run["approval_execution_performed"] is True
    assert run["result"].final_status == "success"
    assert run["result"].step_results[0].status == "executed"


def test_missing_approval_payload_does_not_execute_gated_step() -> None:
    case = _post_approval_case("CASE-POST-APPROVAL-MISSING-PAYLOAD-001")

    run = LangGraphRuntime().run_case(
        case,
        approval_payload=case.approval_payload,
        controlled_approval_execution=True,
    )

    assert run["approval_state"] == "approval_invalid"
    assert run["approval_execution_performed"] is False
    assert run["approval_validation_error"] == "approval_not_granted"
    assert run["result"].step_results[0].status == "approval_required"


def test_invalid_approval_payload_is_rejected() -> None:
    case = _post_approval_case("CASE-POST-APPROVAL-INVALID-PAYLOAD-001")

    run = LangGraphRuntime().run_case(
        case,
        approval_payload=case.approval_payload,
        controlled_approval_execution=True,
    )

    assert run["approval_state"] == "approval_invalid"
    assert run["approval_execution_performed"] is False
    assert "approval_rejected" in run["trace"]


def test_invalid_mapping_after_resume_prevents_execution_safely() -> None:
    case = _post_approval_case("CASE-POST-APPROVAL-INVALID-MAPPING-001")

    run = LangGraphRuntime().run_case(
        case,
        approval_payload=case.approval_payload,
        controlled_approval_execution=True,
    )

    assert run["approval_state"] == "revalidation_failed"
    assert run["approval_execution_performed"] is False
    assert run["approval_validation_error"] == "invalid_execution_mapping"
    assert run["result"].final_status == "safe_aborted"


def test_post_approval_trace_contains_required_markers() -> None:
    case = _post_approval_case("CASE-POST-APPROVAL-VALID-001")

    run = LangGraphRuntime().run_case(
        case,
        approval_payload=case.approval_payload,
        controlled_approval_execution=True,
    )

    assert [
        "planner_node",
        "matcher_node",
        "governance_node",
        "approval_interrupt",
        "approval_resume",
        "approval_validated",
        "approved_execution",
        "execution_node",
        "final_result",
    ] == run["trace"]


def test_reference_v1_remains_unchanged_for_approval_case() -> None:
    case = _post_approval_case("CASE-POST-APPROVAL-VALID-002")

    run = GovernanceAwareReference().run_with_timing(case)

    assert run.result.final_status == "partial_success"
    assert run.result.completed_steps == 0
    assert run.result.step_results[0].status == "approval_required"


def _post_approval_case(case_id: str):
    return next(case for case in load_post_approval_evaluation_cases() if case.case_id == case_id)
