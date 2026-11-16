# ElCon-EE 2027 recovery study — run `20261110T124221Z-33ea97c`

**Evidence label:** In-repository, service-level deterministic simulation. Protocol v1.0 (frozen).
Primary: 52 case-policy trials; 5 deterministic replays each (300 executions incl. stress), used only as a reproducibility check, not as samples. Identical across replays: True.

## Primary metrics (n/N per policy; generated from trials.csv)

| Metric | B0 | B1 | B2 | P |
|---|---|---|---|---|
| duplicate_effect_rate | 6/13 | 6/13 | 2/13 | 0/13 |
| correct_recovery_decision_rate | 4/13 | 4/13 | 10/13 | 13/13 |
| recovery_completion_rate | 6/11 | 6/11 | 9/11 | 10/11 |
| hindsight_completion_rate | 7/12 | 7/12 | 9/12 | 10/12 |
| unnecessary_hold_rate | 0/10 | 0/10 | 0/10 | 0/10 |
| required_hold_compliance | 0/2 | 0/2 | 2/2 | 2/2 |
| information_forced_holds | 0/1 | 0/1 | 1/1 | 1/1 |
| dispatches_total | 27 | 27 | 22 | 20 |
| recovery_dispatches_total | 14 | 14 | 9 | 7 |
| acks_delivered_total | 15 | 15 | 10 | 8 |
| committed_effects_total | 19 | 19 | 14 | 12 |
| adopted_total | 0 | 0 | 3 | 4 |
| holds_total | 0 | 0 | 2 | 3 |
| simulated_wait_s_total | 0.0 | 0.0 | 0.0 | 40.0 |
| unauthorized_effect_rate | not evaluated | not evaluated | not evaluated | not evaluated |

## Case-by-case (replay 0): terminal actions / oracle validity / committed effects / status

| Case | B0 | B1 | B2 | P |
|---|---|---|---|---|
| C01 | REDISPATCH ✓ e=1 completed | REDISPATCH ✓ e=1 completed | REDISPATCH ✓ e=1 completed | REDISPATCH ✓ e=1 completed |
| C02 | REDISPATCH ✗ e=1 completed | REDISPATCH ✗ e=1 completed | REDISPATCH ✓ e=1 completed | REDISPATCH ✓ e=1 completed |
| C03 | REDISPATCH ✗ e=2 not_completed | REDISPATCH ✗ e=2 not_completed | ADOPT ✓ e=1 completed | ADOPT ✓ e=1 completed |
| C04 | REDISPATCH ✓ e=1 completed | REDISPATCH ✓ e=1 completed | REDISPATCH ✓ e=1 completed | REDISPATCH ✓ e=1 completed |
| C05 | REDISPATCH ✗ e=2 not_completed | REDISPATCH ✗ e=2 not_completed | HOLD ✓ e=1 held | HOLD ✓ e=1 held |
| C06 | REDISPATCH ✗ e=1 completed | REDISPATCH ✗ e=1 completed | HOLD ✓ e=0 held | HOLD ✓ e=0 held |
| C07 | REDISPATCH ✓ e=1 completed | REDISPATCH ✓ e=1 completed | REDISPATCH ✓ e=1 completed | REDISPATCH ✓ e=1 completed |
| C08a | REDISPATCH ✗ e=2 not_completed | REDISPATCH ✗ e=2 not_completed | ADOPT ✓ e=1 completed | ADOPT ✓ e=1 completed |
| C08b | REDISPATCH ✗ e=2 not_completed | REDISPATCH ✗ e=2 not_completed | REDISPATCH ✗ e=2 not_completed | ADOPT ✓ e=1 completed |
| C08c | REDISPATCH ✗ e=1 completed | REDISPATCH ✗ e=1 completed | REDISPATCH ✗ e=1 completed | REDISPATCH ✓ e=1 completed |
| C09 | REDISPATCH ✗ e=2 not_completed | REDISPATCH ✗ e=2 not_completed | REDISPATCH ✗ e=2 not_completed | HOLD ✓ e=1 held |
| C10 | REDISPATCH ✓ e=1 completed | REDISPATCH ✓ e=1 completed | REDISPATCH ✓ e=1 completed | REDISPATCH ✓ e=1 completed |
| C11b | REDISPATCH,REDISPATCH ✗ e=2 not_completed | REDISPATCH,REDISPATCH ✗ e=2 not_completed | REDISPATCH,ADOPT ✓ e=1 completed | REDISPATCH,ADOPT ✓ e=1 completed |

