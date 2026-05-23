# Scaled Experimental Design

This package adds deterministic empirical scaling around the existing
vendor-agnostic, governance-aware orchestration prototype. It does not change
the core architecture or `reference_v1` behavior.

## Profiles

| Profile | Command | Scenario Count | Output |
| --- | --- | ---: | --- |
| Default | `python -m app.evaluation.scenario_generator --profile default` | 120 | `data/scenarios/scaled_scenarios_120.json` |
| Journal | `python -m app.evaluation.scenario_generator --profile journal` | 240 | `data/scenarios/scaled_scenarios_240.json` |
| Extended | `python -m app.evaluation.scenario_generator --profile extended` | 500 | `data/scenarios/scaled_scenarios_500.json` |

## Controlled Factors

The deterministic generator balances scenarios across workflow length,
governance pattern, adapter mix, approval condition, containment condition, and
runtime applicability. The fixed seed is recorded in every scenario record.

Workflow length categories are short, medium, and long. Governance patterns
include all-allow, approval, block, safe-abort, mixed workflows,
post-approval variants, invalid mappings, unavailable capabilities, and
malformed payload containment. Adapter mixes cover OPC UA, REST, legacy, and
their combinations.

## Scenario Record

Each scenario includes:

- `scenario_id`
- `scenario_family`
- `workflow_length` and `workflow_step_count`
- governance, adapter, approval, and failure factors
- `runtime_applicability`
- input goal and payload
- deterministic governance plan
- expected governance sequence and final status
- expected execution and policy labels
- expected trace markers
- industrial context, RAMI alignment, and interoperability role

## Interpretation

The scenarios are synthetic and deterministic. They are designed for empirical
coverage and manuscript tables, not for live PLC validation or certified safety
claims.
