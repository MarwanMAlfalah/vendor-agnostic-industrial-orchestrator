# Reference Quality Audit

Source: `docs/source_materials/_Literature_Review_Marwan.xlsx`, sheet `Literature_Tracker`, cross-checked against the reference list extracted from `docs/source_materials/Thesis_Master_Marwan.pdf`.

Audit rules:

- DOI is marked missing when the DOI field contains only a title, URL, arXiv identifier, or database label rather than a DOI.
- BibTeX key is marked missing when the spreadsheet field is blank.
- Venue is marked missing when the spreadsheet field is blank or too generic for submission.
- Publication status is marked risky when the item is a preprint, has future/unclear venue information, has missing author/year data, or appears duplicated.

## Reference Inventory And Metadata Issues

| ID | Reference | Status in Excel | Missing or weak metadata | Core? | Risk level | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| P1 | Lim, Vogel-Heuser, Kovalenko, "Large Language Model-Enabled Multi-Agent Manufacturing Systems", 2024, IEEE CASE | Cited | DOI is arXiv only; BibTeX key missing | Yes | Medium | Core for LLM-enabled MAS in manufacturing. Verify final IEEE CASE metadata and DOI if available. |
| P2 | Romero, Suyama, "Agentic AI for Intent-Based Industrial Automation", 2025, 16th IEEE/IAS International Conference on Industry Applications | Cited | DOI is arXiv only; URL is not clean; BibTeX key missing | Yes | Medium | Core for agentic AI and intent-based industrial automation. Duplicate with P24. |
| P3 | Zeydan et al., "Generative Artificial Intelligence for Intent-Based Industrial Automation", 2024, IEEE Consumer Electronics Magazine | Cited | DOI field is a title/database label; BibTeX key missing | Supporting | Medium | Useful for intent-layer framing. Verify DOI and page/article metadata. |
| P4 | Potekhin et al., "Programming of Open Distributed Industrial Systems Based on IEC 61499", year missing in Excel, Computing, Telecommunications and Control | Cited | Year missing in Excel; DOI field is a title/database label; BibTeX key missing | Yes | High | Core for open distributed industrial systems. Thesis reference lists 2024 and URL. Verify year, venue, and DOI/status. |
| P5 | Zhao et al., "A Large Language Model-based multi-agent manufacturing system for intelligent shopfloor", 2024 | Not marked | Venue missing; DOI is arXiv/title label; BibTeX key missing | Yes | High | Core for LLM MAS shopfloor, but publication status needs verification. |
| P6 | Vagan Terziyan, Oleksandra Vitko, Oleksandr Terziyan, "A Conceptual Design of Industrial Asset Maintenance System by Autonomous Agents Enhanced with ChatGPT", 2025, Intelligent and Sustainable Manufacturing | Not marked | DOI field is title/database label; BibTeX key missing | Supporting | Medium | Useful for maintenance-agent framing; conceptual only. Verify article metadata. |
| P7 | Luigi Gianpio Di Maggio, "Toward Autonomous LLM-Based AI Agents for Predictive Maintenance", 2025, Applied Sciences | Not marked | BibTeX key missing | Yes | Low | Has DOI in thesis reference: 10.3390/app15021151. Strong survey for predictive maintenance and LLM agents. |
| P8 | Guannan Liang, Qianqian Tong, "LLM-Powered AI Agent Systems and Their Applications in Industry", 2025, IEEE conference | Not marked | Venue too generic; DOI field is title label; BibTeX key missing | Supporting | High | Needs exact IEEE venue, DOI, and page metadata. |
| P9 | Deepak Bhaskar Acharya, Karthigeyan Kuppan, B. Divya, "Agentic AI: Autonomous Intelligence for Complex Goals - A Comprehensive Survey", 2025, IEEE | Not marked | Venue too generic; DOI field is title/database label; BibTeX key missing | Supporting | High | Thesis reference uses arXiv link. Verify whether it is IEEE or arXiv and fix possible arXiv mismatch. |
| P10 | Yuchen Xia, Nasser Jazdi, Jize Zhang, Chaitanya Shah, Michael Weyrich, "Control Industrial Automation System with Large Language Model Agents", 2025, 30th IEEE ETFA | Not marked | DOI is arXiv/title label; BibTeX key missing | Yes | Medium | Core for OPC UA and industrial LLM control. Verify ETFA publication status and final DOI. |
| P11 | Xukun Liu et al., "ToolNet: Connecting Large Language Models with Massive Tools via Tool Graph", 2024, arXiv | Not marked | DOI missing; BibTeX key missing | Yes | Medium | Core for tool graph orchestration. Preprint status should be stated if not peer reviewed. |
| P12 | Jiayi Zhang et al., "AFlow: Automating Agentic Workflow Generation", 2025, ICLR | Not marked | DOI is arXiv/title label; BibTeX key missing | Yes | Medium | Core for agentic workflow generation. Verify final ICLR details. |
| P13 | Shuofei Qiao et al., "Benchmarking Agentic Workflow Generation", 2025, ICLR | Not marked | DOI is arXiv URL; BibTeX key missing | Yes | Medium | Core for workflow generation evaluation. Verify final ICLR details. |
| P14 | Yiming Xiong et al., "Self-Organizing Agent Network for LLM-based Workflow Automation", year missing in Excel, AAAI | Not marked | Year missing in Excel; DOI is arXiv URL; BibTeX key missing | Supporting | High | Thesis claims AAAI 2026, while spreadsheet year is blank. Verify publication status carefully. |
| P15 | Yuanshuo Zhang et al., "GNNs as Predictors of Agentic Workflow Performances", 2025 | Not marked | Venue missing; DOI field is title label; BibTeX key missing | Weak | High | Useful only if workflow performance prediction is discussed. Verify arXiv/venue. |
| P16 | Yixin Liu et al., "Graph-Augmented Large Language Model Agents", year missing in Excel, arXiv | Not marked | Year missing in Excel; DOI is arXiv URL; BibTeX key missing | Yes | Medium | Core for graph-augmented agent context. Thesis lists 2025. Verify year and version. |
| P17 | Jingxiong Liu et al., "Exploring the Integration of Large Language Models in Industrial Test Maintenance Processes", 2025, arXiv | Not marked | DOI field is title label; BibTeX key missing | Supporting | High | Thesis reference lists arXiv:2409.06416, which may duplicate/conflict with P9's arXiv link. Verify. |
| P18 | Boming Xia, Qinghua Lu, Liming Zhu, Zhenchang Xing, Dehai Zhao, Hao Zhang, "Evaluation-Driven Development and Operations of LLM Agents", 2025, arXiv | Not marked | DOI is arXiv URL; BibTeX key missing | Yes | Medium | Core for evaluation/AgentOps framing. Verify current version and status. |
| P19 | Sreemaee Akshathala et al., "Beyond Task Completion", 2025, arXiv | Not marked | Relevance missing; DOI is arXiv URL; BibTeX key missing | Yes | High | Core for "raw task success is insufficient" if verified. Check arXiv existence/version before IJTech submission. |
| P20 | Meriem Mastouri, Emna Ksontini, Wael Kessentini, "Making REST APIs Agent-Ready", 2025, arXiv | Not marked | Relevance value is malformed as "H"; DOI is arXiv URL; BibTeX key missing | Supporting | Medium | Useful for REST/API tool integration, not industrial control by itself. |
| P21 | "MCP Security Bench", authors missing, year missing, venue missing | Not marked | Authors, year, venue, DOI, BibTeX key missing | Weak | Very high | Do not cite until fully verified. Useful only for security gap if metadata is fixed. |
| P22 | Mojtaba A. Farahani, Md Irfan Khan, Thorsten Wuest, "Hybrid Agentic AI and Multi-Agent Systems in Smart Manufacturing", year missing, NAMRC | Not marked | Year missing; relevance missing; DOI is arXiv URL; BibTeX key missing | Supporting | High | Verify NAMRC status and exact year before use. |
| P23 | Jiachen Li et al., "An LLM-Assisted Multi-Agent Control Framework for Roll-to-Roll Manufacturing", year missing, NAMRC 54 | Not marked | Year missing; venue incomplete; relevance missing; DOI is title/arXiv label; BibTeX key missing | Supporting | High | Potentially useful industrial control reference, but must be verified. |
| P24 | Marcos Lima Romero, Ricardo Suyama, "Agentic AI for Intent-Based Industrial Automation", 2025, arXiv | Not marked | Duplicate of P2; BibTeX key missing | Duplicate | High | Merge with P2 after verifying whether conference and arXiv entries are the same work. |
| P25 | Rene Bohnsack, Mickie de Wet, "AI is the Strategy", 2025, arXiv | Not marked | Relevance missing; BibTeX key missing | Weak | Medium | Not central to industrial orchestration. Avoid unless discussing business strategy, which is not needed for IJTech manuscript. |

