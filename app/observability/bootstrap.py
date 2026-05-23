"""Hosted LangSmith bootstrap helpers."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LangSmithConfig:
    """Resolved optional LangSmith tracing configuration."""

    enabled: bool
    project: str | None
    endpoint: str | None
    reason: str


def configure_langsmith() -> LangSmithConfig:
    """Configure hosted LangSmith tracing from environment variables if enabled."""

    tracing_enabled = os.getenv("LANGSMITH_TRACING", "").lower() in {
        "1",
        "true",
        "yes",
    }
    api_key = os.getenv("LANGSMITH_API_KEY")
    project = os.getenv("LANGSMITH_PROJECT")
    endpoint = os.getenv("LANGSMITH_ENDPOINT")

    if not tracing_enabled:
        return LangSmithConfig(
            enabled=False,
            project=project,
            endpoint=endpoint,
            reason="LANGSMITH_TRACING is not enabled.",
        )

    if not api_key:
        return LangSmithConfig(
            enabled=False,
            project=project,
            endpoint=endpoint,
            reason="LANGSMITH_API_KEY is missing.",
        )

    if project:
        os.environ["LANGSMITH_PROJECT"] = project

    if endpoint:
        os.environ["LANGSMITH_ENDPOINT"] = endpoint

    return LangSmithConfig(
        enabled=True,
        project=project,
        endpoint=endpoint,
        reason="Hosted LangSmith tracing is enabled.",
    )
