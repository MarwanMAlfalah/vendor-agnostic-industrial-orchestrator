"""Deterministic mock OPC UA-style HTTP service for integration demos."""

from typing import Any

from fastapi import FastAPI

app = FastAPI(
    title="Mock OPC UA Integration Service",
    description="HTTP façade for deterministic OPC UA-style machine reads.",
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Return service health for compose readiness checks."""

    return {"status": "ok", "service": "mock_opcua_server"}


@app.get("/machines/{machine_id}/status")
async def read_machine_status(machine_id: str) -> dict[str, Any]:
    """Return deterministic machine state."""

    return {
        "adapter_name": "opcua_adapter",
        "capability_name": "read_machine_status",
        "result": {
            "machine_id": machine_id,
            "status": "running",
            "last_updated": "2026-05-23T00:00:00Z",
            "source": "containerized_mock_opcua",
        },
    }


@app.get("/machines/{machine_id}/alarm")
async def read_alarm_code(machine_id: str) -> dict[str, Any]:
    """Return deterministic alarm telemetry."""

    return {
        "adapter_name": "opcua_adapter",
        "capability_name": "read_alarm_code",
        "result": {
            "machine_id": machine_id,
            "alarm_code": "ALM-201",
            "severity": "high",
            "source": "containerized_mock_opcua",
        },
    }
