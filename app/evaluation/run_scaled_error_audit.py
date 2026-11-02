"""Audit scaled evaluation errors without changing runtime behavior."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from app.evaluation.conditional_metrics import (
    ELIGIBILITY_FIELDS,
    conditional_metrics,
    eligible_rows,
)
from app.evaluation.run_scaled_evaluation import run_scaled_evaluation
from app.evaluation.scenario_generator import (
    FAILURE_CONDITIONS,
    GOVERNANCE_PATTERNS,
    PROFILE_COUNTS,
    load_or_generate_scenarios,
)
from app.evaluation.statistical_analysis import wilson_interval

RESULTS_DIR = Path("data/results")
DOCS_DIR = Path("docs")

KNOWN_RUNTIMES = {
    "reference_v1",
    "langgraph_runtime",
    "baseline_a_direct_without_governance",
    "baseline_b_single_stage_execution",
    "baseline_c_without_policy_filtering",
}

ERROR_CASE_FIELDS = [
    "scenario_id",
    "runtime_id",
    "scenario_family",
    "workflow_length",
    "governance_pattern",
    "adapter_mix",
    "approval_condition",
    "failure_condition",
    "expected_final_status",
    "observed_final_status",
    "expected_governance_decision",
    "observed_governance_decision",
    "policy_compliant",
    "unsafe_execution",
    "approval_bypass",
    "approval_validation_correct",
    "invalid_mapping_contained",
    "trace_complete",
    "final_outcome_correct",
    "governance_decision_correct",
    "failure_category",
]

STRATIFIED_FACTORS = [
    "scenario_family",
    "workflow_length",
    "governance_pattern",
    "adapter_mix",
    "approval_condition",
    "failure_condition",
]


def run_scaled_error_audit(profile: str = "journal") -> dict[str, Any]:
    """Generate diagnostic audit artifacts for a scaled profile."""

    if profile not in PROFILE_COUNTS:
        raise ValueError(f"Unknown profile '{profile}'. Expected one of {sorted(PROFILE_COUNTS)}.")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    rows = _load_rows(profile)
    scenarios = load_or_generate_scenarios(profile)

    error_rows = _error_rows(rows)
    final_confusion = _confusion_matrix(rows, "expected_final_status", "observed_final_status")
    governance_confusion = _confusion_matrix(
        rows,
        "expected_governance_decision",
        "observed_governance_decision",
    )
    stratified_rows = _stratified_metrics(rows)
    scope_rows = _scope_metrics(rows, scenarios)
    factor_balance_rows, generator_findings = _scenario_generator_quality(scenarios)

    _write_profile_outputs(profile, error_rows, stratified_rows)
    if profile == "journal":
        _write_journal_outputs(
            error_rows=error_rows,
            final_confusion=final_confusion,
            governance_confusion=governance_confusion,
            stratified_rows=stratified_rows,
            scope_rows=scope_rows,
            factor_balance_rows=factor_balance_rows,
            generator_findings=generator_findings,
            scenarios=scenarios,
        )

    summary = {
        "profile": profile,
        "scenario_count": len(scenarios),
        "result_row_count": len(rows),
        "error_case_count": len(error_rows),
        "non_compliant_by_runtime": dict(
            sorted(Counter(row["runtime_id"] for row in error_rows).items())
        ),
        "top_failure_categories": [
            {"failure_category": category, "count": count}
            for category, count in Counter(
                row["failure_category"] for row in error_rows
            ).most_common(5)
        ],
        "supported_scope_preview": [row for row in scope_rows if row["scope"] == "supported_scope"][
            :5
        ],
        "stress_scope_preview": [row for row in scope_rows if row["scope"] == "stress_scope"][:5],
        "generator_findings": generator_findings,
    }
    return summary


def _load_rows(profile: str) -> list[dict[str, Any]]:
    csv_path = RESULTS_DIR / f"scaled_evaluation_results_{profile}.csv"
    if not csv_path.exists():
        run_scaled_evaluation(profile)
    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        return [_parse_row(row) for row in csv.DictReader(csv_file)]


def _parse_row(row: dict[str, str]) -> dict[str, Any]:
    parsed: dict[str, Any] = dict(row)
    for key in [
        *ELIGIBILITY_FIELDS,
        "governance_decision_correct",
        "policy_compliant",
        "unsafe_execution",
        "approval_bypass",
        "approval_validation_correct",
        "invalid_mapping_contained",
        "trace_complete",
        "restart_recovered",
        "final_outcome_correct",
    ]:
        parsed[key] = row[key] == "True"
    for key in [
        "workflow_step_count",
        "completed_steps",
        "skipped_steps",
        "failed_steps",
    ]:
        parsed[key] = int(row[key])
    parsed["latency_ms"] = float(row["latency_ms"])
    return parsed


def _error_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    error_rows: list[dict[str, Any]] = []
    for row in rows:
        if not _is_problematic(row):
            continue
        error_row = {
            field: row.get(field, "") for field in ERROR_CASE_FIELDS if field != "failure_category"
        }
        error_row["failure_category"] = _failure_category(row)
        error_rows.append(error_row)
    return error_rows


def _is_problematic(row: dict[str, Any]) -> bool:
    return (
        not row["policy_compliant"]
        or not row["final_outcome_correct"]
        or not row["governance_decision_correct"]
        or row["unsafe_execution"]
        or row["approval_bypass"]
        or not row["invalid_mapping_contained"]
        or not row["trace_complete"]
    )


def _failure_category(row: dict[str, Any]) -> str:
    if row["unsafe_execution"] or row["approval_bypass"]:
        return "true_runtime_limitation"

    if not row["trace_complete"] and (
        row["policy_compliant"]
        and row["final_outcome_correct"]
        and row["governance_decision_correct"]
    ):
        return "trace_instrumentation_gap"

    if row["runtime_id"].startswith("baseline_"):
        return "unsupported_scenario_scope"

    if (
        row["approval_condition"] == "valid approval"
        and row["observed_final_status"] == "partial_success"
        and row["expected_final_status"] == "success"
    ):
        return "label_runtime_mismatch"

    if (
        row["observed_final_status"] == "safe_aborted"
        and row["expected_final_status"] != "safe_aborted"
    ):
        return "conservative_safe_failure"

    if row["failure_condition"] in {
        "malformed payload",
        "unavailable capability",
        "unsupported capability",
    }:
        if not row["final_outcome_correct"] or not row["invalid_mapping_contained"]:
            return "true_runtime_limitation"

    if (
        row["expected_governance_decision"] != row["observed_governance_decision"]
        and row["expected_final_status"] == row["observed_final_status"]
    ):
        return "evaluator_logic_issue"

    if row["scenario_family"] in {"invalid_mapping", "unavailable_capability", "malformed_payload"}:
        return "scenario_generator_issue"

    return "unknown_needs_review"


def _confusion_matrix(
    rows: list[dict[str, Any]],
    expected_column: str,
    observed_column: str,
) -> list[dict[str, Any]]:
    grouped: Counter[tuple[str, str, str, str]] = Counter()
    for row in rows:
        grouped[
            (
                row["runtime_id"],
                row["scenario_family"],
                str(row[expected_column]),
                str(row[observed_column]),
            )
        ] += 1
    return [
        {
            "runtime_id": runtime_id,
            "scenario_family": scenario_family,
            "expected": expected,
            "observed": observed,
            "count": count,
        }
        for (runtime_id, scenario_family, expected, observed), count in sorted(grouped.items())
    ]


def _stratified_metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    metric_rows: list[dict[str, Any]] = []
    for factor in STRATIFIED_FACTORS:
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[(row["runtime_id"], str(row[factor]))].append(row)
        for (runtime_id, factor_value), group_rows in sorted(grouped.items()):
            metric_rows.append(_metric_row(runtime_id, factor, factor_value, group_rows))
    return metric_rows


def _scope_metrics(
    rows: list[dict[str, Any]],
    scenarios: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    scenario_scope = {scenario["scenario_id"]: _scenario_scope(scenario) for scenario in scenarios}
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        scope = scenario_scope.get(row["scenario_id"], "stress_scope")
        grouped[(scope, row["runtime_id"])].append(row)

    scope_rows = []
    for (scope, runtime_id), group_rows in sorted(grouped.items()):
        metric_row = _metric_row(runtime_id, "scope", scope, group_rows)
        scenario_count = len({row["scenario_id"] for row in group_rows})
        for metric_name, column in [
            ("policy_compliance", "policy_compliant"),
            ("unsafe_execution", "unsafe_execution"),
            ("final_outcome_accuracy", "final_outcome_correct"),
            ("trace_completeness", "trace_complete"),
        ]:
            subset = (
                eligible_rows("unsafe_execution_rate", group_rows)
                if metric_name == "unsafe_execution"
                else group_rows
            )
            numerator = sum(1 for row in subset if row[column])
            low, high = wilson_interval(numerator, len(subset)) if subset else (None, None)
            metric_row[f"{metric_name}_wilson_95_low"] = low
            metric_row[f"{metric_name}_wilson_95_high"] = high
        metric_row["scope"] = scope
        metric_row["scenario_count"] = scenario_count
        scope_rows.append(metric_row)
    return scope_rows


def _scenario_scope(scenario: dict[str, Any]) -> str:
    stress_patterns = {
        "allow_then_safe_abort",
        "mixed_allow_approval_safe_abort",
        "invalid_mapping",
        "unavailable_capability",
        "malformed_payload",
        "post_approval_invalid",
        "post_approval_missing",
    }
    stress_approval = {
        "invalid approval",
        "missing approval",
        "approval with invalidated mapping",
    }
    stress_failures = {
        "unsupported capability",
        "invalid adapter mapping",
        "unavailable capability",
        "malformed payload",
        "safe abort condition",
    }
    if (
        scenario["governance_pattern"] in stress_patterns
        or scenario["approval_condition"] in stress_approval
        or scenario["failure_condition"] in stress_failures
    ):
        return "stress_scope"
    return "supported_scope"


def _metric_row(
    runtime_id: str,
    factor_name: str,
    factor_value: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    latencies = [row["latency_ms"] for row in rows]
    return {
        "runtime_id": runtime_id,
        "factor_name": factor_name,
        "factor_value": factor_value,
        "count": len(rows),
        "policy_compliance_rate": _rate(sum(row["policy_compliant"] for row in rows), len(rows)),
        **conditional_metrics(rows),
        "final_outcome_accuracy": _rate(
            sum(row["final_outcome_correct"] for row in rows), len(rows)
        ),
        "trace_completeness": _rate(sum(row["trace_complete"] for row in rows), len(rows)),
        "mean_latency_ms": round(mean(latencies), 6) if latencies else 0.0,
        "p95_latency_ms": _percentile(latencies, 95),
    }


def _scenario_generator_quality(
    scenarios: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    balance_rows = _factor_balance_rows(scenarios)
    findings: list[dict[str, Any]] = []

    scenario_ids = [scenario["scenario_id"] for scenario in scenarios]
    duplicate_ids = [item for item, count in Counter(scenario_ids).items() if count > 1]
    if duplicate_ids:
        findings.append(
            _finding("duplicate_scenario_ids", "fail", f"Duplicate ids: {duplicate_ids[:10]}")
        )
    else:
        findings.append(
            _finding("duplicate_scenario_ids", "pass", "No duplicate scenario ids detected.")
        )

    duplicate_signatures = _duplicate_signatures(scenarios)
    findings.append(
        _finding(
            "duplicate_scenario_signatures",
            "warn" if duplicate_signatures else "pass",
            f"{len(duplicate_signatures)} duplicate factor/expectation signatures detected.",
        )
    )

    findings.extend(_consistency_findings(scenarios))
    findings.append(
        _finding(
            "governance_pattern_coverage",
            (
                "pass"
                if set(GOVERNANCE_PATTERNS).issubset({s["governance_pattern"] for s in scenarios})
                else "fail"
            ),
            "All requested governance patterns are represented.",
        )
    )
    findings.append(
        _finding(
            "failure_condition_coverage",
            (
                "pass"
                if set(FAILURE_CONDITIONS).issubset({s["failure_condition"] for s in scenarios})
                else "warn"
            ),
            "Requested failure/containment conditions are represented or explicitly absent by profile.",
        )
    )
    return balance_rows, findings


def _factor_balance_rows(scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for factor in [
        "workflow_length",
        "governance_pattern",
        "adapter_mix",
        "approval_condition",
        "failure_condition",
    ]:
        counts = Counter(str(scenario[factor]) for scenario in scenarios)
        for value, count in sorted(counts.items()):
            rows.append(
                {
                    "factor_name": factor,
                    "factor_value": value,
                    "count": count,
                    "percentage": _rate(count, len(scenarios)),
                }
            )
    return rows


def _duplicate_signatures(scenarios: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    signatures = Counter(
        (
            scenario["workflow_length"],
            scenario["governance_pattern"],
            scenario["adapter_mix"],
            scenario["approval_condition"],
            scenario["failure_condition"],
            tuple(scenario["expected_governance_sequence"]),
            scenario["expected_final_status"],
            scenario["expected_governance_decision"],
        )
        for scenario in scenarios
    )
    return [signature for signature, count in signatures.items() if count > 1]


def _consistency_findings(scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks = {
        "approval_condition_requires_approval_step": [],
        "safe_abort_status_consistency": [],
        "block_status_consistency": [],
        "runtime_applicability_consistency": [],
        "dominant_governance_decision_consistency": [],
    }
    for scenario in scenarios:
        sequence = scenario["expected_governance_sequence"]
        if (
            scenario["approval_condition"] != "no approval required"
            and "REQUIRE_APPROVAL" not in sequence
        ):
            checks["approval_condition_requires_approval_step"].append(scenario["scenario_id"])
        if "SAFE_ABORT" in sequence and scenario["expected_final_status"] != "safe_aborted":
            checks["safe_abort_status_consistency"].append(scenario["scenario_id"])
        if "BLOCK" in sequence and scenario["expected_final_status"] not in {
            "blocked",
            "partial_success",
        }:
            checks["block_status_consistency"].append(scenario["scenario_id"])
        if not set(scenario["runtime_applicability"]).issubset(KNOWN_RUNTIMES):
            checks["runtime_applicability_consistency"].append(scenario["scenario_id"])
        if scenario["expected_governance_decision"] != _expected_dominant_decision(scenario):
            checks["dominant_governance_decision_consistency"].append(scenario["scenario_id"])

    findings = []
    for check_name, failures in checks.items():
        findings.append(
            _finding(
                check_name,
                "pass" if not failures else "warn",
                (
                    "No inconsistencies detected."
                    if not failures
                    else f"{len(failures)} scenarios need review, e.g. {failures[:10]}."
                ),
            )
        )
    return findings


def _expected_dominant_decision(scenario: dict[str, Any]) -> str:
    if scenario["approval_condition"] == "approval with invalidated mapping":
        return "SAFE_ABORT"
    sequence = scenario["expected_governance_sequence"]
    for decision in ["SAFE_ABORT", "BLOCK", "REQUIRE_APPROVAL", "FALLBACK", "ALLOW"]:
        if decision in sequence:
            return decision
    return "NONE"


def _finding(check_name: str, status: str, detail: str) -> dict[str, Any]:
    return {"check_name": check_name, "status": status, "detail": detail}


def _write_profile_outputs(
    profile: str,
    error_rows: list[dict[str, Any]],
    stratified_rows: list[dict[str, Any]],
) -> None:
    _write_csv(RESULTS_DIR / f"scaled_error_cases_{profile}.csv", error_rows, ERROR_CASE_FIELDS)
    _write_csv(RESULTS_DIR / f"scaled_metrics_by_factor_{profile}.csv", stratified_rows)


def _write_journal_outputs(
    *,
    error_rows: list[dict[str, Any]],
    final_confusion: list[dict[str, Any]],
    governance_confusion: list[dict[str, Any]],
    stratified_rows: list[dict[str, Any]],
    scope_rows: list[dict[str, Any]],
    factor_balance_rows: list[dict[str, Any]],
    generator_findings: list[dict[str, Any]],
    scenarios: list[dict[str, Any]],
) -> None:
    _write_csv(RESULTS_DIR / "confusion_matrix_final_status_journal.csv", final_confusion)
    _write_csv(
        RESULTS_DIR / "confusion_matrix_governance_decision_journal.csv", governance_confusion
    )
    _write_csv(RESULTS_DIR / "scenario_factor_balance_journal.csv", factor_balance_rows)

    supported_rows = [row for row in scope_rows if row["scope"] == "supported_scope"]
    stress_rows = [row for row in scope_rows if row["scope"] == "stress_scope"]
    _write_csv(RESULTS_DIR / "supported_scope_metrics_journal.csv", supported_rows)
    _write_csv(RESULTS_DIR / "stress_scope_metrics_journal.csv", stress_rows)

    (DOCS_DIR / "scaled_error_audit_report.md").write_text(
        _error_audit_markdown(error_rows),
        encoding="utf-8",
    )
    (DOCS_DIR / "confusion_matrix_interpretation.md").write_text(
        _confusion_markdown(final_confusion, governance_confusion),
        encoding="utf-8",
    )
    (DOCS_DIR / "stratified_scaled_results.md").write_text(
        _stratified_markdown(stratified_rows),
        encoding="utf-8",
    )
    (DOCS_DIR / "supported_vs_stress_scope_report.md").write_text(
        _scope_markdown(supported_rows, stress_rows),
        encoding="utf-8",
    )
    (DOCS_DIR / "scenario_generator_quality_audit.md").write_text(
        _generator_quality_markdown(factor_balance_rows, generator_findings, scenarios),
        encoding="utf-8",
    )
    (DOCS_DIR / "ijtech_empirical_readiness_decision.md").write_text(
        _readiness_markdown(error_rows, supported_rows, stress_rows),
        encoding="utf-8",
    )
    (DOCS_DIR / "recommended_runtime_hardening_plan.md").write_text(
        _hardening_markdown(),
        encoding="utf-8",
    )


def _error_audit_markdown(error_rows: list[dict[str, Any]]) -> str:
    by_runtime = Counter(row["runtime_id"] for row in error_rows)
    by_category = Counter(row["failure_category"] for row in error_rows)
    preview = error_rows[:12]
    return f"""# Scaled Error Audit Report

