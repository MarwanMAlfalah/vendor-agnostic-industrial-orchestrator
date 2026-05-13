"""Deterministic governance agent for mapped execution plans."""

from app.models.capability import Capability
from app.models.governance import GovernanceEvaluation, GovernanceStepDecision
from app.models.mapped_plan import MappedPlan, MappedPlanStep
from app.registry.loader import load_capabilities


class GovernanceAgent:
    """Evaluate mapped plan steps against explicit v1 policy rules."""

    def __init__(self, capabilities: list[Capability] | None = None) -> None:
        self.capabilities = capabilities if capabilities is not None else load_capabilities()
        self._capability_by_name = {
            capability.capability_name: capability for capability in self.capabilities
        }

    def evaluate(self, mapped_plan: MappedPlan) -> GovernanceEvaluation:
        """Evaluate every mapped plan step and return policy decisions."""

        steps = [self._evaluate_step(step, mapped_plan.payload) for step in mapped_plan.steps]
        return GovernanceEvaluation(
            goal_id=mapped_plan.goal_id,
            goal_type=mapped_plan.goal_type,
            payload=mapped_plan.payload,
            steps=steps,
            governance_summary=self._summarize(steps),
        )

    def _evaluate_step(
        self,
        step: MappedPlanStep,
        payload: dict[str, object],
    ) -> GovernanceStepDecision:
        if payload.get("action_name") == "shutdown_line":
            return self._decision(step, "BLOCK", "forbidden_action_policy")

        if not step.matched:
            return self._decision(step, "ALLOW", "reasoning_or_recording_step")

        if step.selected_adapter is None or step.selected_capability is None:
            return self._decision(step, "SAFE_ABORT", "invalid_execution_mapping")

        capability = self._capability_by_name.get(step.selected_capability)
        if capability is None:
            return self._decision(step, "SAFE_ABORT", "capability_not_registered")

        if not capability.availability:
            if step.fallback_candidates:
                return self._decision(step, "FALLBACK", "capability_unavailable")

            return self._decision(step, "SAFE_ABORT", "capability_unavailable")

        if capability.capability_name == "validate_vendor_action":
            return self._decision(step, "REQUIRE_APPROVAL", "sensitive_vendor_action")

        if "read_only" in capability.policy_tags:
            return self._decision(step, "ALLOW", "read_only_capability")

        return self._decision(step, "ALLOW", "no_blocking_policy")

    def _decision(
        self,
        step: MappedPlanStep,
        decision: str,
        reason: str,
    ) -> GovernanceStepDecision:
        return GovernanceStepDecision(
            step_id=step.step_id,
            title=step.title,
            decision=decision,
            reason=reason,
            selected_adapter=step.selected_adapter,
            selected_capability=step.selected_capability,
            notes=step.notes,
        )

    def _summarize(
        self,
        steps: list[GovernanceStepDecision],
    ) -> dict[str, int]:
        summary = {
            "allow": 0,
            "block": 0,
            "require_approval": 0,
            "fallback": 0,
            "safe_abort": 0,
        }
        for step in steps:
            summary[step.decision.lower()] += 1

        return summary
