# Vendor-Agnostic Industrial Orchestrator

Research prototype for governance-aware, vendor-agnostic orchestration of industrial workflows.

The repository contains a FastAPI service, deterministic mock adapters, governance-aware runtime
paths, LangGraph continuation experiments, and reproducible evaluation artifacts used for an
IJTech-oriented journal manuscript.

The project is not production software. It does not claim certified safety, live PLC integration,
regulatory compliance, or production deployment.

All reported industrial evidence is based on deterministic scenarios and mock OPC UA, REST, and
legacy adapters.

## Runtime Paths

`reference_v1` is the deterministic governance-aware reference runtime. It separates planning,
capability matching, governance evaluation, and adapter-mediated execution. It supports blocking,
approval-required stopping, safe-abort behavior, invalid mapping containment, and trace recording.
It intentionally does not perform controlled post-approval continuation.

`langgraph_runtime` preserves the governed execution semantics while adding graph-native
approval interrupt/resume, controlled post-approval continuation, checkpoint persistence, and
restart-resume evidence. The crash/restart demonstration uses a local SQLite checkpointer and is
prototype recovery evidence only.

The evaluation also includes deterministic baselines that remove governance or architectural
protections so policy risk can be measured explicitly.

## Governance-Aware Execution

The orchestration pipeline evaluates mapped plan steps with governance decisions:

- `ALLOW`: execute the mapped adapter step.
- `REQUIRE_APPROVAL`: stop or interrupt until approval is supplied.
- `BLOCK`: prevent execution of prohibited actions.
- `FALLBACK`: record fallback behavior where supported.
- `SAFE_ABORT`: stop execution to contain invalid mappings or malformed payloads.

Correct behavior may be non-execution. For that reason, the repository reports policy compliance,
unsafe execution, approval bypass, invalid mapping containment, trace completeness, and final
outcome accuracy rather than raw task success alone.

## Scaled Evaluation

The deterministic scaled evaluation includes:

- a 240-scenario journal profile used for main manuscript evidence;
- a 500-scenario extended profile for additional deterministic coverage;
- original global-label metrics and runtime-specific aligned metrics;
- baseline comparison;
- supported-versus-stress scope reporting;
- latency summaries interpreted as local prototype measurements.

Run the main evaluations:

```bash
make eval-journal
make eval-aligned
make eval-crash-restart
```

Generated outputs are stored under `data/results/` and supporting reports under `docs/`.

Do not interpret these artifacts as production reliability, certified safety, or live plant evidence.

## LangSmith Observability

LangSmith tracing is optional observability evidence for planning, matching, governance,
approval interrupt/resume, approved execution, and final-result spans. It is used for debugging,
trace inspection, and figure preparation only. Do not include raw LangSmith screenshots in
blind-review materials unless account, workspace, URL, and browser identity are fully removed.

## Docker Demo

The Docker demo runs the crash/restart persistence demonstration and mounts local `data/` and
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

## Reviewer Notes

- `.env` is ignored and must not be committed.
- Generated result artifacts are retained for reproducibility.
- IJTech-oriented manuscript evidence is in `docs/ijtech_*`, the citation mapping files, and the
  aligned/scaled evaluation reports.
- Reproducibility commands are summarized in `docs/reproducibility_commands.md`.
