"""Aligned scaled evaluation using runtime-specific expectation profiles."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any

from app.evaluation.run_scaled_evaluation import run_scaled_evaluation
from app.evaluation.runtime_expectations import (
    RUNTIME_CAPABILITY_PROFILES,
    runtime_expected_outcome,
    write_runtime_capability_profiles,
)
from app.evaluation.scenario_generator import PROFILE_COUNTS, load_or_generate_scenarios
from app.evaluation.scope_classifier import classify_runtime_scope

RESULTS_DIR = Path("data/results")
DOCS_DIR = Path("docs")

BOOL_FIELDS = {
    "governance_decision_correct",
    "policy_compliant",
    "unsafe_execution",
    "approval_bypass",
    "approval_validation_correct",
    "invalid_mapping_contained",
    "trace_complete",
    "restart_recovered",
    "final_outcome_correct",
}

INT_FIELDS = {"workflow_step_count", "completed_steps", "skipped_steps", "failed_steps"}


def run_aligned_scaled_evaluation(profile: str = "journal") -> dict[str, Any]:
    """Recompute scaled metrics with runtime-specific expected outcomes."""

    if profile not in PROFILE_COUNTS:
        raise ValueError(f"Unknown profile '{profile}'. Expected one of {sorted(PROFILE_COUNTS)}.")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    write_runtime_capability_profiles()

    rows = _load_original_rows(profile)
    scenarios = {
        scenario["scenario_id"]: scenario for scenario in load_or_generate_scenarios(profile)
    }
    aligned_rows = [_aligned_row(row, scenarios[row["scenario_id"]]) for row in rows]

    runtime_metrics = _runtime_metrics(aligned_rows)
    scope_metrics = _scope_metrics(aligned_rows)
    supported_rows = [row for row in scope_metrics if row["scope"] == "supported_scope"]
    stress_rows = [row for row in scope_metrics if row["scope"] == "stress_scope"]
    error_rows = _aligned_error_rows(aligned_rows)
    confusion_rows = _aligned_confusion_matrix(aligned_rows)
    baseline_comparison_rows = _baseline_comparison(runtime_metrics)

    summary = {
        "profile": profile,
        "scenario_count": len(scenarios),
        "result_row_count": len(aligned_rows),
        "deterministic": True,
        "runtime_specific_expectations": True,
        "metric_interpretation": (
            "Aligned metrics compare each runtime against documented capability "
            "profiles while preserving original global labels and unsafe flags."
        ),
        "metrics_by_runtime": runtime_metrics,
        "metrics_by_scope": scope_metrics,
        "aligned_error_count": len(error_rows),
        "aligned_error_count_by_runtime": dict(
            sorted(Counter(row["runtime_id"] for row in error_rows).items())
        ),
    }

    _write_outputs(
        profile=profile,
        aligned_rows=aligned_rows,
        summary=summary,
        runtime_metrics=runtime_metrics,
        scope_metrics=scope_metrics,
        supported_rows=supported_rows,
        stress_rows=stress_rows,
        error_rows=error_rows,
        confusion_rows=confusion_rows,
        baseline_comparison_rows=baseline_comparison_rows,
    )
    return summary


def _load_original_rows(profile: str) -> list[dict[str, Any]]:
    csv_path = RESULTS_DIR / f"scaled_evaluation_results_{profile}.csv"
    if not csv_path.exists():
        run_scaled_evaluation(profile)
    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        return [_parse_row(row) for row in csv.DictReader(csv_file)]


def _parse_row(row: dict[str, str]) -> dict[str, Any]:
    parsed: dict[str, Any] = dict(row)
    for field in BOOL_FIELDS:
        parsed[field] = row.get(field) == "True"
    for field in INT_FIELDS:
        parsed[field] = int(row[field])
    parsed["latency_ms"] = float(row["latency_ms"])
    return parsed


def _aligned_row(row: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    expectation = runtime_expected_outcome(scenario, row["runtime_id"])
    scope = classify_runtime_scope(scenario, row["runtime_id"])
    aligned_final_outcome_correct = (
        row["observed_final_status"] == expectation["aligned_expected_final_status"]
    )
    aligned_governance_decision_correct = (
        row["observed_governance_decision"] == expectation["aligned_expected_governance_decision"]
    )
    aligned_policy_compliant = _aligned_policy_compliant(
        row,
        scenario,
        expectation,
        aligned_final_outcome_correct,
        aligned_governance_decision_correct,
    )
    explanation = _alignment_explanation(row, expectation, aligned_policy_compliant)

    return {
        **row,
        "original_expected_final_status": row["expected_final_status"],
        "original_expected_governance_decision": row["expected_governance_decision"],
        "original_policy_compliant": row["policy_compliant"],
        "original_final_outcome_correct": row["final_outcome_correct"],
        "aligned_expected_final_status": expectation["aligned_expected_final_status"],
        "aligned_expected_governance_decision": expectation["aligned_expected_governance_decision"],
        "aligned_final_outcome_correct": aligned_final_outcome_correct,
        "aligned_governance_decision_correct": aligned_governance_decision_correct,
        "aligned_policy_compliant": aligned_policy_compliant,
        "expectation_basis": expectation["expectation_basis"],
        "runtime_supports_expected_behavior": expectation["runtime_supports_expected_behavior"],
        "scope": scope["scope"],
        "scope_reason": scope["scope_reason"],
        "alignment_explanation": explanation,
    }


def _aligned_policy_compliant(
    row: dict[str, Any],
    scenario: dict[str, Any],
    expectation: dict[str, Any],
    aligned_final_outcome_correct: bool,
    aligned_governance_decision_correct: bool,
) -> bool:
    if row["unsafe_execution"] or row["approval_bypass"]:
        return False
    if not aligned_final_outcome_correct or not aligned_governance_decision_correct:
        return False
    if not row["invalid_mapping_contained"]:
        return False
    if row["runtime_id"] == "langgraph_runtime" and _expects_valid_approval_execution(scenario):
        return row["approval_validation_correct"]
    return True


def _expects_valid_approval_execution(scenario: dict[str, Any]) -> bool:
    return (
        "REQUIRE_APPROVAL" in scenario["expected_governance_sequence"]
        and scenario["approval_condition"] == "valid approval"
    )


def _alignment_explanation(
    row: dict[str, Any],
    expectation: dict[str, Any],
    aligned_policy_compliant: bool,
) -> str:
    changed = (
        row["expected_final_status"] != expectation["aligned_expected_final_status"]
        or row["expected_governance_decision"]
        != expectation["aligned_expected_governance_decision"]
    )
    if changed:
        return expectation["expectation_basis"]
    if not aligned_policy_compliant and (row["unsafe_execution"] or row["approval_bypass"]):
        return "Policy-bypassing or unsafe execution remains non-compliant after alignment."
    return "Aligned expectation matches the original scenario label."


def _runtime_metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["runtime_id"]].append(row)
    return [
        _aggregate_rows(runtime_id, group_rows)
        for runtime_id, group_rows in sorted(grouped.items())
    ]


def _scope_metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["scope"], row["runtime_id"])].append(row)
    output = []
    for (scope, runtime_id), group_rows in sorted(grouped.items()):
        metric_row = _aggregate_rows(runtime_id, group_rows)
        metric_row["scope"] = scope
        metric_row["scenario_count"] = len({row["scenario_id"] for row in group_rows})
        metric_row["supported_scope_accuracy"] = (
            metric_row["aligned_final_outcome_accuracy"] if scope == "supported_scope" else ""
        )
        metric_row["stress_scope_containment_rate"] = (
            _rate(
                sum(
                    not row["unsafe_execution"]
                    and not row["approval_bypass"]
                    and row["invalid_mapping_contained"]
                    for row in group_rows
                ),
                len(group_rows),
            )
            if scope == "stress_scope"
            else ""
        )
        output.append(metric_row)
    return output


def _aggregate_rows(runtime_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [row["latency_ms"] for row in rows]
    return {
        "runtime_id": runtime_id,
        "count": len(rows),
        "original_policy_compliance_rate": _rate(
            sum(row["original_policy_compliant"] for row in rows),
            len(rows),
        ),
        "aligned_policy_compliance_rate": _rate(
            sum(row["aligned_policy_compliant"] for row in rows),
            len(rows),
        ),
        "original_final_outcome_accuracy": _rate(
            sum(row["original_final_outcome_correct"] for row in rows),
            len(rows),
        ),
        "aligned_final_outcome_accuracy": _rate(
            sum(row["aligned_final_outcome_correct"] for row in rows),
            len(rows),
        ),
        "unsafe_execution_rate": _rate(sum(row["unsafe_execution"] for row in rows), len(rows)),
        "approval_bypass_rate": _rate(sum(row["approval_bypass"] for row in rows), len(rows)),
        "invalid_mapping_containment_rate": _rate(
            sum(row["invalid_mapping_contained"] for row in rows),
            len(rows),
        ),
        "trace_completeness": _rate(sum(row["trace_complete"] for row in rows), len(rows)),
        "mean_latency_ms": round(mean(latencies), 6) if latencies else 0.0,
        "median_latency_ms": round(median(latencies), 6) if latencies else 0.0,
        "p95_latency_ms": _percentile(latencies, 95),
        "alignment_delta_policy_compliance": round(
            _rate(sum(row["aligned_policy_compliant"] for row in rows), len(rows))
            - _rate(sum(row["original_policy_compliant"] for row in rows), len(rows)),
            6,
        ),
    }


def _aligned_error_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    errors = []
    for row in rows:
        if not _aligned_problematic(row):
            continue
        errors.append(
            {
                "scenario_id": row["scenario_id"],
                "runtime_id": row["runtime_id"],
                "scenario_family": row["scenario_family"],
                "scope": row["scope"],
                "approval_condition": row["approval_condition"],
                "failure_condition": row["failure_condition"],
                "original_expected_final_status": row["original_expected_final_status"],
                "aligned_expected_final_status": row["aligned_expected_final_status"],
                "observed_final_status": row["observed_final_status"],
                "original_policy_compliant": row["original_policy_compliant"],
                "aligned_policy_compliant": row["aligned_policy_compliant"],
                "unsafe_execution": row["unsafe_execution"],
                "approval_bypass": row["approval_bypass"],
                "invalid_mapping_contained": row["invalid_mapping_contained"],
                "trace_complete": row["trace_complete"],
                "failure_category": _aligned_failure_category(row),
                "alignment_explanation": row["alignment_explanation"],
            }
        )
    return errors


def _aligned_problematic(row: dict[str, Any]) -> bool:
    return (
        not row["aligned_policy_compliant"]
        or not row["aligned_final_outcome_correct"]
        or not row["aligned_governance_decision_correct"]
        or row["unsafe_execution"]
        or row["approval_bypass"]
        or not row["invalid_mapping_contained"]
        or not row["trace_complete"]
    )


def _aligned_failure_category(row: dict[str, Any]) -> str:
    if row["unsafe_execution"] or row["approval_bypass"]:
        return "true_policy_violation"
    if not row["trace_complete"]:
        return "trace_instrumentation_gap"
    if row["runtime_id"].startswith("baseline_"):
        return "unsupported_baseline_scope"
    if not row["aligned_final_outcome_correct"] or not row["aligned_governance_decision_correct"]:
        return "remaining_evaluator_or_scope_issue"
    if not row["invalid_mapping_contained"]:
        return "remaining_containment_limitation"
    return "unknown_needs_review"


def _aligned_confusion_matrix(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: Counter[tuple[str, str, str, str, str]] = Counter()
    for row in rows:
        grouped[
            (
                row["runtime_id"],
                row["scope"],
                row["scenario_family"],
                row["aligned_expected_final_status"],
                row["observed_final_status"],
            )
        ] += 1
    return [
        {
            "runtime_id": runtime_id,
            "scope": scope,
            "scenario_family": family,
            "aligned_expected_final_status": expected,
            "observed_final_status": observed,
            "count": count,
        }
        for (runtime_id, scope, family, expected, observed), count in sorted(grouped.items())
    ]


def _baseline_comparison(runtime_metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_runtime = {row["runtime_id"]: row for row in runtime_metrics}
    proposed = ["reference_v1", "langgraph_runtime"]
    baselines = [
        "baseline_a_direct_without_governance",
        "baseline_b_single_stage_execution",
        "baseline_c_without_policy_filtering",
    ]
    rows = []
    for proposed_runtime in proposed:
        for baseline_runtime in baselines:
            if proposed_runtime not in by_runtime or baseline_runtime not in by_runtime:
                continue
            p = by_runtime[proposed_runtime]
            b = by_runtime[baseline_runtime]
            rows.append(
                {
                    "proposed_runtime": proposed_runtime,
                    "baseline_runtime": baseline_runtime,
                    "delta_aligned_policy_compliance": round(
                        p["aligned_policy_compliance_rate"] - b["aligned_policy_compliance_rate"],
                        6,
                    ),
                    "delta_unsafe_execution": round(
                        b["unsafe_execution_rate"] - p["unsafe_execution_rate"],
                        6,
                    ),
                    "proposed_aligned_policy_compliance_rate": p["aligned_policy_compliance_rate"],
                    "baseline_aligned_policy_compliance_rate": b["aligned_policy_compliance_rate"],
                    "proposed_unsafe_execution_rate": p["unsafe_execution_rate"],
                    "baseline_unsafe_execution_rate": b["unsafe_execution_rate"],
                }
            )
    return rows


def _write_outputs(
    *,
    profile: str,
    aligned_rows: list[dict[str, Any]],
    summary: dict[str, Any],
    runtime_metrics: list[dict[str, Any]],
    scope_metrics: list[dict[str, Any]],
    supported_rows: list[dict[str, Any]],
    stress_rows: list[dict[str, Any]],
    error_rows: list[dict[str, Any]],
    confusion_rows: list[dict[str, Any]],
    baseline_comparison_rows: list[dict[str, Any]],
) -> None:
    _write_csv(RESULTS_DIR / f"aligned_scaled_results_{profile}.csv", aligned_rows)
    (RESULTS_DIR / f"aligned_scaled_summary_{profile}.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_csv(RESULTS_DIR / "aligned_scaled_metrics_by_runtime.csv", runtime_metrics)
    _write_csv(RESULTS_DIR / "aligned_scaled_metrics_by_scope.csv", scope_metrics)
    _write_csv(RESULTS_DIR / f"supported_scope_metrics_aligned_{profile}.csv", supported_rows)
    _write_csv(RESULTS_DIR / f"stress_scope_metrics_aligned_{profile}.csv", stress_rows)
    _write_csv(RESULTS_DIR / f"aligned_error_cases_{profile}.csv", error_rows)
    _write_csv(
        RESULTS_DIR / f"aligned_confusion_matrix_final_status_{profile}.csv",
        confusion_rows,
    )

    if profile == "journal":
        _write_csv(RESULTS_DIR / "ijtech_table_2_main_results_aligned.csv", runtime_metrics)
        _write_csv(
            RESULTS_DIR / "ijtech_table_3_baseline_comparison_aligned.csv",
            baseline_comparison_rows,
        )
        _write_csv(
            RESULTS_DIR / "ijtech_table_4_supported_vs_stress_aligned.csv",
            scope_metrics,
        )
        (DOCS_DIR / "aligned_scaled_evaluation_report.md").write_text(
            _aligned_report(summary),
            encoding="utf-8",
        )
        (DOCS_DIR / "aligned_error_audit_report.md").write_text(
            _aligned_error_report(error_rows),
            encoding="utf-8",
        )
        (DOCS_DIR / "ijtech_aligned_empirical_results_report.md").write_text(
            _ijtech_aligned_report(summary, baseline_comparison_rows),
            encoding="utf-8",
        )
        _write_static_docs()


def _write_static_docs() -> None:
    (DOCS_DIR / "runtime_capability_profiles.md").write_text(
        _runtime_profiles_markdown(),
        encoding="utf-8",
    )
    (DOCS_DIR / "runtime_specific_expectation_rules.md").write_text(
        _expectation_rules_markdown(),
        encoding="utf-8",
    )
    (DOCS_DIR / "supported_stress_scope_definition.md").write_text(
        _scope_definition_markdown(),
        encoding="utf-8",
    )


def _aligned_report(summary: dict[str, Any]) -> str:
    return f"""# Aligned Scaled Evaluation Report

