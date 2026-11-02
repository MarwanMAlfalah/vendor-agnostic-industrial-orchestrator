"""Deterministic baseline methods for scientific comparison."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from app.adapters import AdapterError, get_adapter
from app.agents import (
    CapabilityMatchingAgent,
    ExecutionAgent,
    GovernanceAgent,
    PlannerAgent,
)
from app.evaluation.scenario_cases import EvaluationCase
from app.models.execution_result import ExecutionResult, StepExecutionResult
from app.models.governance import GovernanceEvaluation, GovernanceStepDecision
from app.observability.summaries import execution_summary
from app.observability.tracing import run_metadata, trace_experiment


@dataclass(frozen=True)
class MethodRunResult:
    """Execution result plus per-stage timing for one method/case run."""

    case: EvaluationCase
    result: ExecutionResult
    stage_latencies_ms: dict[str, float]
    approval_validated: bool = False


class EvaluationMethod(ABC):
    """Common interface for reference and baseline evaluation methods."""

    method_id: str
    method_name: str
    description: str

    @abstractmethod
    def run(self, case: EvaluationCase) -> ExecutionResult:
        """Run one evaluation case and return a normalized execution result."""

    def run_with_timing(self, case: EvaluationCase) -> MethodRunResult:
        """Run one case with method-level timing metadata."""

        total_start = perf_counter()
        result = self.run(case)
        total_latency_ms = _elapsed_ms(total_start)
        execution_latency_ms = result.total_latency_ms or total_latency_ms
        return MethodRunResult(
            case=case,
            result=result,
            stage_latencies_ms={
                "planning": 0.0,
                "matching": 0.0,
                "governance": 0.0,
                "execution": execution_latency_ms,
                "total": total_latency_ms,
            },
        )


class GovernanceAwareReference(EvaluationMethod):
    """Existing governance-aware staged pipeline used as the reference method."""

    method_id = "reference_governance_aware"
    method_name = "Reference: governance-aware execution"
    description = "Existing Governance -> Execution behavior."

    def __init__(self) -> None:
        self._executor = ExecutionAgent()

    def run(self, case: EvaluationCase) -> ExecutionResult:
        return self._executor.run(case.governance_plan)

    def run_with_timing(self, case: EvaluationCase) -> MethodRunResult:
        total_start = perf_counter()
        with trace_experiment(
            "reference_v1.run_case",
            inputs={"case_id": case.case_id},
            metadata=run_metadata(
                runtime_id="reference_v1",
                case_id=case.case_id,
                goal_type=case.governance_plan.goal_type,
                governance_category=case.scenario_category,
                mixed_workflow=bool(case.expected_governance_sequence),
                approval_case=case.expected_governance_decision == "REQUIRE_APPROVAL"
                or "REQUIRE_APPROVAL" in (case.expected_governance_sequence or []),
            ),
            tags=["reference_v1", "runtime"],
        ) as trace_handle:
            planning_latency_ms, matching_latency_ms, governance_latency_ms = (
                self._measure_structural_stages(case)
            )

            execution_start = perf_counter()
            result = self.run(case)
            execution_latency_ms = _elapsed_ms(execution_start)
            total_latency_ms = _elapsed_ms(total_start)
            result.stage_latencies_ms.update(
                {
                    "planning": planning_latency_ms,
                    "matching": matching_latency_ms,
                    "governance": governance_latency_ms,
                    "execution": execution_latency_ms,
                    "total": total_latency_ms,
                }
            )
            trace_handle.add_outputs(execution_summary(result))

        return MethodRunResult(
            case=case,
            result=result,
            stage_latencies_ms=result.stage_latencies_ms,
        )

    def _measure_structural_stages(
        self,
        case: EvaluationCase,
    ) -> tuple[float, float, float]:
        if case.source_goal is None:
            return 0.0, 0.0, 0.0

        planning_start = perf_counter()
        plan = PlannerAgent().plan(case.source_goal)
        planning_latency_ms = _elapsed_ms(planning_start)

        matching_start = perf_counter()
        mapped_plan = CapabilityMatchingAgent().match_plan(plan)
        matching_latency_ms = _elapsed_ms(matching_start)

        governance_start = perf_counter()
        GovernanceAgent().evaluate(mapped_plan)
        governance_latency_ms = _elapsed_ms(governance_start)

        return planning_latency_ms, matching_latency_ms, governance_latency_ms


class DirectExecutionWithoutGovernanceBaseline(EvaluationMethod):
    """Baseline A: invoke mapped adapter steps without governance enforcement."""

    method_id = "baseline_a_direct_without_governance"
    method_name = "Baseline A: direct execution without governance"
    description = (
        "Executes mapped adapter calls directly and records malformed executable "
        "mappings as failures instead of governance safe aborts."
    )

    def run(self, case: EvaluationCase) -> ExecutionResult:
        run_start = perf_counter()
        step_results = [
            self._execute_step(step, case.governance_plan.payload)
            for step in case.governance_plan.steps
        ]

        return _execution_result(
            run_id=f"{self.method_id}-{case.governance_plan.goal_id}",
            goal_id=case.governance_plan.goal_id,
            step_results=step_results,
            total_latency_ms=_elapsed_ms(run_start),
            governance_summary=_zero_governance_summary(),
        )

    def run_with_timing(self, case: EvaluationCase) -> MethodRunResult:
        total_start = perf_counter()
        result = self.run(case)
        total_latency_ms = _elapsed_ms(total_start)
        execution_latency_ms = result.total_latency_ms or total_latency_ms
        result.stage_latencies_ms.update(
            {
                "planning": 0.0,
                "matching": 0.0,
                "governance": 0.0,
                "execution": execution_latency_ms,
                "total": total_latency_ms,
            }
        )
        return MethodRunResult(
            case=case,
            result=result,
            stage_latencies_ms=result.stage_latencies_ms,
        )

    def _execute_step(
        self,
        step: GovernanceStepDecision,
        payload: dict[str, Any],
    ) -> StepExecutionResult:
        if step.selected_adapter is None or step.selected_capability is None:
            if step.reason == "invalid_execution_mapping":
                return StepExecutionResult(
                    step_id=step.step_id,
                    title=step.title,
                    status="failed",
                    adapter=step.selected_adapter,
                    capability=step.selected_capability,
                    latency_ms=0.0,
                    error="Missing adapter or capability in direct execution baseline.",
                    notes=step.notes,
                )

            return StepExecutionResult(
                step_id=step.step_id,
                title=step.title,
                status="skipped",
                adapter=step.selected_adapter,
                capability=step.selected_capability,
                latency_ms=0.0,
                notes="Non-executable step skipped by direct baseline.",
            )

        return _invoke_adapter_step(step, payload)


class SingleStageExecutionBaseline(EvaluationMethod):
    """Baseline B: use a one-step heuristic instead of Planner and Matcher."""

    method_id = "baseline_b_single_stage_execution"
    method_name = "Baseline B: single-stage execution"
    description = (
        "Selects one deterministic adapter capability directly from the case "
        "payload, bypassing separate planning and matching stages."
    )

    def __init__(self) -> None:
        self._executor = ExecutionAgent()

    def run(self, case: EvaluationCase) -> ExecutionResult:
        plan = self._single_stage_plan(case)
        return self._executor.run(plan)

    def run_with_timing(self, case: EvaluationCase) -> MethodRunResult:
        total_start = perf_counter()

        planning_start = perf_counter()
        plan = self._single_stage_plan(case)
        planning_latency_ms = _elapsed_ms(planning_start)

        execution_start = perf_counter()
        result = self._executor.run(plan)
        execution_latency_ms = _elapsed_ms(execution_start)
        total_latency_ms = _elapsed_ms(total_start)
        result.stage_latencies_ms.update(
            {
                "planning": planning_latency_ms,
                "matching": 0.0,
                "governance": 0.0,
                "execution": execution_latency_ms,
                "total": total_latency_ms,
            }
        )
        return MethodRunResult(
            case=case,
            result=result,
            stage_latencies_ms=result.stage_latencies_ms,
        )

    def _single_stage_plan(self, case: EvaluationCase) -> GovernanceEvaluation:
        payload = dict(case.governance_plan.payload)
        if "action_name" in payload:
            payload["command_name"] = payload["action_name"]
            selected_adapter = "legacy_adapter"
            selected_capability = "run_legacy_command"
            title = "Run selected action"
        else:
            selected_adapter = "opcua_adapter"
            selected_capability = "read_machine_status"
            title = "Read machine status"

        return GovernanceEvaluation(
            goal_id=case.governance_plan.goal_id,
            goal_type=case.governance_plan.goal_type,
            payload=payload,
            steps=[
                GovernanceStepDecision(
                    step_id="single-stage-001",
                    title=title,
                    decision="ALLOW",
                    reason="single_stage_baseline_selection",
                    selected_adapter=selected_adapter,
                    selected_capability=selected_capability,
                    notes="Baseline bypasses explicit Planner and Matcher stages.",
                ),
            ],
            governance_summary={"allow": 1, **_intervention_zero_counts()},
        )


class NoGovernancePolicyFilteringBaseline(EvaluationMethod):
    """Baseline C: execute matched steps without policy-based filtering."""

    method_id = "baseline_c_without_policy_filtering"
    method_name = "Baseline C: without governance-aware policy filtering"
    description = (
        "Keeps mapped adapter selections but converts policy BLOCK and "
        "REQUIRE_APPROVAL decisions into ALLOW decisions."
    )

    def __init__(self) -> None:
        self._executor = ExecutionAgent()

    def run(self, case: EvaluationCase) -> ExecutionResult:
        return self._executor.run(self._policy_filter_removed_plan(case.governance_plan))

    def run_with_timing(self, case: EvaluationCase) -> MethodRunResult:
        total_start = perf_counter()

        governance_start = perf_counter()
        plan = self._policy_filter_removed_plan(case.governance_plan)
        governance_latency_ms = _elapsed_ms(governance_start)

        execution_start = perf_counter()
        result = self._executor.run(plan)
        execution_latency_ms = _elapsed_ms(execution_start)
        total_latency_ms = _elapsed_ms(total_start)
        result.stage_latencies_ms.update(
            {
                "planning": 0.0,
                "matching": 0.0,
                "governance": governance_latency_ms,
                "execution": execution_latency_ms,
                "total": total_latency_ms,
            }
        )
        return MethodRunResult(
            case=case,
            result=result,
            stage_latencies_ms=result.stage_latencies_ms,
        )

    def _policy_filter_removed_plan(
        self,
        governance_plan: GovernanceEvaluation,
    ) -> GovernanceEvaluation:
        steps = [self._remove_policy_filter(step) for step in governance_plan.steps]
        return GovernanceEvaluation(
            goal_id=governance_plan.goal_id,
            goal_type=governance_plan.goal_type,
            payload=governance_plan.payload,
            steps=steps,
            governance_summary=_summarize_decisions(steps),
        )

    def _remove_policy_filter(
        self,
        step: GovernanceStepDecision,
    ) -> GovernanceStepDecision:
        if step.decision in {"BLOCK", "REQUIRE_APPROVAL", "FALLBACK"}:
            return step.model_copy(
                update={
                    "decision": "ALLOW",
                    "reason": "policy_filter_removed",
                    "notes": "Baseline removes governance-aware policy filtering.",
                }
            )

        return step


def comparison_methods() -> list[EvaluationMethod]:
    """Return the deterministic methods included in comparison reporting."""

    return [
        GovernanceAwareReference(),
        DirectExecutionWithoutGovernanceBaseline(),
        SingleStageExecutionBaseline(),
        NoGovernancePolicyFilteringBaseline(),
    ]


def _invoke_adapter_step(
    step: GovernanceStepDecision,
    payload: dict[str, Any],
) -> StepExecutionResult:
    step_start = perf_counter()
    try:
        adapter = get_adapter(str(step.selected_adapter))
        result = adapter.invoke(str(step.selected_capability), payload)
    except AdapterError as exc:
        return StepExecutionResult(
            step_id=step.step_id,
            title=step.title,
            status="failed",
            adapter=step.selected_adapter,
            capability=step.selected_capability,
            latency_ms=_elapsed_ms(step_start),
            error=str(exc),
            notes=step.notes,
        )

    return StepExecutionResult(
        step_id=step.step_id,
        title=step.title,
        status="executed",
        adapter=step.selected_adapter,
        capability=step.selected_capability,
        latency_ms=_elapsed_ms(step_start),
        result=result,
        notes=step.notes,
    )


def _execution_result(
    run_id: str,
    goal_id: str,
    step_results: list[StepExecutionResult],
    total_latency_ms: float,
    governance_summary: dict[str, int],
) -> ExecutionResult:
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
        run_id=run_id,
        goal_id=goal_id,
        final_status=_final_status(step_results),
        total_latency_ms=total_latency_ms,
        stage_latencies_ms={"execution": total_latency_ms},
        completed_steps=completed_steps,
        failed_steps=failed_steps,
        skipped_steps=skipped_steps,
        governance_summary=governance_summary,
        output={
            step.step_id: step.result
            for step in step_results
            if step.status == "executed" and step.result is not None
        },
        step_results=step_results,
    )


def _final_status(step_results: list[StepExecutionResult]) -> str:
    statuses = [step.status for step in step_results]
    completed_steps = statuses.count("executed")

    if "safe_aborted" in statuses:
        return "safe_aborted"
    if "blocked" in statuses and completed_steps == 0:
        return "blocked"
    if "failed" in statuses and completed_steps == 0:
        return "failed"
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


def _summarize_decisions(
    steps: list[GovernanceStepDecision],
) -> dict[str, int]:
    summary = _zero_governance_summary()
    for step in steps:
        summary[step.decision.lower()] += 1

    return summary


def _zero_governance_summary() -> dict[str, int]:
    return {"allow": 0, **_intervention_zero_counts()}


def _intervention_zero_counts() -> dict[str, int]:
    return {
        "block": 0,
        "require_approval": 0,
        "fallback": 0,
        "safe_abort": 0,
    }


def _elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000, 6)
