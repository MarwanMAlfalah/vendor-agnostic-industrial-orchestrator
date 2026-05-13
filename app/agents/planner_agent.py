"""Deterministic planner agent for research prototype goals."""

from app.models.goal import Goal
from app.models.plan import Plan, PlanStep


class UnsupportedGoalTypeError(ValueError):
    """Raised when the planner cannot create a plan for a goal type."""


class PlannerAgent:
    """Convert supported high-level goals into ordered deterministic plans."""

    supported_goal_types = {
        "alarm_handling",
        "governed_action",
        "failure_recovery",
    }

    def plan(self, goal: Goal) -> Plan:
        """Create an ordered plan for a supported goal."""

        if goal.goal_type == "alarm_handling":
            return Plan(
                goal_id=goal.goal_id,
                goal_type=goal.goal_type,
                steps=self._alarm_handling_steps(),
            )

        if goal.goal_type == "governed_action":
            return Plan(
                goal_id=goal.goal_id,
                goal_type=goal.goal_type,
                steps=self._governed_action_steps(),
            )

        if goal.goal_type == "failure_recovery":
            return Plan(
                goal_id=goal.goal_id,
                goal_type=goal.goal_type,
                steps=self._failure_recovery_steps(),
            )

        raise UnsupportedGoalTypeError(
            f"Goal type '{goal.goal_type}' is not supported by PlannerAgent."
        )

    def _alarm_handling_steps(self) -> list[PlanStep]:
        return [
            PlanStep(
                step_id="step-001",
                title="Read machine status",
                intent="Determine the current operating state of the target machine.",
                required_capability="read_machine_status",
                expected_output="Machine status and last updated timestamp.",
                notes="Read-only inspection step.",
            ),
            PlanStep(
                step_id="step-002",
                title="Read alarm code",
                intent="Collect the active alarm code for the target machine.",
                required_capability="read_alarm_code",
                expected_output="Alarm code and severity signal.",
                notes="Read-only inspection step.",
            ),
            PlanStep(
                step_id="step-003",
                title="Assess alarm severity",
                intent="Classify the alarm severity using collected status and alarm data.",
                required_capability=None,
                expected_output="Severity assessment for downstream decision making.",
                notes="No adapter execution required in this step.",
            ),
            PlanStep(
                step_id="step-004",
                title="Decide escalation need",
                intent="Decide whether the alarm requires escalation to maintenance or operations.",
                required_capability=None,
                expected_output="Escalation decision.",
                notes="Decision step only; no governance workflow is implemented yet.",
            ),
            PlanStep(
                step_id="step-005",
                title="Record outcome",
                intent="Capture the alarm handling outcome for traceability.",
                required_capability=None,
                expected_output="Recorded summary of alarm handling result.",
                notes="Trace persistence will be added later.",
            ),
        ]

    def _governed_action_steps(self) -> list[PlanStep]:
        return [
            PlanStep(
                step_id="step-001",
                title="Validate requested action",
                intent="Validate whether the requested vendor action is structurally allowed.",
                required_capability="validate_vendor_action",
                expected_output="Validation result and reason.",
                notes="This does not execute the requested action.",
            ),
            PlanStep(
                step_id="step-002",
                title="Check governance requirements",
                intent="Identify policy constraints that apply to the requested action.",
                required_capability=None,
                expected_output="Governance requirements summary.",
                notes="Placeholder for future governance service integration.",
            ),
            PlanStep(
                step_id="step-003",
                title="Decide approval requirement",
                intent="Decide whether human or system approval is required before execution.",
                required_capability=None,
                expected_output="Approval requirement decision.",
                notes="Decision step only; approval workflow is not implemented yet.",
            ),
            PlanStep(
                step_id="step-004",
                title="Execute action if allowed",
                intent="Run the requested action only if validation and governance checks allow it.",
                required_capability="run_legacy_command",
                expected_output="Action execution acceptance and message.",
                notes="Future orchestration will enforce the preceding decisions.",
            ),
            PlanStep(
                step_id="step-005",
                title="Record outcome",
                intent="Capture the governed action outcome for traceability.",
                required_capability=None,
                expected_output="Recorded summary of governed action result.",
                notes="Trace persistence will be added later.",
            ),
        ]

    def _failure_recovery_steps(self) -> list[PlanStep]:
        return [
            PlanStep(
                step_id="step-001",
                title="Identify target capability or tool",
                intent="Determine the primary capability or tool involved in the failed operation.",
                required_capability=None,
                expected_output="Target capability or tool candidate.",
                notes="Capability matching is intentionally deferred.",
            ),
            PlanStep(
                step_id="step-002",
                title="Attempt primary execution",
                intent="Attempt the primary execution path for the target operation.",
                required_capability=None,
                expected_output="Primary execution result.",
                notes="Execution is not implemented in the planner.",
            ),
            PlanStep(
                step_id="step-003",
                title="Detect failure",
                intent="Inspect the primary execution result for failure signals.",
                required_capability=None,
                expected_output="Failure classification.",
                notes="Failure detection rules will be added later.",
            ),
            PlanStep(
                step_id="step-004",
                title="Attempt fallback or retry",
                intent="Try a fallback path or retry strategy when failure is detected.",
                required_capability=None,
                expected_output="Fallback or retry result.",
                notes="Retry and fallback policies are not implemented yet.",
            ),
            PlanStep(
                step_id="step-005",
                title="Record recovery outcome",
                intent="Capture the recovery attempt outcome for later analysis.",
                required_capability=None,
                expected_output="Recorded recovery summary.",
                notes="Trace persistence will be added later.",
            ),
        ]
