"""Deterministic execution agent for mapped plans."""

from time import perf_counter
from typing import Any

from app.adapters import AdapterError, get_adapter
from app.models.execution_result import ExecutionResult, StepExecutionResult
from app.models.mapped_plan import MappedPlan, MappedPlanStep


class ExecutionAgent:
    """Execute matched plan steps through selected adapters."""

    def run(self, mapped_plan: MappedPlan) -> ExecutionResult:
        """Execute a mapped plan step by step."""

        run_start = perf_counter()
        step_results = [
            self._execute_step(step, mapped_plan.payload) for step in mapped_plan.steps
        ]
        total_latency_ms = self._elapsed_ms(run_start)

        completed_steps = sum(1 for step in step_results if step.status == "executed")
        failed_steps = sum(1 for step in step_results if step.status == "failed")
        skipped_steps = sum(1 for step in step_results if step.status == "skipped")

        return ExecutionResult(
            run_id=f"run-{mapped_plan.goal_id}",
            goal_id=mapped_plan.goal_id,
            final_status=self._final_status(completed_steps, failed_steps, skipped_steps),
            total_latency_ms=total_latency_ms,
            completed_steps=completed_steps,
            failed_steps=failed_steps,
            skipped_steps=skipped_steps,
            output=self._collect_output(step_results),
            step_results=step_results,
        )

    def _execute_step(
        self,
        step: MappedPlanStep,
        payload: dict[str, Any],
    ) -> StepExecutionResult:
        if not step.matched:
            return StepExecutionResult(
                step_id=step.step_id,
                title=step.title,
                status="skipped",
                adapter=step.selected_adapter,
                capability=step.selected_capability,
                latency_ms=0,
                result=None,
                error=None,
                notes=self._skip_reason(step),
            )

        if step.selected_adapter is None or step.selected_capability is None:
            return StepExecutionResult(
                step_id=step.step_id,
                title=step.title,
                status="failed",
                adapter=step.selected_adapter,
                capability=step.selected_capability,
                latency_ms=0,
                result=None,
                error="Matched step is missing selected_adapter or selected_capability.",
                notes=step.notes,
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

    def _final_status(
        self,
        completed_steps: int,
        failed_steps: int,
        skipped_steps: int,
    ) -> str:
        if completed_steps > 0 and failed_steps == 0:
            return "success"

        if completed_steps > 0 and failed_steps > 0:
            return "partial_success"

        if completed_steps == 0 and (failed_steps > 0 or skipped_steps > 0):
            return "failed"

        return "failed"

    def _collect_output(
        self,
        step_results: list[StepExecutionResult],
    ) -> dict[str, Any]:
        return {
            step.step_id: step.result
            for step in step_results
            if step.status == "executed" and step.result is not None
        }

    def _skip_reason(self, step: MappedPlanStep) -> str:
        if step.required_capability is None:
            return "Step has no required capability and is reserved for reasoning or recording."

        return "Step was not matched to a registered executable capability."

    def _elapsed_ms(self, start: float) -> int:
        return int((perf_counter() - start) * 1000)
