# Runtime Capability Profiles

These profiles are used only for fair evaluation interpretation. They do not
remove scenarios and do not change runtime behavior.

| runtime_id | supports | does_not_support |
| --- | --- | --- |
| reference_v1 | deterministic planning; capability matching; governance evaluation; governance-aware execution; blocking unsafe actions; safe abort behavior; approval_required decision recording | workflow-wide approval pause/resume; controlled post-approval execution; graph-native interrupt/resume; checkpoint persistence; SQLite checkpoint reopen/resume |
| langgraph_runtime | deterministic planning; capability matching; governance evaluation; governance-aware execution; controlled post-approval continuation; approval interrupt/resume; checkpoint persistence; SQLite checkpoint reopen/resume; graph-native trace markers | live PLC execution; certified safety enforcement |
| baseline_a_direct_without_governance | direct mapped adapter invocation | policy filtering; approval validation; approval interrupt/resume; governance trace completeness |
| baseline_b_single_stage_execution | single-stage deterministic execution heuristic | explicit capability matching; full workflow preservation; approval continuation; governance trace completeness |
| baseline_c_without_policy_filtering | matched adapter execution without policy filtering | blocking unsafe actions; approval gating; policy-compliant governance enforcement; governance trace completeness |
