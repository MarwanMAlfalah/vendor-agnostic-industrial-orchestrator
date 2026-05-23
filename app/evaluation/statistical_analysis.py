"""Statistical summaries for deterministic scaled evaluation outputs."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any

from app.evaluation.run_scaled_evaluation import run_scaled_evaluation
from app.evaluation.scenario_generator import PROFILE_COUNTS, load_or_generate_scenarios

RESULTS_DIR = Path("data/results")
DOCS_DIR = Path("docs")
PROPOSED_RUNTIME = "reference_v1"
BASELINE_RUNTIMES = [
    "baseline_a_direct_without_governance",
    "baseline_b_single_stage_execution",
    "baseline_c_without_policy_filtering",
]

PROPORTION_METRICS = {
    "policy_compliance_rate": "policy_compliant",
    "unsafe_execution_rate": "unsafe_execution",
    "final_outcome_accuracy": "final_outcome_correct",
    "governance_decision_accuracy": "governance_decision_correct",
    "approval_validation_accuracy": "approval_validation_correct",
    "invalid_mapping_containment_rate": "invalid_mapping_contained",
    "restart_recovery_success_rate": "restart_recovered",
}


def wilson_interval(successes: int, total: int, confidence: float = 0.95) -> tuple[float, float]:
    """Return a Wilson score interval for a binomial proportion."""

    if total <= 0:
        return (0.0, 0.0)
    z = 1.959963984540054 if confidence == 0.95 else _normal_z(confidence)
    phat = successes / total
    denominator = 1 + z * z / total
    center = (phat + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * total)) / total) / denominator
    return (round(max(0.0, center - margin), 6), round(min(1.0, center + margin), 6))


def run_statistical_analysis(profile: str = "journal") -> dict[str, Any]:
    """Compute statistical summaries and paper-oriented output artifacts."""

    if profile not in PROFILE_COUNTS:
        raise ValueError(f"Unknown profile '{profile}'. Expected one of {sorted(PROFILE_COUNTS)}.")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    rows = _load_scaled_rows(profile)
    scenarios = load_or_generate_scenarios(profile)

    proportion_rows = _proportion_summary(rows)
    effect_rows = _effect_sizes(rows)
    latency_rows = _latency_summary(rows)
    paired_rows = _paired_comparisons(rows)
    summary = {
        "profile": profile,
        "deterministic": True,
        "interval_interpretation": (
            "Wilson intervals summarize uncertainty over the deterministic scenario "
            "distribution, not stochastic model sampling uncertainty."
        ),
        "proportion_metrics": proportion_rows,
        "effect_sizes": effect_rows,
        "latency_analysis": latency_rows,
        "paired_comparisons": paired_rows,
    }

    _write_statistical_outputs(profile, proportion_rows, effect_rows, latency_rows, paired_rows, summary)
    _write_ijtech_outputs(profile, scenarios, rows, proportion_rows, effect_rows, latency_rows)
    return summary


def _load_scaled_rows(profile: str) -> list[dict[str, Any]]:
    csv_path = RESULTS_DIR / f"scaled_evaluation_results_{profile}.csv"
    if not csv_path.exists():
        run_scaled_evaluation(profile)
    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        return [_parse_row(row) for row in csv.DictReader(csv_file)]


def _parse_row(row: dict[str, str]) -> dict[str, Any]:
    parsed: dict[str, Any] = dict(row)
    for key in [
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
    for key in ["workflow_step_count", "completed_steps", "skipped_steps", "failed_steps"]:
        parsed[key] = int(row[key])
    parsed["latency_ms"] = float(row["latency_ms"])
    return parsed


def _proportion_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[("runtime", row["runtime_id"])].append(row)
        grouped[("scenario_family", row["scenario_family"])].append(row)

    summary_rows: list[dict[str, Any]] = []
    for (group_type, group_id), group_rows in sorted(grouped.items()):
        for metric_name, column in PROPORTION_METRICS.items():
            denominator_rows = _denominator_rows(metric_name, group_rows)
            numerator = sum(1 for row in denominator_rows if row[column])
            denominator = len(denominator_rows)
            ci_low, ci_high = wilson_interval(numerator, denominator)
            summary_rows.append(
                {
                    "group_type": group_type,
                    "group_id": group_id,
                    "metric": metric_name,
                    "numerator": numerator,
                    "denominator": denominator,
                    "rate": _rate(numerator, denominator),
                    "wilson_95_low": ci_low,
                    "wilson_95_high": ci_high,
                }
            )
    return summary_rows


def _denominator_rows(metric_name: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if metric_name == "approval_validation_accuracy":
        return [row for row in rows if row["approval_condition"] != "no approval required"]
    if metric_name == "invalid_mapping_containment_rate":
        return [
            row
            for row in rows
            if row["failure_condition"]
            in {
                "unsupported capability",
                "invalid adapter mapping",
                "unavailable capability",
                "malformed payload",
                "safe abort condition",
            }
        ]
    if metric_name == "restart_recovery_success_rate":
        return [row for row in rows if row["restart_recovered"]]
    return rows


def _effect_sizes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_runtime: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_runtime[row["runtime_id"]].append(row)

    proposed = _metric_rates(by_runtime.get(PROPOSED_RUNTIME, []))
    effect_rows: list[dict[str, Any]] = []
    for baseline_id in BASELINE_RUNTIMES:
        baseline = _metric_rates(by_runtime.get(baseline_id, []))
        baseline_unsafe = baseline["unsafe_execution_rate"]
        proposed_unsafe = proposed["unsafe_execution_rate"]
        effect_rows.append(
            {
                "comparison": f"{PROPOSED_RUNTIME}_vs_{baseline_id}",
                "proposed_runtime": PROPOSED_RUNTIME,
                "baseline_runtime": baseline_id,
                "delta_policy_compliance": round(
                    proposed["policy_compliance_rate"] - baseline["policy_compliance_rate"],
                    6,
                ),
                "delta_unsafe_execution": round(baseline_unsafe - proposed_unsafe, 6),
                "relative_risk_unsafe_execution": _relative_risk(proposed_unsafe, baseline_unsafe),
                "absolute_risk_reduction": round(baseline_unsafe - proposed_unsafe, 6),
                "number_needed_to_prevent_unsafe_execution": _nnt(baseline_unsafe - proposed_unsafe),
            }
        )
    return effect_rows


def _metric_rates(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {
        metric: _rate(sum(1 for row in _denominator_rows(metric, rows) if row[column]), len(_denominator_rows(metric, rows)))
        for metric, column in PROPORTION_METRICS.items()
    }


def _relative_risk(proposed_rate: float, baseline_rate: float) -> float | None:
    if baseline_rate == 0:
        return None
    return round(proposed_rate / baseline_rate, 6)


def _nnt(absolute_risk_reduction: float) -> float | None:
    if absolute_risk_reduction <= 0:
        return None
    return round(1 / absolute_risk_reduction, 6)


def _latency_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        grouped[(row["runtime_id"], "ALL")].append(row["latency_ms"])
        grouped[(row["runtime_id"], row["scenario_family"])].append(row["latency_ms"])

    summary_rows = []
    for (runtime_id, scenario_family), values in sorted(grouped.items()):
        ordered = sorted(values)
        summary_rows.append(
            {
                "runtime_id": runtime_id,
                "scenario_family": scenario_family,
                "n": len(values),
                "mean_latency_ms": round(mean(values), 6) if values else 0.0,
                "median_latency_ms": round(median(values), 6) if values else 0.0,
                "p50_latency_ms": _percentile(ordered, 50),
                "p95_latency_ms": _percentile(ordered, 95),
                "min_latency_ms": round(min(values), 6) if values else 0.0,
                "max_latency_ms": round(max(values), 6) if values else 0.0,
                "stddev_latency_ms": round(stdev(values), 6) if len(values) > 1 else 0.0,
            }
        )
    return summary_rows


def _paired_comparisons(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_pair = {(row["scenario_id"], row["runtime_id"]): row for row in rows}
    scenario_ids = sorted({row["scenario_id"] for row in rows})
    paired_rows: list[dict[str, Any]] = []
    for baseline_id in BASELINE_RUNTIMES:
        pairs = [
            (by_pair[(scenario_id, PROPOSED_RUNTIME)], by_pair[(scenario_id, baseline_id)])
            for scenario_id in scenario_ids
            if (scenario_id, PROPOSED_RUNTIME) in by_pair
            and (scenario_id, baseline_id) in by_pair
        ]
        paired_rows.append(
            {
                "comparison": f"{PROPOSED_RUNTIME}_vs_{baseline_id}",
                "paired_n": len(pairs),
                "paired_correctness_difference": _mean_difference(
                    pairs,
                    "final_outcome_correct",
                ),
                "paired_unsafe_execution_difference": _mean_difference(
                    pairs,
                    "unsafe_execution",
                    invert=True,
                ),
                "paired_policy_compliance_difference": _mean_difference(
                    pairs,
                    "policy_compliant",
                ),
            }
        )
    return paired_rows


def _mean_difference(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    key: str,
    *,
    invert: bool = False,
) -> float:
    if not pairs:
        return 0.0
    differences = []
    for proposed, baseline in pairs:
        proposed_value = int(proposed[key])
        baseline_value = int(baseline[key])
        differences.append((baseline_value - proposed_value) if invert else (proposed_value - baseline_value))
    return round(sum(differences) / len(differences), 6)


def _write_statistical_outputs(
    profile: str,
    proportion_rows: list[dict[str, Any]],
    effect_rows: list[dict[str, Any]],
    latency_rows: list[dict[str, Any]],
    paired_rows: list[dict[str, Any]],
    summary: dict[str, Any],
) -> None:
    csv_path = RESULTS_DIR / f"scaled_statistical_summary_{profile}.csv"
    json_path = RESULTS_DIR / f"scaled_statistical_summary_{profile}.json"
    md_path = DOCS_DIR / "scaled_statistical_analysis.md"

    flat_rows: list[dict[str, Any]] = []
    for row in proportion_rows:
        flat_rows.append({"section": "proportion", **row})
    for row in effect_rows:
        flat_rows.append({"section": "effect_size", **row})
    for row in latency_rows:
        flat_rows.append({"section": "latency", **row})
    for row in paired_rows:
        flat_rows.append({"section": "paired", **row})

    fieldnames = sorted({key for row in flat_rows for key in row})
    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flat_rows)
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(_statistical_markdown(profile, summary), encoding="utf-8")


def _write_ijtech_outputs(
    profile: str,
    scenarios: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    proportion_rows: list[dict[str, Any]],
    effect_rows: list[dict[str, Any]],
    latency_rows: list[dict[str, Any]],
) -> None:
    _write_csv(
        RESULTS_DIR / "ijtech_table_1_scenario_design.csv",
        _scenario_design_rows(scenarios),
    )
    runtime_metric_rows = [
        row for row in proportion_rows if row["group_type"] == "runtime"
    ]
    _write_csv(RESULTS_DIR / "ijtech_table_2_main_results.csv", runtime_metric_rows)
    _write_csv(RESULTS_DIR / "ijtech_table_3_baseline_comparison.csv", effect_rows)
    _write_csv(RESULTS_DIR / "ijtech_table_5_latency_summary.csv", latency_rows)
    _write_csv(
        RESULTS_DIR / "ijtech_figure_data_policy_vs_unsafe.csv",
        _policy_vs_unsafe_rows(runtime_metric_rows),
    )
    _write_csv(
        RESULTS_DIR / "ijtech_figure_data_latency_distribution.csv",
        [{"runtime_id": row["runtime_id"], "scenario_family": row["scenario_family"], "latency_ms": row["latency_ms"]} for row in rows],
    )
    _write_csv(
        RESULTS_DIR / "ijtech_figure_data_trace_recovery.csv",
        _trace_recovery_rows(rows),
    )
    (DOCS_DIR / "ijtech_empirical_results_report.md").write_text(
        _ijtech_report(profile, scenarios, runtime_metric_rows, effect_rows),
        encoding="utf-8",
    )
    (DOCS_DIR / "ijtech_tables_and_figures_plan.md").write_text(
        _tables_plan(profile),
        encoding="utf-8",
    )


def _scenario_design_rows(scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str, str], int] = defaultdict(int)
    for scenario in scenarios:
        key = (
            scenario["workflow_length"],
            scenario["governance_pattern"],
            scenario["adapter_mix"],
            scenario["approval_condition"],
            scenario["failure_condition"],
        )
        groups[key] += 1
    return [
        {
            "workflow_length": key[0],
            "governance_pattern": key[1],
            "adapter_mix": key[2],
            "approval_condition": key[3],
            "failure_condition": key[4],
            "scenario_count": count,
        }
        for key, count in sorted(groups.items())
    ]


def _policy_vs_unsafe_rows(runtime_metric_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_runtime: dict[str, dict[str, Any]] = defaultdict(dict)
    for row in runtime_metric_rows:
        by_runtime[row["group_id"]][row["metric"]] = row
    return [
        {
            "runtime_id": runtime_id,
            "policy_compliance_rate": metrics.get("policy_compliance_rate", {}).get("rate", 0.0),
            "policy_compliance_wilson_low": metrics.get("policy_compliance_rate", {}).get("wilson_95_low", 0.0),
            "policy_compliance_wilson_high": metrics.get("policy_compliance_rate", {}).get("wilson_95_high", 0.0),
            "unsafe_execution_rate": metrics.get("unsafe_execution_rate", {}).get("rate", 0.0),
            "unsafe_execution_wilson_low": metrics.get("unsafe_execution_rate", {}).get("wilson_95_low", 0.0),
            "unsafe_execution_wilson_high": metrics.get("unsafe_execution_rate", {}).get("wilson_95_high", 0.0),
        }
        for runtime_id, metrics in sorted(by_runtime.items())
    ]


def _trace_recovery_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["runtime_id"]].append(row)
    return [
        {
            "runtime_id": runtime_id,
            "trace_completeness": _rate(sum(1 for row in group_rows if row["trace_complete"]), len(group_rows)),
            "restart_recovery_success_rate": _rate(sum(1 for row in group_rows if row["restart_recovered"]), len(group_rows)),
        }
        for runtime_id, group_rows in sorted(grouped.items())
    ]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row}) if rows else []
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        if not fieldnames:
            return
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _statistical_markdown(profile: str, summary: dict[str, Any]) -> str:
    key_runtime_rows = [
        row
        for row in summary["proportion_metrics"]
        if row["group_type"] == "runtime"
        and row["metric"] in {"policy_compliance_rate", "unsafe_execution_rate", "final_outcome_accuracy"}
    ]
    table = _markdown_table(
        key_runtime_rows,
        ["group_id", "metric", "numerator", "denominator", "rate", "wilson_95_low", "wilson_95_high"],
    )
    return f"""# Scaled Statistical Analysis

