# Governance-Aware Vendor-Agnostic Orchestration for Industrial Workflows: A Deterministic Prototype and IJTech-Oriented Evaluation

## Abstract

Industrial operations often depend on heterogeneous vendor interfaces, including OPC UA endpoints, REST services, and legacy systems. This heterogeneity complicates supervisory orchestration when workflows must preserve governance constraints such as approval gates, blocked actions, invalid mapping containment, and safe-abort behavior. This paper presents a deterministic research prototype for vendor-agnostic, governance-aware industrial orchestration. The prototype separates planning, capability matching, governance evaluation, adapter-mediated execution, and trace recording. It is evaluated against deterministic governance-ablated baselines and an optional LangGraph runtime variant for controlled approval continuation and checkpoint-based recovery.

The evaluation combines canonical governance cases, mixed multi-step workflows, post-approval continuation tests, a local crash/restart persistence demonstration, and a scaled deterministic benchmark. The scaled benchmark includes a 240-scenario journal profile and a 500-scenario extended profile covering workflow length, governance pattern, adapter mix, approval condition, and failure or containment condition. Because runtime capabilities differ, the analysis reports both original global labels and runtime-specific aligned expectations. In the aligned 240-scenario journal profile, `reference_v1` and `langgraph_runtime` both achieve policy compliance of 1.0, final outcome accuracy of 1.0, unsafe execution of 0.0, approval bypass of 0.0, invalid mapping containment of 1.0, and trace completeness of 1.0. Governance-ablated baselines remain substantially weaker: direct execution without governance and execution without policy filtering each show unsafe execution of 0.583333, while the single-stage baseline achieves aligned policy compliance of only 0.083333.

The results provide prototype-level evidence that policy-centric evaluation is essential for industrial orchestration research. The study does not claim production deployment, certified safety, or live PLC integration. All scenarios are deterministic, adapters are mock implementations, and LangSmith traces are used only as observability evidence.

## Keywords

Vendor-agnostic orchestration; industrial workflow governance; OPC UA interoperability; approval-gated execution; safe-abort control; LangGraph runtime; deterministic evaluation; industrial automation middleware.

## 1. Introduction

Industrial software environments are rarely homogeneous. A single operational workflow may need to read machine status from an OPC UA interface, create a maintenance record through a REST service, and validate or invoke a legacy vendor command. This heterogeneity is not only technical. It also introduces governance concerns: some steps are read-only and can be executed automatically, some require explicit approval, some must be blocked, and some should safe-abort when a mapping or payload is invalid. A useful orchestration system for such settings must therefore do more than connect APIs. It must preserve policy intent across planning, capability matching, governance evaluation, and execution.

Recent advances in agentic and graph-based workflow orchestration create an opportunity to revisit this problem. Agents and workflow graphs can decompose goals, select capabilities, and coordinate execution paths, but unconstrained execution is not appropriate for industrial settings. In governed workflows, raw task success can be misleading: an action may succeed technically while violating an approval gate or bypassing a safety-oriented block. This paper therefore treats policy compliance, unsafe execution, approval bypass, invalid mapping containment, trace completeness, and restart recovery as first-class evaluation dimensions.

This paper presents a deterministic prototype for vendor-agnostic, governance-aware industrial orchestration. The prototype uses mock OPC UA, REST, and legacy adapters, a capability registry, a governance layer, and governance-aware execution paths. The reference runtime, `reference_v1`, implements deterministic planning, capability matching, governance evaluation, blocking, safe aborts, trace recording, and approval-required stopping behavior. The optional `langgraph_runtime` preserves the same governed execution semantics while adding controlled post-approval continuation, graph-native interrupt/resume behavior, checkpoint persistence, and richer trace markers. Three deterministic baselines remove governance or architectural protections to provide comparative evidence.

The paper makes six contributions. First, it proposes a governance-aware architecture for vendor-agnostic orchestration across heterogeneous industrial-style interfaces. Second, it implements the architecture as a deterministic research prototype using mock OPC UA, REST, and legacy adapters. Third, it evaluates governance-aware runtimes against deterministic baselines that remove governance enforcement, planner/matcher separation, or policy filtering. Fourth, it introduces a scaled deterministic scenario benchmark with a 240-scenario journal profile and a 500-scenario extended profile. Fifth, it reports both original and runtime-aligned metrics, including policy compliance, unsafe execution, approval bypass, invalid mapping containment, trace completeness, latency, and supported-versus-stress scope behavior. Sixth, it provides prototype-level evidence for LangGraph approval continuation and local crash/restart recovery, while treating LangSmith only as observability evidence.

