"""Deterministic legacy-style vendor service for integration demos."""

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(
    title="Mock Legacy Vendor Service",
    description="HTTP façade for deterministic legacy validation and command behavior.",
)


class ValidateActionRequest(BaseModel):
    """Request to validate a vendor-specific action."""

    action_name: str
    vendor: str = "mock_vendor"
    payload: dict[str, Any] = Field(default_factory=dict)


class RunCommandRequest(BaseModel):
    """Request to run an already-approved legacy command."""

    command_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
async def health() -> dict[str, str]:
    """Return service health for compose readiness checks."""

    return {"status": "ok", "service": "mock_legacy_service"}


@app.post("/validate-action")
async def validate_action(request: ValidateActionRequest) -> dict[str, Any]:
    """Validate a deterministic vendor action without executing it."""

    blocked = request.action_name == "shutdown_line"
    return {
        "adapter_name": "legacy_adapter",
        "capability_name": "validate_vendor_action",
        "result": {
            "valid": not blocked,
            "reason": (
                "Action is allowed by containerized mock vendor policy"
                if not blocked
                else "shutdown_line is blocked by containerized mock vendor policy"
            ),
            "vendor": request.vendor,
        },
    }


@app.post("/run-command")
async def run_command(request: RunCommandRequest) -> dict[str, Any]:
    """Run a deterministic legacy command."""

    return {
        "adapter_name": "legacy_adapter",
        "capability_name": "run_legacy_command",
        "result": {
            "accepted": True,
            "message": f"Command {request.command_name} accepted by containerized legacy service",
            "parameters": request.parameters,
        },
    }
