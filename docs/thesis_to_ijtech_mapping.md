# Thesis To IJTech Mapping

Source: `docs/source_materials/Thesis_Master_Marwan.pdf`.

Purpose: identify which thesis material can support the journal manuscript, which must be rewritten, which tables can be adapted, and which thesis-only claims should be excluded.

## High-Level Alignment

The thesis is an analytical review of LLM-based MAS, agentic AI, workflow orchestration, industrial interoperability, and practical/patent systems. The current journal manuscript is no longer only an analytical review: it presents a deterministic prototype, evaluation scenarios, baseline comparisons, aligned metrics, LangGraph continuation evidence, and bounded observability evidence.

Therefore, thesis material should be used primarily for motivation, literature framing, gap analysis, and qualitative comparison. It should not overwrite the manuscript's implemented-methodology and results sections.

## Paragraphs That Can Be Reused With Light Editing

| Thesis location | Reusable content | Where to use in IJTech manuscript | Required edits |
| --- | --- | --- | --- |
| Abstract, p.7 | Heterogeneous platforms create demand for intelligent coordination beyond centralized control. | Introduction opening motivation | Remove author/institution context; add citations; avoid saying the journal paper is only a review. |
| Abstract, p.7 | Structural divide between research systems and industrial solutions. | Related Work synthesis and Discussion | Reframe as literature context, not as the only contribution. |
| Introduction 1.1, p.8 | Industrial digital transformation creates heterogeneous vendor/platform environments. | Introduction | Add verified citations from P4/P10 and standards references. |
| Introduction 1.1, pp.8-9 | LLMs show reasoning/contextual understanding and motivate MAS integration. | Introduction; Related Work | Phrase cautiously as "recent work explores" or "motivates." |
| Section 2.1, p.11 | LLMs as high-level reasoning components in MAS. | Related Work: LLM-based MAS in manufacturing | Add P1, P5, P7 citations. |
| Section 2.2, pp.11-12 | Agentic AI for intent-based industrial decision support and human-in-the-loop mechanisms. | Related Work: Agentic AI and HITL automation | Add P2/P3/P6/P7 citations and avoid production claims. |
| Section 2.3, p.12 | Workflow orchestration and tool graphs as coordination layer. | Related Work: workflow and tool orchestration | Connect to our planner/matcher/governance separation. |
| Section 2.5, p.13 | Vendor heterogeneity and interoperability remain persistent challenges. | Introduction; Related Work | Emphasize that our prototype uses mock adapters only. |
| Section 5.6, pp.41-43 | Research systems vs industrial solutions dichotomy. | Related Work synthesis; Discussion | Remove quantitative "54%/50%" unless table is adapted and fully justified. |
| Conclusion, pp.42-45 | Vendor-agnostic interoperability as central gap. | Introduction; Related Work gap paragraph | Reframe from thesis future-work language to current manuscript contribution. |

## Paragraphs That Must Be Rewritten

| Thesis location | Why rewrite | IJTech replacement direction |
| --- | --- | --- |
| Introduction 1.2, p.9: "The review does not aim to propose a new system architecture or implementation at this stage." | Direct contradiction: current manuscript presents an implemented deterministic prototype and evaluation package. | Replace with a statement that this journal article builds on prior analytical review and evaluates a deterministic prototype. |
| Section 1.4, p.10: search limited to 2022-2026. | Useful for thesis review, but not sufficient for journal related work. IJTech manuscript may need standards and foundational citations before 2022. | Use as background for thesis source collection only; add verified standards/foundational references separately. |
| Section 4.2.4, pp.24-26: LLM4IAS physical testbed details and industrial partners. | These are claims about another system and must be independently verified before inclusion. | Summarize cautiously as "reported testbed integration" only after checking P10. |
| Section 4.4 ABB/Phaidra patent descriptions, pp.27-37. | Patent interpretations may need direct patent verification and may not belong in full detail. | Use as concise examples of industrial orchestration/governance patterns, not as central literature unless patents are verified. |
| Section 5.4 symbolic comparison table, p.40. | Thesis scale is qualitative and covers different systems than current manuscript. | Adapt only as related-work comparison, not as empirical evidence for our prototype. |
| Section 6 conclusion, pp.42-45: "next phase will propose an architectural concept." | Current manuscript already contains a prototype and evaluation. | Rewrite as "the prior review motivates the evaluated architecture." |

