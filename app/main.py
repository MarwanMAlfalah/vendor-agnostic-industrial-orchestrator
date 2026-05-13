"""FastAPI entrypoint for the industrial orchestrator research prototype."""

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.adapters import AdapterError, build_adapters, get_adapter
from app.agents import (
    CapabilityMatchingAgent,
    ExecutionAgent,
    PlannerAgent,
    UnsupportedGoalTypeError,
)
from app.config import settings
from app.models.capability import Capability
from app.models.execution_result import ExecutionResult
from app.models.goal import Goal
from app.models.mapped_plan import MappedPlan
from app.models.plan import Plan
from app.registry import CapabilityRegistryError
from app.registry.loader import get_capability_by_name, load_capabilities

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=(
        "A research prototype for a vendor-agnostic multi-agent LLM "
        "orchestrator for industrial operations."
    ),
)


class AdapterInvocationRequest(BaseModel):
    """Request body for manual adapter invocation."""

    adapter_name: str
    capability_name: str
    payload: dict[str, Any] = Field(default_factory=dict)


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


@app.get("/adapters")
async def list_adapters() -> list[dict[str, Any]]:
    """Return available mock adapters and their supported capabilities."""

    return [
        {
            "adapter_name": adapter.adapter_name,
            "supported_capabilities": sorted(adapter.supported_capabilities),
        }
        for adapter in build_adapters().values()
    ]


@app.post("/adapters/invoke")
async def invoke_adapter(request: AdapterInvocationRequest) -> dict[str, Any]:
    """Invoke a mock adapter capability through the unified interface."""

    try:
        adapter = get_adapter(request.adapter_name)
        return adapter.invoke(request.capability_name, request.payload)
    except AdapterError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/planner/plan", response_model=Plan)
async def create_plan(goal: Goal) -> Plan:
    """Create a deterministic ordered plan from a high-level goal."""

    planner = PlannerAgent()
    try:
        return planner.plan(goal)
    except UnsupportedGoalTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/matcher/match", response_model=MappedPlan)
async def match_plan(plan: Plan) -> MappedPlan:
    """Map a planner-produced plan to registered capabilities."""

    try:
        matcher = CapabilityMatchingAgent()
        return matcher.match_plan(plan)
    except CapabilityRegistryError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/execute/run", response_model=ExecutionResult)
async def run_execution(mapped_plan: MappedPlan) -> ExecutionResult:
    """Execute a mapped plan through selected mock adapters."""

    executor = ExecutionAgent()
    return executor.run(mapped_plan)
