"""Adapter factory for mock execution adapters."""

from app.adapters.base import AdapterError, BaseAdapter
from app.adapters.legacy_adapter import LegacyAdapter
from app.adapters.opcua_adapter import OPCUAAdapter
from app.adapters.rest_adapter import RESTAdapter


def build_adapters() -> dict[str, BaseAdapter]:
    """Create the available mock adapters keyed by adapter name."""

    adapters: list[BaseAdapter] = [
        OPCUAAdapter(),
        RESTAdapter(),
        LegacyAdapter(),
    ]
    return {adapter.adapter_name: adapter for adapter in adapters}


def get_adapter(adapter_name: str) -> BaseAdapter:
    """Return a configured adapter by name."""

    adapters = build_adapters()
    adapter = adapters.get(adapter_name)
    if adapter is None:
        raise AdapterError(f"Adapter '{adapter_name}' is not supported.")

    return adapter
