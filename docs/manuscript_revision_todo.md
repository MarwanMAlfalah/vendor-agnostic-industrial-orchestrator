# Manuscript Revision TODO

Priority scale:

- `critical`: needed before journal submission.
- `high`: strongly recommended before full draft circulation.
- `medium`: improves polish or review readiness.

## Critical Fixes

- [ ] Replace every `(Author, year)` placeholder with verified references.
- [ ] Resolve P2/P24 duplicate and choose one canonical citation.
- [ ] Verify P9 and P17 arXiv identifier conflict before citing either.
- [ ] Remove or rewrite thesis-origin text that says no implementation is proposed.
- [ ] Ensure every aligned 1.0 claim is paired with original metrics and deterministic mock-adapter scope.
- [ ] Keep explicit limitations: no production deployment, no certified safety, no live PLC integration, no regulatory compliance.
- [ ] Ensure LangSmith is described only as observability evidence.
- [ ] Confirm all references use IJTech-required style after verification.

## Citation Fixes

- [ ] Verify DOI or stable URL for P1 through P25 before inclusion.
- [ ] Add BibTeX keys for all final references.
- [ ] Confirm final venue and publication status for P5, P10, P12, P13, P14, P16, P18, P19, P22, and P23.
- [ ] Add official OPC UA citation or standards reference if IJTech expects standards-level support.
- [ ] Add official IEC 61499 citation or standards reference if using standards claims.
- [ ] Add support for safety/governance terms if referencing IEC 61508/61511 or safety certification background.
- [ ] Decide whether arXiv preprints are acceptable in the final IJTech reference list.
- [ ] Avoid citing P21 until authors/year/venue are complete.
- [ ] Avoid citing P25 unless business-model context is added, which is not currently necessary.

## Wording Fixes

- [ ] Replace "finished product" with "implemented research system" where journal tone requires caution.
- [ ] Replace "universal gap" with "gap across the reviewed set" unless the review scope is fully specified.
- [ ] Use "reported" for third-party system results from the thesis until primary sources are verified.
- [ ] Use "prototype", "deterministic", "synthetic", and "mock adapters" near empirical claims.
- [ ] Avoid "safe" as a certified property; use "safe-abort behavior" only as a prototype governance outcome.
- [ ] Avoid implying LangGraph itself guarantees safety or recovery; describe the implemented runtime behavior.

## Blind-Review Cleanup

- [ ] Remove author name, university, acknowledgements, and thesis-specific identity details from any submitted supplementary material.
- [ ] Do not include raw repository screenshots unless fully anonymized.
- [ ] Do not include raw LangSmith screenshots unless workspace, project, trace URLs, browser profile, and account identity are removed.
- [ ] Replace local filesystem paths with anonymized artifact names.
- [ ] Use anonymized repository or archive links if supplementary materials are submitted.

## IJTech Compliance Items

- [ ] Confirm abstract word limit and structure against IJTech guidelines.
- [ ] Confirm keyword count and formatting.
- [ ] Convert citations and references to the IJTech-required style.
- [ ] Confirm table and figure captions follow journal style.
- [ ] Confirm ethical, data availability, conflict-of-interest, and funding statements if required.
- [ ] Confirm whether supplementary CSV artifacts are allowed.
- [ ] Confirm whether preprints are acceptable references.

## Figures And Tables Still Needed

- [ ] Redraw architecture figure without repository or account identifiers.
- [ ] Redraw governance decision pipeline figure.
- [ ] Create policy compliance vs unsafe execution figure from aligned journal data.
- [ ] Create supported-versus-stress scope figure.
- [ ] Create LangGraph approval continuation schematic.
- [ ] Create local crash/restart checkpoint schematic.
- [ ] Create latency summary figure or table note with local-measurement caveat.
- [ ] Convert thesis qualitative comparison into a shortened verified related-work table if desired.

## Results Consistency Checks

- [ ] Verify that the main manuscript uses the 240-scenario journal profile as primary evidence.
- [ ] Mention the 500-scenario extended profile as additional deterministic coverage only.
- [ ] Keep original metrics visible wherever aligned metrics are emphasized.
- [ ] Do not add ungenerated ablation results.
- [ ] Keep conceptual ablations clearly labeled as conceptual.
- [ ] Keep supported-versus-stress counts and interpretations consistent with current result files.
