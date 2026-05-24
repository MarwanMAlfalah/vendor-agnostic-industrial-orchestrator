# IJTech Threats To Validity Final Candidate

## Synthetic Scenarios

The scaled evaluation uses generated deterministic scenarios rather than field data from an industrial plant. The scenarios are useful for controlled coverage of governance and interoperability conditions, but they may not capture the full variability of real industrial operations.

## Mock Adapters

The prototype uses mock OPC UA, REST, and legacy adapters. These adapters provide deterministic responses and support repeatable evaluation. They do not demonstrate live PLC integration, vendor certification, network behavior, physical process dynamics, or device-level safety.

## Deterministic Benchmark

The evaluation is deterministic and does not include stochastic LLM behavior. Wilson intervals are interpreted as scenario-distribution intervals over the finite generated benchmark, not as estimates of random model uncertainty.

## Runtime-Specific Alignment Risks

Runtime-specific expectation alignment improves fairness when runtimes support different capabilities, but it also introduces a methodological risk: poorly documented alignment could hide failures. This package mitigates the risk by preserving original labels, documenting alignment rules, and keeping unsafe execution and approval bypass non-compliant for all runtimes.

## Baseline Scope

The baselines are deterministic governance-ablated comparisons. They are useful for revealing policy risk, but they are not intended to represent every possible industrial orchestration product or all production engineering alternatives.

## Local Latency

Latency measurements are local runtime measurements. They should not be interpreted as industrial timing guarantees, real-time control benchmarks, network latency estimates, or PLC cycle-time evidence.

## Recovery Demonstration Scope

The crash/restart evidence is a local LangGraph checkpoint demonstration using SQLite persistence. It shows that checkpointed workflow state can be resumed in the prototype setting. It does not demonstrate distributed fault tolerance, production deployment, operational high availability, or plant recovery procedures.

## LangSmith Evidence

LangSmith traces support observability, debugging, and figure preparation. They are not industrial deployment evidence and do not independently validate safety, regulatory compliance, or live integration.

## Containerized And Kubernetes Evidence Scope

Docker Compose and local kind Kubernetes artifacts support reproducibility of the deterministic prototype package. They show that the orchestrator, mock services, jobs, checkpoint PVC, health endpoint, and logs can be exercised in local containerized environments. They do not demonstrate production deployment, live plant networking, operational high availability, cybersecurity readiness, real-time guarantees, or operator acceptance. Docker Desktop or kind control-plane logs are infrastructure logs, not application evidence.

The Kubernetes evidence should be interpreted as local kind evidence only. The corrected application log is `data/results/k8s_logs/orchestrator.log`; the zero-byte `orchestrator-api.log` is an obsolete artifact from using the Service name as though it were a Deployment name. This naming mismatch was an evidence collection issue, not a runtime failure.

## No Production Or Safety Certification Claim

The evidence is prototype-level. It does not claim production deployment, certified safety, operator acceptance, cybersecurity validation, live PLC integration, or regulatory compliance.

Figures and screenshots used in the manuscript or supplement should preserve this boundary. Kubernetes screenshots may show local pods, jobs, service health, and logs; LangSmith screenshots may show redacted trace structure; Docker screenshots may show local mock-service topology. None should be captioned as production, field, or certified safety evidence.