Profile: `{profile}`.

The scaled evaluation is deterministic. Wilson 95% confidence intervals are
reported as scenario-distribution intervals: they summarize uncertainty from
the finite generated scenario set, not stochastic LLM sampling uncertainty.

## Runtime Proportion Metrics

{table}

## Effect Sizes

Effect sizes compare `reference_v1` with deterministic baselines. Relative
risk and number-needed-to-prevent values are omitted where the denominator is
zero or the absolute risk reduction is not positive.

## Latency

Latency summaries are grouped by runtime and scenario family and include mean,
median, p50, p95, min, max, and standard deviation.

## Paired Comparisons

Paired differences compare outcomes scenario-by-scenario where `reference_v1`
and a baseline both executed the same generated case. These are descriptive
deterministic comparisons rather than claims of stochastic statistical
significance.
"""


def _ijtech_report(
    profile: str,
    scenarios: list[dict[str, Any]],
    runtime_metric_rows: list[dict[str, Any]],
    effect_rows: list[dict[str, Any]],
) -> str:
    policy_rows = [
        row
        for row in runtime_metric_rows
        if row["metric"] in {"policy_compliance_rate", "unsafe_execution_rate", "final_outcome_accuracy"}
    ]
    return f"""# IJTech Empirical Results Report

This report summarizes the `{profile}` deterministic scaled evaluation package
over {len(scenarios)} generated scenarios. The evaluation is prototype-level
and does not claim production deployment, live PLC validation, certified
safety, or stochastic LLM performance.

