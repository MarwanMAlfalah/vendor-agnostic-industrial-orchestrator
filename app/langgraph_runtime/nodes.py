"""LangGraph nodes that reuse the existing deterministic agents."""

from time import perf_counter
from typing import Any

from langgraph.types import interrupt

from app.adapters import AdapterError, get_adapter
from app.agents import (
    CapabilityMatchingAgent,
    ExecutionAgent,
    GovernanceAgent,
    PlannerAgent,
)
from app.langgraph_runtime.state import LangGraphRuntimeState
from app.models.goal import Goal
from app.models.governance import GovernanceEvaluation
from app.models.mapped_plan import MappedPlan
from app.models.plan import Plan
from app.observability.summaries import execution_summary
from app.observability.tracing import trace_experiment


def planner_node(state: LangGraphRuntimeState) -> LangGraphRuntimeState:
    """Run deterministic planning when a source goal is available."""

    start = perf_counter()
    with trace_experiment(
        "planner_node",
        inputs={"case_id": state.get("case_id")},
        metadata={"runtime_id": "langgraph_runtime", "case_id": state.get("case_id")},
        tags=["langgraph_node"],
    ) as trace_handle:
        goal = state.get("goal")
        update: LangGraphRuntimeState = {
            "trace": _append_trace(state, "planner_node"),
        }
        if goal is not None:
            plan = PlannerAgent().plan(Goal.model_validate(goal))
            update["plan"] = plan.model_dump()
            trace_handle.add_outputs({"step_count": len(plan.steps)})
        else:
            trace_handle.add_outputs({"step_count": 0, "used_evaluation_plan": True})

    return _with_latency(state, update, "planning", start)


def matcher_node(state: LangGraphRuntimeState) -> LangGraphRuntimeState:
    """Run deterministic capability matching when a plan is available."""

    start = perf_counter()
    with trace_experiment(
        "matcher_node",
        inputs={"case_id": state.get("case_id")},
        metadata={"runtime_id": "langgraph_runtime", "case_id": state.get("case_id")},
        tags=["langgraph_node"],
    ) as trace_handle:
        plan = state.get("plan")
        update: LangGraphRuntimeState = {
            "trace": _append_trace(state, "matcher_node"),
        }
        if plan is not None:
            mapped_plan = CapabilityMatchingAgent().match_plan(Plan.model_validate(plan))
            update["mapped_plan"] = mapped_plan.model_dump()
            trace_handle.add_outputs({"mapped_steps": len(mapped_plan.steps)})
        else:
            trace_handle.add_outputs({"mapped_steps": 0, "used_evaluation_plan": True})

    return _with_latency(state, update, "matching", start)


def governance_node(state: LangGraphRuntimeState) -> LangGraphRuntimeState:
    """Run governance or reuse the fixed evaluation governance plan."""

    start = perf_counter()
    with trace_experiment(
        "governance_node",
        inputs={"case_id": state.get("case_id")},
        metadata={"runtime_id": "langgraph_runtime", "case_id": state.get("case_id")},
        tags=["langgraph_node"],
    ) as trace_handle:
        evaluation_plan = state.get("evaluation_governance_plan")
        mapped_plan = state.get("mapped_plan")
        if evaluation_plan is not None:
            governance_plan = GovernanceEvaluation.model_validate(evaluation_plan)
        elif mapped_plan is not None:
            governance_plan = GovernanceAgent().evaluate(MappedPlan.model_validate(mapped_plan))
        else:
            state_governance_plan = state.get("governance_plan")
            governance_plan = (
                GovernanceEvaluation.model_validate(state_governance_plan)
                if state_governance_plan is not None
                else None
            )

        if governance_plan is None:
            raise ValueError("LangGraph runtime requires a governance plan before execution.")

        update: LangGraphRuntimeState = {
            "governance_plan": governance_plan.model_dump(),
            "approval_required": any(
                step.decision == "REQUIRE_APPROVAL" for step in governance_plan.steps
            ),
            "approval_required_step_id": _approval_required_step_id(governance_plan),
            "trace": _append_trace(state, "governance_node"),
        }
        trace_handle.add_outputs(
            {
                "governance_summary": governance_plan.governance_summary,
                "approval_required_step_id": update["approval_required_step_id"],
            }
        )
    return _with_latency(state, update, "governance", start)


