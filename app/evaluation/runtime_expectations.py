"""Runtime-specific expectations for fair scaled evaluation interpretation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

RESULTS_DIR = Path("data/results")

RUNTIME_CAPABILITY_PROFILES: dict[str, dict[str, Any]] = {
    "reference_v1": {
        "runtime_id": "reference_v1",
        "description": "Reference deterministic governance-aware runtime.",
        "supports": [
            "deterministic planning",
            "capability matching",
            "governance evaluation",
            "governance-aware execution",
            "blocking unsafe actions",
            "safe abort behavior",
            "approval_required stopping behavior",
        ],
        "does_not_support": [
            "controlled post-approval execution",
            "graph-native interrupt/resume",
            "checkpoint persistence",
            "restart-safe continuation",
        ],
        "interpretation_note": (
            "Approval-required steps are expected to stop automatic governed "
            "execution rather than continue through a controlled approval resume."
        ),
    },
    "langgraph_runtime": {
        "runtime_id": "langgraph_runtime",
        "description": "Graph runtime wrapping the deterministic stages with approval continuation.",
        "supports": [
            "deterministic planning",
            "capability matching",
            "governance evaluation",
            "governance-aware execution",
            "controlled post-approval continuation",
            "approval interrupt/resume",
            "checkpoint persistence",
            "restart-safe continuation",
            "graph-native trace markers",
        ],
        "does_not_support": [
            "live PLC execution",
            "certified safety enforcement",
        ],
        "interpretation_note": (
            "Valid approvals may produce success when validation and revalidation pass."
        ),
    },
    "baseline_a_direct_without_governance": {
        "runtime_id": "baseline_a_direct_without_governance",
        "description": "Direct adapter execution baseline without governance enforcement.",
        "supports": ["direct mapped adapter invocation"],
        "does_not_support": [
            "policy filtering",
            "approval validation",
            "approval interrupt/resume",
            "governance trace completeness",
        ],
        "interpretation_note": "Unsafe or policy-bypassing success remains non-compliant.",
    },
    "baseline_b_single_stage_execution": {
        "runtime_id": "baseline_b_single_stage_execution",
        "description": "Single-stage heuristic baseline without planner/matcher separation.",
        "supports": ["single-stage deterministic execution heuristic"],
        "does_not_support": [
            "explicit capability matching",
            "full workflow preservation",
            "approval continuation",
            "governance trace completeness",
        ],
        "interpretation_note": "Reduced architecture is expected to miss many gold outcomes.",
    },
    "baseline_c_without_policy_filtering": {
        "runtime_id": "baseline_c_without_policy_filtering",
        "description": "Baseline that removes policy filtering from matched plans.",
        "supports": ["matched adapter execution without policy filtering"],
        "does_not_support": [
            "blocking unsafe actions",
            "approval gating",
            "policy-compliant governance enforcement",
            "governance trace completeness",
        ],
        "interpretation_note": "Policy-bypassing execution remains non-compliant.",
    },
}


def write_runtime_capability_profiles() -> Path:
    """Write runtime capability profiles to the standard result artifact."""

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / "runtime_capability_profiles.json"
    path.write_text(
        json.dumps(RUNTIME_CAPABILITY_PROFILES, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def runtime_expected_outcome(
    scenario: dict[str, Any],
    runtime_id: str,
) -> dict[str, Any]:
    """Return expected labels for one scenario/runtime pair.

    The global labels remain scenario descriptors. This function adds an
    interpretation layer based on documented runtime capabilities.
    """

    global_final = str(scenario["expected_final_status"])
    global_decision = str(scenario["expected_governance_decision"])
    sequence = list(scenario["expected_governance_sequence"])
    approval_condition = str(scenario["approval_condition"])

    if runtime_id == "reference_v1":
        return _reference_expectation(scenario, sequence)

    if runtime_id == "langgraph_runtime":
        return _langgraph_expectation(scenario, sequence, approval_condition)

    return {
        "aligned_expected_final_status": global_final,
        "aligned_expected_governance_decision": global_decision,
        "expectation_basis": (
            "Baseline expectations keep the global scenario label, but policy "
            "bypass and unsafe execution remain non-compliant."
        ),
        "runtime_supports_expected_behavior": False,
    }


def _reference_expectation(
    scenario: dict[str, Any],
    sequence: list[str],
) -> dict[str, Any]:
    if _requires_controlled_continuation(scenario):
        final_status = _non_continuation_final_status(sequence)
        governance_decision = _dominant_decision(sequence)
        return {
            "aligned_expected_final_status": final_status,
            "aligned_expected_governance_decision": governance_decision,
            "expectation_basis": (
                "reference_v1 supports approval_required stopping behavior, "
                "not controlled post-approval continuation or resume-time "
                "mapping invalidation."
            ),
            "runtime_supports_expected_behavior": True,
        }

    return {
        "aligned_expected_final_status": str(scenario["expected_final_status"]),
        "aligned_expected_governance_decision": str(scenario["expected_governance_decision"]),
        "expectation_basis": "Global label is within reference_v1 capability scope.",
        "runtime_supports_expected_behavior": True,
    }


def _langgraph_expectation(
    scenario: dict[str, Any],
    sequence: list[str],
    approval_condition: str,
) -> dict[str, Any]:
    if "REQUIRE_APPROVAL" in sequence and approval_condition == "valid approval":
        if "SAFE_ABORT" in sequence:
            final_status = "safe_aborted"
            decision = "SAFE_ABORT"
        elif "BLOCK" in sequence:
            final_status = "partial_success"
            decision = "BLOCK"
        else:
            final_status = "success"
            decision = _dominant_decision(sequence)
        return {
            "aligned_expected_final_status": final_status,
            "aligned_expected_governance_decision": decision,
            "expectation_basis": (
                "langgraph_runtime supports controlled continuation after "
                "valid approval and revalidation."
            ),
            "runtime_supports_expected_behavior": True,
        }

    if approval_condition == "approval with invalidated mapping":
        return {
            "aligned_expected_final_status": "safe_aborted",
            "aligned_expected_governance_decision": "SAFE_ABORT",
            "expectation_basis": (
                "langgraph_runtime revalidates approved steps and should safe "
                "abort when the mapping is invalidated."
            ),
            "runtime_supports_expected_behavior": True,
        }

    return {
        "aligned_expected_final_status": str(scenario["expected_final_status"]),
        "aligned_expected_governance_decision": str(scenario["expected_governance_decision"]),
        "expectation_basis": "Global label is within langgraph_runtime capability scope.",
        "runtime_supports_expected_behavior": True,
    }


def _requires_controlled_continuation(scenario: dict[str, Any]) -> bool:
    return (
        "REQUIRE_APPROVAL" in scenario["expected_governance_sequence"]
        and scenario["approval_condition"]
        in {
            "valid approval",
            "invalid approval",
            "missing approval",
            "approval with invalidated mapping",
        }
    )


def _non_continuation_final_status(sequence: list[str]) -> str:
    if "SAFE_ABORT" in sequence:
        return "safe_aborted"
    if "BLOCK" in sequence:
        return "blocked" if sequence[0] == "BLOCK" else "partial_success"
    if "REQUIRE_APPROVAL" in sequence:
        return "partial_success"
    return "success"


def _dominant_decision(sequence: list[str]) -> str:
    for decision in ["SAFE_ABORT", "BLOCK", "REQUIRE_APPROVAL", "FALLBACK", "ALLOW"]:
        if decision in sequence:
            return decision
    return "NONE"
