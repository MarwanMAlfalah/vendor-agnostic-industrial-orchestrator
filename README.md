# Vendor-Agnostic Industrial Orchestrator

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?logo=python" />
</p>

Research prototype for governance-aware, vendor-agnostic orchestration of industrial workflows.

The repository contains a FastAPI service, deterministic mock adapters, governance-aware runtime
paths, LangGraph continuation experiments, and reproducible evaluation artifacts for an
in-progress research manuscript.

The project is not production software. It does not claim certified safety, live PLC integration,
regulatory compliance, or production deployment.

All reported industrial evidence is based on deterministic scenarios and mock OPC UA, REST, and
legacy adapters.

## Runtime Paths

`reference_v1` is the deterministic governance-aware reference runtime. It separates planning,
capability matching, governance evaluation, and adapter-mediated execution. It supports blocking,
safe-abort behavior, invalid mapping containment, and trace recording. It records
`approval_required` decisions without executing those steps, but later allowed executable steps
may still execute. It does not implement a workflow-wide approval pause/resume mechanism or
controlled post-approval continuation.

`langgraph_runtime` adds graph-native approval interrupt/resume, controlled post-approval
continuation, and checkpoint persistence. The checkpoint demonstration closes the initial
runtime/checkpointer, reopens the SQLite-backed runtime, and resumes within the same Python
process. It demonstrates checkpoint reopen/resume behavior, not recovery after an
operating-system process crash.

The evaluation also includes deterministic baselines that remove governance or architectural
protections so policy risk can be measured explicitly.

## Governance-Aware Execution

The orchestration pipeline evaluates mapped plan steps with governance decisions:

- `ALLOW`: execute the mapped adapter step.
- `REQUIRE_APPROVAL`: classify a step as requiring approval. `reference_v1` records the
  decision without a workflow-wide pause; `langgraph_runtime` provides explicit interrupt/resume
  for controlled approval continuation.
- `BLOCK`: prevent execution of prohibited actions.
- `FALLBACK`: record fallback behavior where supported.
- `SAFE_ABORT`: stop execution to contain invalid mappings or malformed payloads.

Correct behavior may be non-execution. For that reason, the repository reports policy compliance,
unsafe execution, approval bypass, invalid mapping containment, trace completeness, and final
outcome accuracy rather than raw task success alone.

## Evaluation Evidence

The deterministic scaled evaluation includes:

- a 240-scenario journal profile used for main manuscript evidence;
- a 500-scenario extended profile for additional deterministic coverage;
- original global-label metrics and runtime-specific aligned metrics;
- five paths: `reference_v1`, `langgraph_runtime`, and baselines A, B, and C;
- baseline comparison and implemented/conceptual ablation reporting;
- supported-versus-stress scope reporting;
- latency summaries interpreted as local prototype measurements.

Run the main evaluations:

```bash
make eval-journal
make eval-aligned
make eval-crash-restart
```

The scaled profiles use prepared governance plans (`source_goal=None`) to isolate runtime
execution, governance, containment, and continuation behavior. They do not independently
benchmark planner or capability-matcher accuracy across all 240/500 scenarios.

Principal committed evidence: [journal summary](data/results/scaled_evaluation_summary_journal.json),
[extended summary](data/results/scaled_evaluation_summary_extended.json),
[aligned runtime metrics](data/results/aligned_scaled_metrics_by_runtime.csv),
[aligned baseline comparison](data/results/ijtech_table_3_baseline_comparison_aligned.csv), and
[ablation summary](data/results/ablation_summary.json). Generated results are under `data/results/`
and reports under `docs/`.

Conditional safety rates include explicit eligible counts; empty subsets are `null` in JSON
and blank in CSV. See [metric definitions](docs/metrics_definitions.md) and the
[P0 correction report](docs/p0_correction_report.md). Scaled `trace_completeness` checks a
reference execution-result marker versus scenario-specific graph markers for LangGraph; equal
scores do not establish identical trace coverage.

Do not interpret these artifacts as production reliability, certified safety, or live plant evidence.

## LangSmith Observability

LangSmith tracing is optional observability evidence for planning, matching, governance,
approval interrupt/resume, approved execution, and final-result spans. It is used for debugging,
trace inspection, and figure preparation only. Do not include raw LangSmith screenshots in
blind-review materials unless account, workspace, URL, and browser identity are fully removed.

## Docker Demo

The Docker demo runs the same-process checkpoint reopen/resume demonstration and mounts local `data/` and
`docs/` directories so generated summaries remain on the host:

```bash
docker compose -f docker-compose.demo.yml up --build
```

This demo exercises local LangGraph checkpoint persistence. It is not a production deployment.

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the package and development tools:

```bash
make install
```

Run tests and lint:

```bash
make test
make lint
```

Format Python files:

```bash
make format
```

## Run the API

Start the FastAPI app:

```bash
make run-api
```

Check the health endpoint:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "vendor-agnostic-industrial-orchestrator",
  "environment": "research"
}
```
---

## Authors

**Marwan M. Al-Falah**<br>
MSc Researcher in Intelligent Systems<br>
Peter the Great St. Petersburg Polytechnic University

**Elena S. Gebel — Co-author / academic collaborator**

## Reviewer Notes

- `.env` is ignored and must not be committed.
- Generated result artifacts are retained for reproducibility.
- IJTech-oriented manuscript evidence is in `docs/ijtech_*`, the citation mapping files, and the
  aligned/scaled evaluation reports.
- Reproducibility commands are summarized in `docs/reproducibility_commands.md`.
