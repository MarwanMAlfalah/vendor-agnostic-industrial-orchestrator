"""Planning contracts for deterministic supervisory plans."""

from typing import Any

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    """A single machine-usable and human-readable planning step."""

    step_id: str
    title: str
    intent: str
    required_capability: str | None = None
    expected_output: str | None = None
    notes: str | None = None


class Plan(BaseModel):
    """An ordered plan generated from a high-level goal."""

    goal_id: str
    goal_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    steps: list[PlanStep]