## Scenario Scaling Summary

The generated set balances workflow length, governance pattern, adapter mix,
approval condition, containment condition, and runtime coverage. Scenario
records include expected governance sequences, final statuses, policy labels,
trace markers, industrial context, RAMI alignment, and interoperability role.

## Main Empirical Findings

{_markdown_table(policy_rows, ["group_id", "metric", "rate", "wilson_95_low", "wilson_95_high"])}

## Baseline Comparison

{_markdown_table(effect_rows, ["comparison", "delta_policy_compliance", "delta_unsafe_execution", "relative_risk_unsafe_execution", "absolute_risk_reduction", "number_needed_to_prevent_unsafe_execution"])}

## Ablation Interpretation

The ablation runner writes `data/results/ijtech_table_4_ablation_results.csv`.
Implemented ablations reuse deterministic baselines where they directly
correspond to removed governance or matching stages. Conceptual ablations are
marked as not implemented rather than simulated.

## Limitations

The scenarios are synthetic and deterministic. They exercise mock adapters and
fixed governance labels, not live industrial equipment. Latency values are
local runtime measurements and should not be interpreted as deployment
benchmarks. LangSmith traces provide observability evidence only.

## Journal Extension Value

The package strengthens a journal extension by adding scaled scenario coverage,
confidence intervals over the scenario distribution, baseline effect sizes,
paired deterministic comparisons, ablation reporting, and table/figure data
that can be audited from reproducible artifacts.
"""


def _tables_plan(profile: str) -> str:
    return f"""# IJTech Tables and Figures Plan

