# Q1 Manuscript Roadmap

## Path A: Conference / Prototype Paper

Target contribution type: research prototype and evaluation methodology.

Required evidence:

- Architecture and workflow description.
- Deterministic governance cases.
- Baseline comparison with policy-centric metrics.
- LangGraph runtime extension and crash/restart demo.

Missing work:

- Tight related work section.
- Clear threat-to-validity section.
- Polished figures and trace screenshots.

Recommended structure:

1. Introduction and motivation
2. Architecture
3. Governance model and metrics
4. Runtime comparison
5. Evaluation results
6. Limitations and future work

Expected risk: moderate. The prototype is coherent, but reviewers may ask for
more industrial realism.

Recommended next actions:

- Freeze artifacts.
- Produce architecture and trace figures.
- Write around claim-evidence matrix.

## Path B: Strong Empirical Journal Paper

Target contribution type: empirically grounded system evaluation.

Required evidence:

- Larger benchmark suite.
- More adapters, richer policy classes, and fault cases.
- External baselines or benchmark comparison.
- Statistical analysis or repeated perturbation tests.
- Expert or operator evaluation.

Missing work:

- Live or high-fidelity industrial environment.
- Formal comparison against related systems.
- Deeper standards and safety analysis.

Recommended structure:

1. Problem statement
2. System architecture
3. Formal evaluation design
4. Experimental setup
5. Quantitative results
6. Comparative discussion
7. Threats to validity

Expected risk: high until empirical depth expands.

Recommended next actions:

- Design a larger benchmark.
- Add scenario generation protocol.
- Identify external comparison systems and datasets.

## Path C: Annual Reviews in Control-Style Vision / Tutorial / Review Paper

Target contribution type: review, taxonomy, tutorial framework, and reference
implementation case study.

Required evidence:

- Systematic literature review.
- Taxonomy of industrial agentic orchestration systems.
- Comparative matrix across industrial copilots, AI agents, multi-agent
  frameworks, interoperability standards, governance mechanisms, persistence,
  and observability.
- Prototype positioned as a reference implementation and case study.

Missing work:

- Formal search protocol and screened bibliography.
- Citation-backed industry/research comparison.
- Tutorial diagrams and conceptual synthesis.

Recommended structure:

1. Introduction: industrial AI agents and supervisory control
2. Systematic review methodology
3. Taxonomy of industrial agentic orchestration
4. Governance-aware orchestration patterns
5. Runtime persistence and human-in-the-loop control
6. Observability and evaluation methodology
7. Reference implementation case study
8. Open challenges and research agenda

Expected risk: moderate. The risk shifts from prototype evidence to review
quality and breadth.

Recommended next actions:

- Execute `docs/systematic_review_plan.md`.
- Build a citation-backed comparison matrix.
- Use this repository as the running tutorial example.

For Path C, explicitly discuss governance, interoperability, runtime
persistence, observability, human-in-the-loop control, OPC UA/vendor-agnostic
adapter patterns, and stateful agent runtimes such as LangGraph.