def execution_node(state: LangGraphRuntimeState) -> LangGraphRuntimeState:
    """Execute the governance plan, pausing through interrupt for approvals."""

    start = perf_counter()
    with trace_experiment(
        "execution_node",
        inputs={"case_id": state.get("case_id")},
        metadata={"runtime_id": "langgraph_runtime", "case_id": state.get("case_id")},
        tags=["langgraph_node"],
    ) as trace_handle:
        governance_plan = state.get("governance_plan")
        if governance_plan is None:
            raise ValueError("LangGraph runtime cannot execute without a governance plan.")
        governance_evaluation = GovernanceEvaluation.model_validate(governance_plan)

        approval_payload: dict[str, Any] | None = state.get("approval_payload")
        if state.get("approval_required") and not state.get("approval_resumed"):
            with trace_experiment(
                "approval_interrupt",
                inputs={"case_id": state.get("case_id")},
                metadata={"runtime_id": "langgraph_runtime", "case_id": state.get("case_id")},
                tags=["approval"],
            ):
                approval_payload = interrupt(
                    {
                        "case_id": state.get("case_id"),
                        "reason": "REQUIRE_APPROVAL",
                        "message": "Human approval checkpoint before governed execution.",
                    }
                )

        trace = state.get("trace", [])
        if approval_payload is not None:
            with trace_experiment(
                "approval_resume",
                inputs={"case_id": state.get("case_id")},
                metadata={"runtime_id": "langgraph_runtime", "case_id": state.get("case_id")},
                tags=["approval"],
            ) as resume_trace:
                resume_trace.add_outputs({"resume_success": True})
            trace = [*trace, "approval_interrupt", "approval_resume"]

        execution_plan = governance_evaluation
        approval_state = state.get("approval_state") or "not_required"
        approval_validation_error = state.get("approval_validation_error")
        approval_execution_performed = False
        approved_by = None
        approval_token = None

        if state.get("controlled_approval_execution") and state.get("approval_required"):
            validation = _validate_approval_payload(approval_payload)
            approved_by = validation.get("approved_by")
            approval_token = validation.get("approval_token")
            if validation["valid"]:
                with trace_experiment(
                    "approval_validated",
                    inputs={"case_id": state.get("case_id")},
                    metadata={"runtime_id": "langgraph_runtime", "case_id": state.get("case_id")},
                    tags=["approval"],
                ) as validation_trace:
                    validation_trace.add_outputs(
                        {"approval_state": "validated", "approved_by": approved_by}
                    )
                trace = [*trace, "approval_validated"]
                mutated_plan = _apply_resume_mutation(
                    governance_evaluation,
                    state.get("approval_resume_mutation"),
                )
                eligible, approval_validation_error = _approval_step_is_still_eligible(
                    mutated_plan,
                    str(state.get("approval_required_step_id")),
                )
                if eligible:
                    execution_plan = _approved_execution_plan(
                        mutated_plan,
                        str(state.get("approval_required_step_id")),
                    )
                    approval_state = "approved"
                    approval_execution_performed = True
                    with trace_experiment(
                        "approved_execution",
                        inputs={"case_id": state.get("case_id")},
                        metadata={"runtime_id": "langgraph_runtime", "case_id": state.get("case_id")},
                        tags=["approval"],
                    ) as approved_trace:
                        approved_trace.add_outputs({"gated_step_executed": True})
                    trace = [*trace, "approved_execution"]
                else:
                    execution_plan = _safe_abort_approval_plan(
                        mutated_plan,
                        str(state.get("approval_required_step_id")),
                        approval_validation_error or "approval_revalidation_failed",
                    )
                    approval_state = "revalidation_failed"
            else:
                approval_state = "approval_invalid"
                approval_validation_error = str(validation["error"])
                trace = [*trace, "approval_rejected"]

        result = ExecutionAgent().run(execution_plan)
        if approval_execution_performed:
            result.governance_summary = governance_evaluation.governance_summary

        with trace_experiment(
            "final_result",
            inputs={"case_id": state.get("case_id")},
            metadata={"runtime_id": "langgraph_runtime", "case_id": state.get("case_id")},
            tags=["langgraph_node"],
        ) as final_trace:
            final_trace.add_outputs(execution_summary(result))

        update: LangGraphRuntimeState = {
            "execution_result": result.model_dump(),
            "approval_payload": approval_payload,
            "approval_resumed": approval_payload is not None
            or state.get("approval_resumed", False),
            "approval_state": approval_state,
            "approved_by": approved_by,
            "approval_token": approval_token,
            "resumed_from_interrupt": approval_payload is not None,
            "approval_validation_error": approval_validation_error,
            "approval_execution_performed": approval_execution_performed,
            "trace": [*trace, "execution_node", "final_result"],
        }
        trace_handle.add_outputs(
            {
                **execution_summary(result),
                "approval_state": approval_state,
                "gated_step_executed": approval_execution_performed,
                "resume_success": approval_payload is not None,
            }
        )
    return _with_latency(state, update, "execution", start)


