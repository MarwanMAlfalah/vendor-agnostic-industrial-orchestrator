# Metrics Definitions

These metrics summarize deterministic execution outcomes across a fixed set of
evaluation runs. Let `N` be the number of runs, `S` the set of all runs, and
`steps(r)` the execution steps recorded for run `r`.

## total_runs

Plain English: The number of evaluation runs included in the comparison.

Formula: `total_runs = N`

Interpretation: This is the denominator for run-level rates. In the current
comparison, each method is evaluated on the same 12 deterministic cases.

## success_count and success_rate

Plain English: The number and fraction of runs that completed with final status
`success`.

Formula: `success_count = |{r in S : status(r) = success}|`;
`success_rate = success_count / N`

Interpretation: A success means the method completed without policy stops,
safe aborts, or execution failures. For baselines, success can include behavior
that ignores governance constraints, so it should be interpreted with the
intervention and coverage metrics.

## partial_success_count and partial_success_rate

Plain English: The number and fraction of runs that completed at least part of
the workflow but stopped or skipped due to a non-terminal policy or execution
condition.

Formula: `partial_success_count = |{r in S : status(r) = partial_success}|`;
`partial_success_rate = partial_success_count / N`

Interpretation: Partial success captures controlled incompleteness, such as a
step requiring approval before automatic execution can continue.

## blocked_count and blocked_rate

Plain English: The number and fraction of runs blocked by governance policy.

Formula: `blocked_count = |{r in S : status(r) = blocked}|`;
`blocked_rate = blocked_count / N`

Interpretation: A nonzero blocked rate can be desirable in governed settings
when forbidden or unsafe actions are present in the evaluation set.

## safe_aborted_count and safe_aborted_rate

Plain English: The number and fraction of runs that stopped safely because the
system detected an invalid or unsafe execution mapping.

Formula: `safe_aborted_count = |{r in S : status(r) = safe_aborted}|`;
`safe_aborted_rate = safe_aborted_count / N`

Interpretation: Safe aborts indicate that the system avoided execution when it
could not establish a valid adapter or capability mapping.

## failed_count and failed_rate

Plain English: The number and fraction of runs that ended in execution failure.

Formula: `failed_count = |{r in S : status(r) = failed}|`;
`failed_rate = failed_count / N`

Interpretation: Failures represent uncontrolled execution errors or malformed
execution attempts that were not converted into governance-level stops.

## governance_intervention_rate

Plain English: The fraction of runs in which governance intervened through a
block, approval requirement, fallback, or safe abort.

Formula: `governance_intervention_rate = |{r in S : block(r) + require_approval(r) + fallback(r) + safe_abort(r) > 0}| / N`

Interpretation: This measures how often the governance layer changes execution
behavior. A higher value is expected when the case set intentionally includes
policy-sensitive scenarios.

## governance_decision_accuracy

Plain English: The fraction of runs whose observed governance decision matches
the gold expected governance decision for the case.

Formula: `governance_decision_accuracy = |{r in S : observed_governance_decision(r) = expected_governance_decision(r)}| / N`

Interpretation: This evaluates policy-decision correctness directly. Methods
that bypass governance can score poorly even when they have high raw execution
coverage.

## final_outcome_accuracy

Plain English: The fraction of runs whose final execution status matches the
gold expected final status.

Formula: `final_outcome_accuracy = |{r in S : status(r) = expected_status(r)}| / N`

Interpretation: This measures whether each method reaches the intended
supervisory outcome, including controlled non-execution outcomes such as
`blocked` and `safe_aborted`.

## policy_compliance_rate

Plain English: The fraction of runs that both obey the expected execution
permission and end in the expected policy outcome.

Formula: `policy_compliance_rate = compliant_runs / N`, where a compliant run
executes only when `expected_execution_allowed = true` and otherwise terminates
with the expected non-execution status and governance decision.

Interpretation: This is the primary safety-oriented aggregate metric. It
rewards controlled execution for allowed cases and controlled non-execution for
policy-sensitive cases.

## unsafe_execution_rate

Plain English: The fraction of forbidden or approval-required cases that were
executed automatically.

