"""Integrity checks for evidence artifacts and deployment manifests."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path

import yaml

RESULTS_DIR = Path("data/results")


def test_repository_text_artifacts_are_not_collapsed_to_one_line() -> None:
    """Key reviewer-facing artifacts should remain readable in committed raw views."""

    expected_minimum_line_counts = {
        Path("README.md"): 20,
        Path("Makefile"): 8,
        Path("pyproject.toml"): 20,
        RESULTS_DIR / "deployment_mode_comparison.csv": 2,
        RESULTS_DIR / "deployment_mode_comparison_with_metadata.csv": 2,
        RESULTS_DIR / "langsmith_trace_manifest.csv": 2,
        RESULTS_DIR / "RESULTS_METADATA_INDEX.csv": 2,
        RESULTS_DIR / "final_manuscript_results_with_metadata.csv": 2,
    }
    expected_minimum_line_counts.update(
        {path: 2 for path in sorted(Path("deploy/k8s/base").glob("*.yaml"))}
    )

    for path, minimum_line_count in expected_minimum_line_counts.items():
        committed_text = subprocess.check_output(
            ["git", "show", f"HEAD:{path.as_posix()}"],
            text=True,
        )
        line_count = len(committed_text.splitlines())
        assert line_count > minimum_line_count, path


def test_kubernetes_yaml_manifests_parse() -> None:
    """All local Kubernetes manifests should be valid YAML documents."""

    manifest_paths = sorted(Path("deploy/k8s/base").glob("*.yaml"))
    assert manifest_paths
    for path in manifest_paths:
        documents = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
        assert documents, path
        assert all(document.get("apiVersion") and document.get("kind") for document in documents)


def test_key_evidence_csv_files_parse_with_rows() -> None:
    """Final evidence CSVs should parse and contain at least one data row."""

    csv_paths = [
        RESULTS_DIR / "deployment_mode_comparison.csv",
        RESULTS_DIR / "deployment_mode_comparison_with_metadata.csv",
        RESULTS_DIR / "langsmith_trace_manifest.csv",
        RESULTS_DIR / "RESULTS_METADATA_INDEX.csv",
        RESULTS_DIR / "final_manuscript_results_with_metadata.csv",
    ]
    for path in csv_paths:
        with path.open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            rows = list(reader)
        assert reader.fieldnames, path
        assert rows, path


def test_key_evidence_json_files_parse() -> None:
    """Final evidence JSON artifacts should parse as objects."""

    json_paths = [
        RESULTS_DIR / "RESULTS_MANIFEST.json",
        RESULTS_DIR / "RESULTS_METADATA_INDEX.json",
        RESULTS_DIR / "evidence_manifest.json",
        RESULTS_DIR / "k8s_reproducibility_summary.json",
    ]
    for path in json_paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), path


def test_kubernetes_log_evidence_uses_correct_deployment_log() -> None:
    """Kubernetes evidence should use the deployment log, not the obsolete service-name log."""

    manifest = json.loads((RESULTS_DIR / "evidence_manifest.json").read_text(encoding="utf-8"))
    log_evidence = manifest["kubernetes_log_evidence"]
    evidence_paths = {artifact["path"] for artifact in log_evidence["files"]}
    obsolete_paths = {
        artifact["path"] for artifact in log_evidence["empty_files_excluded_from_evidence"]
    }

    assert log_evidence["deployment_name"] == "orchestrator"
    assert log_evidence["service_name"] == "orchestrator-api"
    assert log_evidence["health_status"] == "ok"
    assert "data/results/k8s_logs/orchestrator.log" in evidence_paths
    assert "data/results/k8s_logs/events.txt" in evidence_paths
    assert "data/results/k8s_logs/orchestrator-deployment-describe.txt" in evidence_paths
    assert "data/results/k8s_logs/orchestrator-service-describe.txt" in evidence_paths
    assert "data/results/k8s_logs/orchestrator-api.log" not in evidence_paths
    assert "data/results/k8s_logs/orchestrator-api.log" in obsolete_paths

    for path in evidence_paths:
        assert Path(path).stat().st_size > 0, path


def test_results_metadata_index_covers_result_artifacts() -> None:
    """The metadata index should cover stable result artifacts."""

    with (RESULTS_DIR / "RESULTS_METADATA_INDEX.csv").open(
        newline="", encoding="utf-8"
    ) as csv_file:
        indexed_paths = {row["artifact_path"] for row in csv.DictReader(csv_file)}

    expected_paths = {
        str(path)
        for path in RESULTS_DIR.glob("*")
        if path.suffix.lower() in {".csv", ".json"}
        and path.name
        not in {
            "RESULTS_MANIFEST.json",
            "RESULTS_METADATA_INDEX.csv",
            "RESULTS_METADATA_INDEX.json",
        }
    }
    assert expected_paths.issubset(indexed_paths)


def test_results_manifest_hashes_match_files() -> None:
    """Every hash recorded in RESULTS_MANIFEST should match the current file bytes."""

    manifest = json.loads((RESULTS_DIR / "RESULTS_MANIFEST.json").read_text(encoding="utf-8"))
    for artifact in manifest["artifacts"]:
        path = Path(artifact["path"])
        assert path.exists(), path
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == artifact["sha256"], path


def test_metadata_index_hashes_match_and_exclude_self_references() -> None:
    """Metadata indexes cannot contain valid hashes of their own final bytes."""

    document = json.loads((RESULTS_DIR / "RESULTS_METADATA_INDEX.json").read_text())
    artifacts = document["artifacts"]
    assert document["artifact_count"] == len(artifacts)
    exclusions = set(document["self_referential_exclusions"])
    for artifact in artifacts:
        path = Path(artifact["artifact_path"])
        assert path.name not in exclusions
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]
    with (RESULTS_DIR / "RESULTS_METADATA_INDEX.csv").open(newline="") as stream:
        assert list(csv.DictReader(stream)) == artifacts
