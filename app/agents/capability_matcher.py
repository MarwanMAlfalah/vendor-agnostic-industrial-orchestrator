"""Deterministic capability matcher for planner-produced plans."""

from app.agents.planner_agent import PlannerAgent
from app.models.capability import Capability
from app.models.goal import Goal
from app.models.mapped_plan import MappedPlan, MappedPlanStep
from app.models.plan import Plan, PlanStep
from app.registry.loader import load_capabilities


class CapabilityMatchingAgent:
    """Map plan steps to concrete capabilities from the registry."""

    def __init__(self, capabilities: list[Capability] | None = None) -> None:
        self.capabilities = capabilities if capabilities is not None else load_capabilities()
        self._capability_by_name = {
            capability.capability_name: capability for capability in self.capabilities
        }

    def match(self, target: Goal | Plan) -> MappedPlan:
        """Match either a high-level goal or an existing plan."""

        if isinstance(target, Goal):
            plan = PlannerAgent().plan(target)
        else:
            plan = target

        return self.match_plan(plan)

    def match_plan(self, plan: Plan) -> MappedPlan:
        """Match every step in a plan to registered capabilities where possible."""

        return MappedPlan(
            goal_id=plan.goal_id,
            goal_type=plan.goal_type,
            payload=plan.payload,
            steps=[self._match_step(step) for step in plan.steps],
        )

    def _match_step(self, step: PlanStep) -> MappedPlanStep:
        if step.required_capability is None:
            return MappedPlanStep(
                step_id=step.step_id,
                title=step.title,
                intent=step.intent,
                required_capability=None,
                matched=False,
                fallback_candidates=[],
                expected_output=step.expected_output,
                notes=step.notes,
            )

        capability = self._capability_by_name.get(step.required_capability)
        if capability is None:
            return MappedPlanStep(
                step_id=step.step_id,
                title=step.title,
                intent=step.intent,
                required_capability=step.required_capability,
                matched=False,
                selected_adapter=None,
                selected_capability=None,
                fallback_candidates=[],
                expected_output=step.expected_output,
                notes=f"Required capability is not registered. {step.notes or ''}".strip(),
            )

        return MappedPlanStep(
            step_id=step.step_id,
            title=step.title,
            intent=step.intent,
            required_capability=step.required_capability,
            matched=True,
            selected_adapter=capability.adapter_name,
            selected_capability=capability.capability_name,
            fallback_candidates=self._fallback_candidates(capability),
            expected_output=step.expected_output,
            notes=step.notes,
        )

    def _fallback_candidates(self, capability: Capability) -> list[str]:
        """Return explicit, conservative fallback candidates for known cases."""

        fallback_map = {
            "read_machine_status": ["read_alarm_code"],
            "read_alarm_code": ["read_machine_status"],
        }
        return [
            candidate
            for candidate in fallback_map.get(capability.capability_name, [])
            if candidate in self._capability_by_name
        ]
