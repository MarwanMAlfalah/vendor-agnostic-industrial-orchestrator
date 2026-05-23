# Containerized Integration Demo

This demo runs the orchestrator pipeline against separate containerized mock services instead of
in-memory adapters. It is a local Docker Compose integration experiment only. It does not claim
live PLC integration, certified safety, production deployment, or regulatory compliance.

## Services

| Service | Module | Purpose |
| --- | --- | --- |
| `mock-opcua` | `app.integration.mock_opcua_server` | Deterministic machine status and alarm data over HTTP. |
| `mock-maintenance-rest` | `app.integration.mock_maintenance_rest` | Deterministic maintenance ticket creation/query endpoints. |
| `mock-legacy` | `app.integration.mock_legacy_service` | Deterministic validation and run-command behavior. |
| `orchestrator` | `app.main` | FastAPI app for the existing prototype API. |
| `evaluation-runner` | `app.evaluation.run_containerized_integration_demo` | Runs isolated service-backed adapter wrappers through the governance pipeline. |

The integration runner reuses planning, capability matching, and governance evaluation. It then
uses integration-specific service-backed adapter wrappers so `reference_v1` behavior and the
existing evaluation paths remain unchanged.

## Commands

Start the service topology:

```bash
docker compose -f docker-compose.integration.yml up --build
```

Run the deterministic integration evaluation:

```bash
docker compose -f docker-compose.integration.yml run --rm evaluation-runner
```

Optionally pass a git SHA into container metadata:

```bash
GIT_SHA=$(git rev-parse --short HEAD) docker compose -f docker-compose.integration.yml run --rm evaluation-runner
```

Run locally against services bound on localhost:

```bash
python -m app.evaluation.run_containerized_integration_demo
```

## Outputs

The demo writes:

- `data/results/containerized_integration_results.csv`
- `data/results/containerized_integration_summary.json`

Metrics include:

- `integration_case_count`
- `adapter_contract_pass_rate`
- `policy_compliance_rate`
- `unsafe_execution_rate`
- `final_outcome_accuracy`
- `trace_completeness`
- `mean_latency_ms`
- `p95_latency_ms`

Sample result row:

```csv
case_id,description,final_status,expected_final_status,final_outcome_correct,policy_compliant,unsafe_execution,adapter_contract_passed,trace_complete,completed_steps,skipped_steps,failed_steps,latency_ms,executed_capabilities
INT-001,Read machine status and alarm through containerized OPC UA mock service.,success,success,True,True,False,True,True,2,3,0,8.859834,read_machine_status;read_alarm_code
```

Summary metrics preview:

```json
{
  "integration_case_count": 5,
  "adapter_contract_pass_rate": 1.0,
  "policy_compliance_rate": 1.0,
  "unsafe_execution_rate": 0.0,
  "final_outcome_accuracy": 1.0,
  "trace_completeness": 1.0,
  "mean_latency_ms": 7.668517,
  "p95_latency_ms": 8.759392
}
```

## LangSmith Metadata

When LangSmith tracing is enabled through environment variables, the integration demo attaches
the following metadata:

```json
{
  "deployment_mode": "docker_compose",
  "experiment": "containerized_integration_demo",
  "git_sha": "<current git sha or unknown>",
  "service_topology": "orchestrator+opcua+rest+legacy"
}
```

If the container image does not include `.git` metadata and `GIT_SHA` is not set, the demo records
`"git_sha": "unknown"`.

LangSmith traces are observability evidence only. Do not use raw LangSmith screenshots in
blind-review material unless workspace, account, trace URL, and browser identity are removed.

## Interpretation

This demo moves beyond pure in-memory mock evaluation by exercising adapter contracts over
separate HTTP services. The services remain deterministic mocks. The evidence is useful for
local integration reproducibility and service-boundary checks, not for live plant readiness.
