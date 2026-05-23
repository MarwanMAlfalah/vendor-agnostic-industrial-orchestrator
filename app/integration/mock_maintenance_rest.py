"""Deterministic maintenance REST service for integration demos."""

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="Mock Maintenance REST Service",
    description="Deterministic ticket creation and query service.",
)

_TICKETS: dict[str, dict[str, Any]] = {}


class TicketCreateRequest(BaseModel):
    """Request to create a deterministic maintenance ticket."""

    machine_id: str
    summary: str = "Containerized integration demo ticket"
    priority: str = "normal"


@app.get("/health")
async def health() -> dict[str, str]:
    """Return service health for compose readiness checks."""

    return {"status": "ok", "service": "mock_maintenance_rest"}


@app.post("/tickets")
async def create_ticket(request: TicketCreateRequest) -> dict[str, Any]:
    """Create or upsert a deterministic ticket for a machine."""

    ticket_id = f"MT-{request.machine_id}-001"
    ticket = {
        "ticket_id": ticket_id,
        "machine_id": request.machine_id,
        "status": "created",
        "priority": request.priority,
        "summary": request.summary,
    }
    _TICKETS[ticket_id] = ticket
    return {
        "adapter_name": "rest_adapter",
        "capability_name": "create_maintenance_ticket",
        "result": ticket,
    }


@app.get("/tickets/{ticket_id}")
async def query_ticket(ticket_id: str) -> dict[str, Any]:
    """Return deterministic ticket state."""

    ticket = _TICKETS.get(
        ticket_id,
        {
            "ticket_id": ticket_id,
            "machine_id": "unknown",
            "status": "in_progress",
            "priority": "normal",
            "summary": "Synthetic ticket created by deterministic query fallback",
        },
    )
    return {
        "adapter_name": "rest_adapter",
        "capability_name": "query_ticket_status",
        "result": {
            **ticket,
            "owner": "maintenance-team-a",
        },
    }
