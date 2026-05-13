"""Trace contracts for research run observability."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TraceEvent(BaseModel):
    """A single observable event from a future orchestration run."""

    event_id: str
    run_id: str
    step_id: str | None = None
    agent: str
    action: str
    status: str
    adapter: str | None = None
    timestamp: datetime
    details: dict[str, Any] = Field(default_factory=dict)
    latency_ms: int | None = None
