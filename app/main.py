"""FastAPI entrypoint for the industrial orchestrator research prototype."""

from fastapi import FastAPI, HTTPException

from app.config import settings
from app.models.capability import Capability
from app.registry.loader import get_capability_by_name, load_capabilities

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=(
        "A research prototype for a vendor-agnostic multi-agent LLM "
        "orchestrator for industrial operations."
    ),
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Return a minimal health response for local development checks."""

    return {
        "status": "ok",
        "service": "vendor-agnostic-industrial-orchestrator",
        "environment": settings.environment,
    }


@app.get("/capabilities", response_model=list[Capability])
async def list_capabilities() -> list[Capability]:
    """Return all registered adapter capabilities."""

    return load_capabilities()


@app.get("/capabilities/{name}", response_model=Capability)
async def read_capability(name: str) -> Capability:
    """Return one registered capability by name."""

    capability = get_capability_by_name(name)
    if capability is None:
        raise HTTPException(status_code=404, detail="Capability not found")

    return capability
