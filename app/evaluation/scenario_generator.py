"""Deterministic scaled scenario generation for empirical evaluation."""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

from app.models.governance import GovernanceEvaluation, GovernanceStepDecision

FIXED_SEED = 20260523
SCENARIOS_DIR = Path("data/scenarios")

PROFILE_COUNTS = {
    "default": 120,
    "journal": 240,
    "extended": 500,
}

PROFILE_FILES = {
    "default": SCENARIOS_DIR / "scaled_scenarios_120.json",
    "journal": SCENARIOS_DIR / "scaled_scenarios_240.json",
    "extended": SCENARIOS_DIR / "scaled_scenarios_500.json",
}

WORKFLOW_LENGTHS = ["short", "medium", "long"]
GOVERNANCE_PATTERNS = [
    "all_allow",
    "allow_then_require_approval",
    "allow_then_block",
    "allow_then_safe_abort",
    "mixed_allow_approval_block",
    "mixed_allow_approval_safe_abort",
    "post_approval_valid",
    "post_approval_invalid",
    "post_approval_missing",
    "invalid_mapping",
    "unavailable_capability",
    "malformed_payload",
]
ADAPTER_MIXES = [
    "OPC UA only",
    "REST only",
    "Legacy only",
    "OPC UA + REST",
    "OPC UA + Legacy",
    "REST + Legacy",
    "OPC UA + REST + Legacy",
]
APPROVAL_CONDITIONS = [
    "no approval required",
    "valid approval",
    "invalid approval",
    "missing approval",
    "approval with invalidated mapping",
]
FAILURE_CONDITIONS = [
    "none",
    "unsupported capability",
    "invalid adapter mapping",
    "unavailable capability",
    "malformed payload",
    "safe abort condition",
    "blocked action condition",
]
RUNTIME_PATHS = [
    "reference_v1",
    "langgraph_runtime",
    "baseline_a_direct_without_governance",
    "baseline_b_single_stage_execution",
    "baseline_c_without_policy_filtering",
]

ADAPTER_CAPABILITIES = {
    "OPC UA": [
        ("opcua_adapter", "read_machine_status", "Read machine status"),
        ("opcua_adapter", "read_alarm_code", "Read alarm code"),
    ],
    "REST": [
        ("rest_adapter", "create_maintenance_ticket", "Create maintenance ticket"),
        ("rest_adapter", "query_ticket_status", "Query maintenance ticket"),
    ],
    "Legacy": [
        ("legacy_adapter", "validate_vendor_action", "Validate vendor action"),
        ("legacy_adapter", "run_legacy_command", "Run legacy command"),
    ],
}


def generate_scenarios(profile: str = "default") -> list[dict[str, Any]]:
    """Generate a deterministic, balanced scenario set for a named profile."""

    if profile not in PROFILE_COUNTS:
        raise ValueError(f"Unknown profile '{profile}'. Expected one of {sorted(PROFILE_COUNTS)}.")

    rng = random.Random(FIXED_SEED)
    count = PROFILE_COUNTS[profile]
    raw_indices = list(range(count))
    rng.shuffle(raw_indices)

    scenarios = [
        _build_scenario(scenario_number=index + 1, balance_index=balance_index)
        for index, balance_index in enumerate(raw_indices)
    ]
    scenarios.sort(key=lambda scenario: scenario["scenario_id"])
    return scenarios


def write_scenarios(profile: str = "default") -> Path:
    """Generate and write one profile to its stable JSON artifact path."""

    SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)
    scenarios = generate_scenarios(profile)
    output_path = PROFILE_FILES[profile]
    output_path.write_text(json.dumps(scenarios, indent=2, sort_keys=True), encoding="utf-8")
    return output_path


def load_or_generate_scenarios(profile: str = "default") -> list[dict[str, Any]]:
    """Load a generated profile, creating it first when absent."""

    path = PROFILE_FILES[profile]
    if not path.exists():
        write_scenarios(profile)
    return json.loads(path.read_text(encoding="utf-8"))


