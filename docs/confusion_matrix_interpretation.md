# Confusion Matrix Interpretation

The confusion matrices report expected versus observed final status and
expected versus observed governance decision by runtime and scenario family.

## Final Status Mismatch Preview

| runtime_id | scenario_family | expected | observed | count |
| --- | --- | --- | --- | --- |
| baseline_a_direct_without_governance | allow_then_block | partial_success | success | 20 |
| baseline_a_direct_without_governance | allow_then_require_approval | partial_success | success | 15 |
| baseline_a_direct_without_governance | allow_then_require_approval | safe_aborted | success | 5 |
| baseline_a_direct_without_governance | allow_then_safe_abort | safe_aborted | partial_success | 20 |
| baseline_a_direct_without_governance | invalid_mapping | safe_aborted | partial_success | 20 |
| baseline_a_direct_without_governance | malformed_payload | safe_aborted | success | 20 |
| baseline_a_direct_without_governance | mixed_allow_approval_block | partial_success | success | 15 |
| baseline_a_direct_without_governance | mixed_allow_approval_block | safe_aborted | success | 5 |
| baseline_a_direct_without_governance | mixed_allow_approval_safe_abort | safe_aborted | partial_success | 20 |
| baseline_a_direct_without_governance | post_approval_invalid | partial_success | success | 20 |
| baseline_a_direct_without_governance | post_approval_missing | partial_success | success | 20 |
| baseline_a_direct_without_governance | unavailable_capability | safe_aborted | partial_success | 20 |

## Governance Decision Mismatch Preview

| runtime_id | scenario_family | expected | observed | count |
| --- | --- | --- | --- | --- |
| baseline_a_direct_without_governance | all_allow | ALLOW | NONE | 20 |
| baseline_a_direct_without_governance | allow_then_block | BLOCK | NONE | 20 |
| baseline_a_direct_without_governance | allow_then_require_approval | REQUIRE_APPROVAL | NONE | 15 |
| baseline_a_direct_without_governance | allow_then_require_approval | SAFE_ABORT | NONE | 5 |
| baseline_a_direct_without_governance | allow_then_safe_abort | SAFE_ABORT | NONE | 20 |
| baseline_a_direct_without_governance | invalid_mapping | SAFE_ABORT | NONE | 20 |
| baseline_a_direct_without_governance | malformed_payload | SAFE_ABORT | NONE | 20 |
| baseline_a_direct_without_governance | mixed_allow_approval_block | BLOCK | NONE | 15 |
| baseline_a_direct_without_governance | mixed_allow_approval_block | SAFE_ABORT | NONE | 5 |
| baseline_a_direct_without_governance | mixed_allow_approval_safe_abort | SAFE_ABORT | NONE | 20 |
| baseline_a_direct_without_governance | post_approval_invalid | REQUIRE_APPROVAL | NONE | 20 |
| baseline_a_direct_without_governance | post_approval_missing | REQUIRE_APPROVAL | NONE | 20 |

## Interpretation

The main error modes are not concentrated in unsafe proposed-runtime execution.
They are primarily baseline scope mismatches, partial-success versus success
differences for approval continuation, and conservative containment behavior in
stress scenarios. Unsafe execution is concentrated in governance-removing
baseline rows, which is useful as comparative evidence but should not be framed
as a production safety result.
