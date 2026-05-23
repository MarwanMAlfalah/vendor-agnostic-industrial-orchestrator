# IJTech Related Work Plan

This file is a writing plan for the related work section. It intentionally avoids fabricated citations. Before submission, replace each citation placeholder with verified scholarly or standards references in the journal's required style.

## Positioning Goal

The related work should position the manuscript as an industrial software and automation contribution, not only as an agent workflow paper. The central gap is the lack of reproducible, policy-centric evaluation for vendor-agnostic orchestration across heterogeneous industrial-style interfaces.

## Proposed Subsections

### Industrial Interoperability And Vendor Heterogeneity

Discuss industrial systems that combine OPC UA, REST services, and legacy vendor interfaces. Emphasize that interoperability is not only a communication problem; orchestration must preserve operational constraints across different interface styles.

Evidence to connect back to this manuscript:

- mock OPC UA, REST, and legacy adapters;
- capability registry and adapter-mediated execution;
- deterministic scenario factors for adapter mix;
- no claim of live PLC integration.

Citation targets to verify:

- OPC UA standards and interoperability literature;
- industrial middleware and systems integration studies;
- vendor-neutral automation architecture papers.

### Workflow Orchestration And Agentic Planning

Review workflow orchestration, agent planning, and graph-based execution systems. The manuscript should distinguish task decomposition from governed industrial execution. The gap is that general workflow success does not necessarily imply policy compliance.

Evidence to connect back:

- deterministic planner and capability matcher;
- reference runtime versus LangGraph runtime;
- separation of planning, matching, governance, execution, and tracing.

Citation targets to verify:

- workflow orchestration frameworks;
- graph-based agent/workflow runtime literature;
- agent safety and tool-use governance work.

### Governance, Approval Gates, And Safe Execution

Discuss approval-gated workflows, policy enforcement, and fail-safe or safe-abort concepts in industrial or cyber-physical settings. Avoid claiming that this prototype is a safety-certified controller. Frame it as supervisory governance over mock adapter calls.

Evidence to connect back:

- `ALLOW`, `REQUIRE_APPROVAL`, `BLOCK`, `FALLBACK`, and `SAFE_ABORT` decisions;
- unsafe execution rate;
- approval bypass rate;
- invalid mapping containment.

Citation targets to verify:

- access-control and policy-enforcement literature;
- human approval and supervisory control references;
- industrial safety standards as background only, not as compliance claims.

### Observability, Traceability, And Recovery

Review traceability, audit logs, runtime observability, and checkpoint/restart mechanisms. The manuscript should frame LangSmith as observability evidence and LangGraph checkpointing as local recovery evidence.

Evidence to connect back:

- trace completeness;
- graph-native trace markers;
- local SQLite checkpoint crash/restart demonstration;
- no production deployment claim.

Citation targets to verify:

- observability and provenance in workflow systems;
- checkpointing and recovery literature;
- auditability in industrial software systems.

### Evaluation Methodology For Governed Orchestration

Discuss why deterministic benchmarks, scenario generation, baselines, ablations, and supported-versus-stress splits are appropriate for prototype-level evidence. Explain that Wilson intervals are scenario-distribution intervals, not stochastic LLM uncertainty.

Evidence to connect back:

- 240-scenario journal profile;
- 500-scenario extended profile;
- original and aligned metrics;
- deterministic baselines;
- supported versus stress scope.

Citation targets to verify:

- benchmark design and reproducibility literature;
- statistical reporting for proportion metrics;
- software engineering evaluation methods for prototypes.

## Suggested Related Work Thesis

Prior work provides important foundations for industrial interoperability, workflow orchestration, policy enforcement, and observability. However, these threads are rarely combined into a reproducible evaluation of vendor-agnostic industrial orchestration where the correct behavior may be to stop, block, or safe-abort rather than execute. This manuscript addresses that gap with a deterministic prototype, governance-aware baselines, runtime-specific alignment, and explicit supported-versus-stress reporting.