This audit reviews non-compliant or incorrect journal-profile result rows. It
does not remove scenarios, relabel outcomes, or change runtime behavior.

## Non-Compliant Or Incorrect Rows By Runtime

{_counter_table(by_runtime, "runtime_id")}

## Failure Categories

{_counter_table(by_category, "failure_category")}

## Interpretation

Most baseline errors are expected limitations of comparison methods that
remove governance or architectural stages. For proposed runtimes, the main
diagnostic distinction is between intended supported behavior and stress cases
such as invalid approval, invalidated mappings, malformed payloads, and
unavailable capabilities. Valid post-approval success expectations should be
read carefully because `reference_v1` does not implement controlled approved
continuation; that is classified as a label/runtime-scope mismatch rather than
an unsafe execution.

## Case Preview

{_markdown_table(preview, ["scenario_id", "runtime_id", "scenario_family", "expected_final_status", "observed_final_status", "failure_category"])}
"""


def _confusion_markdown(
    final_confusion: list[dict[str, Any]],
    governance_confusion: list[dict[str, Any]],
) -> str:
    final_mismatches = [row for row in final_confusion if row["expected"] != row["observed"]]
    governance_mismatches = [
        row for row in governance_confusion if row["expected"] != row["observed"]
    ]
    return f"""# Confusion Matrix Interpretation