def _build_scenario(scenario_number: int, balance_index: int) -> dict[str, Any]:
    workflow_length = WORKFLOW_LENGTHS[balance_index % len(WORKFLOW_LENGTHS)]
    governance_pattern = GOVERNANCE_PATTERNS[balance_index % len(GOVERNANCE_PATTERNS)]
    adapter_mix = ADAPTER_MIXES[(balance_index * 3) % len(ADAPTER_MIXES)]
    approval_condition = _approval_condition(governance_pattern, balance_index)
    failure_condition = _failure_condition(governance_pattern, balance_index)
    step_count = _step_count(workflow_length, balance_index)
    machine_id = f"M-{100 + (balance_index % 900):03d}"
    payload = _payload(machine_id, governance_pattern, balance_index)
    steps = _steps_for_pattern(
        governance_pattern=governance_pattern,
        adapter_mix=adapter_mix,
        failure_condition=failure_condition,
        step_count=step_count,
        balance_index=balance_index,
    )
    expected_sequence = [step.decision for step in steps]
    expected_final_status = _expected_final_status(
        governance_pattern,
        expected_sequence,
        approval_condition,
    )
    expected_decision = (
        "SAFE_ABORT"
        if approval_condition == "approval with invalidated mapping"
        else _dominant_decision(expected_sequence)
    )
    expected_approval_execution_allowed = approval_condition == "valid approval"
    approval_resume_mutation = _approval_resume_mutation(approval_condition, steps)

    governance_plan = GovernanceEvaluation(
        goal_id=f"G-SCALED-{scenario_number:04d}",
        goal_type="scaled_empirical_workflow",
        payload=payload,
        steps=steps,
        governance_summary=_summary_from_steps(steps),
    )

    industrial_context = {
        "cell": f"Cell-{1 + balance_index % 8}",
        "asset": machine_id,
        "operation": _operation_for_pattern(governance_pattern),
        "supervisory_scope": "deterministic research prototype",
        "rami_alignment": "IEC 62264 operations layer / RAMI 4.0 functional layer",
        "interoperability_role": _interoperability_role(adapter_mix),
    }

    return {
        "scenario_id": f"SCN-{scenario_number:04d}",
        "scenario_family": governance_pattern,
        "workflow_length": workflow_length,
        "workflow_step_count": len(steps),
        "governance_pattern": governance_pattern,
        "adapter_mix": adapter_mix,
        "approval_condition": approval_condition,
        "failure_condition": failure_condition,
        "runtime_applicability": list(RUNTIME_PATHS),
        "input_goal": {
            "goal_id": governance_plan.goal_id,
            "goal_type": governance_plan.goal_type,
            "priority": "normal",
            "requested_by": "scaled_evaluation_generator",
            "payload": payload,
        },
        "input_payload": payload,
        "governance_plan": governance_plan.model_dump(),
        "expected_governance_sequence": expected_sequence,
        "expected_governance_decision": expected_decision,
        "expected_final_status": expected_final_status,
        "expected_execution_allowed": _expected_execution_allowed(expected_sequence),
        "expected_policy_compliance": True,
        "expected_trace_markers": _expected_trace_markers(expected_sequence, approval_condition),
        "expected_approval_execution_allowed": expected_approval_execution_allowed
        if "REQUIRE_APPROVAL" in expected_sequence
        else None,
        "approval_payload": _approval_payload(approval_condition),
        "approval_resume_mutation": approval_resume_mutation,
        "industrial_context": industrial_context,
        "rami_alignment": industrial_context["rami_alignment"],
        "interoperability_role": industrial_context["interoperability_role"],
        "deterministic_seed": FIXED_SEED,
    }


def _approval_condition(governance_pattern: str, balance_index: int) -> str:
    if governance_pattern == "post_approval_valid":
        return "valid approval"
    if governance_pattern == "post_approval_invalid":
        return "invalid approval"
    if governance_pattern == "post_approval_missing":
        return "missing approval"
    if governance_pattern in {
        "allow_then_require_approval",
        "mixed_allow_approval_block",
        "mixed_allow_approval_safe_abort",
    }:
        approval_index = (balance_index // len(GOVERNANCE_PATTERNS)) % 4
        return APPROVAL_CONDITIONS[1 + approval_index]
    return "no approval required"


def _failure_condition(governance_pattern: str, balance_index: int) -> str:
    if governance_pattern in {"all_allow", "allow_then_require_approval", "post_approval_valid"}:
        return "none"
    if governance_pattern in {"allow_then_block", "mixed_allow_approval_block"}:
        return "blocked action condition"
    if governance_pattern in {"allow_then_safe_abort", "mixed_allow_approval_safe_abort"}:
        return "safe abort condition"
    if governance_pattern == "invalid_mapping":
        return "invalid adapter mapping"
    if governance_pattern == "unavailable_capability":
        occurrence = balance_index // len(GOVERNANCE_PATTERNS)
        return "unsupported capability" if occurrence % 2 else "unavailable capability"
    if governance_pattern == "malformed_payload":
        return "malformed payload"
    if governance_pattern == "post_approval_invalid":
        return "none"
    if governance_pattern == "post_approval_missing":
        return "none"
    return FAILURE_CONDITIONS[balance_index % len(FAILURE_CONDITIONS)]


def _step_count(workflow_length: str, balance_index: int) -> int:
    if workflow_length == "short":
        return 2
    if workflow_length == "medium":
        return 4 + (balance_index % 2)
    return 7 + (balance_index % 4)


def _payload(machine_id: str, governance_pattern: str, balance_index: int) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "machine_id": machine_id,
        "priority": "normal" if balance_index % 3 else "high",
        "ticket_id": f"MT-{machine_id}-001",
    }
    if "approval" in governance_pattern or "block" in governance_pattern:
        payload["action_name"] = _action_name(governance_pattern, balance_index)
        payload["command_name"] = payload["action_name"]
    if governance_pattern == "malformed_payload":
        payload["malformed_payload_marker"] = True
    return payload