This report recomputes the `{summary['profile']}` scaled metrics using
runtime-specific expectations. Original global labels remain present in
`data/results/aligned_scaled_results_journal.csv`; aligned labels are added as
separate columns.

## Metrics By Runtime

{_markdown_table(summary["metrics_by_runtime"], ["runtime_id", "count", "original_policy_compliance_rate", "aligned_policy_compliance_rate", "aligned_final_outcome_accuracy", "unsafe_execution_rate", "approval_bypass_rate", "trace_completeness", "alignment_delta_policy_compliance"])}

## Why Original And Aligned Metrics Differ

The original metric used one global expected final status per scenario. The
aligned metric compares each runtime against documented capabilities. For
example, `reference_v1` is expected to stop at approval-required checkpoints,
while `langgraph_runtime` may reach `success` after valid controlled approval
continuation. Unsafe execution and approval bypass are never excused by
alignment.
"""


def _aligned_error_report(error_rows: list[dict[str, Any]]) -> str:
    category_counts = Counter(row["failure_category"] for row in error_rows)
    return f"""# Aligned Error Audit Report

Alignment reduces errors only when the previous error came from a documented
runtime-capability mismatch. It does not hide unsafe execution, approval
bypass, failed containment, or trace gaps.

## Remaining Error Categories

