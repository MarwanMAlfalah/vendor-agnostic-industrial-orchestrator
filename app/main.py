"""FastAPI entrypoint for the industrial orchestrator research prototype."""

from fastapi import FastAPI

from app.config import settings

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
