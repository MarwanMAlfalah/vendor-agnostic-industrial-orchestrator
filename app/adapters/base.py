"""Base adapter contract for mock execution adapters."""

from abc import ABC, abstractmethod
from typing import Any


class AdapterError(ValueError):
    """Raised when an adapter cannot handle a requested invocation."""


class BaseAdapter(ABC):
    """Unified interface shared by all execution adapters."""

    adapter_name: str
    supported_capabilities: set[str]

    @abstractmethod
    def invoke(self, capability_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Invoke a named capability and return a normalized result."""

    def ensure_supported(self, capability_name: str) -> None:
        """Validate that this adapter supports the requested capability."""

        if capability_name not in self.supported_capabilities:
            raise AdapterError(
                f"Capability '{capability_name}' is not supported by {self.adapter_name}."
            )