def _action_name(governance_pattern: str, balance_index: int) -> str:
    if "block" in governance_pattern:
        return "shutdown_line"
    return ["reset_alarm", "override_interlock", "change_vendor_mode"][balance_index % 3]


def _steps_for_pattern(
    *,
    governance_pattern: str,
    adapter_mix: str,
    failure_condition: str,
    step_count: int,
    balance_index: int,
) -> list[GovernanceStepDecision]:
    decisions = _decision_sequence(governance_pattern, step_count)
    allow_specs = _allow_specs(adapter_mix)
    steps: list[GovernanceStepDecision] = []

    for step_index, decision in enumerate(decisions, start=1):
        if decision == "ALLOW":
            adapter, capability, title = allow_specs[(step_index + balance_index) % len(allow_specs)]
            reason = "read_only_or_service_capability"
        elif decision == "REQUIRE_APPROVAL":
            adapter, capability, title = (
                "legacy_adapter",
                "validate_vendor_action",
                "Validate governed vendor action",
            )
            reason = "sensitive_vendor_action"
        elif decision == "BLOCK":
            adapter, capability, title = (
                "legacy_adapter",
                "validate_vendor_action",
                "Block forbidden vendor action",
            )
            reason = "forbidden_action_policy"
        else:
            adapter, capability, title, reason = _safe_abort_mapping(failure_condition)

        steps.append(
            GovernanceStepDecision(
                step_id=f"step-{step_index:03d}",
                title=title,
                decision=decision,
                reason=reason,
                selected_adapter=adapter,
                selected_capability=capability,
                notes=f"Scaled deterministic scenario decision: {decision}.",
            )
        )

    return steps


def _decision_sequence(governance_pattern: str, step_count: int) -> list[str]:
    if governance_pattern == "all_allow":
        return ["ALLOW"] * step_count
    if governance_pattern in {"allow_then_require_approval", "post_approval_valid", "post_approval_invalid", "post_approval_missing"}:
        return _with_terminal(step_count, "REQUIRE_APPROVAL")
    if governance_pattern == "allow_then_block":
        return _with_terminal(step_count, "BLOCK")
    if governance_pattern in {"allow_then_safe_abort", "invalid_mapping", "unavailable_capability", "malformed_payload"}:
        return _with_terminal(step_count, "SAFE_ABORT")
    if governance_pattern == "mixed_allow_approval_block":
        return _with_two_terminals(step_count, "REQUIRE_APPROVAL", "BLOCK")
    if governance_pattern == "mixed_allow_approval_safe_abort":
        return _with_two_terminals(step_count, "REQUIRE_APPROVAL", "SAFE_ABORT")
    return ["ALLOW"] * step_count


def _with_terminal(step_count: int, terminal: str) -> list[str]:
    return ["ALLOW"] * max(step_count - 1, 0) + [terminal]


