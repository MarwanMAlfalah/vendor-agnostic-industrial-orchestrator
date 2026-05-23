# Kubernetes Reproducibility Demo

This demo adds a local Kubernetes packaging and reproducibility path for the orchestrator. It is
intended for Docker Desktop Kubernetes or kind on a local Mac. It does not change runtime logic,
business logic, adapter behavior, or scientific metrics.

The evidence scope is deliberately narrow: local Kubernetes reproducibility only. It does not
claim production deployment, live PLC integration, certified safety, regulatory compliance,
industrial network validation, or operational readiness.

## What It Adds

- Kubernetes namespace, ConfigMap, empty Secret example, checkpoint PVC, Deployment, Service, and
  two Jobs under `deploy/k8s/base/`.
- `scaled-evaluation-job`, which runs the existing deterministic journal evaluation.
- `crash-restart-demo-job`, which runs the existing checkpoint crash/restart demo.
- `app.evaluation.run_k8s_reproducibility_summary`, which writes Kubernetes-specific summary
  artifacts without recalculating or changing scientific results.

## Commands

```bash
docker build -t vendor-orchestrator:local .
kind create cluster --name vendor-orchestrator
kind load docker-image vendor-orchestrator:local --name vendor-orchestrator
kubectl apply -f deploy/k8s/base/
kubectl get pods -n vendor-orchestrator
kubectl logs job/scaled-evaluation-job -n vendor-orchestrator
kubectl logs job/crash-restart-demo-job -n vendor-orchestrator
kubectl port-forward svc/orchestrator-api 8001:8000 -n vendor-orchestrator
```

## Expected Pod And Job Outputs

`kubectl get pods -n vendor-orchestrator` should show one running API pod and completed job pods:

```text
NAME                            READY   STATUS      RESTARTS   AGE
orchestrator-...                1/1     Running     0          ...
scaled-evaluation-job-...       0/1     Completed   0          ...
crash-restart-demo-job-...      0/1     Completed   0          ...
```

`kubectl logs job/scaled-evaluation-job -n vendor-orchestrator` should include:

```json
{
  "profile": "journal",
  "scenario_count": 240,
  "result_row_count": 504,
  "summary_path": "data/results/scaled_evaluation_summary_journal.json"
}
```

`kubectl logs job/crash-restart-demo-job -n vendor-orchestrator` should include:

```text
Checkpoint DB: data/langgraph/checkpoints.db
Crash/restart metrics:
  checkpoint_resume_success_rate: 1.0
  restart_recovery_success_rate: 1.0
  post_restart_final_outcome_accuracy: 1.0
  restart_trace_completeness: 1.0
```

## Result Artifacts

The Kubernetes summary script writes:

- `data/results/k8s_reproducibility_results.csv`
- `data/results/k8s_reproducibility_summary.json`

Sample CSV row:

```csv
deployment_mode,k8s_namespace,k8s_job_name,git_sha,image_tag,k8s_job_success,health_endpoint_available,checkpoint_pvc_used,crash_restart_demo_success,trace_completeness,p95_latency_ms,evidence_scope
kubernetes_local,vendor-orchestrator,k8s-reproducibility-summary,d2bee54,vendor-orchestrator:local,True,True,True,True,1.0,1.493592,local_kubernetes_reproducibility_demo
```

Sample JSON metrics:

```json
{
  "k8s_job_success": true,
  "health_endpoint_available": true,
  "checkpoint_pvc_used": true,
  "crash_restart_demo_success": true,
  "trace_completeness": 1.0,
  "p95_latency_ms": 1.493592
}
```

## LangSmith Metadata

When LangSmith tracing is enabled, the Kubernetes summary attaches:

```json
{
  "deployment_mode": "kubernetes_local",
  "k8s_namespace": "vendor-orchestrator",
  "k8s_job_name": "k8s-reproducibility-summary",
  "git_sha": "d2bee54",
  "image_tag": "vendor-orchestrator:local"
}
```

The Secret example intentionally contains no real API key. Add a local secret only outside
blind-review or public artifacts.

## Limitations

This demo provides local Kubernetes reproducibility evidence only. It shows that the existing
orchestrator image and deterministic evaluation jobs can be scheduled with probes, resource
requests/limits, ConfigMap configuration, Secret wiring, and PVC-backed checkpoint persistence in
a local cluster. It does not demonstrate production deployment, certified safety, live PLC
integration, regulatory compliance, high availability, real industrial network behavior, or
operator acceptance.