## 2. Related Work

This section should be completed with verified references before submission. The intended positioning is industrial software and automation first, with agentic workflow orchestration as an enabling runtime family rather than the only contribution.

The first related work thread is industrial interoperability and vendor heterogeneity. Prior work on OPC UA, industrial middleware, and vendor-neutral automation architectures provides the background for systems that must coordinate different interface types. This manuscript builds on that problem setting but focuses on governance-preserving orchestration across mock OPC UA, REST, and legacy adapters.

The second thread is workflow orchestration and agentic planning. Workflow systems and graph-based runtimes can decompose tasks and coordinate execution, but general task completion is not sufficient for governed industrial workflows. This manuscript contributes an evaluation framing where correct behavior may involve stopping, blocking, or safe-aborting rather than executing.

The third thread is governance, approval gates, and safe execution. Approval-gated workflows, access-control policies, supervisory control, and fail-safe design motivate the policy layer used here. The manuscript should be careful to frame safe abort as prototype-level containment behavior over mock adapters, not as certified device-level safety.

The fourth thread is observability, traceability, and recovery. Audit logs, provenance, checkpointing, and runtime traces are relevant to the LangGraph and LangSmith evidence in this paper. LangGraph is used for controlled continuation and local checkpoint recovery; LangSmith is used only for observability and figure preparation.

The final thread is evaluation methodology. The manuscript uses deterministic scenario generation, baseline comparison, original and aligned metrics, Wilson scenario-distribution intervals, and supported-versus-stress reporting. This provides a reproducible prototype evaluation without claiming field deployment.

## 3. Methodology

The prototype is organized as a supervisory orchestration stack. A goal is converted into a deterministic plan. Plan steps are matched to a capability registry that maps required capabilities to available adapter implementations. A governance layer evaluates each mapped step and assigns one of the supported decisions: `ALLOW`, `REQUIRE_APPROVAL`, `BLOCK`, `FALLBACK`, or `SAFE_ABORT`. The execution layer invokes only governance-compatible adapter calls and records step-level outcomes, final status, skipped steps, failed steps, latency, and trace markers.

The adapter layer contains mock OPC UA, REST, and legacy vendor-style capabilities. These adapters provide deterministic responses and are used for controlled evaluation only. They do not demonstrate live PLC integration, vendor certification, network behavior, device-level control, or production safety.

The `reference_v1` runtime supports deterministic planning, capability matching, governance evaluation, governance-aware execution, blocking unsafe actions, safe-abort behavior, approval-required stopping behavior, and trace recording. It does not support controlled post-approval execution, graph-native interrupt/resume, checkpoint persistence, or restart-safe continuation. The `langgraph_runtime` supports the same deterministic planning, matching, governance, and execution semantics while adding controlled post-approval continuation, approval interrupt/resume, checkpoint persistence, restart-safe continuation, and graph-native trace markers.

Three baselines are included. Baseline A executes mapped adapter steps directly without governance enforcement. Baseline B uses a single-stage execution heuristic instead of explicit planner/matcher separation. Baseline C keeps matched steps but removes policy filtering. These baselines are intentionally limited and are used to reveal policy risks rather than to represent complete industrial competitors.

The scaled evaluation uses a deterministic scenario generator. It balances scenarios across workflow length, governance pattern, adapter mix, approval condition, and failure or containment condition. The 240-scenario journal profile is the main source for manuscript tables. The 500-scenario extended profile provides additional deterministic coverage and reproducibility depth.

The evaluation reports policy compliance, unsafe execution, approval bypass, final outcome accuracy, governance decision accuracy, invalid mapping containment, trace completeness, restart recovery where applicable, and latency summaries. Wilson 95% confidence intervals are used for proportion metrics and interpreted as scenario-distribution intervals over the finite deterministic benchmark, not as stochastic model uncertainty.

Because the runtimes support different capabilities, both original and aligned metrics are reported. The original scaled evaluation uses one global expected final status per scenario. The aligned evaluation keeps original scenario labels visible while adding runtime-specific expected outcomes. Alignment does not remove scenarios, hide negative results, or excuse unsafe behavior. Unsafe execution and approval bypass remain non-compliant for all runtimes.

## 4. Results

