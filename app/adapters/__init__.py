"""Vendor and system adapters."""

from app.adapters.base import AdapterError, BaseAdapter
from app.adapters.factory import build_adapters, get_adapter
from app.adapters.legacy_adapter import LegacyAdapter
from app.adapters.opcua_adapter import OPCUAAdapter
from app.adapters.rest_adapter import RESTAdapter

__all__ = [
    "AdapterError",
    "BaseAdapter",
    "LegacyAdapter",
    "OPCUAAdapter",
    "RESTAdapter",
    "build_adapters",
    "get_adapter",
]
