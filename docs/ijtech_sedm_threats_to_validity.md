# Threats To Validity

## Synthetic Scenarios

The scaled evaluation uses generated deterministic scenarios rather than field data from an industrial plant. The scenarios are useful for controlled coverage of governance and interoperability conditions, but they may not capture the full variability of real industrial operations.

## Mock Adapters

The prototype uses mock OPC UA, REST, and legacy adapters. These adapters provide deterministic responses and support repeatable evaluation. They do not demonstrate live PLC integration, vendor certification, network behavior, or device-level safety.

## Deterministic Benchmark

The evaluation is deterministic and does not include stochastic LLM behavior. Wilson intervals are interpreted as scenario-distribution intervals over the finite generated benchmark, not as estimates of random model uncertainty.

## No Production Deployment

The evidence is prototype-level. It does not claim production deployment, certified safety, operator acceptance, cybersecurity validation, or regulatory compliance.

## Local Latency

Latency measurements are local runtime measurements. They should not be interpreted as industrial timing guarantees or real-time control benchmarks.

## Runtime-Specific Alignment Risks

Runtime-specific expectation alignment improves fairness when runtimes support different capabilities, but it also introduces a methodological risk: poorly documented alignment could hide failures. This package mitigates the risk by preserving original labels, documenting every rule, and keeping unsafe execution and approval bypass non-compliant for all runtimes.

## LangSmith Evidence

LangSmith traces support observability, debugging, and figure preparation. They are not industrial deployment evidence and do not independently validate safety.