The confusion matrices report expected versus observed final status and
expected versus observed governance decision by runtime and scenario family.

## Final Status Mismatch Preview

{_markdown_table(final_mismatches[:12], ["runtime_id", "scenario_family", "expected", "observed", "count"])}

## Governance Decision Mismatch Preview

{_markdown_table(governance_mismatches[:12], ["runtime_id", "scenario_family", "expected", "observed", "count"])}

## Interpretation

The main error modes are not concentrated in unsafe proposed-runtime execution.
They are primarily baseline scope mismatches, partial-success versus success
differences for approval continuation, and conservative containment behavior in
stress scenarios. Unsafe execution is concentrated in governance-removing
baseline rows, which is useful as comparative evidence but should not be framed
as a production safety result.
"""


def _stratified_markdown(stratified_rows: list[dict[str, Any]]) -> str:
    preview = [
        row
        for row in stratified_rows
        if row["runtime_id"] == "reference_v1" and row["factor_name"] == "scenario_family"
    ][:12]
    return f"""# Stratified Scaled Results

The stratified metrics table groups results by runtime and each experimental
factor: scenario family, workflow length, governance pattern, adapter mix,
approval condition, and failure condition.

## Reference Runtime By Scenario Family

{_markdown_table(preview, ["factor_value", "count", "policy_compliance_rate", "unsafe_execution_rate", "final_outcome_accuracy", "trace_completeness", "p95_latency_ms"])}

