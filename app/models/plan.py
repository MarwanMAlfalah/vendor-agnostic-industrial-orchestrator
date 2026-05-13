"""Planning contracts for deterministic supervisory plans."""

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
    steps: list[PlanStep] = Field(default_factory=list)