## Tables That Can Become Paper Tables

| Thesis table | Possible journal use | Required changes |
| --- | --- | --- |
| Table 4.1 Comparative Overview of Research-Derived Finished Systems | Related Work comparison table or supplementary table | Verify all system claims, remove unverifiable institutional/user details, shorten to capabilities relevant to orchestration/interoperability/governance. |
| Table 4.2 ABB Patent vs. Research Systems | Optional related-work table if patents are included | Verify patent claims directly; avoid comparing patents as if they are peer-reviewed experiments. |
| Table 4.3 Phaidra Patent vs. Research Systems | Optional governance-pattern context | Verify patent status and claims; keep as qualitative context only. |
| Table 5.1 Mapping of Qualitative Characteristics to Literature Findings | Useful as a compact gap-analysis table | Recast for journal with verified citations and without thesis-only terminology. |
| Table 5.2 Qualitative Comparison of Existing Solutions | Potential related-work comparison table | Use conservative symbols; add citation footnotes; remove or justify quantitative averages. |

## Thesis-Only Material That Should Not Appear In The Journal Manuscript

- Title page, approval page, acknowledgements, publication placeholder, and university-specific formatting.
- Search-process details that are only relevant to the thesis methodology unless the journal includes a systematic review section.
- Statements that the work does not propose an architecture or implementation.
- Extended patent walkthroughs with figure descriptions unless independently verified and substantially shortened.
- Claims about specific repositories, industrial partners, or physical testbeds for third-party systems unless verified from primary sources.
- Thesis-specific future-work language that says design and implementation will happen later.
- Quantitative averages from the symbolic qualitative comparison unless the scoring rubric is fully included and justified.

## Contradictions To Fix

| Contradiction | Source | Fix |
| --- | --- | --- |
| Thesis says no new architecture or implementation is proposed at this stage. | Thesis 1.2, p.9 | Journal manuscript must state that the current paper presents and evaluates a deterministic prototype. |
| Thesis frames the work as an analytical review only. | Abstract and 1.5 | Journal manuscript should use thesis review as background, then move to implemented methodology and results. |
| Thesis discusses vendor ecosystems such as Siemens, ABB, Schneider in the approach notes. | Excel gap notes | Current prototype should only claim mock OPC UA, REST, and legacy adapters. Do not claim real vendor ecosystem integration. |
| Thesis includes "finished product" language for research systems. | Thesis 4.1 | In journal prose, use "implemented research systems" or "research prototypes" to avoid implying commercial maturity. |
| Thesis mentions industrial solutions can be integrated into real industrial settings. | Thesis 6 | Keep this as third-party literature context only; do not transfer it to our prototype. |
| Thesis qualitative comparison says vendor-agnostic interoperability is entirely unaddressed. | Thesis 5.6 | Soften to "remains insufficiently addressed among reviewed systems" unless the reviewed set and criteria are fully reproduced. |

## Recommended Reuse Strategy

1. Use thesis 1.1 and 2.5 for Introduction motivation.
2. Use thesis section 2 as the backbone for Related Work subsections.
3. Use thesis section 3 to identify gaps in LLM/MAS, HITL, workflow, architecture, and interoperability.
4. Use thesis section 4 selectively for comparative related work, especially ToolNet, AFlow, SOAN, LLM4IAS, ABB, and Phaidra.
5. Use thesis section 5 as a model for a concise qualitative comparison table, not as a direct empirical result.
6. Use current project evaluation reports for all claims about our system's results.
