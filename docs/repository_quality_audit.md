# Repository Quality Audit

This audit summarizes the repository hardening pass for reviewer readability and reproducibility.
It documents quality gates only; it does not change runtime behavior, business logic, evaluation
logic, or reported metrics.

## Current Repository Role

The repository is a research prototype for governance-aware, vendor-agnostic industrial workflow
orchestration. It contains:

- FastAPI endpoints for health checks, capability inspection, adapter invocation, planning,
  matching, governance evaluation, and execution.
- Mock OPC UA, REST, and legacy adapters.
- `reference_v1`, a deterministic governance-aware reference runtime.
- `langgraph_runtime`, an optional LangGraph runtime for approval interrupt/resume, controlled
  continuation, checkpointing, and local crash/restart evidence.
- Deterministic scaled evaluation scripts and generated result artifacts.
- IJTech-oriented manuscript and citation-mapping documentation.

## Quality Gates Added

| Gate | Command | Purpose |
| --- | --- | --- |
| Install | `make install` | Install package plus development dependencies. |
| Tests with coverage | `make test` | Run pytest with coverage for `app`. |
| Lint | `make lint` | Run Ruff checks on `app` and `tests`. |
| Format | `make format` | Run Black and Ruff auto-fixes on Python files. |
| CI | `.github/workflows/ci.yml` | Install `.[dev]`, run Ruff, then run pytest on push/PR. |

## Formatter And Linter Policy

Python formatting uses Black with a line length of 100 characters. Ruff checks `E`, `F`, and `I`
rules for pycodestyle errors, Pyflakes errors, and import ordering. These checks are intentionally
conservative so they improve readability without changing scientific behavior.

## Reproducibility Notes

The main reproducibility commands are captured in `docs/reproducibility_commands.md`. The
evaluation commands intentionally regenerate deterministic artifacts from the current scripts and
scenario profiles. They should not be used to introduce new result values into a manuscript
without a deliberate result-review step.

## Secret Handling

`.env` is ignored by `.gitignore` and should remain local. Do not commit API keys, LangSmith
tokens, credentials, trace URLs with private identifiers, or raw screenshots exposing account
identity.

## Reviewer Cautions

- Generated metrics are deterministic scenario-distribution results, not production reliability
  claims.
- LangSmith traces are observability evidence only.
- The Docker demo is a local crash/restart demonstration, not deployment evidence.
- Mock adapters do not establish live PLC integration or certified safety.