{_counter_table(category_counts, "failure_category")}

## Remaining Error Preview

{_markdown_table(error_rows[:20], ["scenario_id", "runtime_id", "scope", "observed_final_status", "aligned_expected_final_status", "failure_category"])}
"""


def _ijtech_aligned_report(
    summary: dict[str, Any],
    baseline_comparison_rows: list[dict[str, Any]],
) -> str:
    return f"""# IJTech Aligned Empirical Results Report

The aligned empirical results are deterministic and synthetic. Metrics are
scenario-distribution estimates over the generated journal profile, not
production reliability claims.

Runtime-specific expectations are used for fair comparison. Baselines remain
intentionally weak in governance to reveal policy risk. LangGraph value is
evaluated only for capabilities it actually supports, including controlled
approval continuation. `reference_v1` remains useful as a policy-correct
non-continuation runtime that stops at approval-required checkpoints.

## Main Runtime Results

{_markdown_table(summary["metrics_by_runtime"], ["runtime_id", "aligned_policy_compliance_rate", "aligned_final_outcome_accuracy", "unsafe_execution_rate", "approval_bypass_rate", "trace_completeness"])}

## Baseline Comparison

{_markdown_table(baseline_comparison_rows, ["proposed_runtime", "baseline_runtime", "delta_aligned_policy_compliance", "delta_unsafe_execution"])}

