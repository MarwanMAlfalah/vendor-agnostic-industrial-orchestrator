"""State contract for the experimental LangGraph runtime."""

from typing import Any, TypedDict


class LangGraphRuntimeState(TypedDict, total=False):
    """Shared state passed between LangGraph runtime nodes."""

    case_id: str
    goal: dict[str, Any] | None
    plan: dict[str, Any] | None
    mapped_plan: dict[str, Any] | None
    governance_plan: dict[str, Any] | None
    evaluation_governance_plan: dict[str, Any] | None
    execution_result: dict[str, Any] | None
    trace: list[str]
    stage_latencies_ms: dict[str, float]
    approval_required: bool
    approval_resumed: bool
    approval_payload: dict[str, Any] | None
    approval_required_step_id: str | None
    approval_state: str | None
    approved_by: str | None
    approval_token: str | None
    resumed_from_interrupt: bool
    approval_validation_error: str | None
    approval_execution_performed: bool
    approval_resume_mutation: dict[str, Any] | None
    controlled_approval_execution: bool
