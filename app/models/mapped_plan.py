"""Mapped execution plan contracts."""

from typing import Any

from pydantic import BaseModel, Field


class MappedPlanStep(BaseModel):
    """A plan step annotated with registry-backed capability matching."""

    step_id: str
    title: str
    intent: str
    required_capability: str | None = None
    matched: bool
    selected_adapter: str | None = None
    selected_capability: str | None = None
    fallback_candidates: list[str] = Field(default_factory=list)
    expected_output: str | None = None
    notes: str | None = None


class MappedPlan(BaseModel):
    """An ordered plan after deterministic capability matching."""

    goal_id: str
    goal_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    steps: list[MappedPlanStep] = Field(default_factory=list)
