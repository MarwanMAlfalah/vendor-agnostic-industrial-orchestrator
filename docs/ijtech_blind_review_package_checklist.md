# IJTech Blind Review Package Checklist

## Manuscript Identity

- Remove author names and affiliations from the manuscript.
- Remove acknowledgements before blind review unless the journal explicitly permits them.
- Remove personal GitHub identity, organization names, and repository owner names from manuscript text.
- Replace local filesystem paths with anonymized artifact references.
- Use an anonymized repository or supplementary package if code/data access is required during review.
- Blind-review warning: repository screenshots can expose owner names, branch names, issue or pull request URLs, local paths, and browser account details.

## Claims Audit

- Do not claim production deployment.
- Do not claim certified safety.
- Do not claim live PLC integration.
- Do not claim vendor certification.
- Do not claim regulatory compliance.
- State that the adapters are mock implementations.
- State that scenarios are deterministic and synthetic.
- State that LangSmith is observability evidence only.
- State that checkpoint reopen/resume is local checkpoint evidence only.

## Evidence Audit

- Main empirical profile: 240 deterministic journal scenarios.
- Additional coverage profile: 500 deterministic extended scenarios.
- Report original metrics and aligned metrics together.
- Preserve baseline results, including weak or negative baseline behavior.
- Preserve supported and stress scope results.
- Use Wilson intervals only as scenario-distribution intervals.
- Do not add ungenerated metrics or field results.

## Tables

- Keep tables editable, not screenshots.
- Use consistent runtime names: `reference_v1`, `langgraph_runtime`, `baseline_a_direct_without_governance`, `baseline_b_single_stage_execution`, and `baseline_c_without_policy_filtering`.
- Include notes explaining deterministic synthetic evaluation.
- Include notes explaining runtime-specific expectation alignment.
- Mark conceptual ablations as conceptual only.

## Figures

- Redraw diagrams cleanly for submission.
- Export final figures at 300 dpi or higher if rasterized.
- Ensure all text is readable in grayscale.
- Avoid screenshots exposing account identity.
- Prefer redrawn LangGraph/LangSmith schematics over raw screenshots for blind review.
- Caption LangSmith-related material as observability evidence only.
- Blind-review warning: LangSmith screenshots can expose workspace names, trace URLs, project names, account identity, and browser profile details.

## References

- Verify every citation manually.
- Use the journal's required reference style.
- Do not cite internal repository files as external scholarly sources.
- Do not add placeholder references to the submission version.

## Supplementary Material

- Include relevant CSV tables if supplementary artifacts are allowed.
- Include scenario generator description, not hidden generated claims.
- Remove personal paths, usernames, and environment-specific identifiers.
- Confirm supplementary material does not expose account credentials or private project metadata.

## Final Submission Gate

- Title and abstract are journal-oriented rather than conference-oriented.
- Limitations are explicit.
- No code/runtime/business logic changes are required for the manuscript revision.
- All manuscript files are under `docs/`.
