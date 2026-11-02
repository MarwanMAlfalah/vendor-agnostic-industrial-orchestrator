# IJTech Results Final Candidate

## Canonical Governance Comparison

The canonical comparison evaluates 12 deterministic cases covering allowed actions, approval-required actions, blocked actions, and safe-abort conditions. In these controlled cases, the reference governance-aware execution path achieves policy compliance of 1.0, unsafe execution of 0.0, governance decision accuracy of 1.0, and final outcome accuracy of 1.0. The deterministic baselines show why raw execution success is insufficient. Baseline B, for example, reaches execution coverage of 1.0 in the unified table but has policy compliance of 0.25 and unsafe execution of 1.0. This supports the claim that policy-centric metrics are necessary for governed industrial workflows.

## Journal Scenario Profile

The main IJTech profile contains 240 deterministic scenarios. The scenario design is balanced across 12 governance patterns, each represented by 20 scenarios: `all_allow`, `allow_then_block`, `allow_then_require_approval`, `allow_then_safe_abort`, `invalid_mapping`, `malformed_payload`, `mixed_allow_approval_block`, `mixed_allow_approval_safe_abort`, `post_approval_invalid`, `post_approval_missing`, `post_approval_valid`, and `unavailable_capability`. Workflow length is balanced across 80 short, 80 medium, and 80 long workflows. Adapter mix includes OPC UA only, REST only, legacy only, OPC UA plus REST, OPC UA plus legacy, REST plus legacy, and OPC UA plus REST plus legacy.

The extended profile contains 500 deterministic scenarios and is used as additional coverage evidence. It preserves the same factor structure while increasing the number of generated cases. In the extended original metrics, `reference_v1` has policy compliance of 0.854, final outcome accuracy of 0.876, unsafe execution of 0.0, and trace completeness of 1.0; `langgraph_runtime` has policy compliance of 0.978, final outcome accuracy of 0.978, unsafe execution of 0.0, and trace completeness of 1.0. Baseline A and Baseline C both show conditional unsafe execution of 1.0 in the extended profile.

## Original And Aligned Journal Metrics

Original and aligned metrics are both reported. Under the original global labels in the 240-scenario journal profile, `reference_v1` has policy compliance of 0.854167 and final outcome accuracy of 0.875, while `langgraph_runtime` has policy compliance and final outcome accuracy of 0.979167. These original metrics retain the global scenario expectations and show where runtime capability differences affect interpretation.

The aligned evaluation corrects runtime-capability mismatches by evaluating `reference_v1` as a non-continuation runtime and `langgraph_runtime` as a controlled-continuation runtime. Under original global labels in the 240-scenario journal profile, `reference_v1` has policy compliance of 0.854167 and final outcome accuracy of 0.875, while `langgraph_runtime` has policy compliance and final outcome accuracy of 0.979167. Under documented aligned expectations for the deterministic mock-adapter scope, both proposed runtimes report policy compliance of 1.0, final outcome accuracy of 1.0, unsafe execution of 0.0, approval bypass of 0.0, invalid mapping containment of 1.0, and trace completeness of 1.0.

| Runtime | Original policy compliance | Aligned policy compliance | Aligned final outcome accuracy | Unsafe execution | Approval bypass | Trace completeness |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `baseline_a_direct_without_governance` | 0.0 | 0.0 | 0.166667 | 1.0 | 1.0 | 0.0 |
| `baseline_b_single_stage_execution` | 0.083333 | 0.083333 | 0.166667 | 0.0 | 0.0 | 0.0 |
| `baseline_c_without_policy_filtering` | 0.5 | 0.416667 | 0.583333 | 1.0 | 1.0 | 0.0 |
| `langgraph_runtime` | 0.979167 | 1.0 | 1.0 | 0.0 | 0.0 | 1.0 |
| `reference_v1` | 0.854167 | 1.0 | 1.0 | 0.0 | 0.0 | 1.0 |

## Baseline Comparison

The aligned journal comparison shows substantial separation between governance-aware runtimes and governance-ablated baselines. Baseline A, direct execution without governance, has aligned policy compliance of 0.0, conditional unsafe execution of 1.0, conditional approval bypass of 1.0, and trace completeness of 0.0. Baseline C, without policy filtering, has aligned policy compliance of 0.416667 and conditional unsafe execution of 1.0. Baseline B avoids unsafe execution in this aligned table but has aligned policy compliance of only 0.083333 and final outcome accuracy of 0.166667.

Relative to Baseline A, both proposed runtimes improve aligned policy compliance by 1.0 and reduce conditional unsafe execution by 1.0. Relative to Baseline B, both improve aligned policy compliance by 0.916667. Relative to Baseline C, both improve aligned policy compliance by 0.583333 and reduce conditional unsafe execution by 1.0. These results indicate that removing governance or architectural stages can produce technically completed executions that do not satisfy policy requirements.

