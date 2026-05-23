"""Graph builder and runtime wrapper for the optional LangGraph experiment."""

from time import perf_counter
from typing import Any
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from app.evaluation.scenario_cases import EvaluationCase
from app.langgraph_runtime.nodes import (
    execution_node,
    governance_node,
    matcher_node,
    planner_node,
)
from app.langgraph_runtime.state import LangGraphRuntimeState
from app.models.execution_result import ExecutionResult
from app.observability.summaries import langgraph_run_summary
from app.observability.tracing import run_metadata, trace_experiment


def build_graph() -> Any:
    """Build the experimental LangGraph pipeline."""

    graph = StateGraph(LangGraphRuntimeState)
    graph.add_node("planner", planner_node)
    graph.add_node("matcher", matcher_node)
    graph.add_node("governance", governance_node)
    graph.add_node("execution", execution_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "matcher")
    graph.add_edge("matcher", "governance")
    graph.add_edge("governance", "execution")
    graph.add_edge("execution", END)
    return graph


class LangGraphRuntime:
    """Optional runtime that executes the same logical stages via LangGraph."""

    def __init__(self, checkpointer: Any | None = None) -> None:
        self._checkpointer_context = None
        self._checkpointer = checkpointer if checkpointer is not None else InMemorySaver()
        self._graph = build_graph().compile(checkpointer=self._checkpointer)

    @classmethod
    def with_sqlite_checkpointer(cls, path: str) -> "LangGraphRuntime":
        """Create a runtime backed by a persistent SQLite checkpoint database."""

        context = SqliteSaver.from_conn_string(path)
        checkpointer = context.__enter__()
        checkpointer.setup()
        runtime = cls(checkpointer=checkpointer)
        runtime._checkpointer_context = context
        return runtime

    def close(self) -> None:
        """Close a persistent checkpointer context if one is open."""

        if self._checkpointer_context is not None:
            self._checkpointer_context.__exit__(None, None, None)
            self._checkpointer_context = None

    def run_case(
        self,
        case: EvaluationCase,
        approval_payload: dict[str, Any] | None = None,
        controlled_approval_execution: bool = False,
    ) -> dict[str, Any]:
        """Run one evaluation case, resuming approval interrupts deterministically."""

        total_start = perf_counter()
        thread_id = f"langgraph-{case.case_id}-{uuid4()}"
        with trace_experiment(
            "langgraph_runtime.run_case",
            inputs={"case_id": case.case_id},
            metadata=run_metadata(
                runtime_id="langgraph_runtime",
                case_id=case.case_id,
                goal_type=case.governance_plan.goal_type,
                governance_category=case.scenario_category,
                mixed_workflow=bool(case.expected_governance_sequence),
                approval_case=case.expected_governance_decision == "REQUIRE_APPROVAL"
                or "REQUIRE_APPROVAL" in (case.expected_governance_sequence or []),
            ),
            tags=["langgraph", "runtime"],
        ) as trace_handle:
            state = self.start_case(
                case,
                thread_id=thread_id,
                controlled_approval_execution=controlled_approval_execution,
            )
            interrupted = "__interrupt__" in state
            resumed = False

            if interrupted:
                resume_payload = approval_payload
                if resume_payload is None and not controlled_approval_execution:
                    resume_payload = {
                        "approved": True,
                        "approved_by": "deterministic_evaluation_runner",
                        "approval_token": "APPROVED-LEGACY-PAUSE-RESUME",
                    }
                state = self.resume_case(thread_id=thread_id, approval_payload=resume_payload)
                resumed = True

            output = self._run_output(
                case=case,
                state=state,
                total_start=total_start,
                interrupted=interrupted,
                resumed=resumed,
                thread_id=thread_id,
            )
            trace_handle.add_outputs(langgraph_run_summary(output))
            return output

    def start_case(
        self,
        case: EvaluationCase,
        *,
        thread_id: str,
        controlled_approval_execution: bool = False,
    ) -> dict[str, Any]:
        """Start a case and return the state, possibly at an interrupt."""

        config = {"configurable": {"thread_id": thread_id}}
        return self._graph.invoke(
            self._initial_state(case, controlled_approval_execution),
            config=config,
        )

    def resume_case(
        self,
        *,
        thread_id: str,
        approval_payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Resume a previously interrupted case with explicit approval input."""

        config = {"configurable": {"thread_id": thread_id}}
        return self._graph.invoke(Command(resume=approval_payload), config=config)

    def _initial_state(
        self,
        case: EvaluationCase,
        controlled_approval_execution: bool,
    ) -> LangGraphRuntimeState:
        return {
            "case_id": case.case_id,
            "goal": case.source_goal.model_dump() if case.source_goal is not None else None,
            "evaluation_governance_plan": case.governance_plan.model_dump(),
            "trace": [],
            "stage_latencies_ms": {},
            "approval_required": False,
            "approval_resumed": False,
            "approval_payload": None,
            "approval_required_step_id": None,
            "approval_state": None,
            "approved_by": None,
            "approval_token": None,
            "resumed_from_interrupt": False,
            "approval_validation_error": None,
            "approval_execution_performed": False,
            "approval_resume_mutation": case.approval_resume_mutation,
            "controlled_approval_execution": controlled_approval_execution,
        }

    def _run_output(
        self,
        *,
        case: EvaluationCase,
        state: dict[str, Any],
        total_start: float,
        interrupted: bool,
        resumed: bool,
        thread_id: str,
    ) -> dict[str, Any]:
        result_data = state.get("execution_result")
        if result_data is None:
            raise ValueError(f"LangGraph case {case.case_id} did not produce a result.")
        result = ExecutionResult.model_validate(result_data)

        stage_latencies = dict(state.get("stage_latencies_ms", {}))
        stage_latencies["total"] = _elapsed_ms(total_start)
        result.stage_latencies_ms.update(stage_latencies)

        return {
            "case": case,
            "result": result,
            "stage_latencies_ms": stage_latencies,
            "trace": state.get("trace", []),
            "interrupted": interrupted,
            "resumed": resumed,
            "approval_state": state.get("approval_state"),
            "approved_by": state.get("approved_by"),
            "approval_token": state.get("approval_token"),
            "approval_validation_error": state.get("approval_validation_error"),
            "approval_execution_performed": state.get("approval_execution_performed", False),
            "approval_required_step_id": state.get("approval_required_step_id"),
            "thread_id": thread_id,
        }


def _elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000, 6)
