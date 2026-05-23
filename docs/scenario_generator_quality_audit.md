# Scenario Generator Quality Audit

Journal profile scenario count: 240.

## Factor Balance Preview

| factor_name | factor_value | count | percentage |
| --- | --- | --- | --- |
| workflow_length | long | 80 | 0.333333 |
| workflow_length | medium | 80 | 0.333333 |
| workflow_length | short | 80 | 0.333333 |
| governance_pattern | all_allow | 20 | 0.083333 |
| governance_pattern | allow_then_block | 20 | 0.083333 |
| governance_pattern | allow_then_require_approval | 20 | 0.083333 |
| governance_pattern | allow_then_safe_abort | 20 | 0.083333 |
| governance_pattern | invalid_mapping | 20 | 0.083333 |
| governance_pattern | malformed_payload | 20 | 0.083333 |
| governance_pattern | mixed_allow_approval_block | 20 | 0.083333 |
| governance_pattern | mixed_allow_approval_safe_abort | 20 | 0.083333 |
| governance_pattern | post_approval_invalid | 20 | 0.083333 |
| governance_pattern | post_approval_missing | 20 | 0.083333 |
| governance_pattern | post_approval_valid | 20 | 0.083333 |
| governance_pattern | unavailable_capability | 20 | 0.083333 |
| adapter_mix | Legacy only | 34 | 0.141667 |
| adapter_mix | OPC UA + Legacy | 34 | 0.141667 |
| adapter_mix | OPC UA + REST | 35 | 0.145833 |
| adapter_mix | OPC UA + REST + Legacy | 34 | 0.141667 |
| adapter_mix | OPC UA only | 35 | 0.145833 |

## Consistency Checks

| check_name | status | detail |
| --- | --- | --- |
| duplicate_scenario_ids | pass | No duplicate scenario ids detected. |
| duplicate_scenario_signatures | warn | 62 duplicate factor/expectation signatures detected. |
| approval_condition_requires_approval_step | pass | No inconsistencies detected. |
| safe_abort_status_consistency | pass | No inconsistencies detected. |
| block_status_consistency | warn | 5 scenarios need review, e.g. ['SCN-0048', 'SCN-0145', 'SCN-0158', 'SCN-0176', 'SCN-0224']. |
| runtime_applicability_consistency | pass | No inconsistencies detected. |
| dominant_governance_decision_consistency | pass | No inconsistencies detected. |
| governance_pattern_coverage | pass | All requested governance patterns are represented. |
| failure_condition_coverage | pass | Requested failure/containment conditions are represented or explicitly absent by profile. |

## Interpretation

The generator provides broad deterministic factor coverage. Duplicate factor
signatures can occur because the scenario count exceeds the Cartesian coverage
needed for some factor combinations; this is not necessarily a duplicate
scenario id. Unrealistic or unsupported combinations are flagged as audit
findings rather than silently removed.
