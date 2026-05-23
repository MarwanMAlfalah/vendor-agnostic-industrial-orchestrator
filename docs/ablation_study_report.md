# Ablation Study Report

The ablation study reuses implemented deterministic baselines when they
directly correspond to removing part of the governance-aware architecture.
Conceptual ablations are explicitly marked as not implemented; no behavior is
invented for manuscript convenience.

## Results

| variant_id | implemented | policy_compliance_rate | unsafe_execution_rate | final_outcome_accuracy | trace_completeness | recovery_success_rate | mean_latency_ms |
| --- | --- | --- | --- | --- | --- | --- | --- |
| full_system | True | 0.858333 | 0.0 | 0.883333 | 1.0 | 0.0 | 0.019668 |
| without_governance | True | 0.0 | 0.583333 | 0.166667 | 0.0 | 0.0 | 0.016658 |
| without_capability_matching | True | 0.083333 | 0.0 | 0.166667 | 0.0 | 0.0 | 0.009672 |
| without_approval_revalidation | False |  |  |  |  |  |  |
| without_langgraph_persistence | False |  |  |  |  |  |  |
| without_trace_observability | False |  |  |  |  |  |  |

## Interpretation

`full_system` corresponds to the unchanged `reference_v1` runtime. The
`without_governance` and `without_capability_matching` variants are implemented
by existing baselines. Approval revalidation, LangGraph persistence removal,
and trace observability removal are reported as conceptual because the
repository does not include isolated runtime switches for those conditions.

## Limitations

These results are deterministic prototype measurements over generated
scenarios. They do not demonstrate production deployment, live PLC behavior, or
certified safety properties.
