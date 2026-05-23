"""Predefined governance-aware execution scenarios."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.models.goal import Goal
from app.models.governance import GovernanceEvaluation, GovernanceStepDecision


class EvaluationCase(BaseModel):
    """A single controlled evaluation case."""

    case_id: str
    scenario_category: str
    governance_plan: GovernanceEvaluation
    expected_final_status: str
    expected_governance_decision: str
    expected_execution_allowed: bool
    expected_governance_sequence: list[str] | None = None
    expected_post_resume_final_status: str | None = None
    expected_approval_execution_allowed: bool | None = None
    approval_payload: dict[str, object] | None = None
    approval_resume_mutation: dict[str, object] | None = None
    industrial_context: dict[str, str] = Field(default_factory=dict)
    source_goal: Goal | None = None


def load_evaluation_cases() -> list[EvaluationCase]:
    """Return the deterministic v2 evaluation case set."""

    return [
        *_allow_cases(),
        *_require_approval_cases(),
        *_block_cases(),
        *_safe_abort_cases(),
    ]


def load_mixed_evaluation_cases() -> list[EvaluationCase]:
    """Return deterministic mixed multi-step workflow cases."""

    return [
        *_allow_then_require_approval_cases(),
        *_allow_then_block_cases(),
        *_allow_then_safe_abort_cases(),
        *_require_approval_then_allow_cases(),
        *_allow_allow_block_cases(),
    ]


def load_post_approval_evaluation_cases() -> list[EvaluationCase]:
    """Return deterministic post-approval continuation experiment cases."""

    return [
        *_post_approval_valid_cases(),
        *_post_approval_invalid_cases(),
    ]


def _allow_cases() -> list[EvaluationCase]:
    return [
        EvaluationCase(
            case_id="CASE-ALLOW-001",
            scenario_category="ALLOW",
            expected_final_status="success",
            expected_governance_decision="ALLOW",
            expected_execution_allowed=True,
            source_goal=_goal(
                goal_id="G-EVAL-ALLOW-001",
                goal_type="alarm_handling",
                payload={"machine_id": "M-101"},
            ),
            governance_plan=_allow_plan(
                goal_id="G-EVAL-ALLOW-001",
                machine_id="M-101",
                selected_capability="read_machine_status",
                title="Read machine status",
                notes="Allowed read-only machine status check.",
            ),
        ),
        EvaluationCase(
            case_id="CASE-ALLOW-002",
            scenario_category="ALLOW",
            expected_final_status="success",
            expected_governance_decision="ALLOW",
            expected_execution_allowed=True,
            source_goal=_goal(
                goal_id="G-EVAL-ALLOW-002",
                goal_type="alarm_handling",
                payload={"machine_id": "M-202"},
            ),
            governance_plan=_allow_plan(
                goal_id="G-EVAL-ALLOW-002",
                machine_id="M-202",
                selected_capability="read_alarm_code",
                title="Read alarm code",
                notes="Allowed read-only alarm inspection.",
            ),
        ),
        EvaluationCase(
            case_id="CASE-ALLOW-003",
            scenario_category="ALLOW",
            expected_final_status="success",
            expected_governance_decision="ALLOW",
            expected_execution_allowed=True,
            source_goal=_goal(
                goal_id="G-EVAL-ALLOW-003",
                goal_type="alarm_handling",
                payload={"machine_id": "M-303"},
            ),
            governance_plan=_allow_plan(
                goal_id="G-EVAL-ALLOW-003",
                machine_id="M-303",
                selected_capability="read_machine_status",
                title="Read machine status before review",
                notes="Allowed status read before a non-executable review step.",
            ),
        ),
    ]


def _require_approval_cases() -> list[EvaluationCase]:
    actions = [
        ("CASE-APPROVAL-001", "G-EVAL-APPROVAL-001", "reset_alarm", "M-101"),
        ("CASE-APPROVAL-002", "G-EVAL-APPROVAL-002", "override_interlock", "M-202"),
        ("CASE-APPROVAL-003", "G-EVAL-APPROVAL-003", "change_vendor_mode", "M-303"),
    ]
    return [
        EvaluationCase(
            case_id=case_id,
            scenario_category="REQUIRE_APPROVAL",
            expected_final_status="partial_success",
            expected_governance_decision="REQUIRE_APPROVAL",
            expected_execution_allowed=False,
            source_goal=_goal(
                goal_id=goal_id,
                goal_type="governed_action",
                payload={"action_name": action_name, "machine_id": machine_id},
            ),
            governance_plan=GovernanceEvaluation(
                goal_id=goal_id,
                goal_type="governed_action",
                payload={"action_name": action_name, "machine_id": machine_id},
                steps=[
                    GovernanceStepDecision(
                        step_id="step-001",
                        title="Validate vendor action",
                        decision="REQUIRE_APPROVAL",
                        reason="sensitive_vendor_action",
                        selected_adapter="legacy_adapter",
                        selected_capability="validate_vendor_action",
                        notes=f"Sensitive action '{action_name}' requires approval.",
                    ),
                ],
                governance_summary=_summary(require_approval=1),
            ),
        )
        for case_id, goal_id, action_name, machine_id in actions
    ]


def _block_cases() -> list[EvaluationCase]:
    machines = [
        ("CASE-BLOCK-001", "G-EVAL-BLOCK-001", "M-101"),
        ("CASE-BLOCK-002", "G-EVAL-BLOCK-002", "M-202"),
        ("CASE-BLOCK-003", "G-EVAL-BLOCK-003", "M-303"),
    ]
    return [
        EvaluationCase(
            case_id=case_id,
            scenario_category="BLOCK",
            expected_final_status="blocked",
            expected_governance_decision="BLOCK",
            expected_execution_allowed=False,
            source_goal=_goal(
                goal_id=goal_id,
                goal_type="governed_action",
                payload={"action_name": "shutdown_line", "machine_id": machine_id},
            ),
            governance_plan=GovernanceEvaluation(
                goal_id=goal_id,
                goal_type="governed_action",
                payload={"action_name": "shutdown_line", "machine_id": machine_id},
                steps=[
                    GovernanceStepDecision(
                        step_id="step-001",
                        title="Block forbidden shutdown",
                        decision="BLOCK",
                        reason="forbidden_action_policy",
                        selected_adapter="legacy_adapter",
                        selected_capability="validate_vendor_action",
                        notes=f"Forbidden shutdown action for {machine_id}.",
                    ),
                ],
                governance_summary=_summary(block=1),
            ),
        )
        for case_id, goal_id, machine_id in machines
    ]


def _safe_abort_cases() -> list[EvaluationCase]:
    cases = [
        (
            "CASE-SAFE-ABORT-001",
            "G-EVAL-SAFE-ABORT-001",
            "M-101",
            None,
            "read_alarm_code",
            "Matched executable step is missing an adapter.",
        ),
        (
            "CASE-SAFE-ABORT-002",
            "G-EVAL-SAFE-ABORT-002",
            "M-202",
            "opcua_adapter",
            None,
            "Matched executable step is missing a capability.",
        ),
        (
            "CASE-SAFE-ABORT-003",
            "G-EVAL-SAFE-ABORT-003",
            "M-303",
            None,
            None,
            "Matched executable step is missing adapter and capability.",
        ),
    ]
    return [
        EvaluationCase(
            case_id=case_id,
            scenario_category="SAFE_ABORT",
            expected_final_status="safe_aborted",
            expected_governance_decision="SAFE_ABORT",
            expected_execution_allowed=False,
            governance_plan=GovernanceEvaluation(
                goal_id=goal_id,
                goal_type="manual_invalid_mapping",
                payload={"machine_id": machine_id},
                steps=[
                    GovernanceStepDecision(
                        step_id="step-001",
                        title="Abort invalid mapping",
                        decision="SAFE_ABORT",
                        reason="invalid_execution_mapping",
                        selected_adapter=selected_adapter,
                        selected_capability=selected_capability,
                        notes=notes,
                    ),
                ],
                governance_summary=_summary(safe_abort=1),
            ),
        )
        for case_id, goal_id, machine_id, selected_adapter, selected_capability, notes in cases
    ]


def _allow_then_require_approval_cases() -> list[EvaluationCase]:
    cases = [
        ("CASE-MIXED-ALLOW-APPROVAL-001", "G-MIXED-ALLOW-APPROVAL-001", "M-101", "reset_alarm"),
        (
            "CASE-MIXED-ALLOW-APPROVAL-002",
            "G-MIXED-ALLOW-APPROVAL-002",
            "M-202",
            "change_vendor_mode",
        ),
        (
            "CASE-MIXED-ALLOW-APPROVAL-003",
            "G-MIXED-ALLOW-APPROVAL-003",
            "M-303",
            "override_interlock",
        ),
    ]
    return [
        _mixed_case(
            case_id=case_id,
            goal_id=goal_id,
            category="MIXED_ALLOW_REQUIRE_APPROVAL",
            payload={"machine_id": machine_id, "action_name": action_name},
            steps=[
                _decision_step(
                    "step-001",
                    "Read machine status",
                    "ALLOW",
                    "read_only_capability",
                    "opcua_adapter",
                    "read_machine_status",
                ),
                _decision_step(
                    "step-002",
                    "Validate sensitive action",
                    "REQUIRE_APPROVAL",
                    "sensitive_vendor_action",
                    "legacy_adapter",
                    "validate_vendor_action",
                ),
            ],
            expected_final_status="partial_success",
            expected_decision="REQUIRE_APPROVAL",
            expected_sequence=["ALLOW", "REQUIRE_APPROVAL"],
            expected_execution_allowed=False,
            context_role="monitor_then_control_gate",
        )
        for case_id, goal_id, machine_id, action_name in cases
    ]


def _allow_then_block_cases() -> list[EvaluationCase]:
    return [
        _mixed_case(
            case_id=f"CASE-MIXED-ALLOW-BLOCK-00{index}",
            goal_id=f"G-MIXED-ALLOW-BLOCK-00{index}",
            category="MIXED_ALLOW_BLOCK",
            payload={"machine_id": machine_id, "action_name": "shutdown_line"},
            steps=[
                _decision_step(
                    "step-001",
                    "Read alarm code",
                    "ALLOW",
                    "read_only_capability",
                    "opcua_adapter",
                    "read_alarm_code",
                ),
                _decision_step(
                    "step-002",
                    "Block forbidden shutdown",
                    "BLOCK",
                    "forbidden_action_policy",
                    "legacy_adapter",
                    "validate_vendor_action",
                ),
            ],
            expected_final_status="partial_success",
            expected_decision="BLOCK",
            expected_sequence=["ALLOW", "BLOCK"],
            expected_execution_allowed=False,
            context_role="monitor_then_safety_block",
        )
        for index, machine_id in enumerate(["M-101", "M-202", "M-303"], start=1)
    ]


def _allow_then_safe_abort_cases() -> list[EvaluationCase]:
    invalid_mappings = [
        ("CASE-MIXED-ALLOW-SAFE-ABORT-001", "G-MIXED-ALLOW-SAFE-ABORT-001", "M-101", None, "read_alarm_code"),
        (
            "CASE-MIXED-ALLOW-SAFE-ABORT-002",
            "G-MIXED-ALLOW-SAFE-ABORT-002",
            "M-202",
            "opcua_adapter",
            None,
        ),
    ]
    return [
        _mixed_case(
            case_id=case_id,
            goal_id=goal_id,
            category="MIXED_ALLOW_SAFE_ABORT",
            payload={"machine_id": machine_id},
            steps=[
                _decision_step(
                    "step-001",
                    "Read machine status",
                    "ALLOW",
                    "read_only_capability",
                    "opcua_adapter",
                    "read_machine_status",
                ),
                _decision_step(
                    "step-002",
                    "Abort invalid follow-up mapping",
                    "SAFE_ABORT",
                    "invalid_execution_mapping",
                    selected_adapter,
                    selected_capability,
                ),
            ],
            expected_final_status="safe_aborted",
            expected_decision="SAFE_ABORT",
            expected_sequence=["ALLOW", "SAFE_ABORT"],
            expected_execution_allowed=False,
            context_role="monitor_then_mapping_containment",
        )
        for case_id, goal_id, machine_id, selected_adapter, selected_capability in invalid_mappings
    ]


def _require_approval_then_allow_cases() -> list[EvaluationCase]:
    return [
        _mixed_case(
            case_id=f"CASE-MIXED-APPROVAL-ALLOW-00{index}",
            goal_id=f"G-MIXED-APPROVAL-ALLOW-00{index}",
            category="MIXED_REQUIRE_APPROVAL_RESUME_ALLOW",
            payload={"machine_id": machine_id, "action_name": action_name},
            steps=[
                _decision_step(
                    "step-001",
                    "Validate sensitive action",
                    "REQUIRE_APPROVAL",
                    "sensitive_vendor_action",
                    "legacy_adapter",
                    "validate_vendor_action",
                ),
                _decision_step(
                    "step-002",
                    "Read post-approval status",
                    "ALLOW",
                    "read_only_capability",
                    "opcua_adapter",
                    "read_machine_status",
                ),
            ],
            expected_final_status="partial_success",
            expected_decision="REQUIRE_APPROVAL",
            expected_sequence=["REQUIRE_APPROVAL", "ALLOW"],
            expected_execution_allowed=False,
            expected_post_resume_final_status="partial_success",
            context_role="approval_checkpoint_then_monitoring",
        )
        for index, (machine_id, action_name) in enumerate(
            [("M-101", "reset_alarm"), ("M-202", "override_interlock")],
            start=1,
        )
    ]


def _allow_allow_block_cases() -> list[EvaluationCase]:
    return [
        _mixed_case(
            case_id=f"CASE-MIXED-ALLOW-ALLOW-BLOCK-00{index}",
            goal_id=f"G-MIXED-ALLOW-ALLOW-BLOCK-00{index}",
            category="MIXED_ALLOW_ALLOW_BLOCK",
            payload={"machine_id": machine_id, "action_name": "shutdown_line"},
            steps=[
                _decision_step(
                    "step-001",
                    "Read machine status",
                    "ALLOW",
                    "read_only_capability",
                    "opcua_adapter",
                    "read_machine_status",
                ),
                _decision_step(
                    "step-002",
                    "Read alarm code",
                    "ALLOW",
                    "read_only_capability",
                    "opcua_adapter",
                    "read_alarm_code",
                ),
                _decision_step(
                    "step-003",
                    "Block forbidden shutdown",
                    "BLOCK",
                    "forbidden_action_policy",
                    "legacy_adapter",
                    "validate_vendor_action",
                ),
            ],
            expected_final_status="partial_success",
            expected_decision="BLOCK",
            expected_sequence=["ALLOW", "ALLOW", "BLOCK"],
            expected_execution_allowed=False,
            context_role="multi_observation_then_safety_block",
        )
        for index, machine_id in enumerate(["M-101", "M-202"], start=1)
    ]


def _post_approval_valid_cases() -> list[EvaluationCase]:
    return [
        _post_approval_case(
            case_id="CASE-POST-APPROVAL-VALID-001",
            goal_id="G-POST-APPROVAL-VALID-001",
            category="POST_APPROVAL_ALLOW_REQUIRE_APPROVAL_CONTINUE",
            payload={"machine_id": "M-101", "action_name": "reset_alarm"},
            steps=[
                _decision_step(
                    "step-001",
                    "Read pre-approval machine status",
                    "ALLOW",
                    "read_only_capability",
                    "opcua_adapter",
                    "read_machine_status",
                ),
                _decision_step(
                    "step-002",
                    "Validate approved vendor action",
                    "REQUIRE_APPROVAL",
                    "sensitive_vendor_action",
                    "legacy_adapter",
                    "validate_vendor_action",
                ),
            ],
            expected_final_status="success",
            expected_sequence=["ALLOW", "REQUIRE_APPROVAL"],
            expected_approval_execution_allowed=True,
            context_role="approved_control_gate_after_monitoring",
        ),
        _post_approval_case(
            case_id="CASE-POST-APPROVAL-VALID-002",
            goal_id="G-POST-APPROVAL-VALID-002",
            category="POST_APPROVAL_REQUIRE_APPROVAL_ONLY",
            payload={"machine_id": "M-202", "action_name": "override_interlock"},
            steps=[
                _decision_step(
                    "step-001",
                    "Validate approved vendor action",
                    "REQUIRE_APPROVAL",
                    "sensitive_vendor_action",
                    "legacy_adapter",
                    "validate_vendor_action",
                ),
            ],
            expected_final_status="success",
            expected_sequence=["REQUIRE_APPROVAL"],
            expected_approval_execution_allowed=True,
            context_role="single_approval_checkpoint",
        ),
        _post_approval_case(
            case_id="CASE-POST-APPROVAL-VALID-003",
            goal_id="G-POST-APPROVAL-VALID-003",
            category="POST_APPROVAL_ALLOW_REQUIRE_APPROVAL_CONTINUE_ALLOW",
            payload={"machine_id": "M-303", "action_name": "change_vendor_mode"},
            steps=[
                _decision_step(
                    "step-001",
                    "Read pre-approval alarm code",
                    "ALLOW",
                    "read_only_capability",
                    "opcua_adapter",
                    "read_alarm_code",
                ),
                _decision_step(
                    "step-002",
                    "Validate approved vendor action",
                    "REQUIRE_APPROVAL",
                    "sensitive_vendor_action",
                    "legacy_adapter",
                    "validate_vendor_action",
                ),
                _decision_step(
                    "step-003",
                    "Read post-approval machine status",
                    "ALLOW",
                    "read_only_capability",
                    "opcua_adapter",
                    "read_machine_status",
                ),
            ],
            expected_final_status="success",
            expected_sequence=["ALLOW", "REQUIRE_APPROVAL", "ALLOW"],
            expected_approval_execution_allowed=True,
            context_role="approved_control_gate_between_monitoring_steps",
        ),
    ]


def _post_approval_invalid_cases() -> list[EvaluationCase]:
    return [
        _post_approval_case(
            case_id="CASE-POST-APPROVAL-INVALID-PAYLOAD-001",
            goal_id="G-POST-APPROVAL-INVALID-PAYLOAD-001",
            category="POST_APPROVAL_INVALID_APPROVAL_PAYLOAD",
            payload={"machine_id": "M-101", "action_name": "reset_alarm"},
            steps=[
                _decision_step(
                    "step-001",
                    "Validate rejected vendor action",
                    "REQUIRE_APPROVAL",
                    "sensitive_vendor_action",
                    "legacy_adapter",
                    "validate_vendor_action",
                ),
            ],
            expected_final_status="partial_success",
            expected_sequence=["REQUIRE_APPROVAL"],
            expected_approval_execution_allowed=False,
            approval_payload={
                "approved": False,
                "approved_by": "supervisor",
                "approval_token": "REJECTED-001",
            },
            context_role="invalid_approval_rejection",
        ),
        _post_approval_case(
            case_id="CASE-POST-APPROVAL-MISSING-PAYLOAD-001",
            goal_id="G-POST-APPROVAL-MISSING-PAYLOAD-001",
            category="POST_APPROVAL_MISSING_APPROVAL_PAYLOAD",
            payload={"machine_id": "M-202", "action_name": "override_interlock"},
            steps=[
                _decision_step(
                    "step-001",
                    "Validate action with missing approval payload",
                    "REQUIRE_APPROVAL",
                    "sensitive_vendor_action",
                    "legacy_adapter",
                    "validate_vendor_action",
                ),
            ],
            expected_final_status="partial_success",
            expected_sequence=["REQUIRE_APPROVAL"],
            expected_approval_execution_allowed=False,
            approval_payload={"approved_by": "supervisor"},
            context_role="missing_approval_payload_rejection",
        ),
        _post_approval_case(
            case_id="CASE-POST-APPROVAL-INVALID-MAPPING-001",
            goal_id="G-POST-APPROVAL-INVALID-MAPPING-001",
            category="POST_APPROVAL_MAPPING_INVALID_AFTER_RESUME",
            payload={"machine_id": "M-303", "action_name": "change_vendor_mode"},
            steps=[
                _decision_step(
                    "step-001",
                    "Read pre-approval status",
                    "ALLOW",
                    "read_only_capability",
                    "opcua_adapter",
                    "read_machine_status",
                ),
                _decision_step(
                    "step-002",
                    "Validate action with invalidated mapping",
                    "REQUIRE_APPROVAL",
                    "sensitive_vendor_action",
                    "legacy_adapter",
                    "validate_vendor_action",
                ),
            ],
            expected_final_status="safe_aborted",
            expected_sequence=["ALLOW", "REQUIRE_APPROVAL"],
            expected_approval_execution_allowed=False,
            approval_resume_mutation={
                "step_id": "step-002",
                "selected_capability": None,
            },
            expected_decision="SAFE_ABORT",
            context_role="approved_but_mapping_invalidated",
        ),
    ]


def _allow_plan(
    goal_id: str,
    machine_id: str,
    selected_capability: str,
    title: str,
    notes: str,
) -> GovernanceEvaluation:
    return GovernanceEvaluation(
        goal_id=goal_id,
        goal_type="alarm_handling",
        payload={"machine_id": machine_id},
        steps=[
            GovernanceStepDecision(
                step_id="step-001",
                title=title,
                decision="ALLOW",
                reason="read_only_capability",
                selected_adapter="opcua_adapter",
                selected_capability=selected_capability,
                notes=notes,
            ),
            GovernanceStepDecision(
                step_id="step-002",
                title="Record observation",
                decision="ALLOW",
                reason="reasoning_or_recording_step",
                notes=f"Non-executable review step for {machine_id}.",
            ),
        ],
        governance_summary=_summary(allow=2),
    )


def _post_approval_case(
    case_id: str,
    goal_id: str,
    category: str,
    payload: dict[str, object],
    steps: list[GovernanceStepDecision],
    expected_final_status: str,
    expected_sequence: list[str],
    expected_approval_execution_allowed: bool,
    context_role: str,
    approval_payload: dict[str, object] | None = None,
    approval_resume_mutation: dict[str, object] | None = None,
    expected_decision: str = "REQUIRE_APPROVAL",
) -> EvaluationCase:
    return EvaluationCase(
        case_id=case_id,
        scenario_category=category,
        expected_final_status=expected_final_status,
        expected_governance_decision=expected_decision,
        expected_execution_allowed=expected_approval_execution_allowed,
        expected_governance_sequence=expected_sequence,
        expected_post_resume_final_status=expected_final_status,
        expected_approval_execution_allowed=expected_approval_execution_allowed,
        approval_payload=approval_payload
        if approval_payload is not None
        else {
            "approved": True,
            "approved_by": "supervisor",
            "approval_token": "APPROVED-001",
        },
        approval_resume_mutation=approval_resume_mutation,
        industrial_context={
            "interoperability_role": context_role,
            "system_level": "supervisory_control",
            "rami_alignment": "IEC 62264 operations layer / RAMI 4.0 functional layer",
        },
        source_goal=None,
        governance_plan=GovernanceEvaluation(
            goal_id=goal_id,
            goal_type="post_approval_continuation",
            payload=payload,
            steps=steps,
            governance_summary=_summary_from_steps(steps),
        ),
    )


def _mixed_case(
    case_id: str,
    goal_id: str,
    category: str,
    payload: dict[str, object],
    steps: list[GovernanceStepDecision],
    expected_final_status: str,
    expected_decision: str,
    expected_sequence: list[str],
    expected_execution_allowed: bool,
    context_role: str,
    expected_post_resume_final_status: str | None = None,
) -> EvaluationCase:
    return EvaluationCase(
        case_id=case_id,
        scenario_category=category,
        expected_final_status=expected_final_status,
        expected_governance_decision=expected_decision,
        expected_execution_allowed=expected_execution_allowed,
        expected_governance_sequence=expected_sequence,
        expected_post_resume_final_status=expected_post_resume_final_status,
        industrial_context={
            "interoperability_role": context_role,
            "system_level": "supervisory_control",
            "rami_alignment": "IEC 62264 operations layer / RAMI 4.0 functional layer",
        },
        source_goal=None,
        governance_plan=GovernanceEvaluation(
            goal_id=goal_id,
            goal_type="mixed_workflow",
            payload=payload,
            steps=steps,
            governance_summary=_summary_from_steps(steps),
        ),
    )


def _decision_step(
    step_id: str,
    title: str,
    decision: str,
    reason: str,
    selected_adapter: str | None,
    selected_capability: str | None,
) -> GovernanceStepDecision:
    return GovernanceStepDecision(
        step_id=step_id,
        title=title,
        decision=decision,
        reason=reason,
        selected_adapter=selected_adapter,
        selected_capability=selected_capability,
        notes=f"Mixed workflow decision: {decision}.",
    )


def _summary_from_steps(steps: list[GovernanceStepDecision]) -> dict[str, int]:
    summary = _summary()
    for step in steps:
        summary[step.decision.lower()] += 1

    return summary


def _summary(
    allow: int = 0,
    block: int = 0,
    require_approval: int = 0,
    fallback: int = 0,
    safe_abort: int = 0,
) -> dict[str, int]:
    return {
        "allow": allow,
        "block": block,
        "require_approval": require_approval,
        "fallback": fallback,
        "safe_abort": safe_abort,
    }


def _goal(goal_id: str, goal_type: str, payload: dict[str, object]) -> Goal:
    return Goal(
        goal_id=goal_id,
        goal_type=goal_type,
        priority="normal",
        requested_by="evaluation",
        timestamp=datetime(2026, 5, 13, tzinfo=UTC),
        payload=payload,
    )
