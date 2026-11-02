"""Ablation study reporting for the scaled deterministic evaluation package."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from app.evaluation.conditional_metrics import (
    ELIGIBILITY_FIELDS,
    conditional_metrics,
)
from app.evaluation.run_scaled_evaluation import run_scaled_evaluation

RESULTS_DIR = Path("data/results")
DOCS_DIR = Path("docs")

ABLATION_VARIANTS = {
    "full_system": {
        "runtime_id": "reference_v1",
        "implemented": True,
        "description": "Reference deterministic governance-aware runtime.",
    },
    "without_governance": {
        "runtime_id": "baseline_a_direct_without_governance",
        "implemented": True,
        "description": "Existing direct execution baseline reuses mapped steps without governance enforcement.",
    },
    "without_capability_matching": {
        "runtime_id": "baseline_b_single_stage_execution",
        "implemented": True,
        "description": "Existing single-stage baseline bypasses the planner/matcher separation.",
    },
    "without_approval_revalidation": {
        "runtime_id": None,
        "implemented": False,
        "description": "Conceptual ablation only; no implemented runtime removes approval revalidation while preserving continuation.",
    },
    "without_langgraph_persistence": {
        "runtime_id": None,
        "implemented": False,
        "description": "Conceptual ablation only in this package; scaled runs use in-memory LangGraph rather than restart persistence.",
    },
    "without_trace_observability": {
        "runtime_id": None,
        "implemented": False,
        "description": "Conceptual ablation only; trace observability is instrumentation, not a separate behavior runtime.",
    },
}


def run_ablation_study() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Write ablation results and report artifacts."""

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    scaled_rows = _load_default_rows()
    rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {
        "profile": "default",
        "deterministic": True,
        "variants": {},
        "limitations": [
            "Conceptual ablations are not simulated.",
            "Implemented ablations reuse existing deterministic baselines.",
            "No core runtime behavior is modified by the ablation runner.",
        ],
    }

    for variant_id, metadata in ABLATION_VARIANTS.items():
        variant_rows = [row for row in scaled_rows if row["runtime_id"] == metadata["runtime_id"]]
        metrics = (
            _variant_metrics(variant_rows)
            if metadata["implemented"]
            else _not_implemented_metrics()
        )
        result_row = {
            "variant_id": variant_id,
            "implemented": metadata["implemented"],
            "runtime_id": metadata["runtime_id"] or "",
            "description": metadata["description"],
            **metrics,
        }
        rows.append(result_row)
        summary["variants"][variant_id] = result_row

    _write_outputs(rows, summary)
    return rows, summary


def _load_default_rows() -> list[dict[str, Any]]:
    csv_path = RESULTS_DIR / "scaled_evaluation_results_default.csv"
    if not csv_path.exists():
        run_scaled_evaluation("default")
    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        return [_parse_row(row) for row in csv.DictReader(csv_file)]


def _parse_row(row: dict[str, str]) -> dict[str, Any]:
    parsed: dict[str, Any] = dict(row)
    for key in [
        *ELIGIBILITY_FIELDS,
        "approval_bypass",
        "invalid_mapping_contained",
        "policy_compliant",
        "unsafe_execution",
        "final_outcome_correct",
        "trace_complete",
        "restart_recovered",
    ]:
        parsed[key] = row[key] == "True"
    parsed["latency_ms"] = float(row["latency_ms"])
    return parsed


def _variant_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "policy_compliance_rate": _rate(sum(row["policy_compliant"] for row in rows), len(rows)),
        **conditional_metrics(rows),
        "final_outcome_accuracy": _rate(
            sum(row["final_outcome_correct"] for row in rows), len(rows)
        ),
        "trace_completeness": _rate(sum(row["trace_complete"] for row in rows), len(rows)),
        "recovery_success_rate": _rate(sum(row["restart_recovered"] for row in rows), len(rows)),
        "mean_latency_ms": (
            round(sum(row["latency_ms"] for row in rows) / len(rows), 6) if rows else 0.0
        ),
        "run_count": len(rows),
        "not_implemented_reason": "",
    }


def _not_implemented_metrics() -> dict[str, Any]:
    return {
        "policy_compliance_rate": "",
        "unsafe_execution_rate": "",
        "final_outcome_accuracy": "",
        "trace_completeness": "",
        "recovery_success_rate": "",
        "mean_latency_ms": "",
        "run_count": 0,
        "not_implemented_reason": "No supported runtime variant exists; reported as conceptual only.",
    }


def _write_outputs(rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    csv_path = RESULTS_DIR / "ablation_results.csv"
    summary_path = RESULTS_DIR / "ablation_summary.json"
    report_path = DOCS_DIR / "ablation_study_report.md"
    table4_path = RESULTS_DIR / "ijtech_table_4_ablation_results.csv"

    fieldnames = [
        "variant_id",
        "implemented",
        "runtime_id",
        "description",
        "policy_compliance_rate",
        "unsafe_execution_rate",
        "final_outcome_accuracy",
        "trace_completeness",
        "recovery_success_rate",
        "mean_latency_ms",
        "run_count",
        "not_implemented_reason",
        *sorted(conditional_metrics([]).keys() - {"unsafe_execution_rate"}),
    ]
    for path in [csv_path, table4_path]:
        with path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    report_path.write_text(_markdown_report(rows), encoding="utf-8")


def _markdown_report(rows: list[dict[str, Any]]) -> str:
    return f"""# Ablation Study Report

The ablation study reuses implemented deterministic baselines when they
directly correspond to removing part of the governance-aware architecture.
Conceptual ablations are explicitly marked as not implemented; no behavior is
invented for manuscript convenience.

## Results

{_markdown_table(rows)}

## Interpretation

`full_system` corresponds to the unchanged `reference_v1` runtime. The
`without_governance` and `without_capability_matching` variants are implemented
by existing baselines. Approval revalidation, LangGraph persistence removal,
and trace observability removal are reported as conceptual because the
repository does not include isolated runtime switches for those conditions.

## Limitations

These results are deterministic prototype measurements over generated
scenarios. They do not demonstrate production deployment, live PLC behavior, or
certified safety properties.
"""


def _markdown_table(rows: list[dict[str, Any]]) -> str:
    columns = [
        "variant_id",
        "implemented",
        "policy_compliance_rate",
        "unsafe_execution_rate",
        "final_outcome_accuracy",
        "trace_completeness",
        "recovery_success_rate",
        "mean_latency_ms",
    ]
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = [
        "| " + " | ".join(str(row.get(column, "")) for column in columns) + " |" for row in rows
    ]
    return "\n".join([header, separator, *body])


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def main() -> None:
    rows, summary = run_ablation_study()
    print(
        json.dumps(
            {
                "variant_count": len(rows),
                "implemented_variants": sum(1 for row in rows if row["implemented"]),
                "summary_path": str(RESULTS_DIR / "ablation_summary.json"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
