"""Load and validate capability registry entries."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from app.models.capability import Capability

DEFAULT_REGISTRY_PATH = Path(__file__).with_name("capabilities.yaml")


class CapabilityRegistryError(ValueError):
    """Raised when the capability registry cannot be loaded or validated."""


def load_capabilities(path: Path = DEFAULT_REGISTRY_PATH) -> list[Capability]:
    """Load capability definitions from YAML as validated Capability objects."""

    try:
        raw_registry = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CapabilityRegistryError(f"Unable to read capability registry: {path}") from exc
    except yaml.YAMLError as exc:
        raise CapabilityRegistryError(f"Invalid capability registry YAML: {path}") from exc

    if not isinstance(raw_registry, list):
        raise CapabilityRegistryError("Capability registry must be a YAML list.")

    capabilities: list[Capability] = []
    for index, item in enumerate(raw_registry):
        if not isinstance(item, dict):
            raise CapabilityRegistryError(f"Capability entry at index {index} must be a mapping.")

        try:
            capabilities.append(Capability.model_validate(item))
        except ValidationError as exc:
            raise CapabilityRegistryError(
                f"Invalid capability entry at index {index}: {exc}"
            ) from exc

    return capabilities


def get_capability_by_name(
    capability_name: str,
    capabilities: list[Capability] | None = None,
) -> Capability | None:
    """Find a capability by its registry name."""

    registry = capabilities if capabilities is not None else load_capabilities()
    return next(
        (capability for capability in registry if capability.capability_name == capability_name),
        None,
    )
