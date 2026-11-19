"""Opt-in ElCon-EE 2027 adapter: ExecutionAgent -> MaintenanceClient.

Not registered in ``app.adapters.factory``; nothing uses it unless a caller
injects it. It exists to route a real ExecutionAgent step to the simulated
maintenance effect service.

Operation identity is ``{workflow_id}:{step_id}``:

* ``workflow_id`` is the durable workflow identity. By default this is the
  LangGraph ``thread_id`` of the running graph: the key its checkpoints are
  stored under. It is chosen before the graph runs and is reused by recovery of
  the same thread, so it is stable across attempts and distinct across workflow
  instances. It is never generated inside a node.
* ``step_id`` is the plan step identity, supplied by ExecutionAgent through the
  optional ``invoke_step`` hook.

The service binds the operation ID to the request fingerprint (capability +
``machine_id``) on first dispatch.

Without both identities the adapter refuses to dispatch. A lost acknowledgment
(``AcknowledgmentLost``) is deliberately NOT converted into ``AdapterError``.
ExecutionAgent turns an ``AdapterError`` into a ``failed`` step and the node then
completes normally, so the graph would checkpoint a finished execution while an
external effect may have committed. Letting the exception propagate keeps the
execution node incomplete.

Optional ``guard`` (``RecoveryGuard``): when given, the adapter asks it before
every dispatch, records each attempt in the guard's journal BEFORE calling the
service, and carries out the guard's decision:

* DISPATCH / REDISPATCH: submit with the same operation ID and request;
* ADOPT: return the existing ticket without dispatching;
* HOLD: escalate through ``hold`` (default: LangGraph ``interrupt()`` with
  reason ``RECOVERY_HOLD``). The graph pauses with the execution step
  incomplete. An operator resume only makes the guard re-evaluate; it never
  forces a dispatch.

Without a guard the adapter is the unprotected path (blind replay).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langgraph.config import get_config
from langgraph.types import interrupt

from app.adapters.base import AdapterError, BaseAdapter
from app.integration.maintenance_effect_service import MaintenanceClient
from app.integration.recovery_guard import GuardDecision, RecoveryGuard

MAX_HOLD_ROUNDS = 16


class RecoveryHoldUnresolved(RuntimeError):
    """A hold callable kept returning without the guard leaving HOLD."""


def operation_id(workflow_id: str, step_id: str) -> str:
    """Stable logical operation identity for one plan step of one workflow.

    Raises AdapterError (a ValueError) so that ExecutionAgent records a refused
    dispatch instead of the execution node crashing on every replay. ':' is
    rejected in both parts so the encoding is unambiguous.
    """
    for name, value in (("workflow_id", workflow_id), ("step_id", step_id)):
        if not isinstance(value, str) or not value:
            raise AdapterError(f"{name} must be a non-empty string")
        if ":" in value:
            raise AdapterError(f"{name} must not contain ':'")
    return f"{workflow_id}:{step_id}"


def langgraph_thread_id() -> str:
    """The running graph's thread_id; refuses outside a LangGraph run."""
    try:
        config = get_config()
    except RuntimeError as exc:
        raise AdapterError(
            "no LangGraph run context: refusing to dispatch without durable workflow identity"
        ) from exc
    thread_id = config.get("configurable", {}).get("thread_id")
    if not thread_id:
        raise AdapterError("no thread_id: refusing to dispatch without durable workflow identity")
    return str(thread_id)


def langgraph_hold(payload: dict[str, Any]) -> Any:
    """Pause the graph for an operator (genuine human-in-the-loop interrupt)."""
    return interrupt(payload)


class MaintenanceEffectAdapter(BaseAdapter):
    """Create maintenance tickets through the simulated effect service."""

    adapter_name = "maintenance_effect_adapter"
    supported_capabilities = {"create_maintenance_ticket"}
    requires_step_identity = True  # ExecutionAgent opt-in: call invoke_step

    def __init__(
        self,
        client: MaintenanceClient,
        *,
        workflow_id_provider: Callable[[], str] = langgraph_thread_id,
        guard: RecoveryGuard | None = None,
        hold: Callable[[dict[str, Any]], Any] = langgraph_hold,
    ) -> None:
        self._client = client
        self._workflow_id_provider = workflow_id_provider
        self._guard = guard
        self._hold = hold

    def invoke(self, capability_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        raise AdapterError(
            "maintenance_effect_adapter requires step identity; it must be called through "
            "ExecutionAgent's invoke_step hook"
        )

    def invoke_step(
        self,
        capability_name: str,
        payload: dict[str, Any],
        *,
        step_id: str,
    ) -> dict[str, Any]:
        self.ensure_supported(capability_name)
        workflow_id = self._workflow_id_provider()
        op_id = operation_id(workflow_id, step_id)
        machine_id = payload.get("machine_id")
        if not isinstance(machine_id, str) or not machine_id:
            raise AdapterError("create_maintenance_ticket requires a non-empty machine_id")

        if self._guard is None:
            return self._dispatch(capability_name, op_id, machine_id, attempt_id=None)

        def decide() -> GuardDecision:
            return self._guard.decide(
                operation_id=op_id,
                workflow_id=workflow_id,
                step_id=step_id,
                capability=capability_name,
                adapter=self.adapter_name,
                request=payload,
                query=self._client.query,
            )

        # Each HOLD round pauses for an operator. LangGraph replays earlier
        # interrupt() calls on resume, so the cap counts rounds over the
        # operation's lifetime. Exceeding it raises (never success, never a
        # dispatch); the decision after the last permitted round is honoured.
        decision = decide()
        rounds = 0
        while decision.action == "HOLD":
            if rounds == MAX_HOLD_ROUNDS:
                raise RecoveryHoldUnresolved(
                    f"{op_id} still on HOLD after {MAX_HOLD_ROUNDS} rounds"
                )
            rounds += 1
            self._hold(
                {
                    "reason": "RECOVERY_HOLD",
                    "operation_id": op_id,
                    "basis": decision.basis,
                    "message": "Outcome of an earlier dispatch is uncertain; operator required.",
                }
            )
            decision = decide()  # resumed by an operator: re-evaluate, never force

        if decision.action == "ADOPT":
            return {
                "adapter_name": self.adapter_name,
                "capability_name": capability_name,
                "operation_id": op_id,
                "recovery_action": "ADOPT",
                "recovery_basis": decision.basis,
                "result": {"ticket_id": decision.ticket_id, "status": "adopted"},
            }
        attempt_id = self._guard.begin_attempt(op_id)  # durable before the external call
        result = self._dispatch(capability_name, op_id, machine_id, attempt_id=attempt_id)
        result["recovery_action"] = decision.action
        result["recovery_basis"] = decision.basis
        return result

    def _dispatch(
        self, capability_name: str, op_id: str, machine_id: str, *, attempt_id: int | None
    ) -> dict[str, Any]:
        response = self._client.submit(op_id, machine_id)  # AcknowledgmentLost propagates
        if attempt_id is not None:
            self._guard.record_reply(attempt_id, response.status, response.ticket_id)
        if response.status not in {"committed", "deduplicated"}:
            # 'failed' is attempt-scoped (this attempt committed nothing);
            # 'conflict' means the ID is bound to a different request.
            raise AdapterError(f"maintenance service replied '{response.status}' for {op_id}")
        return {
            "adapter_name": self.adapter_name,
            "capability_name": capability_name,
            "operation_id": op_id,
            "result": {"ticket_id": response.ticket_id, "status": response.status},
        }
