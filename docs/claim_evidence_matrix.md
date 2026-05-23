# Claim-Evidence Matrix

| Claim | Evidence Source | Metric / Artifact | Strength | Caution / Limitation |
| --- | --- | --- | --- | --- |
| Vendor-agnostic orchestration is feasible. | Capability registry, heterogeneous adapters, workflow docs. | YAML registry; OPC UA, REST, and legacy adapters; `docs/workflow_summary.md`. | Moderate | Feasibility is shown with mock adapters, not live industrial systems. |
| Policy-aware execution is achieved. | Canonical comparison. | Reference policy compliance 1.0; governance decision accuracy 1.0; final outcome accuracy 1.0. | Strong | Applies to deterministic controlled cases. |
| Unsafe execution is prevented in controlled cases. | Canonical comparison and post-approval cases. | Reference unsafe execution 0.0; LangGraph post-approval unsafe execution 0.0. | Strong | Unsafe action space is curated and limited. |
| Raw success and coverage can be misleading. | Baseline comparison. | Baseline B success/coverage 1.0 but policy compliance 0.25 and unsafe execution 1.0. | Strong | Baselines are simple ablations, not full competing systems. |
| LangGraph runtime preserves policy correctness. | LangGraph canonical and mixed comparisons. | Policy compliance 1.0; unsafe execution 0.0; final outcome accuracy 1.0. | Strong | Evidence is parity on current deterministic cases. |
| LangGraph adds runtime-level value through interrupt/resume and persistence. | Mixed workflow, post-approval, crash/restart results. | Trace stage coverage 1.0; interrupt trace quality 1.0; approval continuation metrics 1.0; restart recovery 1.0. | Strong | Runtime value is demonstrated locally with SQLite checkpointing. |
| LangSmith improves observability and trace inspection. | Observability docs and trace wrappers. | `docs/langsmith_trace_examples.md`; structured trace outputs. | Moderate | Observability improves inspection, not correctness. |
| Current evidence is prototype-level, not production deployment evidence. | Scope of evaluation and mock adapters. | Limitations in final unified report. | Strong | Additional live-system, safety, and operator studies are needed. |

