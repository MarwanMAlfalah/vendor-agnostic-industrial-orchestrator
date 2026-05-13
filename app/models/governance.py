"""Governance evaluation contracts."""

from typing import Any, Literal

from pydantic import BaseModel, Field

GovernanceDecision = Literal[
    "ALLOW",
    "BLOCK",
    "REQUIRE_APPROVAL",
    "FALLBACK",
    "SAFE_ABORT",
]


class GovernanceStepDecision(BaseModel):
    """Governance decision for a single mapped plan step."""

    step_id: str
    title: str
    decision: GovernanceDecision
    reason: str
    selected_adapter: str | None = None
    selected_capability: str | None = None
    notes: str | None = None


class GovernanceEvaluation(BaseModel):
    """Governance evaluation for an entire mapped plan."""

    goal_id: str
    goal_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    steps: list[GovernanceStepDecision] = Field(default_factory=list)
    governance_summary: dict[str, int] = Field(default_factory=dict)