The canonical comparison evaluates 12 deterministic cases covering allowed actions, approval-required actions, blocked actions, and safe-abort conditions. In these controlled cases, the reference governance-aware execution path achieves policy compliance of 1.0, unsafe execution of 0.0, governance decision accuracy of 1.0, and final outcome accuracy of 1.0. The baselines show why raw execution success is insufficient: Baseline B reaches execution coverage of 1.0 in the unified table but has policy compliance of 0.25 and unsafe execution of 1.0.

The journal profile contains 240 deterministic scenarios. The design is balanced across 12 governance patterns, each represented by 20 scenarios, and workflow length is balanced across 80 short, 80 medium, and 80 long workflows. Adapter mix includes OPC UA only, REST only, legacy only, OPC UA plus REST, OPC UA plus legacy, REST plus legacy, and OPC UA plus REST plus legacy. The extended profile contains 500 deterministic scenarios and preserves the same factor structure.

Under original global labels in the 240-scenario journal profile, `reference_v1` has policy compliance of 0.854167 and final outcome accuracy of 0.875, while `langgraph_runtime` has policy compliance and final outcome accuracy of 0.979167. Under aligned expectations, both proposed runtimes achieve policy compliance of 1.0, final outcome accuracy of 1.0, unsafe execution of 0.0, approval bypass of 0.0, invalid mapping containment of 1.0, and trace completeness of 1.0.

| Runtime | Original policy compliance | Aligned policy compliance | Aligned final outcome accuracy | Unsafe execution | Approval bypass | Trace completeness |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `baseline_a_direct_without_governance` | 0.0 | 0.0 | 0.166667 | 0.583333 | 0.5 | 0.0 |
| `baseline_b_single_stage_execution` | 0.083333 | 0.083333 | 0.166667 | 0.0 | 0.0 | 0.0 |
| `baseline_c_without_policy_filtering` | 0.5 | 0.416667 | 0.583333 | 0.583333 | 0.5 | 0.0 |
| `langgraph_runtime` | 0.979167 | 1.0 | 1.0 | 0.0 | 0.0 | 1.0 |
| `reference_v1` | 0.854167 | 1.0 | 1.0 | 0.0 | 0.0 | 1.0 |

Relative to Baseline A, both proposed runtimes improve aligned policy compliance by 1.0 and reduce unsafe execution by 0.583333. Relative to Baseline B, both improve aligned policy compliance by 0.916667. Relative to Baseline C, both improve aligned policy compliance by 0.583333 and reduce unsafe execution by 0.583333. These results indicate that removing governance or architectural stages can produce technically completed executions that do not satisfy policy requirements.

The aligned supported/stress split is runtime-specific. For `reference_v1`, supported-scope scenarios have aligned policy compliance of 1.0, final outcome accuracy of 1.0, unsafe execution of 0.0, and trace completeness of 1.0. For `langgraph_runtime`, supported-scope and stress-scope rows both show aligned policy compliance of 1.0, unsafe execution of 0.0, and trace completeness of 1.0. Baselines remain weak in stress scope: Baseline A has stress-scope unsafe execution of 0.636364, and Baseline C has stress-scope unsafe execution of 0.777778.

The post-approval continuation experiment distinguishes stopping at an approval checkpoint from controlled continuation after explicit approval. `reference_v1` is policy-correct as a non-continuation runtime but does not execute gated steps after approval. `langgraph_runtime` supports approval interrupt/resume, approval validation, revalidation of mapping eligibility, and controlled execution of approved steps. In the unified report, the LangGraph post-approval comparison reports 1.0 for approval validation accuracy, approved step execution rate, post-resume final outcome accuracy, gated step policy compliance, and approved execution trace completeness.

The crash/restart persistence demo uses a SQLite LangGraph checkpointer. It demonstrates that a workflow can reach an approval interrupt, persist checkpoint state, simulate process stop, reopen the runtime with the same checkpoint database and thread identifier, resume with approval input, and reach the expected final result. The unified report records checkpoint resume success, restart recovery success, post-restart final outcome accuracy, and restart trace completeness as 1.0 for this local demo.

## 5. Discussion

The results show why raw task success is an incomplete metric for industrial orchestration. A baseline can execute adapter calls and still violate the intended governance policy. In the canonical comparison, Baseline B reaches full execution coverage but has unsafe execution of 1.0 and policy compliance of only 0.25. In the aligned journal profile, direct execution without governance and execution without policy filtering both show unsafe execution of 0.583333. These results support a policy-centric interpretation of orchestration quality.

