# Post-Approval Metrics Definitions

## approval_resume_correctness
Fraction of approval-gated cases that interrupt, resume, and end with the gold
post-resume final status.

Formula: `correct_resumed_approval_cases / approval_gated_cases`

## approved_step_execution_rate
Fraction of validly approved gated steps that actually execute.

Formula: `executed_valid_approved_gated_steps / valid_approved_gated_steps`

## approval_validation_accuracy
Fraction of approval decisions correctly accepted or rejected according to the
approval payload.

Formula: `correct_approval_validation_decisions / approval_gated_cases`

## post_resume_final_outcome_accuracy
Fraction of resumed workflows whose final status matches the gold post-resume
status.

Formula: `post_resume_status_matches / approval_gated_cases`

## gated_step_policy_compliance_rate
Fraction of gated steps handled according to expected policy before and after
resume.

Formula: `policy_compliant_gated_step_runs / approval_gated_cases`

## resume_success_rate
Fraction of approval-gated cases where the graph resumes after interrupt.

Formula: `resumed_approval_cases / approval_gated_cases`

## approved_execution_trace_completeness
Fraction of approval-resumed runs whose traces contain all required approval
markers. A complete trace includes either `approval_validated` or
`approval_rejected`; runs expected to execute must also contain
`approved_execution`.

Formula: `complete_approval_traces / approval_gated_cases`