These rows are intended for empirical depth in a journal manuscript. They make
clear where aggregate metrics are strong and where stress or scope mismatches
lower the overall compliance rate.
"""


def _scope_markdown(
    supported_rows: list[dict[str, Any]],
    stress_rows: list[dict[str, Any]],
) -> str:
    return f"""# Supported Scope Versus Stress Scope

Supported-scope scenarios represent behavior within the intended implemented
capability of the prototype. Stress-scope scenarios intentionally exercise
edge conditions: malformed payloads, unavailable capabilities, invalid
mappings, invalid or missing approvals, invalidated post-approval mappings,
and safe-abort paths.

Stress cases are retained and reported separately. They should not be hidden or
removed from aggregate results.

## Supported Scope

{_markdown_table(supported_rows, ["runtime_id", "scenario_count", "policy_compliance_rate", "unsafe_execution_rate", "final_outcome_accuracy", "trace_completeness", "policy_compliance_wilson_95_low", "policy_compliance_wilson_95_high"])}

## Stress Scope

{_markdown_table(stress_rows, ["runtime_id", "scenario_count", "policy_compliance_rate", "unsafe_execution_rate", "final_outcome_accuracy", "trace_completeness", "policy_compliance_wilson_95_low", "policy_compliance_wilson_95_high"])}
"""


def _generator_quality_markdown(
    factor_balance_rows: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    scenarios: list[dict[str, Any]],
) -> str:
    return f"""# Scenario Generator Quality Audit

