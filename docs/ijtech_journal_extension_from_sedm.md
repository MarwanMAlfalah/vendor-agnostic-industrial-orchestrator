# IJTech Journal Extension From SEDM

## Extension Thesis

The IJTech manuscript should be framed as a journal article on governance-aware vendor-agnostic industrial orchestration. The SEDM-style material is useful as a seed, but the journal contribution is broader: it adds scaled deterministic evaluation, runtime-specific expectation alignment, supported-versus-stress analysis, richer table/figure packaging, and clearer industrial validity boundaries.

## What Carries Over From The SEDM Draft

- Core motivation: heterogeneous industrial workflows across OPC UA, REST, and legacy-style interfaces.
- Core architecture: planner, capability matcher, governance layer, adapter-mediated execution, and trace recording.
- Core governance decisions: `ALLOW`, `REQUIRE_APPROVAL`, `BLOCK`, `FALLBACK`, and `SAFE_ABORT`.
- Core caution: the prototype uses deterministic synthetic scenarios and mock adapters.
- Core LangGraph evidence: continuation, checkpointing, and graph-native traces.

## What Must Be Expanded For IJTech

- Make the 240-scenario journal profile the primary empirical study.
- Include the 500-scenario extended profile as additional deterministic coverage.
- Report original and aligned metrics together.
- Explain runtime-specific expectation alignment as a methodology contribution.
- Add supported-versus-stress scope results.
- Add baseline comparison tables with aligned policy-compliance deltas and unsafe-execution reductions.
- Add a richer threats-to-validity section.
- Add a complete table and figure package.
- Treat LangSmith as observability only.

## New Journal-Level Contributions

1. A deterministic benchmark design for governance-aware industrial orchestration.
2. Runtime-specific expectation alignment for fair comparison across runtimes with different continuation capabilities.
3. Supported-versus-stress reporting that keeps edge cases visible.
4. Baseline comparison showing that governance-ablated execution can create unsafe or policy-bypassing behavior.
5. Local LangGraph checkpoint recovery evidence for approval-gated workflows.

## Claims To Avoid In The Journal Version

- Production deployment.
- Certified safety.
- Live PLC integration.
- Regulatory compliance.
- Real-time industrial timing guarantees.
- LangSmith as validation evidence.
- Conceptual ablations as executed experiments.

## Recommended IJTech Manuscript Structure

1. Abstract
2. Keywords
3. Introduction
4. Related Work
5. Methodology
6. Results
7. Discussion
8. Threats to Validity
9. Conclusion
10. References
11. Tables and Figures

## Difference Statement Candidate

Compared with the shorter SEDM-oriented version, the IJTech manuscript expands the empirical basis from canonical governance examples to a deterministic 240-scenario journal profile and a 500-scenario extended profile. It adds runtime-specific expectation alignment, supported-versus-stress scope reporting, baseline effect comparisons, local checkpoint recovery evidence, and a fuller limitations analysis. The journal version remains bounded to deterministic prototype evidence with mock adapters and does not claim production deployment, certified safety, or live PLC integration.