Policy compliance, unsafe execution, approval bypass, and invalid mapping containment are therefore more informative than success rate alone. The proposed runtimes are designed to stop, block, or safe-abort when a workflow demands it. This distinction matters in industrial contexts because the absence of execution can be the correct outcome when an action is blocked, approval is missing, or a capability mapping is invalid.

The LangGraph runtime adds value at the runtime level. It preserves deterministic governance behavior while supporting approval interrupt/resume, controlled post-approval continuation, checkpoint persistence, restart-safe continuation, and graph-native trace markers. This value is not simply higher task success. It is the ability to represent and recover governed workflow state around approval checkpoints, which the simpler `reference_v1` path intentionally does not support.

Runtime-specific expectation alignment is methodologically fair because the evaluated runtimes do not claim identical capabilities. The reference runtime is a policy-correct non-continuation runtime; it should not be penalized for failing to perform controlled continuation that it does not implement. The LangGraph runtime, by contrast, should be evaluated for continuation behavior when valid approval and revalidation are present. This alignment is not metric manipulation because original labels remain visible, all rules are documented, and unsafe execution or approval bypass remains non-compliant for all runtimes.

The latency results should be interpreted cautiously. Local deterministic latencies show implementation overhead under the test environment. They do not represent real-time industrial timing, networked device behavior, PLC scan-cycle constraints, or production scheduling guarantees. The LangGraph runtime has higher local latency than the reference path, which is expected because it includes graph runtime overhead and trace-related execution structure.

## 6. Threats To Validity

The scaled evaluation uses generated deterministic scenarios rather than field data from an industrial plant. The scenarios are useful for controlled coverage of governance and interoperability conditions, but they may not capture the full variability of real industrial operations.

The prototype uses mock OPC UA, REST, and legacy adapters. These adapters provide deterministic responses and support repeatable evaluation. They do not demonstrate live PLC integration, vendor certification, network behavior, physical process dynamics, or device-level safety.

Runtime-specific expectation alignment improves fairness when runtimes support different capabilities, but it also introduces a methodological risk: poorly documented alignment could hide failures. This package mitigates the risk by preserving original labels, documenting alignment rules, and keeping unsafe execution and approval bypass non-compliant for all runtimes.

The baselines are deterministic governance-ablated comparisons. They are useful for revealing policy risk, but they are not intended to represent every possible industrial orchestration product or all production engineering alternatives.

The crash/restart evidence is a local LangGraph checkpoint demonstration using SQLite persistence. It shows that checkpointed workflow state can be resumed in the prototype setting. It does not demonstrate distributed fault tolerance, production deployment, operational high availability, or plant recovery procedures.

LangSmith traces support observability, debugging, and figure preparation. They are not industrial deployment evidence and do not independently validate safety, regulatory compliance, or live integration.

## 7. Conclusion

This paper presented a deterministic prototype for governance-aware, vendor-agnostic orchestration of industrial workflows. The prototype separates planning, capability matching, governance evaluation, and adapter-mediated execution, and it supports heterogeneous mock interfaces representing OPC UA, REST, and legacy systems. The evaluation shows that policy-centric metrics are essential: baselines that remove governance or policy filtering can execute workflows while producing unsafe or policy-bypassing behavior.

The IJTech-oriented evaluation provides broader empirical evidence than the initial canonical case set. Across the aligned 240-scenario journal profile, `reference_v1` and `langgraph_runtime` achieve policy compliance of 1.0, final outcome accuracy of 1.0, unsafe execution of 0.0, approval bypass of 0.0, invalid mapping containment of 1.0, and trace completeness of 1.0. The 500-scenario extended profile provides additional deterministic coverage and preserves the same core pattern: governance-aware runtimes avoid unsafe execution, while governance-ablated baselines expose policy risk. The LangGraph runtime further demonstrates controlled approval continuation, graph-native tracing, and local checkpoint-based restart recovery.

The contribution is intentionally bounded. The prototype uses deterministic synthetic scenarios and mock adapters; it does not claim certified safety, production deployment, or live PLC integration. Future work should evaluate the approach with richer industrial datasets, stricter schema validation, live or hardware-in-the-loop adapters, operator-in-the-loop approval studies, cybersecurity analysis, and more detailed standards mapping. Within its stated scope, the work provides a reproducible foundation for policy-aware industrial orchestration research and an IJTech-first journal manuscript package.