## Interpretation

Alignment is not metric manipulation: original labels are retained, every rule
is documented, and unsafe execution remains non-compliant. The corrected view
separates runtime capability scope from actual policy violations.
"""


def _runtime_profiles_markdown() -> str:
    rows = []
    for runtime_id, profile in RUNTIME_CAPABILITY_PROFILES.items():
        rows.append(
            {
                "runtime_id": runtime_id,
                "supports": "; ".join(profile["supports"]),
                "does_not_support": "; ".join(profile["does_not_support"]),
            }
        )
    return f"""# Runtime Capability Profiles

These profiles are used only for fair evaluation interpretation. They do not
remove scenarios and do not change runtime behavior.

{_markdown_table(rows, ["runtime_id", "supports", "does_not_support"])}
"""


def _expectation_rules_markdown() -> str:
    return """# Runtime-Specific Expectation Rules

Global scenario labels describe the scenario intent. Aligned labels describe
what each runtime should be expected to do, given its documented capability
profile.

Rules:

- `reference_v1`: valid post-approval scenarios are expected to end in
  `partial_success` with an approval-required checkpoint, not `success`,
  because the runtime does not perform controlled post-approval continuation.
- `reference_v1`: approval invalidation after resume is outside continuation
  scope; the expected decision is derived from the original governance plan
  rather than the resume-time mutation.
