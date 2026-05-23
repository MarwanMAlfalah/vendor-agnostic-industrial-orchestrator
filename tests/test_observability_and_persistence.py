"""Tests for optional tracing bootstrap and persisted LangGraph resume."""

from app.evaluation.scenario_cases import load_post_approval_evaluation_cases
from app.langgraph_runtime import LangGraphRuntime
from app.observability.bootstrap import configure_langsmith


def test_langsmith_bootstrap_disabled_without_env(monkeypatch) -> None:
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)

    config = configure_langsmith()

    assert config.enabled is False
    assert "not enabled" in config.reason


def test_langsmith_bootstrap_enabled_with_env(monkeypatch) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "test-key")
    monkeypatch.setenv("LANGSMITH_PROJECT", "test-project")

    config = configure_langsmith()

    assert config.enabled is True
    assert config.project == "test-project"


def test_langgraph_checkpoint_persistence_file_is_created(tmp_path) -> None:
    db_path = tmp_path / "checkpoints.db"
    case = _post_approval_case("CASE-POST-APPROVAL-VALID-001")
    runtime = LangGraphRuntime.with_sqlite_checkpointer(str(db_path))
    try:
        state = runtime.start_case(
            case,
            thread_id="test-checkpoint-file",
            controlled_approval_execution=True,
        )
    finally:
        runtime.close()

    assert "__interrupt__" in state
    assert db_path.exists()
    assert db_path.stat().st_size > 0


def test_workflow_resumes_from_checkpoint_with_same_thread_id(tmp_path) -> None:
    db_path = tmp_path / "checkpoints.db"
    case = _post_approval_case("CASE-POST-APPROVAL-VALID-001")
    thread_id = "test-valid-restart"

    runtime = LangGraphRuntime.with_sqlite_checkpointer(str(db_path))
    try:
        state = runtime.start_case(
            case,
            thread_id=thread_id,
            controlled_approval_execution=True,
        )
        assert "__interrupt__" in state
    finally:
        runtime.close()

    restarted = LangGraphRuntime.with_sqlite_checkpointer(str(db_path))
    try:
        resumed = restarted.resume_case(
            thread_id=thread_id,
            approval_payload=case.approval_payload,
        )
    finally:
        restarted.close()

    assert resumed["approval_state"] == "approved"
    assert resumed["approval_execution_performed"] is True
    assert "approved_execution" in resumed["trace"]


def test_invalid_approval_after_restart_does_not_execute(tmp_path) -> None:
    db_path = tmp_path / "checkpoints.db"
    case = _post_approval_case("CASE-POST-APPROVAL-INVALID-PAYLOAD-001")
    thread_id = "test-invalid-restart"

    runtime = LangGraphRuntime.with_sqlite_checkpointer(str(db_path))
    try:
        runtime.start_case(
            case,
            thread_id=thread_id,
            controlled_approval_execution=True,
        )
    finally:
        runtime.close()

    restarted = LangGraphRuntime.with_sqlite_checkpointer(str(db_path))
    try:
        resumed = restarted.resume_case(
            thread_id=thread_id,
            approval_payload=case.approval_payload,
        )
    finally:
        restarted.close()

    assert resumed["approval_state"] == "approval_invalid"
    assert resumed["approval_execution_performed"] is False
    assert "approval_rejected" in resumed["trace"]


def _post_approval_case(case_id: str):
    return next(
        case
        for case in load_post_approval_evaluation_cases()
        if case.case_id == case_id
    )
