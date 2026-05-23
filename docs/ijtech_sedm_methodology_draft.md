# Methodology Draft

## Reference Architecture

The prototype is organized as a supervisory orchestration stack. A goal is first converted into a deterministic plan. Plan steps are then matched to a capability registry that maps required capabilities to available adapter implementations. A governance layer evaluates each mapped step and assigns one of the supported decisions: `ALLOW`, `REQUIRE_APPROVAL`, `BLOCK`, `FALLBACK`, or `SAFE_ABORT`. The execution layer invokes only governance-compatible adapter calls and records step-level outcomes, final status, skipped steps, failed steps, and latency.

The implementation uses mock adapters for OPC UA, REST, and legacy vendor-style capabilities. These adapters provide deterministic responses and are intended for controlled evaluation, not live plant integration.

## Runtime Profiles

The `reference_v1` runtime supports deterministic planning, capability matching, governance evaluation, governance-aware execution, blocking unsafe actions, safe abort behavior, and approval-required stopping behavior. It does not support controlled post-approval execution, graph-native interrupt/resume, checkpoint persistence, or restart-safe continuation.

The `langgraph_runtime` supports the same deterministic planning, matching, governance, and execution semantics while adding controlled post-approval continuation, approval interrupt/resume, checkpoint persistence, restart-safe continuation, and graph-native trace markers. It is used to evaluate runtime-level capabilities beyond the basic reference path.

Three baselines are included. Baseline A executes mapped adapter steps directly without governance enforcement. Baseline B uses a single-stage execution heuristic instead of explicit planner/matcher separation. Baseline C keeps matched steps but removes policy filtering. These baselines are intentionally limited and are used to reveal policy risks rather than to represent complete industrial competitors.

## Scenario Generator

The scaled evaluation uses a deterministic scenario generator with a fixed seed. It balances scenarios across workflow length, governance pattern, adapter mix, approval condition, containment condition, and runtime applicability. Workflow lengths include short, medium, and long workflows. Governance patterns include all-allow workflows, approval gates, blocked actions, safe aborts, mixed workflows, post-approval cases, invalid mappings, unavailable capabilities, and malformed payload conditions.

Three profiles are generated:

- default profile: 120 scenarios;
- journal profile: 240 scenarios;
- extended profile: 500 scenarios.

The journal profile is used for the main manuscript tables. The extended profile provides additional stress coverage and reproducibility depth.

## Metrics

The evaluation reports policy compliance, unsafe execution, approval bypass, final outcome accuracy, governance decision accuracy, invalid mapping containment, trace completeness, restart recovery where applicable, and latency summaries. Wilson 95% confidence intervals are used for proportion metrics. Since the benchmark is deterministic, these intervals are interpreted as scenario-distribution intervals rather than stochastic model uncertainty.

## Runtime-Specific Expectation Alignment

The original scaled evaluation used one global expected final status per scenario. The error audit showed that this can unfairly penalize runtimes with different supported capabilities. For example, `reference_v1` intentionally stops at `approval_required` and does not perform controlled post-approval continuation. Conversely, `langgraph_runtime` may correctly reach `success` after a valid approval and revalidation.

The aligned evaluation therefore keeps original scenario labels as descriptive labels, but adds runtime-specific expected outcomes. Alignment does not remove scenarios, hide negative results, or excuse unsafe behavior. Unsafe execution and approval bypass remain non-compliant for all runtimes. Each aligned result row includes the original expected label, aligned expected label, and the documented rule used for alignment.
