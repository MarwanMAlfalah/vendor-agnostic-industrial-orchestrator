"""Refresh consolidated evidence and SHA-256 indexes from generated source artifacts.

Original evaluation runners own result values. This refresh copies their outputs;
it does not infer experimental outcomes or regenerate captured deployment logs.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RESULTS_DIR = Path("data/results")
DOCS_DIR = Path("docs")
REOPEN_NAMES = {
    "restart_recovery_success_rate": "checkpoint_reopen_resume_success_rate",
    "post_restart_final_outcome_accuracy": "post_reopen_final_outcome_accuracy",
    "restart_trace_completeness": "checkpoint_reopen_trace_completeness",
}


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _renamed(row: dict[str, Any]) -> dict[str, Any]:
    return {REOPEN_NAMES.get(key, key): value for key, value in row.items()}


def _refresh_consolidated(timestamp: str, git_sha: str) -> None:
    path = RESULTS_DIR / "final_unified_metrics.csv"
    unified = [_renamed(row) for row in _read_csv(path)]
    for row in unified:
        source_path = Path(row["source_artifact"])
        if source_path.suffix == ".json":
            source = json.loads(source_path.read_text())["metrics"]
            row["evaluation_layer"] = "checkpoint_reopen_resume_demo"
            row["subject_name"] = "LangGraph SQLite same-process checkpoint reopen/resume demo"
        else:
            source = next(
                candidate
                for candidate in _read_csv(source_path)
                if candidate.get("runtime_id", candidate.get("method_id")) == row["subject_id"]
            )
        for key in row.keys() & source.keys():
            row[key] = source[key]
    _write_csv(path, unified)
    json_path = path.with_suffix(".json")
    document = json.loads(json_path.read_text())
    document["rows"] = unified
    document["checkpoint_evidence_scope"] = (
        "same-process runtime/checkpointer reopen/resume; no OS process crash/restart"
    )
    json_path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")

    normalized_path = RESULTS_DIR / "final_manuscript_results_with_metadata.csv"
    normalized = [_renamed(row) for row in _read_csv(normalized_path)]
    for index, (row, metrics) in enumerate(zip(normalized, unified, strict=True), 1):
        assert row["subject_id"] == metrics["subject_id"]
        row.update(metrics)
        row.update(
            run_id=f"p0-correction-{git_sha}-worktree-{index:03}",
            git_sha=git_sha,
            timestamp_utc=timestamp,
        )
    _write_csv(normalized_path, normalized)

    # Local synthetic rows refer to the regenerated journal summary. Captured
    # Docker/kind/LangSmith rows retain their historical provenance and values.
    summary = json.loads((RESULTS_DIR / "scaled_evaluation_summary_journal.json").read_text())
    for name in ["deployment_mode_comparison.csv", "deployment_mode_comparison_with_metadata.csv"]:
        rows = _read_csv(RESULTS_DIR / name)
        for row in rows:
            if row["deployment_mode"] != "local_synthetic_scaled":
                continue
            metrics = summary["runtime_summary"][row["runtime_or_evidence_type"]]
            for key in row.keys() & metrics.keys():
                row[key] = metrics[key]
            if "run_id" in row:
                row.update(
                    run_id=f"p0-correction-{git_sha}-worktree",
                    git_sha=git_sha,
                    timestamp_utc=timestamp,
                )
        _write_csv(RESULTS_DIR / name, rows)


def _refresh_manuscript_tables() -> None:
    runtimes = {
        row["runtime_id"]: row
        for row in _read_csv(RESULTS_DIR / "aligned_scaled_metrics_by_runtime.csv")
    }
    scopes = {
        (row["runtime_id"], row["scope"].removesuffix("_scope")): row
        for row in _read_csv(RESULTS_DIR / "aligned_scaled_metrics_by_scope.csv")
    }
    baselines = {
        (row["proposed_runtime"], row["baseline_runtime"]): row
        for row in _read_csv(RESULTS_DIR / "ijtech_table_3_baseline_comparison_aligned.csv")
    }
    ablations = {row["variant_id"]: row for row in _read_csv(RESULTS_DIR / "ablation_results.csv")}
    columns = {
        "original policy compliance": "original_policy_compliance_rate",
        "aligned policy compliance": "aligned_policy_compliance_rate",
        "aligned final outcome accuracy": "aligned_final_outcome_accuracy",
        "unsafe execution": "unsafe_execution_rate",
        "approval bypass": "approval_bypass_rate",
        "invalid mapping containment": "invalid_mapping_containment_rate",
        "trace completeness": "trace_completeness",
        "delta unsafe execution": "delta_unsafe_execution",
        "delta aligned policy compliance": "delta_aligned_policy_compliance",
        "policy compliance": "policy_compliance_rate",
        "final outcome accuracy": "final_outcome_accuracy",
        "recovery success": "recovery_success_rate",
    }
    targets = [
        "ijtech_tables_ready_for_manuscript.md",
        "ijtech_results_final_candidate.md",
        "ijtech_manuscript_full_draft.md",
    ]
    for name in targets:
        path = DOCS_DIR / name
        lines = path.read_text().splitlines()
        header: list[str] = []
        for index, line in enumerate(lines):
            if not line.startswith("|"):
                header = []
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            first = cells[0].strip("`")
            if not header:
                header = [cell.lower() for cell in cells]
                continue
            source = None
            if len(cells) > 1 and (first, cells[1].strip("`")) in baselines:
                source = baselines[(first, cells[1].strip("`"))]
            elif "scope" in header and first in runtimes:
                source = scopes.get((first, cells[header.index("scope")]))
            elif first in runtimes:
                source = runtimes[first]
            elif first in ablations:
                source = ablations[first]
            if source:
                for position, title in enumerate(header):
                    metric = columns.get(title)
                    if metric not in source and f"aligned_{metric}" in source:
                        metric = f"aligned_{metric}"
                    if metric in source:
                        cells[position] = str(source[metric]) if source[metric] != "" else "N/A"
                lines[index] = "| " + " | ".join(cells) + " |"
        path.write_text("\n".join(lines) + "\n")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _refresh_indexes(timestamp: str, git_sha: str) -> int:
    index_path = RESULTS_DIR / "RESULTS_METADATA_INDEX.json"
    index = json.loads(index_path.read_text())
    exclusions = set(index["self_referential_exclusions"])
    index["artifacts"] = [
        artifact
        for artifact in index["artifacts"]
        if Path(artifact["artifact_path"]).name not in exclusions
    ]
    index["artifact_count"] = len(index["artifacts"])
    for artifact in index["artifacts"]:
        path = Path(artifact["artifact_path"])
        digest = _digest(path)
        if artifact["sha256"] != digest:
            artifact["sha256"] = digest
            # Preserve original audit metadata rather than claim it describes
            # the new run. Explicitly record the later artifact refresh.
            artifact["notes"] = (
                artifact["notes"].split("; P0 refresh:")[0]
                + f"; P0 refresh: {timestamp}; SHA-256 reflects corrected artifact; original indexing provenance retained"
            )
    index["refreshed_at_utc"] = timestamp
    index_path.write_text(json.dumps(index, indent=2) + "\n")
    _write_csv(index_path.with_suffix(".csv"), index["artifacts"])

    manifest_path = RESULTS_DIR / "RESULTS_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    paths = {artifact["path"] for artifact in manifest["artifacts"]}
    paths.update(
        str(path)
        for path in RESULTS_DIR.iterdir()
        if path.suffix in {".csv", ".json"} and path != manifest_path
    )
    paths.add(str(DOCS_DIR / "p0_correction_report.md"))
    manifest["artifacts"] = [
        {"path": name, "bytes": Path(name).stat().st_size, "sha256": _digest(Path(name))}
        for name in sorted(paths)
    ]
    manifest["artifact_count"] = len(paths)
    manifest["refreshed_at_utc"] = timestamp
    manifest["refresh_base_git_sha"] = git_sha
    manifest["notes"] = (
        "SHA-256/byte counts refreshed from current files after P0 correction; original creation provenance retained. Refresh base revision has uncommitted corrections. Captured deployment logs are historical evidence, not rerun by this command."
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return len(paths)


def main() -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    git_sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    _refresh_consolidated(timestamp, git_sha)
    _refresh_manuscript_tables()
    count = _refresh_indexes(timestamp, git_sha)
    print(f"Refreshed consolidated evidence and {count} SHA-256 manifest entries.")


if __name__ == "__main__":
    main()
