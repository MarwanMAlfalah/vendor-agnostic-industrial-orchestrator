# Recommended Runtime Hardening Plan

No hardening changes are implemented in this audit task. The following items
are future work candidates based on the diagnostic evidence.

| improvement | motivation | affected_failure_categories | expected_effect_on_metrics | risk_of_changing_claims | needed_before_sedm | needed_before_ijtech |
| --- | --- | --- | --- | --- | --- | --- |
| Schema validation for capability inputs | Catch malformed payloads before adapter invocation. | scenario_generator_issue, true_runtime_limitation | Improve stress-scope final outcome accuracy and containment explainability. | Low if reported as future hardening, moderate if old/new results are mixed. | No | Recommended |
| Clearer unavailable capability handling | Differentiate unsupported, unavailable, and invalid mappings. | true_runtime_limitation, conservative_safe_failure | Improve diagnosis and possibly containment accuracy. | Moderate; requires re-running scaled results. | No | Recommended |
| Explicit supported-scope labels | Prevent ambiguity between intended behavior and stress tests. | unsupported_scenario_scope, label_runtime_mismatch | Improve interpretability, not runtime behavior. | Low if both scopes remain reported. | Helpful | Yes |
| Stronger trace outputs for failure cases | Make safe abort, invalid approval, and unavailable capability evidence easier to audit. | trace_instrumentation_gap, unknown_needs_review | Improve trace completeness and evidence quality. | Low; instrumentation-only if behavior unchanged. | No | Recommended |
| Additional tests for failure families | Lock in expected behavior for malformed, unavailable, and invalidated-mapping scenarios. | scenario_generator_issue, true_runtime_limitation | Improves reproducibility confidence, not necessarily aggregate rates. | Low. | Helpful | Yes |