- `langgraph_runtime`: valid approval scenarios may reach `success` when
  validation and revalidation pass.
- `langgraph_runtime`: invalidated mappings after approval are expected to
  safe-abort.
- Baselines: final `success` is still non-compliant when it is produced by
  unsafe execution, approval bypass, or removed policy filtering.

Every aligned row includes the original expected labels, aligned expected
labels, and an `expectation_basis` explanation.
"""


def _scope_definition_markdown() -> str:
    return """# Supported And Stress Scope Definition

Scope is runtime-specific.

- `post_approval_valid` is supported scope for `langgraph_runtime`.
- Post-approval continuation is stress/out-of-scope for `reference_v1`.
- Malformed payload, unavailable capability, and unsupported capability cases
  are stress scope for all runtimes unless explicitly supported.
- Unsafe blocked-action cases are supported scope for governance-aware runtimes
  because blocking unsafe actions is an intended capability.
- Direct unsafe execution cases are expected failure/stress cases for baselines.

Stress cases are retained and reported separately. They are not deleted or
hidden.
"""


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row}) if rows else []
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        if not fieldnames:
            return
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _counter_table(counter: Counter[str], label: str) -> str:
    return _markdown_table(
        [{label: key, "count": value} for key, value in counter.most_common()],
        [label, "count"],
    )


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
    parser = argparse.ArgumentParser(description="Run aligned scaled evaluation.")
    parser.add_argument("--profile", choices=sorted(PROFILE_COUNTS), default="journal")
    args = parser.parse_args()
    summary = run_aligned_scaled_evaluation(args.profile)
    print(
        json.dumps(
            {
                "profile": args.profile,
                "scenario_count": summary["scenario_count"],
                "result_row_count": summary["result_row_count"],
                "aligned_error_count": summary["aligned_error_count"],
                "summary_path": str(RESULTS_DIR / f"aligned_scaled_summary_{args.profile}.json"),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
