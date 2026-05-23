# Mathematical Metrics Appendix

Let `R` be the set of evaluation runs and `N = |R|`. Let `status(r)` be the
final status of run `r`. Let `E(r)` indicate whether a protected or target step
was executed. Let `G(r)` be the observed governance decision and `G*(r)` the
gold expected decision.

## policy_compliance_rate

Formula: `|{r in R : compliant(r)}| / N`

Interpretation: Fraction of runs that obey expected execution permissions and
final policy outcomes.

High values mean: runs followed the policy model.

High values are not necessarily good when: the case set is too narrow or lacks
realistic unsafe scenarios.

Level: run-level.

## unsafe_execution_rate

Formula: `|{r in R_sensitive : sensitive_step_executed(r)}| / |R_sensitive|`

Interpretation: Fraction of forbidden or approval-required cases where the
sensitive step executed automatically.

High values mean: unsafe bypass behavior.

High values are not good.

Level: step-aware run-level.

## approval_bypass_rate

Formula: `|{r in R_approval : approval_step_executed_without_valid_approval(r)}| / |R_approval|`

Interpretation: Measures approval-gate bypass.

High values mean: approval control failed.

High values are not good.

Level: approval-step level.

## governance_decision_accuracy

Formula: `|{r in R : G(r) = G*(r)}| / N`

Interpretation: Fraction of runs with the expected governance decision.

High values mean: governance classifications match the gold labels.

High values are not necessarily good when: gold labels are incomplete or
oversimplified.

Level: run-level.

## final_outcome_accuracy

Formula: `|{r in R : status(r) = status*(r)}| / N`

Interpretation: Fraction of runs ending in the expected final state.

High values mean: execution outcomes match expected supervisory behavior.

High values are not necessarily good when: expected statuses do not cover enough
edge cases.

Level: run-level.

## execution_coverage_ratio

Formula: `completed_steps / (completed_steps + skipped_steps + failed_steps)`

Interpretation: Fraction of observed steps that executed.

High values mean: more steps executed.

High values are not necessarily good when: execution occurs by bypassing
governance.

Level: step-level aggregate.

## governance_intervention_rate

Formula: `|{r in R : block(r) + require_approval(r) + fallback(r) + safe_abort(r) > 0}| / N`

Interpretation: Fraction of runs where governance changed or constrained
execution.

High values mean: frequent policy intervention.

High values are not necessarily good or bad; they depend on the case mix.

Level: run-level.

## trace_completeness

Formula: `|{r in R : required_trace_markers subset trace(r)}| / N`

Interpretation: Fraction of traces containing required markers.

High values mean: trace records are complete for inspection.

High values are not necessarily good when: traces are complete but behavior is
incorrect.

Level: trace-level.

## trace_stage_coverage

Formula: `(sum over r of covered_required_stages(r) / total_required_stages) / N`

Interpretation: Mean fraction of expected runtime stages present in traces.

High values mean: graph/runtime stages are visible.

High values are not necessarily good when: trace visibility hides poor policy
behavior.

Level: trace-level.

## interrupt_trace_quality

Formula: `|{r in R_approval : interrupt_before_resume_before_execution(r)}| / |R_approval|`

Interpretation: Fraction of approval traces with correctly ordered interrupt
and resume markers.

High values mean: approval checkpoint traces are coherent.

High values are not necessarily good when: approval validation is incorrect.

Level: trace-level.

## approval_resume_correctness

Formula: `|{r in R_approval : resumed(r) and status(r) = post_resume_status*(r)}| / |R_approval|`

Interpretation: Fraction of approval cases that resume and end correctly.

High values mean: pause/resume semantics match expectations.

High values are not necessarily good when: approved steps execute without
validation.

Level: recovery / approval-run level.

## approval_validation_accuracy

Formula: `|{r in R_approval : observed_validation(r) = expected_validation(r)}| / |R_approval|`

Interpretation: Fraction of approval payloads correctly accepted or rejected.

High values mean: approval input handling is correct.

High values are not necessarily good when: approval payload policy is too weak.

Level: approval-run level.

## approved_step_execution_rate

Formula: `executed_valid_approved_gated_steps / valid_approved_gated_steps`

Interpretation: Fraction of validly approved gated steps that execute.

High values mean: valid approvals lead to controlled continuation.

High values are not necessarily good unless approval validation and policy
revalidation also pass.

Level: gated-step level.

## checkpoint_resume_success_rate

Formula: `checkpointed_and_interrupt_reached_runs / restart_demo_runs`

Interpretation: Fraction of demo runs that reach an interrupt and save a
checkpoint.

High values mean: checkpoint creation works at the approval boundary.

High values are not necessarily good unless resume also succeeds.

Level: recovery-level.

## restart_recovery_success_rate

Formula: `resumed_after_process_restart_runs / restart_demo_runs`

Interpretation: Fraction of demo runs that resume from persisted checkpoint
state after simulated restart.

High values mean: restart recovery works in the demo configuration.

High values are not necessarily good when: only one narrow checkpoint type is
tested.

Level: recovery-level.

## post_restart_final_outcome_accuracy

Formula: `|{r in R_restart : status(r) = post_restart_status*(r)}| / |R_restart|`

Interpretation: Fraction of restart demo runs ending in expected final state.

High values mean: recovery preserves final supervisory behavior.

High values are not necessarily good when: restart cases are too few.

Level: recovery-level.

