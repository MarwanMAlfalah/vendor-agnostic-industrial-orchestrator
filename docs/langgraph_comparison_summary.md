# LangGraph Runtime Comparison

This experiment compares the existing deterministic reference runtime with an
optional LangGraph runtime path. The LangGraph path does not replace the
reference implementation; it wraps the same planner, matcher, governance, and
execution logic in a graph runtime with interrupt/resume support for approval
checkpoints.

## Results

| Runtime | Policy Compliance | Unsafe Exec. | Gov. Decision Acc. | Final Outcome Acc. | Trace Completeness | Total ms | Execution ms | Approval Resume Correctness | Resume Success |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Reference v1 custom deterministic orchestration | 1.0 | 0.0 | 1.0 | 1.0 | 1.0 | 5.015024 | 0.01258 | 1.0 | 1.0 |
| Experimental LangGraph runtime | 1.0 | 0.0 | 1.0 | 1.0 | 1.0 | 5.545788 | 0.221382 | 1.0 | 1.0 |

## Interpretation

The LangGraph runtime is expected to match the reference method on policy and
final-outcome metrics while adding explicit graph traces and pause/resume
semantics for `REQUIRE_APPROVAL` cases.
