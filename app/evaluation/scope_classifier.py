"""Runtime-specific supported/stress scope classification."""

from __future__ import annotations

from typing import Any

STRESS_FAILURES = {
    "unsupported capability",
    "invalid adapter mapping",
    "unavailable capability",
    "malformed payload",
    "safe abort condition",
}

POST_APPROVAL_PATTERNS = {
    "post_approval_valid",
    "post_approval_invalid",
    "post_approval_missing",
}


def classify_runtime_scope(scenario: dict[str, Any], runtime_id: str) -> dict[str, str]:
    """Classify a scenario as supported or stress/out-of-scope for a runtime."""

    governance_pattern = str(scenario["governance_pattern"])
    approval_condition = str(scenario["approval_condition"])
    failure_condition = str(scenario["failure_condition"])
    sequence = list(scenario["expected_governance_sequence"])

    if failure_condition in {"malformed payload", "unsupported capability", "unavailable capability"}:
        return _scope("stress_scope", "Malformed or unavailable capability condition.")

    if runtime_id == "reference_v1":
        if governance_pattern in POST_APPROVAL_PATTERNS:
            return _scope(
                "stress_scope",
                "Post-approval continuation is outside reference_v1 capability scope.",
            )
        if approval_condition == "approval with invalidated mapping":
            return _scope(
                "stress_scope",
                "Resume-time invalidated mapping requires continuation/revalidation support.",
            )
        return _scope("supported_scope", "Scenario is within reference_v1 governance behavior.")

    if runtime_id == "langgraph_runtime":
        if approval_condition == "approval with invalidated mapping":
            return _scope(
                "stress_scope",
                "Invalidated mapping is a revalidation stress case, even though containment is supported.",
            )
        if failure_condition in {"invalid adapter mapping", "safe abort condition"}:
            return _scope("stress_scope", "Invalid mapping and safe-abort cases test containment limits.")
        return _scope("supported_scope", "Scenario is within LangGraph runtime capability scope.")

    if runtime_id == "baseline_a_direct_without_governance":
        if _governance_sensitive(sequence):
            return _scope(
                "stress_scope",
                "Governance-sensitive scenario is an expected failure case for direct execution.",
            )
        return _scope("supported_scope", "Direct all-allow execution is within baseline scope.")

    if runtime_id == "baseline_b_single_stage_execution":
        if governance_pattern == "all_allow":
            return _scope("supported_scope", "Simple all-allow behavior is within single-stage scope.")
        return _scope(
            "stress_scope",
            "Multi-decision or policy-sensitive scenario exceeds single-stage baseline scope.",
        )

    if runtime_id == "baseline_c_without_policy_filtering":
        if "BLOCK" in sequence or "REQUIRE_APPROVAL" in sequence:
            return _scope(
                "stress_scope",
                "Policy-sensitive scenario exposes removed filtering behavior.",
            )
        return _scope("supported_scope", "Non-policy-filtering case is within baseline scope.")

    return _scope("stress_scope", "Unknown runtime capability profile.")


def _governance_sensitive(sequence: list[str]) -> bool:
    return any(decision in sequence for decision in ["BLOCK", "REQUIRE_APPROVAL", "SAFE_ABORT"])


def _scope(scope: str, reason: str) -> dict[str, str]:
    return {"scope": scope, "scope_reason": reason}
