# IJTech Methodology Final Candidate

## Reference Architecture

The prototype is organized as a supervisory orchestration stack. A goal is converted into a deterministic plan. Plan steps are matched to a capability registry that maps required capabilities to available adapter implementations. A governance layer evaluates each mapped step and assigns one of the supported decisions: `ALLOW`, `REQUIRE_APPROVAL`, `BLOCK`, `FALLBACK`, or `SAFE_ABORT` (Author, year). The execution layer invokes only governance-compatible adapter calls and records step-level outcomes, final status, skipped steps, failed steps, latency, and trace markers.

The adapter layer contains mock OPC UA, REST, and legacy vendor-style capabilities. These adapters provide deterministic responses and are used for controlled evaluation only. They do not demonstrate live PLC integration, vendor certification, network behavior, device-level control, or production safety.

## Runtime Profiles

The `reference_v1` runtime supports deterministic planning, capability matching, governance evaluation, governance-aware execution, blocking unsafe actions, safe-abort behavior, approval-required stopping behavior, and trace recording. It does not support controlled post-approval execution, graph-native interrupt/resume, checkpoint persistence, or restart-safe continuation.

The `langgraph_runtime` supports the same deterministic planning, matching, governance, and execution semantics while adding controlled post-approval continuation, approval interrupt/resume, checkpoint persistence, restart-safe continuation, and graph-native trace markers. It is used to evaluate runtime-level capabilities beyond the basic reference path.

Three baselines are included. Baseline A executes mapped adapter steps directly without governance enforcement. Baseline B uses a single-stage execution heuristic instead of explicit planner/matcher separation. Baseline C keeps matched steps but removes policy filtering. These baselines are intentionally limited and are used to reveal policy risks rather than to represent complete industrial competitors.

## Scenario Generator

The scaled evaluation uses a deterministic scenario generator with fixed configuration. It balances scenarios across workflow length, governance pattern, adapter mix, approval condition, and failure or containment condition (Author, year). Workflow lengths include short, medium, and long workflows. Governance patterns include all-allow workflows, approval gates, blocked actions, safe aborts, mixed workflows, post-approval cases, invalid mappings, unavailable capabilities, and malformed payload conditions.

Three profiles are available:

| Profile | Scenario count | Manuscript role |
| --- | ---: | --- |
| Default | 120 | Development and ablation support |
| Journal | 240 | Main IJTech manuscript tables |
| Extended | 500 | Additional deterministic coverage and reproducibility depth |

The 240-scenario journal profile is the main source for the manuscript tables. The 500-scenario extended profile is used to show that the scenario design and aggregate patterns extend beyond the main journal profile without introducing claims about field deployment.

## Metrics

The evaluation reports policy compliance, unsafe execution, approval bypass, final outcome accuracy, governance decision accuracy, invalid mapping containment, trace completeness, restart recovery where applicable, and latency summaries. Wilson 95% confidence intervals are used for proportion metrics. Since the benchmark is deterministic, these intervals are interpreted as scenario-distribution intervals over a finite generated benchmark, not as stochastic model uncertainty (Author, year).

The main manuscript emphasizes policy-centric metrics. In governed industrial workflows, the correct outcome may be non-execution: a workflow can be correct when it stops for approval, blocks a prohibited step, or safe-aborts after invalid mapping or malformed payload detection. Therefore, raw execution coverage or apparent task completion is insufficient.

## Runtime-Specific Expectation Alignment

The original scaled evaluation used one global expected final status per scenario. The error audit showed that this can unfairly penalize runtimes with different supported capabilities. For example, `reference_v1` intentionally stops at `approval_required` and does not perform controlled post-approval continuation. Conversely, `langgraph_runtime` may correctly reach `success` after valid approval and revalidation.

The aligned evaluation keeps original scenario labels as descriptive labels but adds runtime-specific expected outcomes. Alignment does not remove scenarios, hide negative results, or excuse unsafe behavior. Unsafe execution and approval bypass remain non-compliant for all runtimes. Each aligned result row includes the original expected label, aligned expected label, and the documented rule used for alignment.

## Reproducibility

For reproducibility, the evaluation artifacts are organized around deterministic scenario profiles and generated result tables. The main manuscript uses the current 240-scenario journal profile, the 500-scenario extended profile, and the existing CSV/JSON summaries for baseline comparison, aligned metrics, latency, supported-versus-stress scope, and figure data. Reproduction should preserve the same deterministic scenario configuration, runtime profiles, and mock-adapter setting; regenerated outputs should be compared against the provided result summaries before being used in a revised manuscript.

The final validation package adds containerized and local Kubernetes reproducibility checks around the same deterministic prototype. Docker Compose runs the orchestrator against separate local mock OPC UA-style, REST, and legacy service containers. The local kind Kubernetes run uses the existing image, manifests, `orchestrator` Deployment, `orchestrator-api` Service, checkpoint PVC, scaled-evaluation job, crash/restart job, and health endpoint. Captured Kubernetes artifacts include non-empty deployment and job logs, events, Deployment/Service descriptions, and `health_response.json` with `status=ok`. These artifacts document reproducibility of the software package in local environments; they do not alter evaluation metrics or introduce production claims.

Local validation closes the evidence package with `python -m ruff check app tests`, `python -m pytest` with 45 tests, `make lint`, `make test` with 45 tests and 56% coverage, and a passing `RESULTS_MANIFEST.json` hash check. Evaluation tests write generated outputs to temporary pytest directories, preventing accidental mutation of committed result artifacts. The frozen manifest therefore remains an integrity check for the committed evidence package.

## Supported And Stress Scope

Supported-scope scenarios represent behavior within the intended implemented capability of a runtime. Stress-scope scenarios exercise edge conditions such as malformed payloads, unavailable capabilities, invalid mappings, invalid or missing approvals, invalidated post-approval mappings, and safe-abort paths. Stress cases are retained and reported separately. They are not removed from aggregate results.

## LangGraph Continuation And Recovery Evaluation

The LangGraph runtime is evaluated for controlled approval continuation, approval validation, revalidation after approval, graph-native trace markers, and checkpoint-based recovery. The crash/restart demonstration uses local SQLite checkpoint persistence: the workflow reaches an approval interrupt, state is persisted, a process stop is simulated, the runtime is reopened with the same checkpoint database and thread identifier, approval input is supplied, and the workflow reaches the expected final result. This is local prototype recovery evidence, not production deployment evidence.

## Observability Evidence

LangSmith is used only as observability evidence. Traces can support debugging, auditability, and figure preparation by recording stages such as planning, matching, governance, approval interrupt, approval resume, approved execution, execution, and final result. LangSmith traces do not validate industrial deployment, certified safety, or live PLC readiness.

Recommended manuscript figure insertion points are: an architecture figure in the methodology section, a scenario-factor design figure after the scenario generator description, a Docker/Kubernetes reproducibility evidence figure or table after the reproducibility subsection, and a redacted LangSmith trace screenshot after the observability subsection. Screenshots should be sanitized to remove account identifiers, browser identity, API keys, and private URLs.