## Possible Duplicates Or Conflicts

| Items | Issue | Recommended action |
| --- | --- | --- |
| P2 and P24 | Same title and authors, one conference row and one arXiv row. | Merge into one verified citation. Keep conference version if accepted; include arXiv only if needed. |
| P9 and P17 | Thesis references appear to reuse arXiv:2409.06416 in both rows, but titles differ. | Verify both arXiv IDs and correct the spreadsheet before submission. |
| P4 thesis vs Excel | Excel year is blank, thesis reference lists 2024. | Update only after verifying the publication record. |
| P14 thesis vs Excel | Thesis says AAAI 2026, spreadsheet has year blank and arXiv 2508.13732. | Verify acceptance status, year, and venue before using as a strong claim. |

## Core References Recommended For IJTech

1. P1 Lim et al. - LLM-enabled MAS in manufacturing.
2. P2/P24 Romero and Suyama - agentic AI for intent-based industrial automation.
3. P4 Potekhin et al. - IEC 61499, open distributed industrial systems.
4. P5 Zhao et al. - LLM-based MAS for intelligent shopfloor.
5. P7 Di Maggio - autonomous LLM agents for predictive maintenance survey.
6. P10 Xia et al. - LLM agents with OPC UA industrial automation control.
7. P11 ToolNet - graph-based tool orchestration.
8. P12 AFlow - automated agentic workflow generation.
9. P16 Graph-Augmented LLM Agents - graph context for LLM agents.
10. P18 Evaluation-Driven Development and Operations of LLM Agents - evaluation/AgentOps framing.

## Risky References To Avoid Until Verified

- P14 SOAN, because year/venue status must be confirmed.
- P19 Beyond Task Completion, because relevance and publication metadata are incomplete.
- P21 MCP Security Bench, because author/year/venue metadata are missing.
- P22 and P23, because year and venue status are incomplete.
- P25, because it is weakly connected to the manuscript's technical claims.

## Must-Verify Before IJTech Submission

- DOI or stable URL for every cited source.
- Final venue, year, and publication status for P2/P24, P5, P10, P12, P13, P14, P16, P18, P19, P22, and P23.
- Whether P9 and P17 have incorrect or duplicated arXiv identifiers.
- Whether P4 has a formal DOI or only a publisher URL.
- BibTeX keys for every final cited item.
- Whether arXiv-only papers are acceptable for the target IJTech reference mix.
