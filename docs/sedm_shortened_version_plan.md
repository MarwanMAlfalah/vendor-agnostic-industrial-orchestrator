# SEDM Shortened Version Plan

## Purpose

The SEDM version should be a shorter conference-style derivative of the journal manuscript, not the primary manuscript. It should focus on the core architecture and a compact empirical story while pointing to the journal version for the expanded deterministic evaluation.

## Recommended Short Title

Governance-Aware Vendor-Agnostic Orchestration for Industrial Workflows

## Scope For The Shortened Version

Keep:

- motivation around heterogeneous industrial workflows;
- reference architecture;
- governance decisions;
- canonical governance comparison;
- headline aligned journal-profile results;
- one compact reproducibility evidence paragraph;
- brief LangGraph continuation note;
- concise limitations.

Compress:

- related work to one short section;
- methodology details to architecture plus metric definitions;
- scenario generator details to one table;
- supported-versus-stress details to one paragraph;
- LangGraph crash/restart details to one short subsection.

Move to IJTech journal version:

- full original-versus-aligned methodology discussion;
- full 240-scenario and 500-scenario evidence;
- full supported-versus-stress tables;
- full Docker/Kubernetes/LangSmith evidence table;
- detailed latency table;
- conceptual ablation discussion;
- expanded threats to validity;
- full figure package.

## Suggested SEDM Structure

1. Introduction
2. Architecture
3. Evaluation Design
4. Results
5. Limitations
6. Conclusion

## Candidate SEDM Abstract

Industrial workflows often span OPC UA interfaces, REST services, and legacy vendor systems while requiring governance constraints such as approval gates, blocked actions, and safe-abort behavior. This short paper presents a deterministic prototype for governance-aware, vendor-agnostic industrial orchestration. The prototype separates planning, capability matching, governance evaluation, and adapter-mediated execution. In deterministic evaluation, governance-aware runtimes avoid unsafe execution, while baselines that remove governance or policy filtering expose policy risk. The optional LangGraph runtime adds controlled approval continuation and checkpoint-based recovery evidence. The prototype uses synthetic scenarios and mock adapters and does not claim certified safety, production deployment, or live PLC integration.

## Length Control

- Target 6 to 8 pages if a conference-style limit applies.
- Use no more than 2 main tables.
- Use no more than 3 figures.
- Keep numerical reporting to the strongest headline metrics.
- Put detailed table/figure package and extended-profile results in the IJTech manuscript.

## Shortened Results To Retain

- Canonical governance reference runtime: policy compliance 1.0, unsafe execution 0.0, governance decision accuracy 1.0, final outcome accuracy 1.0.
- Aligned 240-scenario journal profile: under original labels, `reference_v1` reports policy compliance of 0.854167 and final outcome accuracy of 0.875, while `langgraph_runtime` reports 0.979167 for both metrics; under documented aligned expectations within the deterministic mock-adapter scope, both report aligned policy compliance 1.0, final outcome accuracy 1.0, unsafe execution 0.0, approval bypass 0.0, invalid mapping containment 1.0, and trace completeness 1.0.
- Baseline A and Baseline C: unsafe execution 0.583333 in the aligned journal profile.
- Baseline B: aligned policy compliance 0.083333 and final outcome accuracy 0.166667.
- LangGraph post-approval continuation: approval validation, approved step execution, post-resume final outcome accuracy, gated step policy compliance, and approved execution trace completeness are reported as 1.0 in the local deterministic continuation tests.
- Reproducibility evidence: Docker Compose mock-service integration, actual local kind Kubernetes execution, frozen manifest validation, and LangSmith observability traces are available as supporting evidence, not as production or live-plant validation.

## Suggested Figure And Screenshot Package

- Main architecture figure: planning, capability matching, governance, execution, adapters, and trace recording.
- Results table: compact original/aligned policy metrics for the two proposed runtimes and three baselines.
- Optional reproducibility figure: local Docker/Kubernetes evidence with sanitized command output or topology.
- Optional observability figure: redacted LangSmith trace screenshot showing planning, governance, approval, execution, and final-result spans.

## Shortened Limitations To Retain

- Deterministic synthetic scenarios.
- Mock OPC UA, REST, and legacy adapters.
- No certified safety.
- No production deployment.
- No live PLC integration.
- LangSmith only as observability evidence.
- Docker and Kubernetes evidence only as local reproducibility evidence.
