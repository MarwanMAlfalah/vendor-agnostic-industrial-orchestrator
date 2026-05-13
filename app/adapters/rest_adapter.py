"""Mock REST adapter for service-oriented capabilities."""

from typing import Any

from app.adapters.base import BaseAdapter


class RESTAdapter(BaseAdapter):
    """Deterministic mock adapter for REST service calls."""

    adapter_name = "rest_adapter"
    supported_capabilities = {"create_maintenance_ticket", "query_ticket_status"}

    def invoke(self, capability_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Invoke a REST-style mock service capability."""

        self.ensure_supported(capability_name)

        if capability_name == "create_maintenance_ticket":
            machine_id = str(payload.get("machine_id", "unknown"))
            priority = str(payload.get("priority", "normal"))
            return {
                "adapter_name": self.adapter_name,
                "capability_name": capability_name,
                "result": {
                    "ticket_id": f"MT-{machine_id}-001",
                    "status": "created",
                    "priority": priority,
                },
            }

        ticket_id = str(payload.get("ticket_id", "unknown"))
        return {
            "adapter_name": self.adapter_name,
            "capability_name": capability_name,
            "result": {
                "ticket_id": ticket_id,
                "status": "in_progress",
            },
        }
