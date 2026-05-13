"""Deterministic execution agent for governance-evaluated plans."""

from time import perf_counter
from typing import Any

from app.adapters import AdapterError, get_adapter
from app.models.execution_result import ExecutionResult, StepExecutionResult
from app.models.governance import GovernanceEvaluation, GovernanceStepDecision


class ExecutionAgent:
    """Execute governance-approved plan steps through selected adapters."""

    def run(self, governance_plan: GovernanceEvaluation) -> ExecutionResult:
        """Execute a governance-evaluated plan step by step."""

        run_start = perf_counter()
        step_results = self._run_steps(governance_plan)
        total_latency_ms = self._elapsed_ms(run_start)

        completed_steps = sum(1 for step in step_results if step.status == "executed")
        failed_steps = sum(1 for step in step_results if step.status == "failed")
        skipped_steps = sum(
            1
            for step in step_results
            if step.status
            in {
                "skipped",
                "approval_required",
                "blocked",
                "safe_aborted",
                "fallback_pending",
            }
        )

        return ExecutionResult(
            run_id=f"run-{governance_plan.goal_id}",
            goal_id=governance_plan.goal_id,
            final_status=self._final_status(step_results),
            total_latency_ms=total_latency_ms,
            completed_steps=completed_steps,
            failed_steps=failed_steps,
            skipped_steps=skipped_steps,
            governance_summary=governance_plan.governance_summary,
            output=self._collect_output(step_results),
            step_results=step_results,
        )

    def _run_steps(
        self,
        governance_plan: GovernanceEvaluation,
    ) -> list[StepExecutionResult]:
        step_results: list[StepExecutionResult] = []
        for step in governance_plan.steps:
            step_result = self._execute_step(step, governance_plan.payload)
            step_results.append(step_result)

            if step_result.status in {"blocked", "safe_aborted"}:
                break

        return step_results

    def _execute_step(
        self,
        step: GovernanceStepDecision,
        payload: dict[str, Any],
    ) -> StepExecutionResult:
        if step.decision == "REQUIRE_APPROVAL":
            return self._policy_step(step, "approval_required")

        if step.decision == "BLOCK":
            return self._policy_step(step, "blocked")

        if step.decision == "SAFE_ABORT":
            return self._policy_step(step, "safe_aborted")

        if step.decision == "FALLBACK":
            return self._policy_step(step, "fallback_pending")

        if step.selected_adapter is None or step.selected_capability is None:
            return StepExecutionResult(
                step_id=step.step_id,
                title=step.title,
                status="skipped",
                adapter=step.selected_adapter,
                capability=step.selected_capability,
                latency_ms=0,
                result=None,
                error=None,
                notes=self._notes(step, "Allowed non-executable step was skipped."),
            )

        step_start = perf_counter()
        try:
            adapter = get_adapter(step.selected_adapter)
            result = adapter.invoke(step.selected_capability, payload)
        except AdapterError as exc:
            return StepExecutionResult(
                step_id=step.step_id,
                title=step.title,
                status="failed",
                adapter=step.selected_adapter,
                capability=step.selected_capability,
                latency_ms=self._elapsed_ms(step_start),
                result=None,
                error=str(exc),
                notes=step.notes,
            )

        return StepExecutionResult(
            step_id=step.step_id,
            title=step.title,
            status="executed",
            adapter=step.selected_adapter,
            capability=step.selected_capability,
            latency_ms=self._elapsed_ms(step_start),
            result=result,
            error=None,
            notes=step.notes,
        )

    def _policy_step(
        self,
        step: GovernanceStepDecision,
        status: str,
    ) -> StepExecutionResult:
        return StepExecutionResult(
            step_id=step.step_id,
            title=step.title,
            status=status,
            adapter=step.selected_adapter,
            capability=step.selected_capability,
            latency_ms=0,
            result=None,
            error=None,
            notes=self._notes(step, f"Governance decision: {step.decision}."),
        )

    def _final_status(self, step_results: list[StepExecutionResult]) -> str:
        statuses = [step.status for step in step_results]
        completed_steps = statuses.count("executed")

        if "safe_aborted" in statuses:
            return "safe_aborted"

        if "blocked" in statuses and completed_steps == 0:
            return "blocked"

        if "failed" in statuses and completed_steps == 0:
            return "failed"

        if completed_steps == 0 and any(
            status in {"approval_required", "fallback_pending"} for status in statuses
        ):
            return "partial_success"

        if completed_steps > 0 and any(
            status
            in {
                "approval_required",
                "blocked",
                "failed",
                "fallback_pending",
            }
            for status in statuses
        ):
            return "partial_success"

        if "failed" in statuses:
            return "failed"

        return "success"

    def _collect_output(
        self,
        step_results: list[StepExecutionResult],
    ) -> dict[str, Any]:
        return {
            step.step_id: step.result
            for step in step_results
            if step.status == "executed" and step.result is not None
        }

    def _notes(self, step: GovernanceStepDecision, suffix: str) -> str:
        note_parts = [f"Governance reason: {step.reason}.", suffix]
        if step.notes:
            note_parts.append(step.notes)

        return " ".join(note_parts)

    def _elapsed_ms(self, start: float) -> int:
        return int((perf_counter() - start) * 1000)
