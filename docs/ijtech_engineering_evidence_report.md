# IJTech Engineering Evidence Consolidation Report

This report consolidates generated engineering evidence for the deterministic industrial
orchestrator prototype. It uses only repository artifacts already generated under `data/results`,
`docs`, `.github`, and deployment manifests. It does not introduce new scientific metrics or
change runtime/business logic.

## Evidence Sources

| Category | Artifact(s) | Role in evidence package |
| --- | --- | --- |
| Synthetic scaled evaluation | `data/results/scaled_evaluation_summary_journal.json`; `data/results/scaled_evaluation_results_journal.csv` | Main deterministic empirical evidence for `reference_v1`, `langgraph_runtime`, and baselines across the 240-scenario journal profile. |
| Dockerized integration | `data/results/containerized_integration_summary.json`; `data/results/containerized_integration_results.csv`; `docker-compose.integration.yml` | Local service-boundary evidence using separate containerized mock OPC UA-style, REST, and legacy services. |
| Local Kubernetes reproducibility | `data/results/k8s_reproducibility_summary.json`; `data/results/k8s_reproducibility_results.csv`; `deploy/k8s/base/` | Actual local kind execution evidence with API deployment, completed jobs, probes, resource bounds, ConfigMap, Secret example, service health check, and checkpoint PVC. |
| LangSmith observability | `data/results/langsmith_trace_manifest.csv`; `docs/langsmith_trace_examples.md`; `docs/langsmith_trace_usage.md`; `docs/langsmith_setup.md` | Queried LangSmith trace IDs and documented trace markers for deterministic traces and metadata. |
| GitHub Actions CI | `.github/workflows/ci.yml`; GitHub Actions run `26346770533` | CI workflow and verified public run status for Python 3.11 install, lint, and tests. |

## Consolidated Table Preview

| Mode | Runtime/evidence | Cases or runs | Policy compliance | Unsafe execution | Final outcome accuracy | Trace completeness | p95 latency ms | Evidence interpretation |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Local synthetic scaled | `reference_v1` | 240 | `0.8542` | `0.0` | `0.875` | `1.0` | `0.075116` | Deterministic governance-aware reference runtime evidence. |
| Local synthetic scaled | `langgraph_runtime` | 240 | `0.9792` | `0.0` | `0.9792` | `1.0` | `3.815129` | Deterministic graph-runtime approval/checkpoint evidence. |
| Docker Compose | containerized mock service integration | 5 | `1.0` | `0.0` | `1.0` | `1.0` | `8.625191` | Actual Docker Compose service-boundary run against separate local mock containers. |
| Kubernetes local kind | actual reproducibility run | 1 summary row | n/a | n/a | n/a | `1.0` | `2.235687` | Actual kind run with API pod, completed jobs, port-forward health check, and checkpoint PVC evidence. |
| LangSmith optional | queried observability traces | 7 trace rows | n/a | n/a | n/a | n/a | n/a | Observability/debugging support only. |
| GitHub Actions | CI workflow run | 1 run | n/a | n/a | n/a | n/a | n/a | Public CI run completed successfully. |

The machine-readable companion table is `data/results/deployment_mode_comparison.csv`.

## Updated Results Narrative

The empirical evidence now combines deterministic local evaluation with containerized and local
Kubernetes reproducibility artifacts. In the 240-scenario synthetic journal profile, the
`reference_v1` runtime achieved policy compliance of `0.8542`, unsafe execution of `0.0`, final
outcome accuracy of `0.875`, trace completeness of `1.0`, and p95 latency of `0.075116 ms`.
The `langgraph_runtime` achieved policy compliance of `0.9792`, unsafe execution of `0.0`, final
outcome accuracy of `0.9792`, trace completeness of `1.0`, and p95 latency of `3.815129 ms`.
The Docker Compose integration artifact adds five deterministic service-boundary cases using
containerized OPC UA-style, REST, and legacy mock services, with adapter contract pass rate
`1.0`, policy compliance `1.0`, unsafe execution `0.0`, final outcome accuracy `1.0`, and trace
completeness `1.0`. The local Kubernetes kind artifact records completed evaluation and
crash/restart jobs, observed service health through port forwarding, checkpoint PVC use, and
crash/restart demo success, with trace completeness `1.0`. These artifacts strengthen the engineering reproducibility evidence
for the prototype while preserving the original scope: deterministic synthetic and mock-service
experiments rather than production industrial deployment.

## LangSmith Evidence Framing

LangSmith is included as optional observability evidence. The final verification pass queried
seven trace rows in `data/results/langsmith_trace_manifest.csv`, including Docker Compose,
Kubernetes-summary, crash/restart, and representative scaled-evaluation traces. The generated
summaries contain metadata previews for Docker Compose and local Kubernetes contexts, including
`deployment_mode`, `experiment`, `git_sha`, `service_topology`, `k8s_namespace`,
`k8s_job_name`, and `image_tag`.
The LangSmith documentation identifies useful trace markers such as `planner_node`,
`matcher_node`, `governance_node`, `approval_interrupt`, `approval_resume`,
`approval_validated`, `approved_execution`, `execution_node`, and `final_result`.

This supports inspection and debugging of deterministic experiment structure. It does not
participate in policy decisions and does not establish industrial validation, safety
certification, or production readiness.

## GitHub Actions Evidence Framing

The repository contains `.github/workflows/ci.yml`, which configures a Python 3.11 CI workflow to
install the package with development dependencies, run `ruff check app tests`, and run `pytest`.
The final verification pass also queried the public GitHub Actions API and recorded run
`26346770533` for commit `36853bdc7363d6b587606ddd11f9cf5803accd37` with status `completed` and
conclusion `success`. This is software quality evidence only, not industrial deployment evidence.

## Limitations And Non-Claims

The additional engineering evidence does not change the scientific claim boundary. Docker and
Kubernetes artifacts demonstrate local reproducibility and containerized deployment feasibility,
not production deployment, high availability, cybersecurity readiness, real-time guarantees, or
industrial certification. The OPC UA-style, REST, and legacy services used in the Docker demo are
deterministic mock services and integration proxies, not live PLCs, SCADA systems, or vendor
certified controllers. LangSmith traces and metadata support observability, debugging, and
inspection of deterministic execution structure, but they do not validate industrial safety,
regulatory compliance, physical process behavior, or live plant integration. GitHub Actions CI
success is lint/test automation evidence only and does not validate industrial operation.

## Recommended Manuscript Insertion Points

1. Methods / Implementation: describe the evidence stack as local deterministic evaluation,
   Docker Compose mock-service integration, and actual local kind reproducibility evidence.
2. Results: add the updated results narrative after the main scaled-evaluation results table.
3. Reproducibility Package: cite `data/results/deployment_mode_comparison.csv` and
   `data/results/evidence_manifest.json` as the consolidated artifact index.
4. Threats to Validity: add the limitations and non-claims paragraph, explicitly distinguishing
   mock-service integration from live PLC integration.
5. Supplementary Material: include `docs/ijtech_reproducibility_evidence_table.md` as an evidence
   table for reviewers.
