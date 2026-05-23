"""Execution result contract for completed research runs."""

from typing import Any

from pydantic import BaseModel, Field


class StepExecutionResult(BaseModel):
    """Execution outcome for a single mapped plan step."""

    step_id: str
    title: str
    status: str
    adapter: str | None = None
    capability: str | None = None
    latency_ms: float | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    notes: str | None = None


class ExecutionResult(BaseModel):
    """Summary of an orchestration run outcome."""

    run_id: str
    goal_id: str
    final_status: str
    total_latency_ms: float | None = None
    stage_latencies_ms: dict[str, float] = Field(default_factory=dict)
    completed_steps: int = 0
    failed_steps: int = 0
    skipped_steps: int = 0
    governance_summary: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    step_results: list[StepExecutionResult] = Field(default_factory=list)