Formula: `unsafe_execution_rate = automatically_executed(BLOCK or REQUIRE_APPROVAL cases) / total(BLOCK or REQUIRE_APPROVAL cases)`

Interpretation: Lower is better. A value of `0.0` indicates that the method did
not automatically execute actions that should have been blocked or held for
approval.

## approval_bypass_rate

Plain English: The fraction of `REQUIRE_APPROVAL` cases that executed without
approval.

Formula: `approval_bypass_rate = automatically_executed(REQUIRE_APPROVAL cases) / total(REQUIRE_APPROVAL cases)`

Interpretation: Lower is better. This metric isolates whether a method respects
approval gates rather than only aggregate block behavior.

## invalid_mapping_containment_rate

Plain English: The fraction of invalid mapping cases that correctly ended in
`SAFE_ABORT` or equivalent safe handling.

Formula: `invalid_mapping_containment_rate = contained_invalid_mapping_cases / total_invalid_mapping_cases`

Interpretation: Higher is better. This measures whether malformed adapter or
capability mappings are contained before execution.

## average_completed_steps

Plain English: The mean number of executed steps per run.

Formula: `average_completed_steps = (sum completed_steps(r) for r in S) / N`

Interpretation: This indicates how much adapter-backed work each method
completed on average.

## average_skipped_steps

Plain English: The mean number of skipped, blocked, approval-required,
fallback-pending, or safe-aborted steps per run.

Formula: `average_skipped_steps = (sum skipped_steps(r) for r in S) / N`

Interpretation: This measures how much of the workflow was intentionally not
executed because it was non-executable, policy-constrained, or unsafe.

## execution_coverage_ratio

Plain English: The fraction of observed steps that were executed.

Formula: `execution_coverage_ratio = total_completed_steps / (total_completed_steps + total_skipped_steps + total_failed_steps)`

Interpretation: Higher coverage means more recorded steps were executed. In
governed industrial workflows, higher coverage is not automatically better if it
comes from bypassing approval, block, or safe-abort behavior.

## adapter_utilization_ratio per adapter

Plain English: For each adapter, the fraction of executed adapter-backed steps
handled by that adapter.

Formula: `adapter_utilization_ratio(adapter_i) = executed_steps(adapter_i) / total_executed_adapter_steps`

Interpretation: This shows how execution load is distributed across the
heterogeneous adapter set. A ratio of `0.0` means the adapter was not used by a
method in the comparison.

## average_total_latency_ms

Plain English: The mean measured wall-clock latency per run across all measured
stages.

Formula: `average_total_latency_ms = (sum total_latency_ms(r) for r in S) / N`

Interpretation: This reports computational overhead for a method in the local
deterministic prototype. It is not a live industrial latency benchmark.

## average_execution_latency_ms

Plain English: The mean measured latency of the execution stage per run.

Formula: `average_execution_latency_ms = (sum execution_latency_ms(r) for r in S) / N`

Interpretation: This isolates adapter invocation and execution-policy handling
from planning, matching, and governance timing.

## average_planning_latency_ms

Plain English: The mean measured latency of planning or baseline selection per
run.

Formula: `average_planning_latency_ms = (sum planning_latency_ms(r) for r in S) / N`

Interpretation: For the reference method this measures deterministic planning
over source goals. For baselines that do not include a planner, this is `0.0`
unless the baseline performs a direct deterministic selection step.

## average_matching_latency_ms

Plain English: The mean measured latency of capability matching per run.

Formula: `average_matching_latency_ms = (sum matching_latency_ms(r) for r in S) / N`

Interpretation: This captures the cost of mapping planned steps to registered
adapter capabilities. Baselines that bypass matching report `0.0`.

## average_governance_latency_ms

Plain English: The mean measured latency of governance evaluation or policy
filtering per run.

Formula: `average_governance_latency_ms = (sum governance_latency_ms(r) for r in S) / N`

Interpretation: This captures deterministic policy-evaluation overhead. A
baseline that removes governance-aware filtering can have lower latency while
also producing poorer policy-compliance metrics.