## Supported Versus Stress Scope

The aligned supported/stress split is runtime-specific and should be read alongside the original aggregate metrics above. For `reference_v1`, supported-scope scenarios have aligned policy compliance of 1.0, final outcome accuracy of 1.0, unsafe execution of 0.0, and trace completeness of 1.0 within its non-continuation capability profile. Its stress-scope rows also show aligned containment of 1.0, reflecting that the alignment treats post-approval continuation as outside its capability profile while preserving containment expectations. For `langgraph_runtime`, supported-scope and stress-scope rows both show aligned policy compliance of 1.0, unsafe execution of 0.0, and trace completeness of 1.0 within the deterministic continuation-capable profile.

Baselines remain weak in stress scope. Baseline A has stress-scope conditional unsafe execution of 1.0. Baseline C has stress-scope conditional unsafe execution of 1.0 and aligned policy compliance of 0.222222. These stress results are retained to show how runtimes behave under malformed payloads, unavailable capabilities, invalid mappings, invalid or missing approvals, invalidated mappings after approval, and safe-abort paths.

## LangGraph Approval Continuation

The post-approval continuation experiment distinguishes recording approval requirements from controlled continuation after explicit approval. `reference_v1` is policy-correct as a non-continuation runtime but does not execute gated steps after approval. `langgraph_runtime` supports approval interrupt/resume, approval validation, revalidation of mapping eligibility, and controlled execution of approved steps. In the unified report, the LangGraph post-approval comparison reports 1.0 for approval validation accuracy, approved step execution rate, post-resume final outcome accuracy, gated step policy compliance, and approved execution trace completeness within the local deterministic continuation tests.

## Crash/Restart Persistence

The same-process checkpoint reopen/resume demo uses a SQLite LangGraph checkpointer. It demonstrates that a workflow can reach an approval interrupt, persist checkpoint state, close the runtime/checkpointer within the same Python process, reopen the runtime with the same checkpoint database and thread identifier, resume with approval input, and reach the expected final result. The unified report records checkpoint resume success, checkpoint reopen/resume success, post-reopen final outcome accuracy, and checkpoint reopen trace completeness as 1.0 for this local demo, which is separate from the original scaled metrics and does not imply production recovery capability. This is checkpoint recovery evidence in a deterministic prototype, not evidence of production deployment.

## LangSmith Observability

LangSmith tracing is used as optional observability evidence. It records experiment-level and child span outputs for stages such as planning, matching, governance, approval interrupt, approval resume, approved execution, execution, and final result. These traces support debugging, auditability, and figure preparation. They do not validate industrial deployment, certified safety, or live PLC integration.

## Reproducibility Evidence Integration

The final evidence package adds reproducibility artifacts around the deterministic result tables without changing the scientific metrics. Docker Compose evidence shows local service-boundary execution against separate mock OPC UA-style, REST, and legacy service containers. Kubernetes evidence comes from an actual local kind run with the `orchestrator` Deployment, `orchestrator-api` Service, completed scaled-evaluation and crash/restart jobs, a bound checkpoint PVC, non-empty application/job/event logs, Deployment and Service descriptions, and a port-forwarded health response with `status=ok`. LangSmith trace evidence is available for observability and debugging after key rotation. The frozen manifest validation passes, and the scaled evaluation tests no longer mutate committed `data/results/` or `docs/` artifacts.

| Evidence category | Representative artifacts | Result-section use | Figure or screenshot insertion point |
| --- | --- | --- | --- |
| Docker Compose integration | `containerized_integration_summary.json`; `containerized_integration_results.csv` | Supports local mock-service boundary evidence with policy compliance 1.0 and unsafe execution 0.0 in the recorded integration cases. | Optional container topology or command-output screenshot after the Docker evidence paragraph. |
| Kubernetes local kind | `k8s_reproducibility_summary.json`; `k8s_logs/orchestrator.log`; job logs; events; health response | Supports local Kubernetes reproducibility with completed jobs, service health, checkpoint PVC, and non-empty logs. | Insert a compact screenshot of `kubectl get pods`, `kubectl get jobs`, and health response near the Kubernetes paragraph. |
| LangSmith traces | `langsmith_trace_manifest.csv`; `docs/langsmith_trace_usage.md` | Supports observability, trace inspection, and figure preparation only. | Insert a redacted trace screenshot after the LangGraph continuation or observability paragraph. |
| Manifest validation | `RESULTS_MANIFEST.json`; `RESULTS_METADATA_INDEX.*`; closure note | Supports artifact integrity and non-mutating test behavior. | Optional supplementary screenshot of passing validation commands. |

These evidence sources should be described as reproducibility and observability support for a deterministic prototype. They should not be described as production deployment, live PLC integration, certified safety, regulatory compliance, or field validation.
