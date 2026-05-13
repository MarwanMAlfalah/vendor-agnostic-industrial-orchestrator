"""Goal contract for supervisory orchestration requests."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Goal(BaseModel):
    """A requested operational objective for a future orchestration run."""

    goal_id: str
    goal_type: str
    target: str | None = None
    priority: str
    requested_by: str
    timestamp: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