def _approval_required_step_id(
    governance_plan: GovernanceEvaluation,
) -> str | None:
    approval_step = next(
        (step for step in governance_plan.steps if step.decision == "REQUIRE_APPROVAL"),
        None,
    )
    return approval_step.step_id if approval_step is not None else None


def _validate_approval_payload(
    approval_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    if not approval_payload:
        return {"valid": False, "error": "approval_payload_missing"}

    approval_token = approval_payload.get("approval_token")
    approved_by = approval_payload.get("approved_by")
    if approval_payload.get("approved") is not True:
        return {"valid": False, "error": "approval_not_granted"}
    if not isinstance(approved_by, str) or not approved_by:
        return {"valid": False, "error": "approved_by_missing"}
    if not isinstance(approval_token, str) or not approval_token.startswith("APPROVED-"):
        return {"valid": False, "error": "approval_token_invalid"}

    return {
        "valid": True,
        "approved_by": approved_by,
        "approval_token": approval_token,
    }


def _apply_resume_mutation(
    governance_plan: GovernanceEvaluation,
    mutation: dict[str, Any] | None,
) -> GovernanceEvaluation:
    if not mutation:
        return governance_plan

    step_id = mutation.get("step_id")
    steps = [
        step.model_copy(update={key: value for key, value in mutation.items() if key != "step_id"})
        if step.step_id == step_id
        else step
        for step in governance_plan.steps
    ]
    return governance_plan.model_copy(update={"steps": steps})


def _approval_step_is_still_eligible(
    governance_plan: GovernanceEvaluation,
    step_id: str,
) -> tuple[bool, str | None]:
    step = next((candidate for candidate in governance_plan.steps if candidate.step_id == step_id), None)
    if step is None:
        return False, "approval_step_missing"
    if step.decision != "REQUIRE_APPROVAL" or step.reason != "sensitive_vendor_action":
        return False, "approval_step_not_policy_eligible"
    if step.selected_adapter is None or step.selected_capability is None:
        return False, "invalid_execution_mapping"

    try:
        adapter = get_adapter(step.selected_adapter)
        adapter.ensure_supported(step.selected_capability)
    except AdapterError:
        return False, "invalid_execution_mapping"

    return True, None


def _approved_execution_plan(
    governance_plan: GovernanceEvaluation,
    step_id: str,
) -> GovernanceEvaluation:
    steps = [
        step.model_copy(
            update={
                "decision": "ALLOW",
                "reason": "approved_controlled_continuation",
                "notes": "LangGraph approved continuation after explicit approval.",
            }
        )
        if step.step_id == step_id
        else step
        for step in governance_plan.steps
    ]
    return governance_plan.model_copy(
        update={"steps": steps, "governance_summary": _summary_from_steps(steps)}
    )


def _safe_abort_approval_plan(
    governance_plan: GovernanceEvaluation,
    step_id: str,
    reason: str,
) -> GovernanceEvaluation:
    steps = [
        step.model_copy(
            update={
                "decision": "SAFE_ABORT",
                "reason": reason,
                "notes": "LangGraph blocked approved continuation during revalidation.",
            }
        )
        if step.step_id == step_id
        else step
        for step in governance_plan.steps
    ]
    return governance_plan.model_copy(
        update={"steps": steps, "governance_summary": _summary_from_steps(steps)}
    )


def _summary_from_steps(governance_steps: list[Any]) -> dict[str, int]:
    summary = {
        "allow": 0,
        "block": 0,
        "require_approval": 0,
        "fallback": 0,
        "safe_abort": 0,
    }
    for step in governance_steps:
        summary[step.decision.lower()] += 1

    return summary


def _append_trace(state: LangGraphRuntimeState, node_name: str) -> list[str]:
    return [*state.get("trace", []), node_name]


def _with_latency(
    state: LangGraphRuntimeState,
    update: LangGraphRuntimeState,
    stage: str,
    start: float,
) -> LangGraphRuntimeState:
    latencies = dict(state.get("stage_latencies_ms", {}))
    latencies[stage] = latencies.get(stage, 0.0) + _elapsed_ms(start)
    update["stage_latencies_ms"] = latencies
    return update


def _elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000, 6)
