"""Execution result contract for completed research runs."""

from typing import Any

from pydantic import BaseModel, Field


class ExecutionResult(BaseModel):
    """Summary of a future orchestration run outcome."""

    run_id: str
    goal_id: str
    final_status: str
    total_latency_ms: int | None = None
    completed_steps: int = 0
    failed_steps: int = 0
    governance_summary: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
