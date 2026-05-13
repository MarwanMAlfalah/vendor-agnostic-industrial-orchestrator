"""Mock legacy adapter for vendor-specific capabilities."""

from typing import Any

from app.adapters.base import BaseAdapter


class LegacyAdapter(BaseAdapter):
    """Deterministic mock adapter that normalizes legacy-style responses."""

    adapter_name = "legacy_adapter"
    supported_capabilities = {"run_legacy_command", "validate_vendor_action"}

    def invoke(self, capability_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Invoke a legacy mock capability and normalize the internal response."""

        self.ensure_supported(capability_name)

        if capability_name == "run_legacy_command":
            legacy_response = {
                "RC": 0,
                "MSG": f"Command {payload.get('command_name', 'unknown')} accepted",
            }
            return self._normalize_run_command(capability_name, legacy_response)

        legacy_response = {
            "VALID_FLG": "Y",
            "WHY": "Action is allowed by mock vendor policy",
        }
        return self._normalize_validation(capability_name, legacy_response)

    def _normalize_run_command(
        self,
        capability_name: str,
        legacy_response: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "adapter_name": self.adapter_name,
            "capability_name": capability_name,
            "result": {
                "accepted": legacy_response.get("RC") == 0,
                "message": str(legacy_response.get("MSG", "")),
            },
        }

    def _normalize_validation(
        self,
        capability_name: str,
        legacy_response: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "adapter_name": self.adapter_name,
            "capability_name": capability_name,
            "result": {
                "valid": legacy_response.get("VALID_FLG") == "Y",
                "reason": str(legacy_response.get("WHY", "")),
            },
        }
