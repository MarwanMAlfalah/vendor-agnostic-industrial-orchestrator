"""Minimal deterministic contract tests for the research prototype."""

from datetime import UTC, datetime

from app.agents import (
    CapabilityMatchingAgent,
    ExecutionAgent,
    GovernanceAgent,
    PlannerAgent,
)
from app.models.goal import Goal
from app.models.governance import GovernanceEvaluation, GovernanceStepDecision
from app.models.mapped_plan import MappedPlan, MappedPlanStep


def test_planner_alarm_handling_produces_read_steps() -> None:
    goal = _goal(
        goal_id="G-TEST-PLAN",
        goal_type="alarm_handling",
        payload={"machine_id": "M-101"},
    )

    plan = PlannerAgent().plan(goal)

    assert [step.required_capability for step in plan.steps[:2]] == [
        "read_machine_status",
        "read_alarm_code",
    ]
    assert plan.steps[-1].required_capability is None


def test_matcher_maps_registered_capability_to_adapter() -> None:
    goal = _goal(
        goal_id="G-TEST-MATCH",
        goal_type="alarm_handling",
        payload={"machine_id": "M-101"},
    )
    plan = PlannerAgent().plan(goal)

    mapped_plan = CapabilityMatchingAgent().match_plan(plan)

    first_step = mapped_plan.steps[0]
    assert first_step.matched is True
    assert first_step.selected_adapter == "opcua_adapter"
    assert first_step.selected_capability == "read_machine_status"


def test_governance_blocks_forbidden_shutdown() -> None:
    mapped_plan = MappedPlan(
        goal_id="G-TEST-BLOCK",
        goal_type="governed_action",
        payload={"action_name": "shutdown_line", "machine_id": "M-101"},
        steps=[
            MappedPlanStep(
                step_id="step-001",
                title="Validate requested action",
                intent="Validate shutdown request.",
                required_capability="validate_vendor_action",
                matched=True,
                selected_adapter="legacy_adapter",
                selected_capability="validate_vendor_action",
            )
        ],
    )

    evaluation = GovernanceAgent().evaluate(mapped_plan)

    assert evaluation.steps[0].decision == "BLOCK"
    assert evaluation.governance_summary["block"] == 1


def test_governance_aware_execution_does_not_execute_approval_required_step() -> None:
    governance_plan = GovernanceEvaluation(
        goal_id="G-TEST-APPROVAL",
        goal_type="governed_action",
        payload={"action_name": "reset_alarm", "machine_id": "M-101"},
        steps=[
            GovernanceStepDecision(
                step_id="step-001",
                title="Validate vendor action",
                decision="REQUIRE_APPROVAL",
                reason="sensitive_vendor_action",
                selected_adapter="legacy_adapter",
                selected_capability="validate_vendor_action",
            )
        ],
        governance_summary={
            "allow": 0,
            "block": 0,
            "require_approval": 1,
            "fallback": 0,
            "safe_abort": 0,
        },
    )

    result = ExecutionAgent().run(governance_plan)

    assert result.final_status == "partial_success"
    assert result.completed_steps == 0
    assert result.step_results[0].status == "approval_required"
    assert result.output == {}


def test_execution_payload_propagates_machine_id_to_adapter_output() -> None:
    governance_plan = GovernanceEvaluation(
        goal_id="G-TEST-PAYLOAD",
        goal_type="alarm_handling",
        payload={"machine_id": "M-777"},
        steps=[
            GovernanceStepDecision(
                step_id="step-001",
                title="Read machine status",
                decision="ALLOW",
                reason="read_only_capability",
                selected_adapter="opcua_adapter",
                selected_capability="read_machine_status",
            )
        ],
        governance_summary={
            "allow": 1,
            "block": 0,
            "require_approval": 0,
            "fallback": 0,
            "safe_abort": 0,
        },
    )

    result = ExecutionAgent().run(governance_plan)

    assert result.final_status == "success"
    assert result.output["step-001"]["result"]["machine_id"] == "M-777"


def _goal(goal_id: str, goal_type: str, payload: dict[str, object]) -> Goal:
    return Goal(
        goal_id=goal_id,
        goal_type=goal_type,
        priority="normal",
        requested_by="pytest",
        timestamp=datetime(2026, 5, 13, tzinfo=UTC),
        payload=payload,
    )