Profile source: `{profile}`.

| Artifact | File | Manuscript Role |
| --- | --- | --- |
| Table 1 | `data/results/ijtech_table_1_scenario_design.csv` | Scenario factor design and scaling coverage. |
| Table 2 | `data/results/ijtech_table_2_main_results.csv` | Main policy, safety, accuracy, and interval metrics. |
| Table 3 | `data/results/ijtech_table_3_baseline_comparison.csv` | Effect sizes versus deterministic baselines. |
| Table 4 | `data/results/ijtech_table_4_ablation_results.csv` | Implemented and conceptual ablation outcomes. |
| Table 5 | `data/results/ijtech_table_5_latency_summary.csv` | Latency summary by runtime and scenario family. |
| Figure data | `data/results/ijtech_figure_data_policy_vs_unsafe.csv` | Policy compliance versus unsafe execution plot. |
| Figure data | `data/results/ijtech_figure_data_latency_distribution.csv` | Runtime latency distribution plot. |
| Figure data | `data/results/ijtech_figure_data_trace_recovery.csv` | Trace completeness and restart recovery plot. |

All figures should be captioned as deterministic prototype evaluation outputs.
"""


def _markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "_No rows available._"
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = [
        "| " + " | ".join(str(row.get(column, "")) for column in columns) + " |"
        for row in rows
    ]
    return "\n".join([header, separator, *body])


def _normal_z(confidence: float) -> float:
    if confidence <= 0 or confidence >= 1:
        raise ValueError("confidence must be between 0 and 1")
    # The code path is kept for completeness; the evaluation uses 95%.
    return 1.959963984540054


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    rank = (len(values) - 1) * percentile / 100
    lower = int(rank)
    upper = min(lower + 1, len(values) - 1)
    weight = rank - lower
    return round(values[lower] * (1 - weight) + values[upper] * weight, 6)


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze scaled deterministic results.")
    parser.add_argument("--profile", choices=sorted(PROFILE_COUNTS), default="journal")
    args = parser.parse_args()
    summary = run_statistical_analysis(args.profile)
    print(
        json.dumps(
            {
                "profile": args.profile,
                "proportion_rows": len(summary["proportion_metrics"]),
                "effect_size_rows": len(summary["effect_sizes"]),
                "summary_path": str(RESULTS_DIR / f"scaled_statistical_summary_{args.profile}.json"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
