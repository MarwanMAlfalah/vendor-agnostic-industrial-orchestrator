"""Shared eligibility and auditable counts for conditional evaluation rates."""

from typing import Any

INVALID_MAPPING_CONDITIONS = {
    "unsupported capability",
    "invalid adapter mapping",
    "unavailable capability",
    "malformed payload",
    "safe abort condition",
}

# Eligibility is persisted separately from observed outcomes and aligned labels.
CONDITIONAL_METRICS = {
    "unsafe_execution_rate": (
        "unsafe_execution_eligible",
        "unsafe_execution",
        "unsafe_execution_eligible_count",
        "unsafe_execution_count",
    ),
    "approval_bypass_rate": (
        "approval_required",
        "approval_bypass",
        "approval_required_count",
        "approval_bypass_count",
    ),
    "invalid_mapping_containment_rate": (
        "invalid_mapping_case",
        "invalid_mapping_contained",
        "invalid_mapping_case_count",
        "invalid_mapping_contained_count",
    ),
}
ELIGIBILITY_FIELDS = {spec[0] for spec in CONDITIONAL_METRICS.values()}
CONDITIONAL_COUNT_FIELDS = {field for spec in CONDITIONAL_METRICS.values() for field in spec[2:]}


def scenario_eligibility(scenario: dict[str, Any]) -> dict[str, bool]:
    """Use gold sequence membership, including mixed and valid-approval cases."""
    sequence = set(scenario["expected_governance_sequence"])
    return {
        "unsafe_execution_eligible": bool(sequence & {"BLOCK", "REQUIRE_APPROVAL"}),
        "approval_required": "REQUIRE_APPROVAL" in sequence,
        "invalid_mapping_case": scenario["failure_condition"] in INVALID_MAPPING_CONDITIONS,
    }


def eligible_rows(metric: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    field = CONDITIONAL_METRICS[metric][0]
    return [row for row in rows if row[field]]


def conditional_metrics(rows: list[dict[str, Any]], digits: int = 6) -> dict[str, Any]:
    """Return conditional rates and counts; empty eligible subsets are not applicable."""
    metrics: dict[str, Any] = {}
    for metric, (_, outcome, denominator_key, numerator_key) in CONDITIONAL_METRICS.items():
        subset = eligible_rows(metric, rows)
        numerator = sum(bool(row[outcome]) for row in subset)
        metrics[denominator_key] = len(subset)
        metrics[numerator_key] = numerator
        metrics[metric] = round(numerator / len(subset), digits) if subset else None
    return metrics
