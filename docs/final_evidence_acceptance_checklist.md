# Final Evidence Acceptance Checklist

This checklist records the final local evidence verification pass. It does not make production,
live PLC, or certified safety claims.

## Verification Commands

| Check | Command or source | Observed status |
| --- | --- | --- |
| Local lint | `ruff check app tests` | Passed: `All checks passed!` |
| Local tests | `python3 -m pytest` | Passed: `44 passed` |
| Docker Compose integration | `docker compose -f docker-compose.integration.yml up --build -d ...` and `docker compose -f docker-compose.integration.yml run --rm evaluation-runner` | Passed; `data/results/containerized_integration_summary.json` updated with `git_sha=36853bd`. |
| LangSmith traces | LangSmith API query for project `vendor-agnostic-industrial-orchestrator` | Passed; `data/results/langsmith_trace_manifest.csv` contains 7 trace rows. |
| Local Kubernetes kind | `kind create cluster --name vendor-orchestrator`, image load, `kubectl apply`, waits, logs, events, describes, and port-forward health check | Passed. API pod ran, both jobs completed, health returned `status=ok`, and non-empty deployment/job logs were captured. |
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
| `data/results/k8s_logs/orchestrator.log` | Non-empty corrected Deployment log for `deployment/orchestrator`. |
| `data/results/k8s_logs/scaled-evaluation-job.log` | Non-empty completed job log. |
| `data/results/k8s_logs/crash-restart-demo-job.log` | Non-empty completed job log. |
| `data/results/k8s_logs/events.txt` | Non-empty Kubernetes event log from the local kind namespace. |
| `data/results/k8s_logs/health_response.json` | Contains `status=ok`. |

## Kubernetes Evidence Classification

Kubernetes evidence is classified as actual local kind evidence because the final pass observed:

- kind cluster creation for `vendor-orchestrator`;
- local image load for `vendor-orchestrator:local`;
- `orchestrator` deployment available in namespace `vendor-orchestrator`;
- `orchestrator-api` Service available in namespace `vendor-orchestrator`;
- `scaled-evaluation-job` completed successfully;
- `crash-restart-demo-job` completed successfully;
- `kubectl port-forward svc/orchestrator-api 8001:8000 -n vendor-orchestrator`;
- `curl -fsS http://localhost:8001/health` returned `status=ok`.

The first `kubectl apply -f deploy/k8s/base/` encountered namespace ordering errors for some
resources; a second apply succeeded. This is recorded as a local apply behavior, not a runtime
logic issue.

The earlier zero-byte `data/results/k8s_logs/orchestrator-api.log` was caused by using the Service
name as though it were a Deployment name. The corrected application log is
`data/results/k8s_logs/orchestrator.log`. Docker Desktop or kind control-plane logs are
infrastructure/node logs and are not counted as application evidence.

## LangSmith Evidence Classification

LangSmith evidence is observability evidence only. The trace manifest includes Docker Compose,
local Kubernetes summary, crash/restart, and representative scaled-evaluation traces. Traces do
not participate in governance decisions and do not validate industrial deployment. The exposed key
was rotated; no LangSmith API key is stored in repository artifacts. Prefer clean-revision traces;
dirty revision traces are retained only where no cleaner replacement exists.

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
