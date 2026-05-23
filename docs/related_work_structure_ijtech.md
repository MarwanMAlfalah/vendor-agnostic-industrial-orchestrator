# Related Work Structure For IJTech Manuscript

This structure is journal-ready in argument flow, but citation metadata must still be verified using `docs/reference_quality_audit.md`. Do not insert unverified DOI or publication status.

## 1. Industrial Interoperability And Vendor Heterogeneity

References to use:

- Thesis 1.1, p.8; Thesis 2.5, p.13; Thesis 5.6, pp.41-43.
- P4 Potekhin et al. on IEC 61499/open distributed industrial systems.
- P10 Xia et al. for OPC UA-based industrial automation.
- P20 Mastouri et al. for REST/OpenAPI-to-agent tool integration context.

Main argument:

Modern industrial environments combine multiple vendors, control stacks, protocols, and service interfaces. Standards such as IEC 61499 and OPC UA address parts of the interoperability problem, but practical orchestration across heterogeneous systems remains difficult.

Gap to extract:

Existing work often treats interoperability as a communication or standards problem rather than a governance-aware orchestration problem across multiple adapter types.

Connection to proposed system:

The manuscript positions the prototype as a supervisory vendor-agnostic orchestration layer using mock OPC UA, REST, and legacy adapters, without claiming live PLC integration.

## 2. LLM-Based Multi-Agent Systems In Manufacturing

References to use:

- Thesis 2.1, p.11; Thesis 3.1, pp.14-15.
- P1 Lim et al.
- P5 Zhao et al.
- P7 Di Maggio.
- P22 Farahani et al., only if verified.
- P23 Li et al., only if verified.

Main argument:

LLM-enabled MAS can improve flexible reasoning, task decomposition, and coordination in manufacturing and maintenance settings. Reported studies show promise in simulations, shopfloor scheduling, predictive maintenance, and industrial task coordination.

Gap to extract:

Many systems remain tied to narrow tasks, simulated workflows, or a single industrial setup. They do not fully address governance, runtime traceability, or vendor-agnostic orchestration.

Connection to proposed system:

The proposed prototype uses deterministic planning and governance-aware execution to evaluate what happens when LLM/MAS-inspired orchestration must respect approval gates, blocks, and safe aborts.

## 3. Agentic AI And Human-In-The-Loop Industrial Automation

References to use:

- Thesis 2.2, pp.11-12; Thesis 3.2, p.15.
- P2/P24 Romero and Suyama.
- P3 Zeydan et al.
- P6 Terziyan et al.
- P7 Di Maggio.

Main argument:

Agentic AI can translate high-level intent into diagnostics, planning, maintenance recommendations, or operational actions. Human-in-the-loop mechanisms are important for accountability and safety-sensitive environments.

Gap to extract:

Existing intent-based systems often remain conceptual, proof-of-concept, or dataset-bound. They rarely define formal governance outcomes for when execution should stop, require approval, block, or safe-abort.

Connection to proposed system:

The manuscript's governance layer operationalizes approval and non-execution decisions as first-class runtime outcomes in deterministic scenarios.

## 4. Workflow And Tool Orchestration

References to use:

- Thesis 2.3, p.12; Thesis 3.3, pp.15-16.
- P11 ToolNet.
- P12 AFlow.
- P13 Benchmarking Agentic Workflow Generation.
- P20 REST APIs Agent-Ready.

Main argument:

Tool and workflow orchestration research provides graph-based or structured mechanisms for selecting tools, generating workflows, and coordinating multi-step execution.

Gap to extract:

General tool orchestration benchmarks rarely include industrial communication protocols, approval gates, unsafe execution measures, or invalid mapping containment.

Connection to proposed system:

The prototype evaluates workflow orchestration under industrial-style governance conditions rather than only task completion or tool selection accuracy.

## 5. Graph-Based Agentic Workflows

References to use:

- Thesis 4.2.1 ToolNet, pp.19-21.
- Thesis 4.2.2 AFlow, pp.21-22.
- Thesis 4.2.3 SOAN, pp.22-24.
- P11, P12, P14, P15, P16.

Main argument:

Graph structures can represent tool relationships, workflow dependencies, memory, planning structure, and agent coordination. Graph-based runtimes are relevant to scalable agent orchestration.

Gap to extract:

Graph-based agentic workflow research generally emphasizes reasoning and workflow accuracy, not governed execution, approval continuation, restart recovery, or industrial interoperability.

Connection to proposed system:

The LangGraph runtime variant is presented as a runtime-level continuation and checkpoint mechanism, while the reference runtime remains a policy-correct non-continuation path.

## 6. Industrial Control And OPC UA Integration

References to use:

- Thesis 2.5, p.13.
- Thesis 4.2.4 LLM4IAS, pp.24-26.
- P4 Potekhin et al.
- P10 Xia et al.

Main argument:

OPC UA and related standards are important bridges between high-level software systems and industrial automation environments. LLM4IAS provides a relevant example of LLM-based control with OPC UA in a research testbed.

Gap to extract:

Existing OPC UA/industrial LLM control work remains bounded to specific setups, supervisory latency, and non-certified research prototypes. It does not establish scalable multi-vendor orchestration.

Connection to proposed system:

The manuscript uses mock OPC UA as one adapter class to evaluate orchestration semantics without claiming live PLC, SCADA, or certified safety integration.

## 7. Governance, Safety, And AgentOps

References to use:

- Thesis 4.4.2 Phaidra patent discussion, pp.32-37.
- Thesis 5.1, p.38, for safety readiness as a qualitative characteristic.
- P18 Evaluation-Driven Development and Operations.
- P19 Beyond Task Completion, only after verification.
- P21 MCP Security Bench, only after metadata completion.

Main argument:

Industrial AI adoption requires governed execution, fallback behavior, bounded recommendations, operator oversight, and continuous evaluation. AgentOps and evaluation-driven operations are relevant patterns for making agentic systems inspectable and controllable.

Gap to extract:

Agent governance is often discussed at a process or safety principle level, but fewer systems provide reproducible metrics for approval bypass, unsafe execution, invalid mapping containment, and trace completeness.

Connection to proposed system:

The manuscript evaluates governance outcomes explicitly and keeps unsafe execution and approval bypass non-compliant under both original and aligned metrics.

## 8. Observability And Evaluation Of LLM Agents

References to use:

- P18 Evaluation-Driven Development and Operations.
- P19 Beyond Task Completion, if verified.
- P13 Benchmarking Agentic Workflow Generation.
- Thesis qualitative comparison section 5, pp.37-43.
- Project evidence: LangSmith traces as observability only; scaled statistical analysis as deterministic scenario-distribution evidence.

Main argument:

Agentic systems need evaluation beyond final task completion. Traceability, runtime observability, benchmark design, and explicit metric definitions are needed to understand behavior.

Gap to extract:

Existing evaluation frameworks often do not focus on industrial governance-specific failure modes such as unsafe execution, approval bypass, safe abort, and runtime continuation after approval.

Connection to proposed system:

The manuscript contributes a deterministic evaluation package with original and aligned metrics, supported-versus-stress scope reporting, baseline comparisons, local checkpoint evidence, and observability traces scoped carefully to debugging and auditability.