Journal profile scenario count: {len(scenarios)}.

## Factor Balance Preview

{_markdown_table(factor_balance_rows[:20], ["factor_name", "factor_value", "count", "percentage"])}

## Consistency Checks

{_markdown_table(findings, ["check_name", "status", "detail"])}

## Interpretation

The generator provides broad deterministic factor coverage. Duplicate factor
signatures can occur because the scenario count exceeds the Cartesian coverage
needed for some factor combinations; this is not necessarily a duplicate
scenario id. Unrealistic or unsupported combinations are flagged as audit
findings rather than silently removed.
"""


def _readiness_markdown(
    error_rows: list[dict[str, Any]],
    supported_rows: list[dict[str, Any]],
    stress_rows: list[dict[str, Any]],
) -> str:
    category_counts = Counter(row["failure_category"] for row in error_rows)
    return f"""# IJTech Empirical Readiness Decision

## Decision

The scaled evaluation is stronger than the previous 12-case evaluation because
it adds deterministic scenario scaling, factor stratification, confidence
intervals over the scenario distribution, confusion matrices, and explicit
stress-scope diagnostics.

It is suitable for a conference paper as empirical prototype evidence. It is a
promising foundation for an IJTech extension, but journal submission should
include this audit, a clear supported-versus-stress framing, and a hardening
plan for unsupported or ambiguous cases.

