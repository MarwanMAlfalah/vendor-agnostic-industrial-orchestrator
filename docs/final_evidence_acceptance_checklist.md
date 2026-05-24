# Final Evidence Acceptance Checklist

This checklist records the final local evidence verification pass. It does not make production,
live PLC, or certified safety claims.

## Verification Commands

| Check | Command or source | Observed status |
| --- | --- | --- |
| Local lint | `ruff check app tests` | Passed: `All checks passed!` |
| Local tests | `.venv/bin/python -m pytest` | Passed: `38 passed` |
| Docker Compose integration | `docker compose -f docker-compose.integration.yml up --build -d ...` and `docker compose -f docker-compose.integration.yml run --rm evaluation-runner` | Passed; `data/results/containerized_integration_summary.json` updated with `git_sha=36853bd`. |
| LangSmith traces | LangSmith API query for project `vendor-agnostic-industrial-orchestrator` | Passed; `data/results/langsmith_trace_manifest.csv` contains 7 trace rows. |
| Local Kubernetes kind | `kind create cluster --name vendor-orchestrator`, image load, `kubectl apply`, waits, logs, and port-forward health check | Passed after a second `kubectl apply` resolved namespace ordering. API pod ran and both jobs completed. |
| GitHub Actions CI | GitHub REST API for repository Actions runs | Latest observed run `26346770533` completed with conclusion `success`. |

## Required Artifacts

| Artifact | Status |
| --- | --- |
| `data/results/RESULTS_MANIFEST.json` | Created; contains SHA256 hashes for result CSV/JSON artifacts, excluding itself. |
| `data/results/langsmith_trace_manifest.csv` | Created; includes trace name, deployment mode, runtime, profile, SHA, run ID, case ID, approval/checkpoint flags, and screenshot recommendation. |
| `data/results/deployment_mode_comparison.csv` | Updated with actual local, Docker, local kind, LangSmith, and GitHub Actions evidence. |
| `docs/ijtech_engineering_evidence_report.md` | Updated with actual execution evidence and current generated values. |
| `docs/kubernetes_reproducibility_demo.md` | Updated with actual commands and observed kind outputs. |
| `docs/final_evidence_acceptance_checklist.md` | Created. |

## Kubernetes Evidence Classification

Kubernetes evidence is classified as actual local kind evidence because the final pass observed:

- kind cluster creation for `vendor-orchestrator`;
- local image load for `vendor-orchestrator:local`;
- `orchestrator` deployment available in namespace `vendor-orchestrator`;
- `scaled-evaluation-job` completed successfully;
- `crash-restart-demo-job` completed successfully;
- `kubectl port-forward svc/orchestrator-api 8001:8000 -n vendor-orchestrator`;
- `curl -fsS http://localhost:8001/health` returned `status=ok`.

The first `kubectl apply -f deploy/k8s/base/` encountered namespace ordering errors for some
resources; a second apply succeeded. This is recorded as a local apply behavior, not a runtime
logic issue.

## LangSmith Evidence Classification

LangSmith evidence is observability evidence only. The trace manifest includes Docker Compose,
local Kubernetes summary, crash/restart, and representative scaled-evaluation traces. Traces do
not participate in governance decisions and do not validate industrial deployment.

## GitHub Actions Evidence Classification

GitHub Actions evidence is CI evidence only. The observed public run was:

- workflow: `CI`
- branch: `main`
- commit: `36853bdc7363d6b587606ddd11f9cf5803accd37`
- status: `completed`
- conclusion: `success`
- URL: `https://github.com/MarwanMAlfalah/vendor-agnostic-industrial-orchestrator/actions/runs/26346770533`

## Non-Claims

- No production deployment claim.
- No live PLC integration claim.
- No certified safety or regulatory compliance claim.
- Docker and Kubernetes evidence demonstrate local reproducibility and containerized deployment
  feasibility only.
- Mock OPC UA-style, REST, and legacy services are deterministic integration proxies, not real
  industrial controllers.
- LangSmith demonstrates observability and debugging support, not industrial validation.

