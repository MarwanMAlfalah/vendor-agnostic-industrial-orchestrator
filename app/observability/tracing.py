"""Optional tracing context managers for experiments."""

from contextlib import contextmanager, nullcontext
from typing import Any, Iterator

from app.observability.bootstrap import configure_langsmith


@contextmanager
def trace_experiment(
    name: str,
    *,
    inputs: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> Iterator[None]:
    """Trace an experiment block when hosted LangSmith is configured."""

    config = configure_langsmith()
    if not config.enabled:
        with nullcontext():
            yield
        return

    from langsmith.run_helpers import trace

    with trace(
        name,
        run_type="chain",
        inputs=inputs or {},
        metadata={
            **(metadata or {}),
            "langsmith_project": config.project,
            "langsmith_endpoint": config.endpoint,
        },
        tags=tags or [],
        project_name=config.project,
    ):
        yield


def run_metadata(
    *,
    runtime_id: str,
    case_id: str | None = None,
    goal_type: str | None = None,
    governance_category: str | None = None,
    mixed_workflow: bool = False,
    approval_case: bool = False,
) -> dict[str, Any]:
    """Build standard metadata for runtime/evaluation traces."""

    return {
        "runtime_id": runtime_id,
        "case_id": case_id,
        "goal_type": goal_type,
        "governance_category": governance_category,
        "mixed_workflow": mixed_workflow,
        "approval_case": approval_case,
    }