def _with_two_terminals(step_count: int, first_terminal: str, second_terminal: str) -> list[str]:
    if step_count <= 2:
        return [first_terminal, second_terminal]
    middle_index = max(1, step_count // 2)
    decisions = ["ALLOW"] * step_count
    decisions[middle_index - 1] = first_terminal
    decisions[-1] = second_terminal
    return decisions


def _allow_specs(adapter_mix: str) -> list[tuple[str, str, str]]:
    adapter_names = [
        name.strip().removesuffix(" only").strip()
        for name in adapter_mix.split("+")
    ]
    specs: list[tuple[str, str, str]] = []
    for adapter_name in adapter_names:
        specs.extend(ADAPTER_CAPABILITIES[adapter_name])
    return specs or ADAPTER_CAPABILITIES["OPC UA"]


def _safe_abort_mapping(failure_condition: str) -> tuple[str | None, str | None, str, str]:
    if failure_condition == "invalid adapter mapping":
        return None, "read_machine_status", "Abort invalid adapter mapping", "invalid_execution_mapping"
    if failure_condition == "unavailable capability":
        return "opcua_adapter", "capability_not_registered", "Abort unavailable capability", "invalid_execution_mapping"
    if failure_condition == "unsupported capability":
        return "legacy_adapter", "capability_not_supported", "Abort unsupported capability", "invalid_execution_mapping"
    if failure_condition == "malformed payload":
        return "rest_adapter", None, "Abort malformed payload", "malformed_payload"
    return None, None, "Abort unsafe or unmapped action", "invalid_execution_mapping"


def _expected_final_status(
    governance_pattern: str,
    expected_sequence: list[str],
    approval_condition: str,
) -> str:
    if governance_pattern == "post_approval_valid" and approval_condition == "valid approval":
        return "success"
    if approval_condition == "approval with invalidated mapping":
        return "safe_aborted"
    if "SAFE_ABORT" in expected_sequence:
        return "safe_aborted"
    if "BLOCK" in expected_sequence:
        return "blocked" if expected_sequence[0] == "BLOCK" else "partial_success"
    if "REQUIRE_APPROVAL" in expected_sequence:
        return "partial_success"
    return "success"


def _expected_execution_allowed(expected_sequence: list[str]) -> bool:
    return set(expected_sequence) == {"ALLOW"}


def _dominant_decision(expected_sequence: list[str]) -> str:
    for decision in ("SAFE_ABORT", "BLOCK", "REQUIRE_APPROVAL", "FALLBACK", "ALLOW"):
        if decision in expected_sequence:
            return decision
    return "NONE"


def _summary_from_steps(steps: list[GovernanceStepDecision]) -> dict[str, int]:
    summary = {"allow": 0, "block": 0, "require_approval": 0, "fallback": 0, "safe_abort": 0}
    for step in steps:
        summary[step.decision.lower()] += 1
    return summary


def _approval_payload(approval_condition: str) -> dict[str, Any] | None:
    if approval_condition == "valid approval":
        return {
            "approved": True,
            "approved_by": "deterministic_supervisor",
            "approval_token": "APPROVED-SCALED-001",
        }
    if approval_condition == "invalid approval":
        return {
            "approved": False,
            "approved_by": "deterministic_supervisor",
            "approval_token": "REJECTED-SCALED-001",
        }
    if approval_condition == "missing approval":
        return {"approved_by": "deterministic_supervisor"}
    if approval_condition == "approval with invalidated mapping":
        return {
            "approved": True,
            "approved_by": "deterministic_supervisor",
            "approval_token": "APPROVED-SCALED-INVALIDATED",
        }
    return None


def _approval_resume_mutation(
    approval_condition: str,
    steps: list[GovernanceStepDecision],
) -> dict[str, Any] | None:
    if approval_condition == "approval with invalidated mapping":
        approval_step = next((step for step in steps if step.decision == "REQUIRE_APPROVAL"), None)
        if approval_step is not None:
            return {"step_id": approval_step.step_id, "selected_capability": None}
    return None


def _expected_trace_markers(expected_sequence: list[str], approval_condition: str) -> list[str]:
    markers = ["planner_node", "matcher_node", "governance_node", "execution_node", "final_result"]
    if "REQUIRE_APPROVAL" in expected_sequence:
        markers.extend(["approval_interrupt", "approval_resume"])
        if approval_condition == "valid approval":
            markers.extend(["approval_validated", "approved_execution"])
        elif approval_condition == "approval with invalidated mapping":
            markers.append("approval_validated")
        elif approval_condition in {"invalid approval", "missing approval"}:
            markers.append("approval_rejected")
    return markers


def _operation_for_pattern(governance_pattern: str) -> str:
    if "block" in governance_pattern:
        return "forbidden control action containment"
    if "approval" in governance_pattern:
        return "human-gated vendor action"
    if governance_pattern in {"invalid_mapping", "unavailable_capability", "malformed_payload"}:
        return "invalid execution containment"
    return "vendor-agnostic monitoring and service coordination"


def _interoperability_role(adapter_mix: str) -> str:
    return f"adapter orchestration across {adapter_mix}"


def _profile_summary(scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "scenario_count": len(scenarios),
        "seed": FIXED_SEED,
        "workflow_length_counts": dict(Counter(s["workflow_length"] for s in scenarios)),
        "governance_pattern_counts": dict(Counter(s["governance_pattern"] for s in scenarios)),
        "adapter_mix_counts": dict(Counter(s["adapter_mix"] for s in scenarios)),
        "approval_condition_counts": dict(Counter(s["approval_condition"] for s in scenarios)),
        "failure_condition_counts": dict(Counter(s["failure_condition"] for s in scenarios)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic scaled scenarios.")
    parser.add_argument("--profile", choices=sorted(PROFILE_COUNTS), default="default")
    args = parser.parse_args()

    output_path = write_scenarios(args.profile)
    scenarios = load_or_generate_scenarios(args.profile)
    print(json.dumps({"output_path": str(output_path), **_profile_summary(scenarios)}, indent=2))


if __name__ == "__main__":
    main()
