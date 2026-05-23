"""Optional tracing context managers for experiments."""

from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from typing import Any, Iterator

from app.observability.bootstrap import configure_langsmith


@dataclass
class TraceHandle:
    """Small adapter over LangSmith RunTree outputs."""

    run_tree: Any | None = None

    def add_outputs(self, outputs: dict[str, Any]) -> None:
        """Attach structured outputs when tracing is active."""

        if self.run_tree is not None:
            self.run_tree.add_outputs(outputs)


@contextmanager
def trace_experiment(
    name: str,
    *,
    inputs: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> Iterator[TraceHandle]:
    """Trace an experiment block when hosted LangSmith is configured."""

    config = configure_langsmith()
    if not config.enabled:
        with nullcontext():
            yield TraceHandle()
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
    ) as run_tree:
        yield TraceHandle(run_tree)


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