## Comparison with protocol v1.0 §3 inferred behaviour: 52/52 match


## Concurrency stress cases (excluded from primary metrics)

| Case | Policy | Terminal | Valid | Dispatches | Effects | Status |
|---|---|---|---|---|---|---|
| C11a | B0 | REDISPATCH,REDISPATCH | False | 3 | 2 | not_completed |
| C11a | B1 | REDISPATCH,REDISPATCH | False | 3 | 2 | not_completed |
| C11a | B2 | REDISPATCH,REDISPATCH | True | 3 | 2 | not_completed |
| C11a | P | REDISPATCH,REDISPATCH | True | 3 | 2 | not_completed |
| C12 | B0 | REDISPATCH,REDISPATCH | True | 3 | 1 | completed |
| C12 | B1 | REDISPATCH,REDISPATCH | True | 3 | 1 | completed |
| C12 | B2 | REDISPATCH,REDISPATCH | True | 3 | 1 | completed |
| C12 | P | REDISPATCH,REDISPATCH | True | 3 | 1 | completed |

## Opt-in LangGraph pipeline integration cross-check (not the 52-trial evaluation)

| Case | Policy | Recovery decision | Dispatches | Effects | Status | Service-level terminal / effects | Match |
|---|---|---|---|---|---|---|---|
| C03 | B0 | REDISPATCH | 2 | 2 | completed | REDISPATCH / 2 | True |
| C03 | B2 | ADOPT | 1 | 1 | completed | ADOPT / 1 | True |
| C03 | P | ADOPT | 1 | 1 | completed | ADOPT / 1 | True |
| C04 | B0 | REDISPATCH | 2 | 1 | completed | REDISPATCH / 1 | True |
| C04 | B2 | REDISPATCH | 2 | 1 | completed | REDISPATCH / 1 | True |
| C04 | P | REDISPATCH | 2 | 1 | completed | REDISPATCH / 1 | True |
| C05 | B0 | REDISPATCH | 2 | 2 | completed | REDISPATCH / 2 | True |
| C05 | B2 | HOLD | 1 | 1 | held | HOLD / 1 | True |
| C05 | P | HOLD | 1 | 1 | held | HOLD / 1 | True |
| C08b | B0 | REDISPATCH | 2 | 2 | completed | REDISPATCH / 2 | True |
| C08b | B2 | REDISPATCH | 2 | 2 | completed | REDISPATCH / 2 | True |
| C08b | P | ADOPT | 1 | 1 | completed | ADOPT / 1 | True |
| C08c | B0 | REDISPATCH | 2 | 1 | completed | REDISPATCH / 1 | True |
| C08c | B2 | REDISPATCH | 2 | 1 | completed | REDISPATCH / 1 | True |
| C08c | P | REDISPATCH | 2 | 1 | completed | REDISPATCH / 1 | True |
| C09 | B0 | REDISPATCH | 2 | 2 | completed | REDISPATCH / 2 | True |
| C09 | B2 | REDISPATCH | 2 | 2 | completed | REDISPATCH / 2 | True |
| C09 | P | HOLD | 1 | 1 | held | HOLD / 1 | True |

Not claimed: exactly-once execution, late or in-flight commits (F5c), concurrent-resume safety, pipeline-integrated or industrial evidence for the primary matrix, or a new waiting algorithm.
