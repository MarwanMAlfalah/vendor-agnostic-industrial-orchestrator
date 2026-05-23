"""Capability contract for vendor and system adapter actions."""

from typing import Any

from pydantic import BaseModel, Field


class Capability(BaseModel):
    """A discrete operation exposed by an adapter."""

    capability_name: str
    description: str
    adapter_name: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    policy_tags: list[str] = Field(default_factory=list)
    availability: bool = True
    interoperability_role: str | None = None
    system_level: str | None = None
    rami_alignment: str | None = None
