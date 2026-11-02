"""Summarize local Kubernetes reproducibility evidence without changing metrics."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from app.observability.tracing import trace_experiment

RESULTS_DIR = Path("data/results")
K8S_RESULTS_CSV = RESULTS_DIR / "k8s_reproducibility_results.csv"
K8S_SUMMARY_JSON = RESULTS_DIR / "k8s_reproducibility_summary.json"
SCALED_JOURNAL_SUMMARY = RESULTS_DIR / "scaled_evaluation_summary_journal.json"
CRASH_RESTART_SUMMARY = RESULTS_DIR / "crash_restart_demo_summary.json"
CHECKPOINT_DB = Path("data/langgraph/checkpoints.db")

ROW_FIELDS = [
    "deployment_mode",
    "k8s_namespace",
    "k8s_job_name",
    "git_sha",
    "image_tag",
    "k8s_job_success",
    "health_endpoint_available",
    "checkpoint_pvc_used",
    "crash_restart_demo_success",
    "trace_completeness",
    "p95_latency_ms",
    "evidence_scope",
]


def run_k8s_reproducibility_summary(
    *,
    k8s_namespace: str | None = None,
    k8s_job_name: str | None = None,
    image_tag: str | None = None,
    health_url: str | None = None,
    evidence_scope: str = "local_kubernetes_reproducibility_demo",
) -> dict[str, Any]:
    """Write deterministic local Kubernetes reproducibility summary artifacts."""

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    metadata = {
        "deployment_mode": "kubernetes_local",
        "k8s_namespace": k8s_namespace or os.getenv("K8S_NAMESPACE", "vendor-orchestrator"),
        "k8s_job_name": k8s_job_name or os.getenv("K8S_JOB_NAME", "local-summary"),
        "git_sha": _git_sha(),
        "image_tag": image_tag or os.getenv("IMAGE_TAG", "vendor-orchestrator:local"),
    }
    scaled_summary = _read_json(SCALED_JOURNAL_SUMMARY)
    crash_summary = _read_json(CRASH_RESTART_SUMMARY)
    row = _result_row(
        metadata=metadata,
        scaled_summary=scaled_summary,
        crash_summary=crash_summary,
        health_url=health_url or os.getenv("HEALTH_CHECK_URL"),
        evidence_scope=evidence_scope,
    )
    summary = {
        "deterministic": True,
        "deployment_claim": "local Kubernetes reproducibility evidence only",
        "langsmith_trace_metadata_preview": metadata,
        "metrics": {
            "k8s_job_success": row["k8s_job_success"],
            "health_endpoint_available": row["health_endpoint_available"],
            "checkpoint_pvc_used": row["checkpoint_pvc_used"],
            "crash_restart_demo_success": row["crash_restart_demo_success"],
            "trace_completeness": row["trace_completeness"],
            "p95_latency_ms": row["p95_latency_ms"],
        },
        "source_artifacts": {
            "scaled_journal_summary": str(SCALED_JOURNAL_SUMMARY),
            "crash_restart_summary": str(CRASH_RESTART_SUMMARY),
            "checkpoint_db": str(CHECKPOINT_DB),
        },
        "row": row,
    }

    with trace_experiment(
        "k8s_reproducibility_summary",
        inputs={"source_artifacts": summary["source_artifacts"]},
        metadata=metadata,
        tags=["kubernetes", "local", "reproducibility"],
    ) as trace:
        _write_outputs(row, summary)
        trace.add_outputs(summary)

    return summary


def _result_row(
    *,
    metadata: dict[str, Any],
    scaled_summary: dict[str, Any],
    crash_summary: dict[str, Any],
    health_url: str | None,
    evidence_scope: str,
) -> dict[str, Any]:
    checkpoint_pvc_used = _env_bool("K8S_CHECKPOINT_PVC_USED")
    if checkpoint_pvc_used is None:
        checkpoint_pvc_used = CHECKPOINT_DB.exists() and CHECKPOINT_DB.stat().st_size > 0

    crash_restart_demo_success = _env_bool("K8S_CRASH_RESTART_DEMO_SUCCESS")
    if crash_restart_demo_success is None:
        crash_restart_demo_success = _crash_restart_success(crash_summary)

    k8s_job_success = _env_bool("K8S_JOB_SUCCESS")
    if k8s_job_success is None:
        k8s_job_success = _job_success(metadata["k8s_job_name"], scaled_summary, crash_summary)

    trace_completeness = _trace_completeness(scaled_summary, crash_summary)

    return {
        **metadata,
        "k8s_job_success": k8s_job_success,
        "health_endpoint_available": _health_available(health_url),
        "checkpoint_pvc_used": checkpoint_pvc_used,
        "crash_restart_demo_success": crash_restart_demo_success,
        "trace_completeness": trace_completeness,
        "p95_latency_ms": _p95_latency(scaled_summary),
        "evidence_scope": evidence_scope,
    }


def _job_success(
    k8s_job_name: str,
    scaled_summary: dict[str, Any],
    crash_summary: dict[str, Any],
) -> bool:
    if k8s_job_name == "scaled-evaluation-job":
        return bool(scaled_summary.get("scenario_count")) and bool(
            scaled_summary.get("result_row_count")
        )
    if k8s_job_name == "crash-restart-demo-job":
        return _crash_restart_success(crash_summary)
    return bool(scaled_summary.get("scenario_count")) and _crash_restart_success(crash_summary)


def _crash_restart_success(crash_summary: dict[str, Any]) -> bool:
    metrics = crash_summary.get("metrics", {})
    required = [
        "checkpoint_resume_success_rate",
        "checkpoint_reopen_resume_success_rate",
        "post_reopen_final_outcome_accuracy",
        "checkpoint_reopen_trace_completeness",
    ]
    return bool(metrics) and all(float(metrics.get(key, 0.0)) == 1.0 for key in required)


def _trace_completeness(
    scaled_summary: dict[str, Any],
    crash_summary: dict[str, Any],
) -> float:
    trace_values: list[float] = []
    runtime_summary = scaled_summary.get("runtime_summary", {})
    if "langgraph_runtime" in runtime_summary:
        trace_values.append(
            float(runtime_summary["langgraph_runtime"].get("trace_completeness", 0.0))
        )
    if "reference_v1" in runtime_summary:
        trace_values.append(float(runtime_summary["reference_v1"].get("trace_completeness", 0.0)))

    crash_trace = crash_summary.get("metrics", {}).get("checkpoint_reopen_trace_completeness")
    if crash_trace is not None:
        trace_values.append(float(crash_trace))

    return round(min(trace_values), 6) if trace_values else 0.0


def _p95_latency(scaled_summary: dict[str, Any]) -> float:
    runtime_summary = scaled_summary.get("runtime_summary", {})
    if not runtime_summary:
        return 0.0
    p95_values = [
        float(metrics.get("p95_latency_ms", 0.0))
        for metrics in runtime_summary.values()
        if "p95_latency_ms" in metrics
    ]
    return round(max(p95_values), 6) if p95_values else 0.0


def _health_available(health_url: str | None) -> bool:
    override = _env_bool("K8S_HEALTH_ENDPOINT_AVAILABLE")
    if override is not None:
        return override
    if not health_url:
        return False
    for _ in range(10):
        try:
            with urlopen(health_url, timeout=3.0) as response:
                if response.status == 200:
                    return True
        except (OSError, URLError, TimeoutError):
            time.sleep(2.0)
    return False


def _env_bool(name: str) -> bool | None:
    value = os.getenv(name)
    if value is None or value == "":
        return None
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_outputs(row: dict[str, Any], summary: dict[str, Any]) -> None:
    with K8S_RESULTS_CSV.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=ROW_FIELDS)
        writer.writeheader()
        writer.writerow(row)
    K8S_SUMMARY_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")


def _git_sha() -> str:
    env_sha = os.getenv("GIT_SHA")
    if env_sha:
        return env_sha
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def main() -> None:
    """Command-line entrypoint."""

    parser = argparse.ArgumentParser(description="Summarize local Kubernetes reproducibility.")
    parser.add_argument("--namespace", default=None)
    parser.add_argument("--job-name", default=None)
    parser.add_argument("--image-tag", default=None)
    parser.add_argument("--health-url", default=None)
    parser.add_argument(
        "--evidence-scope",
        default="local_kubernetes_reproducibility_demo",
    )
    args = parser.parse_args()

    summary = run_k8s_reproducibility_summary(
        k8s_namespace=args.namespace,
        k8s_job_name=args.job_name,
        image_tag=args.image_tag,
        health_url=args.health_url,
        evidence_scope=args.evidence_scope,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
