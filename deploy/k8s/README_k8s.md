# Local Kubernetes Reproducibility Demo

This directory contains local Kubernetes manifests for Docker Desktop Kubernetes or kind on a
local Mac. The manifests are reproducibility scaffolding only. They do not claim production
deployment, certified safety, live PLC integration, or operational readiness.

## Files

| File | Purpose |
| --- | --- |
| `base/namespace.yaml` | Creates the `vendor-orchestrator` namespace. |
| `base/configmap.yaml` | Stores non-secret local demo configuration. |
| `base/secret.example.yaml` | Creates an empty `langsmith-secret`; replace locally if tracing is needed. |
| `base/pvc-checkpoints.yaml` | Provides local checkpoint persistence for the LangGraph crash/restart demo. |
| `base/deployment-orchestrator.yaml` | Runs the FastAPI orchestrator with readiness/liveness probes and resource bounds. |
| `base/service-orchestrator.yaml` | Exposes the orchestrator as `orchestrator-api` inside the cluster. |
| `base/job-scaled-evaluation.yaml` | Runs the deterministic journal scaled evaluation job. |
| `base/job-crash-restart-demo.yaml` | Runs the checkpoint crash/restart demo job. |

## Commands

Build the local image:

```bash
docker build -t vendor-orchestrator:local .
```

Create a kind cluster:

```bash
kind create cluster --name vendor-orchestrator
```

Load the local image into kind:

```bash
kind load docker-image vendor-orchestrator:local --name vendor-orchestrator
```

Apply the local Kubernetes manifests:

```bash
kubectl apply -f deploy/k8s/base/
```

Check pods:

```bash
kubectl get pods -n vendor-orchestrator
```

Expected shape:

```text
NAME                            READY   STATUS      RESTARTS   AGE
orchestrator-...                1/1     Running     0          ...
scaled-evaluation-job-...       0/1     Completed   0          ...
crash-restart-demo-job-...      0/1     Completed   0          ...
```

Read journal evaluation logs:

```bash
kubectl logs job/scaled-evaluation-job -n vendor-orchestrator
```

Expected log shape:

```json
{
  "profile": "journal",
  "scenario_count": 240,
  "result_row_count": 504,
  "summary_path": "data/results/scaled_evaluation_summary_journal.json"
}
```

Read crash/restart demo logs:

```bash
kubectl logs job/crash-restart-demo-job -n vendor-orchestrator
```

Expected log shape:

```text
Checkpoint DB: data/langgraph/checkpoints.db
Crash/restart summary JSON: data/results/crash_restart_demo_summary.json
Crash/restart metrics:
  checkpoint_resume_success_rate: 1.0
  restart_recovery_success_rate: 1.0
```

Port-forward the API:

```bash
kubectl port-forward svc/orchestrator-api 8001:8000 -n vendor-orchestrator
```

Then check:

```bash
curl http://localhost:8001/health
```

## Optional Metadata

The manifests set the following metadata inputs through `ConfigMap` and downward API values:

```text
deployment_mode=kubernetes_local
k8s_namespace=vendor-orchestrator
k8s_job_name=<job name>
git_sha=<GIT_SHA or unknown>
image_tag=vendor-orchestrator:local
```

To stamp the current commit in local runs, patch or recreate the ConfigMap after applying:

```bash
kubectl create configmap orchestrator-config \
  --namespace vendor-orchestrator \
  --from-literal=ORCHESTRATOR_ENVIRONMENT=kubernetes-local-repro \
  --from-literal=LANGSMITH_TRACING=false \
  --from-literal=LANGSMITH_PROJECT=vendor-agnostic-industrial-orchestrator \
  --from-literal=LANGSMITH_ENDPOINT= \
  --from-literal=DEPLOYMENT_MODE=kubernetes_local \
  --from-literal=IMAGE_TAG=vendor-orchestrator:local \
  --from-literal=GIT_SHA="$(git rev-parse --short HEAD)" \
  --from-literal=HEALTH_CHECK_URL=http://orchestrator-api:8000/health \
  --dry-run=client -o yaml | kubectl apply -f -
```

## Cleanup

```bash
kubectl delete namespace vendor-orchestrator
kind delete cluster --name vendor-orchestrator
```

## Limitations

This is local Kubernetes reproducibility evidence only. It demonstrates that the existing
orchestrator image and deterministic evaluation entrypoints can run under local Kubernetes
objects with probes, resource bounds, non-secret configuration, an empty secret template, and a
checkpoint PVC. It does not establish production deployment, live plant integration, certified
safety, regulatory compliance, high availability, cybersecurity posture, or performance under
industrial network conditions.

