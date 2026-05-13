"""Mock OPC UA adapter for industrial read capabilities."""

from typing import Any

from app.adapters.base import BaseAdapter


class OPCUAAdapter(BaseAdapter):
    """Deterministic mock adapter for OPC UA-style machine reads."""

    adapter_name = "opcua_adapter"
    supported_capabilities = {"read_machine_status", "read_alarm_code"}

    def invoke(self, capability_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Invoke an OPC UA mock read capability."""

        self.ensure_supported(capability_name)
        machine_id = str(payload.get("machine_id", "unknown"))

        if capability_name == "read_machine_status":
            return {
                "adapter_name": self.adapter_name,
                "capability_name": capability_name,
                "result": {
                    "machine_id": machine_id,
                    "status": "running",
                    "last_updated": "2026-05-13T00:00:00Z",
                },
            }

        return {
            "adapter_name": self.adapter_name,
            "capability_name": capability_name,
            "result": {
                "machine_id": machine_id,
                "alarm_code": "ALM-201",
                "severity": "high",
            },
        }
