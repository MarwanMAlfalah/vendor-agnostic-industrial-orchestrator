"""Run a deterministic containerized integration demo against mock services."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.agents import CapabilityMatchingAgent, GovernanceAgent, PlannerAgent
from app.models.execution_result import ExecutionResult, StepExecutionResult
from app.models.goal import Goal
from app.models.governance import GovernanceEvaluation, GovernanceStepDecision
from app.models.plan import Plan, PlanStep
from app.observability.tracing import trace_experiment

RESULTS_DIR = Path("data/results")
RESULTS_CSV = RESULTS_DIR / "containerized_integration_results.csv"
SUMMARY_JSON = RESULTS_DIR / "containerized_integration_summary.json"

DEFAULT_ENDPOINTS = {
    "opcua_adapter": "http://localhost:8001",
    "rest_adapter": "http://localhost:8002",
    "legacy_adapter": "http://localhost:8003",
}

ROW_FIELDS = [
    "case_id",
    "description",
    "final_status",
    "expected_final_status",
    "final_outcome_correct",
    "policy_compliant",
    "unsafe_execution",
    "adapter_contract_passed",
    "trace_complete",
    "completed_steps",
    "skipped_steps",
    "failed_steps",
    "latency_ms",
    "executed_capabilities",
]


@dataclass(frozen=True)
class IntegrationCase:
    """A deterministic integration demo case."""

    case_id: str
    description: str
    expected_final_status: str
    expected_trace_markers: set[str]
    goal: Goal | None = None
    plan: Plan | None = None
    unsafe_capabilities: set[str] = field(default_factory=set)


@dataclass
class IntegrationRun:
    """Result bundle for one containerized integration case."""

    case: IntegrationCase
    result: ExecutionResult
    trace: list[str]
    adapter_contract_checks: list[bool]
    latency_ms: float


class HttpJsonClient:
    """Tiny stdlib JSON client used to avoid adding runtime dependencies."""

    def __init__(self, base_url: str, timeout_seconds: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def get(self, path: str) -> dict[str, Any]:
        request = Request(f"{self.base_url}{path}", method="GET")
        return self._send(request)

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        return self._send(request)

    def _send(self, request: Request) -> dict[str, Any]:
        with urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))


class ServiceBackedAdapter:
    """Adapter wrapper that calls a containerized mock service."""

    adapter_name: str
    supported_capabilities: set[str]

    def __init__(self, adapter_name: str, base_url: str) -> None:
        self.adapter_name = adapter_name
        self.client = HttpJsonClient(base_url)

    def health(self) -> bool:
        response = self.client.get("/health")
        return response.get("status") == "ok"

    def invoke(self, capability_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        if capability_name not in self.supported_capabilities:
            raise ValueError(f"{self.adapter_name} does not support {capability_name}")
        response = self._invoke_supported(capability_name, payload)
        if not _adapter_contract_valid(response, self.adapter_name, capability_name):
            raise ValueError(f"Invalid adapter contract response for {capability_name}")
        return response

    def _invoke_supported(self, capability_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class ServiceBackedOPCUAAdapter(ServiceBackedAdapter):
    """Service-backed OPC UA adapter wrapper for the integration demo."""

    supported_capabilities = {"read_machine_status", "read_alarm_code"}

    def __init__(self, base_url: str) -> None:
        super().__init__("opcua_adapter", base_url)

    def _invoke_supported(self, capability_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        machine_id = quote(str(payload.get("machine_id", "unknown")))
        if capability_name == "read_machine_status":
            return self.client.get(f"/machines/{machine_id}/status")
        return self.client.get(f"/machines/{machine_id}/alarm")


class ServiceBackedMaintenanceAdapter(ServiceBackedAdapter):
    """Service-backed REST adapter wrapper for the integration demo."""

    supported_capabilities = {"create_maintenance_ticket", "query_ticket_status"}

    def __init__(self, base_url: str) -> None:
        super().__init__("rest_adapter", base_url)

    def _invoke_supported(self, capability_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        if capability_name == "create_maintenance_ticket":
            return self.client.post(
                "/tickets",
                {
                    "machine_id": str(payload.get("machine_id", "unknown")),
                    "summary": str(payload.get("summary", "Containerized integration demo")),
                    "priority": str(payload.get("priority", "normal")),
                },
            )
        ticket_id = quote(str(payload.get("ticket_id", "unknown")))
        return self.client.get(f"/tickets/{ticket_id}")


class ServiceBackedLegacyAdapter(ServiceBackedAdapter):
    """Service-backed legacy adapter wrapper for the integration demo."""

    supported_capabilities = {"validate_vendor_action", "run_legacy_command"}

    def __init__(self, base_url: str) -> None:
        super().__init__("legacy_adapter", base_url)

    def _invoke_supported(self, capability_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        if capability_name == "validate_vendor_action":
            return self.client.post(
                "/validate-action",
                {
                    "action_name": str(payload.get("action_name", "unknown")),
                    "vendor": str(payload.get("vendor", "mock_vendor")),
                    "payload": dict(payload.get("payload", {})),
                },
            )
        return self.client.post(
            "/run-command",
            {
                "command_name": str(
                    payload.get("command_name", payload.get("action_name", "unknown"))
                ),
                "parameters": dict(payload.get("parameters", {})),
            },
        )


class ServiceBackedIntegrationExecutor:
    """Integration-only executor that routes governed steps to service-backed adapters."""

    def __init__(self, adapters: dict[str, ServiceBackedAdapter]) -> None:
        self.adapters = adapters

    def run(
        self, governance_plan: GovernanceEvaluation
    ) -> tuple[ExecutionResult, list[str], list[bool]]:
        start = perf_counter()
        trace = ["execution_start"]
        contract_checks: list[bool] = []
        step_results: list[StepExecutionResult] = []

        for step in governance_plan.steps:
            step_result = self._execute_step(step, governance_plan.payload, trace, contract_checks)
            step_results.append(step_result)
            if step_result.status in {
                "approval_required",
                "blocked",
                "safe_aborted",
                "fallback_pending",
            }:
                break

        total_latency_ms = _elapsed_ms(start)
        result = ExecutionResult(
            run_id=f"containerized-run-{governance_plan.goal_id}",
            goal_id=governance_plan.goal_id,
            final_status=self._final_status(step_results),
            total_latency_ms=total_latency_ms,
            stage_latencies_ms={"containerized_execution": total_latency_ms},
            completed_steps=sum(1 for step in step_results if step.status == "executed"),
            failed_steps=sum(1 for step in step_results if step.status == "failed"),
            skipped_steps=sum(1 for step in step_results if step.status != "executed"),
            governance_summary=governance_plan.governance_summary,
            output={
                step.step_id: step.result
                for step in step_results
                if step.status == "executed" and step.result is not None
            },
            step_results=step_results,
        )
        trace.append("final_result")
        return result, trace, contract_checks

    def _execute_step(
        self,
        step: GovernanceStepDecision,
        payload: dict[str, Any],
        trace: list[str],
        contract_checks: list[bool],
    ) -> StepExecutionResult:
        if step.decision == "REQUIRE_APPROVAL":
            trace.append("approval_required_stop")
            return _policy_step(step, "approval_required")
        if step.decision == "BLOCK":
            trace.append("blocked_stop")
            return _policy_step(step, "blocked")
        if step.decision == "SAFE_ABORT":
            trace.append("safe_abort_stop")
            return _policy_step(step, "safe_aborted")
        if step.decision == "FALLBACK":
            trace.append("fallback_stop")
            return _policy_step(step, "fallback_pending")
        if step.selected_adapter is None or step.selected_capability is None:
            return _skipped_step(step)

        step_start = perf_counter()
        try:
            adapter = self.adapters[step.selected_adapter]
            response = adapter.invoke(step.selected_capability, payload)
            contract_checks.append(
                _adapter_contract_valid(response, step.selected_adapter, step.selected_capability)
            )
            trace.append(f"service_call:{step.selected_adapter}:{step.selected_capability}")
            return StepExecutionResult(
                step_id=step.step_id,
                title=step.title,
                status="executed",
                adapter=step.selected_adapter,
                capability=step.selected_capability,
                latency_ms=_elapsed_ms(step_start),
                result=response,
                error=None,
                notes=step.notes,
            )
        except (KeyError, ValueError, URLError, TimeoutError) as exc:
            contract_checks.append(False)
            trace.append(f"service_error:{step.selected_adapter}:{step.selected_capability}")
            return StepExecutionResult(
                step_id=step.step_id,
                title=step.title,
                status="failed",
                adapter=step.selected_adapter,
                capability=step.selected_capability,
                latency_ms=_elapsed_ms(step_start),
                result=None,
                error=str(exc),
                notes=step.notes,
            )

    def _final_status(self, step_results: list[StepExecutionResult]) -> str:
        statuses = [step.status for step in step_results]
        completed_steps = statuses.count("executed")
        if "safe_aborted" in statuses:
            return "safe_aborted"
        if "blocked" in statuses and completed_steps == 0:
            return "blocked"
        if "failed" in statuses and completed_steps == 0:
            return "failed"
        if "approval_required" in statuses or "fallback_pending" in statuses:
            return "partial_success"
        if "failed" in statuses:
            return "failed" if completed_steps == 0 else "partial_success"
        return "success"


def run_containerized_integration_demo() -> dict[str, Any]:
    """Run the deterministic integration demo and write result artifacts."""

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    endpoints = _endpoints_from_environment()
    adapters = _service_backed_adapters(endpoints)
    cases = _integration_cases()
    service_health_checks = _wait_for_services(adapters)
    trace_metadata = _trace_metadata(endpoints)

    with trace_experiment(
        "containerized_integration_demo",
        inputs={"case_count": len(cases), "service_topology": trace_metadata["service_topology"]},
        metadata=trace_metadata,
        tags=["integration", "docker_compose", "deterministic"],
    ) as trace:
        runs = [_run_case(case, adapters, service_health_checks) for case in cases]
        rows = [_result_row(run) for run in runs]
        summary = _summary(rows, runs, service_health_checks, trace_metadata)
        _write_outputs(rows, summary)
        trace.add_outputs({"summary": summary, "rows": rows})

    return summary


def _run_case(
    case: IntegrationCase,
    adapters: dict[str, ServiceBackedAdapter],
    service_health_checks: list[bool],
) -> IntegrationRun:
    run_start = perf_counter()
    trace = ["planning_start"]
    plan = case.plan if case.plan is not None else PlannerAgent().plan(case.goal)  # type: ignore[arg-type]
    trace.append("planning_complete")
    mapped_plan = CapabilityMatchingAgent().match_plan(plan)
    trace.append("matching_complete")
    governance_plan = GovernanceAgent().evaluate(mapped_plan)
    trace.append("governance_complete")
    result, execution_trace, adapter_checks = ServiceBackedIntegrationExecutor(adapters).run(
        governance_plan
    )
    trace.extend(execution_trace)
    return IntegrationRun(
        case=case,
        result=result,
        trace=trace,
        adapter_contract_checks=[*service_health_checks, *adapter_checks],
        latency_ms=_elapsed_ms(run_start),
    )


def _integration_cases() -> list[IntegrationCase]:
    timestamp = datetime(2026, 5, 23, tzinfo=UTC)
    return [
        IntegrationCase(
            case_id="INT-001",
            description="Read machine status and alarm through containerized OPC UA mock service.",
            goal=Goal(
                goal_id="INT-001",
                goal_type="alarm_handling",
                priority="normal",
                requested_by="integration-demo",
                timestamp=timestamp,
                payload={"machine_id": "M-101"},
            ),
            expected_final_status="success",
            expected_trace_markers={
                "planning_complete",
                "matching_complete",
                "governance_complete",
                "final_result",
            },
        ),
        IntegrationCase(
            case_id="INT-002",
            description="Create and query a maintenance ticket through containerized REST mock service.",
            plan=Plan(
                goal_id="INT-002",
                goal_type="maintenance_ticket_demo",
                payload={
                    "machine_id": "M-202",
                    "ticket_id": "MT-M-202-001",
                    "summary": "Containerized integration demo alarm follow-up",
                    "priority": "high",
                },
                steps=[
                    PlanStep(
                        step_id="step-001",
                        title="Create maintenance ticket",
                        intent="Create a deterministic ticket through the service-backed REST adapter.",
                        required_capability="create_maintenance_ticket",
                    ),
                    PlanStep(
                        step_id="step-002",
                        title="Query maintenance ticket",
                        intent="Read back deterministic ticket state from the REST service.",
                        required_capability="query_ticket_status",
                    ),
                ],
            ),
            expected_final_status="success",
            expected_trace_markers={
                "service_call:rest_adapter:create_maintenance_ticket",
                "final_result",
            },
        ),
        IntegrationCase(
            case_id="INT-003",
            description="Stop at approval-required governance decision before legacy command execution.",
            goal=Goal(
                goal_id="INT-003",
                goal_type="governed_action",
                priority="normal",
                requested_by="integration-demo",
                timestamp=timestamp,
                payload={
                    "action_name": "reset_alarm",
                    "command_name": "reset_alarm",
                    "machine_id": "M-303",
                    "vendor": "mock_vendor",
                },
            ),
            expected_final_status="partial_success",
            expected_trace_markers={"approval_required_stop", "final_result"},
            unsafe_capabilities={"run_legacy_command"},
        ),
        IntegrationCase(
            case_id="INT-004",
            description="Block a forbidden shutdown action without invoking service-backed adapters.",
            goal=Goal(
                goal_id="INT-004",
                goal_type="governed_action",
                priority="high",
                requested_by="integration-demo",
                timestamp=timestamp,
                payload={
                    "action_name": "shutdown_line",
                    "command_name": "shutdown_line",
                    "machine_id": "M-404",
                    "vendor": "mock_vendor",
                },
            ),
            expected_final_status="blocked",
            expected_trace_markers={"blocked_stop", "final_result"},
            unsafe_capabilities={"validate_vendor_action", "run_legacy_command"},
        ),
        IntegrationCase(
            case_id="INT-005",
            description="Run an already-approved command through the containerized legacy mock service.",
            plan=Plan(
                goal_id="INT-005",
                goal_type="approved_legacy_command_demo",
                payload={
                    "command_name": "acknowledge_alarm",
                    "parameters": {"machine_id": "M-505", "alarm_code": "ALM-201"},
                },
                steps=[
                    PlanStep(
                        step_id="step-001",
                        title="Run approved legacy command",
                        intent="Exercise the service-backed legacy run-command contract.",
                        required_capability="run_legacy_command",
                    )
                ],
            ),
            expected_final_status="success",
            expected_trace_markers={
                "service_call:legacy_adapter:run_legacy_command",
                "final_result",
            },
        ),
    ]


def _endpoints_from_environment() -> dict[str, str]:
    return {
        "opcua_adapter": os.getenv("INTEGRATION_OPCUA_URL", DEFAULT_ENDPOINTS["opcua_adapter"]),
        "rest_adapter": os.getenv(
            "INTEGRATION_MAINTENANCE_URL",
            DEFAULT_ENDPOINTS["rest_adapter"],
        ),
        "legacy_adapter": os.getenv("INTEGRATION_LEGACY_URL", DEFAULT_ENDPOINTS["legacy_adapter"]),
    }


def _service_backed_adapters(endpoints: dict[str, str]) -> dict[str, ServiceBackedAdapter]:
    return {
        "opcua_adapter": ServiceBackedOPCUAAdapter(endpoints["opcua_adapter"]),
        "rest_adapter": ServiceBackedMaintenanceAdapter(endpoints["rest_adapter"]),
        "legacy_adapter": ServiceBackedLegacyAdapter(endpoints["legacy_adapter"]),
    }


def _wait_for_services(
    adapters: dict[str, ServiceBackedAdapter],
    attempts: int = 30,
    sleep_seconds: float = 1.0,
) -> list[bool]:
    latest = [False for _ in adapters]
    for _ in range(attempts):
        latest = []
        for adapter in adapters.values():
            try:
                latest.append(adapter.health())
            except (URLError, TimeoutError):
                latest.append(False)
        if all(latest):
            return latest
        time.sleep(sleep_seconds)
    return latest


def _result_row(run: IntegrationRun) -> dict[str, Any]:
    executed_capabilities = [
        step.capability
        for step in run.result.step_results
        if step.status == "executed" and step.capability is not None
    ]
    unsafe_execution = bool(run.case.unsafe_capabilities.intersection(executed_capabilities))
    trace_complete = run.case.expected_trace_markers.issubset(set(run.trace))
    final_outcome_correct = run.result.final_status == run.case.expected_final_status
    adapter_contract_passed = all(run.adapter_contract_checks)
    policy_compliant = (
        final_outcome_correct and not unsafe_execution and run.result.failed_steps == 0
    )

    return {
        "case_id": run.case.case_id,
        "description": run.case.description,
        "final_status": run.result.final_status,
        "expected_final_status": run.case.expected_final_status,
        "final_outcome_correct": final_outcome_correct,
        "policy_compliant": policy_compliant,
        "unsafe_execution": unsafe_execution,
        "adapter_contract_passed": adapter_contract_passed,
        "trace_complete": trace_complete,
        "completed_steps": run.result.completed_steps,
        "skipped_steps": run.result.skipped_steps,
        "failed_steps": run.result.failed_steps,
        "latency_ms": run.latency_ms,
        "executed_capabilities": ";".join(executed_capabilities),
    }


def _summary(
    rows: list[dict[str, Any]],
    runs: list[IntegrationRun],
    service_health_checks: list[bool],
    trace_metadata: dict[str, Any],
) -> dict[str, Any]:
    latencies = [float(row["latency_ms"]) for row in rows]
    return {
        "integration_case_count": len(rows),
        "adapter_contract_pass_rate": _rate(
            sum(row["adapter_contract_passed"] for row in rows),
            len(rows),
        ),
        "service_health_pass_rate": _rate(sum(service_health_checks), len(service_health_checks)),
        "policy_compliance_rate": _rate(sum(row["policy_compliant"] for row in rows), len(rows)),
        "unsafe_execution_rate": _rate(sum(row["unsafe_execution"] for row in rows), len(rows)),
        "final_outcome_accuracy": _rate(
            sum(row["final_outcome_correct"] for row in rows),
            len(rows),
        ),
        "trace_completeness": _rate(sum(row["trace_complete"] for row in rows), len(rows)),
        "mean_latency_ms": round(mean(latencies), 6) if latencies else 0.0,
        "p95_latency_ms": _percentile(latencies, 95),
        "deterministic": True,
        "deployment_claim": "local docker-compose integration experiment only",
        "service_topology": trace_metadata["service_topology"],
        "langsmith_trace_metadata_preview": trace_metadata,
        "case_trace_markers": {run.case.case_id: run.trace for run in runs},
    }


def _write_outputs(rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    with RESULTS_CSV.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=ROW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")


def _trace_metadata(endpoints: dict[str, str]) -> dict[str, Any]:
    return {
        "deployment_mode": "docker_compose",
        "experiment": "containerized_integration_demo",
        "git_sha": _git_sha(),
        "service_topology": "orchestrator+opcua+rest+legacy",
        "opcua_endpoint": endpoints["opcua_adapter"],
        "maintenance_endpoint": endpoints["rest_adapter"],
        "legacy_endpoint": endpoints["legacy_adapter"],
    }


def _git_sha() -> str:
    env_sha = os.getenv("GIT_SHA")
    if env_sha:
        return env_sha

    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _adapter_contract_valid(
    response: dict[str, Any],
    adapter_name: str,
    capability_name: str,
) -> bool:
    result = response.get("result")
    return (
        response.get("adapter_name") == adapter_name
        and response.get("capability_name") == capability_name
        and isinstance(result, dict)
    )


def _policy_step(step: GovernanceStepDecision, status: str) -> StepExecutionResult:
    return StepExecutionResult(
        step_id=step.step_id,
        title=step.title,
        status=status,
        adapter=step.selected_adapter,
        capability=step.selected_capability,
        latency_ms=0.0,
        result=None,
        error=None,
        notes=f"Integration demo stopped on governance decision {step.decision}.",
    )


def _skipped_step(step: GovernanceStepDecision) -> StepExecutionResult:
    return StepExecutionResult(
        step_id=step.step_id,
        title=step.title,
        status="skipped",
        adapter=step.selected_adapter,
        capability=step.selected_capability,
        latency_ms=0.0,
        result=None,
        error=None,
        notes="Allowed non-executable step skipped in integration demo.",
    )


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = (len(ordered) - 1) * percentile / 100
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return round(ordered[lower] * (1 - weight) + ordered[upper] * weight, 6)


def _elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000, 6)


def main() -> None:
    """Command-line entrypoint."""

    parser = argparse.ArgumentParser(description="Run containerized integration demo.")
    parser.parse_args()
    summary = run_containerized_integration_demo()
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
