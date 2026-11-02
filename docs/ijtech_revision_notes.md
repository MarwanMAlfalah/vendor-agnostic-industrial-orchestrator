# IJTech Revision Notes

This revision pass changed manuscript and documentation wording only. It did not change code, runtime logic, evaluation logic, generated metrics, or result files.

## Changed Claims And Rationale

| Area | Changed claim or wording | Why it changed |
| --- | --- | --- |
| Title | Removed "IJTech-Oriented" from the full manuscript title. | The title should read as a manuscript title, not as an internal venue-preparation label. |
| Abstract | Rewrote the abstract to 237 words. | The requested target was 220-240 words. |
| Abstract | Replaced a standalone aligned-results claim with original metrics plus aligned metrics. | Perfect aligned metrics need to be interpreted alongside original global-label metrics and runtime scope limitations. |
| Abstract | Added "within the deterministic mock-adapter scope" to the aligned-results sentence. | Prevents overgeneralizing aligned 1.0 metrics beyond the synthetic deterministic evaluation. |
| Abstract | Changed "essential" to "prototype-level evidence for policy-centric evaluation." | Softens the claim and keeps it at prototype-evidence level. |
| Introduction | Removed "IJTech-first" and changed the phrasing to "journal-oriented." | Removes internal package language from manuscript-facing prose. |
| Introduction | Added Harvard-style citation placeholders such as `(Author, year)`. | Marks where verified scholarly or standards citations are required without inventing references. |
| Full manuscript | Added an abbreviations and nomenclature section. | Provides definitions for OPC UA, REST, LangGraph, LangSmith, runtime IDs, and governance decisions. |
| Related Work | Added Harvard-style citation placeholders to interoperability, workflow orchestration, governance, observability, and evaluation-methodology topics. | Keeps citation needs visible while avoiding fabricated citations. |
| Methodology | Added citation placeholders for governance decisions, scenario generation, and Wilson interval reporting. | Flags methodological claims that need verified sources. |
| Methodology | Added a reproducibility paragraph. | Documents that reproduction should use the existing deterministic profiles, runtime profiles, mock-adapter setting, and generated CSV/JSON summaries. |
| Results | Reworded "under aligned expectations, both proposed runtimes achieve..." to "under documented aligned expectations... report..." | Softens perfect aligned metrics and frames them as reported deterministic results. |
| Results | Added original metrics before aligned metrics in the aligned-results explanation. | Ensures aligned metrics are paired with original metrics. |
| Results | Added deterministic mock-adapter and capability-profile scope language to supported/stress and LangGraph continuation claims. | Prevents implying production or general industrial capability from prototype tests. |
| Results | Clarified that crash/restart metrics are separate from scaled metrics and do not imply production recovery capability. | Keeps local SQLite checkpoint evidence bounded. |
| Discussion | Added citation placeholders for task-success limitations, policy-centric metrics, graph runtimes, alignment methodology, and latency interpretation. | Marks citation needs without inventing references. |
| Discussion | Kept latency framed as local deterministic overhead. | Prevents real-time or production timing claims. |
| Conclusion | Replaced a standalone aligned 1.0 claim with original metrics plus aligned metrics and deterministic scope. | Pairs aligned claims with original evidence and scope limitations. |
| Conclusion | Removed "IJTech-first journal manuscript package." | Eliminates internal package wording from manuscript-facing conclusion. |
| Figures | Added blind-review warnings for repository and LangSmith screenshots. | Screenshots may expose identity, workspace names, trace URLs, browser profiles, or local paths. |
| Blind-review checklist | Added explicit repository and LangSmith screenshot warnings. | Strengthens anonymization guidance for review. |
| SEDM shortening plan | Replaced standalone aligned 1.0 wording with original-plus-aligned wording. | Keeps the shortened plan consistent with the softened journal claims. |
| SEDM conclusion draft | Replaced "IJTech-oriented journal extension" with "journal extension." | Removes venue-preparation wording from manuscript-facing draft text. |

## Citation Placeholder Policy

All citation placeholders are intentionally generic Harvard-style placeholders, for example `(Author, year)`. They are not real citations and must be replaced with verified references before submission.

## Results Policy

No new metrics, experiments, citations, deployments, safety claims, or live integration claims were added. All numerical claims remain drawn from the existing deterministic evidence: canonical governance cases, the 240-scenario journal profile, the 500-scenario extended profile, original and aligned metrics, baseline comparison, supported-versus-stress scope, LangGraph continuation and checkpoint reopen/resume evidence, and LangSmith observability evidence only.