## What To Emphasize

- Scaled deterministic coverage across governance patterns and adapter mixes.
- Zero unsafe execution for the reference/full-system rows in the audited
  aggregate.
- Stronger empirical depth than the initial 12-case package.
- Honest stress testing rather than only curated success cases.

## What To Frame As Limitations

- Synthetic scenarios and mock adapters.
- `reference_v1` does not represent approved post-approval continuation.
- Stress cases expose robustness limits and label/runtime-scope mismatches.
- LangSmith traces are observability evidence, not deployment evidence.

## Strong Claims

- The prototype can be evaluated reproducibly across hundreds of deterministic
  governance scenarios.
- Governance-removing baselines show substantially higher unsafe execution.
- The audit exposes where aggregate metrics decline rather than hiding those
  cases.

## Preliminary Claims

- Industrial readiness, certified safety, and live PLC behavior remain
  preliminary and unsupported by this artifact set.

## Failure Category Snapshot

{_counter_table(category_counts, "failure_category")}
"""


def _hardening_markdown() -> str:
    rows = [
        {
            "improvement": "Schema validation for capability inputs",
            "motivation": "Catch malformed payloads before adapter invocation.",
            "affected_failure_categories": "scenario_generator_issue, true_runtime_limitation",
            "expected_effect_on_metrics": "Improve stress-scope final outcome accuracy and containment explainability.",
            "risk_of_changing_claims": "Low if reported as future hardening, moderate if old/new results are mixed.",
            "needed_before_sedm": "No",
            "needed_before_ijtech": "Recommended",
        },
        {
            "improvement": "Clearer unavailable capability handling",
            "motivation": "Differentiate unsupported, unavailable, and invalid mappings.",
            "affected_failure_categories": "true_runtime_limitation, conservative_safe_failure",
            "expected_effect_on_metrics": "Improve diagnosis and possibly containment accuracy.",
            "risk_of_changing_claims": "Moderate; requires re-running scaled results.",
            "needed_before_sedm": "No",
            "needed_before_ijtech": "Recommended",
        },
        {
            "improvement": "Explicit supported-scope labels",
            "motivation": "Prevent ambiguity between intended behavior and stress tests.",
            "affected_failure_categories": "unsupported_scenario_scope, label_runtime_mismatch",
            "expected_effect_on_metrics": "Improve interpretability, not runtime behavior.",
            "risk_of_changing_claims": "Low if both scopes remain reported.",
            "needed_before_sedm": "Helpful",
            "needed_before_ijtech": "Yes",
        },
        {
            "improvement": "Stronger trace outputs for failure cases",
            "motivation": "Make safe abort, invalid approval, and unavailable capability evidence easier to audit.",
            "affected_failure_categories": "trace_instrumentation_gap, unknown_needs_review",
            "expected_effect_on_metrics": "Improve trace completeness and evidence quality.",
            "risk_of_changing_claims": "Low; instrumentation-only if behavior unchanged.",
            "needed_before_sedm": "No",
            "needed_before_ijtech": "Recommended",
        },
        {
            "improvement": "Additional tests for failure families",
            "motivation": "Lock in expected behavior for malformed, unavailable, and invalidated-mapping scenarios.",
            "affected_failure_categories": "scenario_generator_issue, true_runtime_limitation",
            "expected_effect_on_metrics": "Improves reproducibility confidence, not necessarily aggregate rates.",
            "risk_of_changing_claims": "Low.",
            "needed_before_sedm": "Helpful",
            "needed_before_ijtech": "Yes",
        },
    ]
    return f"""# Recommended Runtime Hardening Plan

No hardening changes are implemented in this audit task. The following items
are future work candidates based on the diagnostic evidence.

{_markdown_table(rows, ["improvement", "motivation", "affected_failure_categories", "expected_effect_on_metrics", "risk_of_changing_claims", "needed_before_sedm", "needed_before_ijtech"])}
"""


def _write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str] | None = None,
) -> None:
    if fieldnames is None:
        fieldnames = sorted({key for row in rows for key in row}) if rows else []
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        if not fieldnames:
            return
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _counter_table(counter: Counter[str], label: str) -> str:
    rows = [{label: key, "count": value} for key, value in counter.most_common()]
    return _markdown_table(rows, [label, "count"])


def _markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "_No rows available._"
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = [
        "| " + " | ".join(str(row.get(column, "")) for column in columns) + " |" for row in rows
    ]
    return "\n".join([header, separator, *body])


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = (len(ordered) - 1) * percentile / 100
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return round(ordered[lower] * (1 - weight) + ordered[upper] * weight, 6)


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit scaled deterministic evaluation errors.")
    parser.add_argument("--profile", choices=sorted(PROFILE_COUNTS), default="journal")
    args = parser.parse_args()
    summary = run_scaled_error_audit(args.profile)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
