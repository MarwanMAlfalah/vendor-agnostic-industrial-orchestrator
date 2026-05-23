# Mixed Workflow Comparison Summary

This experiment adds 12 deterministic mixed multi-step workflows and compares
the existing reference runtime with the optional LangGraph runtime.

## Aggregate Results

| Runtime | Policy Compliance | Unsafe Exec. | Gov. Decision Acc. | Final Outcome Acc. | Trace Completeness | Stage Coverage | Interrupt Trace Quality | Resume Success | Post-Resume Outcome Acc. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Reference v1 custom deterministic orchestration | 1.0 | 0.0 | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Experimental LangGraph runtime | 1.0 | 0.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |

## Sample Mixed Case

- Case: `CASE-MIXED-ALLOW-APPROVAL-001`
- Category: `MIXED_ALLOW_REQUIRE_APPROVAL`
- Expected governance sequence: `['ALLOW', 'REQUIRE_APPROVAL']`
- Industrial context: `{'interoperability_role': 'monitor_then_control_gate', 'system_level': 'supervisory_control', 'rami_alignment': 'IEC 62264 operations layer / RAMI 4.0 functional layer'}`

## Sample Interrupt/Resume Case

- Case: `CASE-MIXED-ALLOW-APPROVAL-001`
- Interrupted: `True`
- Resumed: `True`
- Final status: `partial_success`
- Trace: `['planner_node', 'matcher_node', 'governance_node', 'approval_interrupt', 'approval_resume', 'execution_node', 'final_result']`

## Interpretation

The reference runtime preserves policy correctness. The LangGraph runtime is
evaluated for additional runtime-level value: persisted approval checkpoints,
explicit resume behavior, and stage-level graph traces.
