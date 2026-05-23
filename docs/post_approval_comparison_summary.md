# Post-Approval Continuation Comparison

This experiment extends the optional LangGraph runtime from simple
pause/resume semantics to controlled post-approval continuation. A
`REQUIRE_APPROVAL` step now pauses, persists graph state, resumes with an
explicit approval payload, revalidates policy eligibility and adapter mapping,
and executes the gated step only when approval and mapping checks pass.

## Results

| Runtime | Final Outcome Acc. | Resume Correctness | Approved Step Exec. | Approval Validation Acc. | Gated Policy Compliance | Trace Completeness |
| --- | --- | --- | --- | --- | --- | --- |
| Reference v1 custom deterministic orchestration | 0.3333 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Experimental LangGraph controlled approval continuation | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |

## Valid Approval Example

- Case: `CASE-POST-APPROVAL-VALID-001`
- Approval state: `approved`
- Final status: `success`
- Gated step executed: `True`
- Trace: `['planner_node', 'matcher_node', 'governance_node', 'approval_interrupt', 'approval_resume', 'approval_validated', 'approved_execution', 'execution_node', 'final_result']`

## Invalid Or Missing Approval Example

- Case: `CASE-POST-APPROVAL-INVALID-PAYLOAD-001`
- Approval state: `approval_invalid`
- Validation error: `approval_not_granted`
- Final status: `partial_success`
- Gated step executed: `False`

## What This Adds Beyond Parity

The reference runtime remains policy-correct but does not execute approval-gated
steps after resume. The LangGraph runtime now demonstrates graph-native
checkpointing plus controlled continuation: approval validation, revalidation of
adapter/capability mapping, approved execution, safe rejection, and complete
approval traces.
