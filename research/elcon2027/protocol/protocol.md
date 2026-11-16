# ElCon-EE 2027 recovery study — experimental protocol

Version **1.0**, status **FROZEN** (2026-11-09). `oracle_table.json` is authoritative for per-case
oracle data. `tests/test_elcon_protocol_oracle.py` checks its internal consistency, eligibility and
denominators. No policy-comparison results have been generated.

**Evidence label: In-repository, service-level deterministic simulation.** The harness drives
`app/integration/maintenance_effect_service.py` directly. This is not pipeline-integrated, live
industrial, OPC UA, PLC or production evidence. It is never combined with SEDM evidence or the
standalone ElCon simulation in one table or claim.

Research question: how should a workflow recover when a command may already have executed but
its outcome was not received?

Changes from 0.2:
- Added the completion bound and the visibility/completion time semantics (§2). An elapsed
  visibility bound alone no longer authorises REDISPATCH.
- Approved decisions 1–4 recorded.
- Metric metadata is checked by test.
- Development history recorded (§6).

## 1. Recovery observation

A policy is a pure function `next_action(obs: Observation, ev: Evidence) -> Action`. It never holds
the service, a client, the ledger, the database path, the fault schedule or the oracle. The harness
executes every action and records the evidence.

| Field | Content |
|---|---|
| `workflow_id`, `step_id` | identifiers of the interrupted step |
| `operation_id` | stable `{workflow_id}:{step_id}`; identical on every redispatch |
| `capability`, `adapter` | `create_maintenance_ticket`, `maintenance_effect_service` |
| `request` | `{machine_id}` as first dispatched; a redispatch reuses it unchanged (same fingerprint) |
| `dispatch.attempts`, `dispatch.last_dispatch_at` | orchestrator's durable journal (policy-side, not ground truth) |
| `ack.state` | `received` / `failure_received` / `conflict` / `missing` |
| `ack.status`, `ack.ticket_id` | only when a reply was delivered |
| `contract.deduplicates_by_operation_id` | `true` / `false` / `null` (missing) |
| `contract.binds_request_fingerprint` | `true`: a reused ID with different parameters is answered `conflict` |
| `contract.outcome_query` | `available` / `unavailable` / `null` |
| `contract.visibility_bound_s` | declared upper bound on query lag **after a commit**, or `null` |
| `contract.completion_bound_s` | declared upper bound from dispatch to terminal state (committed, or can no longer commit), or `null` |
| `contract.failure_response_scope` | `attempt`: a `failed` reply means terminal non-execution of *that attempt* |
| `approval` | `{required: false, status: "not_required"}` for this capability |
| `preconditions` | `{governance_revalidation: "available", equipment_state: "not_modelled"}` |
| `resume_at`, `horizon_end` | simulated times |

`Evidence` (harness-recorded): `governance` (REVALIDATE result, or none), `queries`
(`(status, ticket_id, query_time)` list), `now`.

**Never visible:** case ID, fault class, `FaultSpec`, true commit or visibility times, service
configuration beyond the declared contract, ledger, oracle row, expected decision, replay index,
number of concurrent resumers.

**Result certainty** (identical to the oracle's evidence predicates):

- **Confirmed committed:** a delivered `committed` or `deduplicated` reply, or a query `found`.
- **Confirmed not committed:** a `failed` reply when it was the only attempt. Or a query
  `not_found` at `query_time >= last_dispatch_at + completion_bound_s + visibility_bound_s`, with
  **both** bounds declared.
- **Unknown:** everything else: a missing reply; `not_found` before that deadline; `not_found`
  when either bound is undeclared; no outcome query.

The harness asserts before each trial that the declared contract is truthful:
- deduplication flag equal;
- every scheduled visibility delay `<=` the declared visibility bound;
- the declared completion bound `>= 0`, which is truthful because the simulator commits inside
  the dispatch transaction or never;
- no visibility bound without a query.

"Unverifiable" means the harness rejects QUERY.

## 2. Time semantics and fault model

| Term | Meaning |
|---|---|
| Commit time | when the external effect is committed (ledger row); hidden |
| Visibility time | when a query can first see a committed effect = commit time + lag; hidden |
| Terminal state | the dispatch has committed or can no longer commit |
| In-flight request | a dispatch not yet terminal; it may still commit, and no query can rule that out |
| Visibility bound | limits lag **after** a commit; says nothing about whether a request can still commit |
| Completion bound | limits time from dispatch to terminal state |

A declared visibility bound alone never proves that an earlier command cannot commit later.
`not_found` is authoritative absence only after `last_dispatch_at + completion_bound_s +
visibility_bound_s`, with both bounds declared.

**Implemented fault mechanism:** `FaultSpec(commit, ack_delivered, visibility_delay)`, consumed per
dispatch in order. Validated: bool flags, finite non-negative delay, no delay on a non-committing
fault.

- **F5v, implemented:** post-commit visibility lag. The effect is committed inside the dispatch
  and becomes queryable `visibility_delay` seconds later. The simulator's completion bound is
  therefore 0. Executed test: `test_dispatch_is_terminal_when_submit_returns`.
- **F5c, NOT implemented:** a late or in-flight commit after a read-back or redispatch. Every
  case declares `completion_bound_s = 0`, so the completion-bound rule is never the factor that
  separates safe from unsafe decisions in this matrix. Any statement about in-flight commits
  would be outside the evidence.

Time: initial dispatch 1000, resume 1010, horizon end 1070 (simulated seconds). One
`SimulatedClock` and one fresh database per trial, single OS process.

**Primary set: 13 cases × 4 policies = 52 trials**

| Case | Fault | IC | Dedup | Query / visibility bound / completion bound | Hidden effects at resume |
|---|---|---|---|---|---|
| C01 | F1 fail before commit, failure reply | IC1 | no | yes / 0 / 0 | 0 |
| C02 | F1 fail before commit, no reply | IC2 | no | yes / 0 / 0 | 0 |
| C03 | F2 commit, ack lost | IC2 | no | yes / 0 / 0 | 1, visible |
| C04 | F3 commit, ack lost, dedup | IC3 | yes | yes / 0 / 0 | 1, visible |
| C05 | F4 commit, ack lost, unverifiable | IC4 | no | no / – / 0 | 1 |
| C06 | F4-control: no commit, no reply, unverifiable | IC4 | no | no / – / 0 | 0 |
| C07 | F4+F3 unverifiable, dedup | IC5 | yes | no / – / 0 | 1 |
| C08a | F5v lag 5 s | IC6 | no | yes / 30 / 0 | 1, visible from 1005 |
| C08b | F5v lag 30 s | IC6 | no | yes / 30 / 0 | 1, visible from 1030 |
| C08c | F5v-control: no commit, no reply | IC6 | no | yes / 30 / 0 | 0 |
| C09 | F5v lag 30 s, visibility bound undeclared | IC7 | no | yes / none / 0 | 1, visible from 1030 |
| C10 | F5v+F3 lag 30 s, dedup | IC8 | yes | yes / 30 / 0 | 1, visible from 1030 |
| C11b | F6 duplicate resume, sequential | IC2 | no | yes / 0 / 0 | 0 |

**Concurrency stress set, reported separately and excluded from every primary denominator**

| Case | Fault | IC | Dedup | Why stress |
|---|---|---|---|---|
| C11a | F6 overlapping resumes | IC2 | no | no recovery-claim or lease mechanism exists; single-active-resumer is not enforced |
| C12 | F6+F3 overlapping resumes | IC3 | yes | same; safety relies only on service deduplication |

**Deferred, not implemented:**
- F5c late commit;
- F7 approval expiry/revocation;
- F8 equipment-state change;
- cross-process simulated time;
- operation-ID conflict cases (the service behaviour is tested but no case is defined).

## 3. Policies

All four face identical schedules, observations, horizon and step budget (20 non-terminal
actions; exceeding it is invalid). **Every contract field is available to every policy.** The
policies differ only in which rules they apply. None can read the ledger or the oracle.

```python
def B0(obs, ev):                     # blind re-dispatch
    return REDISPATCH

def B1(obs, ev):                     # governance/approval revalidation, then re-dispatch
    if ev.governance is None: return REVALIDATE
    return REDISPATCH if ev.governance == "ALLOW" else HOLD

def B2(obs, ev):                     # idempotency key + read-back; holds when uncertain
    if ev.governance is None: return REVALIDATE
    if ev.governance != "ALLOW": return HOLD
    if obs.ack.state == "conflict": return HOLD
    if obs.ack.state == "failure_received" and obs.dispatch.attempts == 1: return REDISPATCH
    if obs.contract.deduplicates_by_operation_id is True:
        return REDISPATCH            # same operation_id, identical parameters (same fingerprint)
    if obs.contract.outcome_query != "available": return HOLD
    if not ev.queries: return QUERY
    q = ev.queries[-1]
    return ADOPT(q.ticket_id) if q.status == "found" else REDISPATCH

def P(obs, ev):                      # capability-aware
    # identical to B2 up to and including the first query result ...
    if ev.governance is None: return REVALIDATE
    if ev.governance != "ALLOW": return HOLD
    if obs.ack.state == "conflict": return HOLD
    if obs.ack.state == "failure_received" and obs.dispatch.attempts == 1: return REDISPATCH
    if obs.contract.deduplicates_by_operation_id is True: return REDISPATCH
    if obs.contract.outcome_query != "available": return HOLD
    if not ev.queries: return QUERY
    q = ev.queries[-1]
    if q.status == "found": return ADOPT(q.ticket_id)  # positive evidence, any bound
    # ... the only difference: when is not_found authoritative?
    vb, cb = obs.contract.visibility_bound_s, obs.contract.completion_bound_s
    if vb is None or cb is None: return HOLD           # cannot rule out a later commit or a lagging view
    deadline = obs.dispatch.last_dispatch_at + cb + vb
    if q.query_time >= deadline: return REDISPATCH
    if ev.now < deadline <= obs.horizon_end: return WAIT_UNTIL(deadline)
    if ev.now >= deadline: return QUERY
    return HOLD
```

**Rules used by each policy** (all fields are visible to all)

| Rule input | B0 | B1 | B2 | P |
|---|---|---|---|---|
| governance revalidation | – | ✓ | ✓ | ✓ |
| `ack.state`, `dispatch.attempts` (attempt-scoped failure, conflict) | – | – | ✓ | ✓ |
| `deduplicates_by_operation_id` (retry with same ID and fingerprint) | – | – | ✓ | ✓ |
| `outcome_query` + query results (adopt on found, hold if no query) | – | – | ✓ | ✓ |
| `visibility_bound_s`, `completion_bound_s`, `last_dispatch_at`, `now` | – | – | – | ✓ |

**Exact B2 vs P distinction.** B2 and P share every rule up to and including the first query
result. They differ in one rule only: how a `not_found` is interpreted.
- B2 treats any `not_found` as absence and redispatches.
- P treats `not_found` as absence only after `last_dispatch_at + completion_bound_s +
  visibility_bound_s`, with both bounds declared. Before that deadline it waits, if the deadline
  is within the horizon. If either bound is undeclared, it holds.

P's improvement over B2, if observed, comes solely from using a declared visibility (and
completion) bound. Bounded waiting on a known bound is ordinary engineering practice, not a new
algorithm. The contribution is limited to evaluating this capability-specific decision framework
and its observed trade-offs. A B2 variant that also used the bounds would be P.

Expected behaviour in the three discriminating cases (inferred from the definitions; not results):

| Case | B2 | P | Effect-level difference |
|---|---|---|---|
| C08b | QUERY at 1010 → `not_found` → REDISPATCH (invalid) | QUERY → WAIT_UNTIL 1030 → QUERY → `found` → ADOPT (valid) | B2 two effects, P one; P waits 20 s |
| C08c | QUERY at 1010 → `not_found` → REDISPATCH (invalid: lucky) | QUERY → WAIT_UNTIL 1030 → QUERY → `not_found` (authoritative) → REDISPATCH (valid) | none: both one effect. Decision validity and 20 s wait differ |
| C09 | QUERY → `not_found` → REDISPATCH (invalid) | QUERY → `not_found` → HOLD (valid) | B2 two effects and completes; P one effect and does not complete |

**Expected equivalence (inferred):** B2 and P are expected to be identical in the other 10
primary cases: C01–C07, C08a, C10, C11b. B0 and B1 are expected to be indistinguishable in F1–F6;
B1's value needs F7/F8. Equivalence is reported where observed. B0 is never described as
LangGraph's default unless driven through LangGraph replay and measured.

## 4. Independent decision oracle

- **Decision:** a terminal action, evaluated against evidence predicates computed by the harness
  at decision time. A policy's own explanation is never used.
- **Validity rule:** valid iff some `valid_actions` entry has the same action and a true
  predicate. Everything else is invalid; an unnecessary HOLD is invalid.
- **Rules R1–R9** are in `oracle_table.json`. The core rules:
  - **R7, information-only:** valid actions are a function of the information class
    (observation + declared contract) and evidence. All cases in one class have identical valid
    actions. Hidden state only decides which evidence a query can return.
  - **R2, corrected:** an elapsed visibility bound alone is not authoritative absence.
  - **R1:** a positively confirmed effect may be adopted even with no bound declared.
- **Executed checks** (`tests/test_elcon_protocol_oracle.py`):
  - valid sets are rebuilt from visible fields only;
  - a class whose members' observations, contracts or valid sets differ is rejected;
  - eligibility is derived from hidden state;
  - contracts are truthful;
  - C05/C06 are confirmed indistinguishable;
  - stress cases are excluded from denominators;
  - metric metadata is checked;
  - deferred faults are not presented as cases;
  - every contract declares every field;
  - each schedule has exactly one fault, consumed by the initial dispatch;
  - each case's hidden state (effects, ack, visibility time) is **executed on the service and read
    from `EffectLedger`**.
  - Mutation checks confirmed these tests catch: a C06 lucky-redispatch reward, a dropped
    completion bound, stress cases counted as primary, the Unauthorized Effect Rate reported as
    0%, and replays treated as samples.
- **Precondition, single active resumer:** assumed, NOT enforced. No recovery-claim or in-flight
  lease exists. For C11a and C12 we report:
  - the observed committed-effect count;
  - per-decision validity;
  - the required safety property (≤ 1 effect) and whether the design guarantees it (C11a: no;
    C12: only via service deduplication).

  A duplicate in C11a is a documented limitation, not an expected or correct outcome.

**C05 vs C06: safety versus completion.** Both have the identical observation IC4 (no reply, no
deduplication, no query). Any rule maps both to the same action.
- REDISPATCH completes C06 but duplicates C05.
- HOLD is safe in both but forgoes C06's completion.
- The oracle judges from the available information, so HOLD is correct in both.
- C06's HOLD is `information_forced`: it is excluded from the Unnecessary Hold denominator, and
  the forgone completion is reported as the cost of safety.
- A redispatch in C06 is invalid even though it produces exactly one effect.

**Decision correctness vs committed effects.** Decision validity comes from the oracle, and
committed effects from the ledger. They are reported side by side and neither is inferred from
the other. C08c shows they can diverge: B2's decision is invalid there, yet its effect count is
correct.

## 5. Metrics and eligibility

Unit of analysis: **operation trial** = (primary case, policy); N = 52 (13 per policy). Stress
trials (8) are reported separately and never enter a primary denominator. Rates are n/N per
policy, with the eligibility set. Denominators below are stored in `oracle_table.json`
(`denominators`, `metrics`) and checked by test against the per-case eligibility flags.

| Case | Hindsight recoverable | Safely recoverable (info) | HOLD valid | Hold class | Unnecessary-hold eligible |
|---|---|---|---|---|---|
| C01 | ✓ | ✓ | – | unnecessary | ✓ |
| C02 | ✓ | ✓ | – | unnecessary | ✓ |
| C03 | ✓ | ✓ | – | unnecessary | ✓ |
| C04 | ✓ | ✓ | – | unnecessary | ✓ |
| C05 | – | – | ✓ | required | – |
| C06 | ✓ | – | ✓ | information_forced | – |
| C07 | ✓ | ✓ | – | unnecessary | ✓ |
| C08a | ✓ | ✓ | – | unnecessary | ✓ |
| C08b | ✓ | ✓ | – | unnecessary | ✓ |
| C08c | ✓ | ✓ | – | unnecessary | ✓ |
| C09 | ✓ | ✓ | ✓ | acceptable | – |
| C10 | ✓ | ✓ | – | unnecessary | ✓ |
| C11b | ✓ | ✓ | – | unnecessary | ✓ |
| **count** | **12** | **11** | **3** | | **10** |

Definitions:
- **Hindsight recoverable:** with knowledge of hidden state, some interface action ends with
  exactly one effect and the ticket recorded. C05 is not: redispatch duplicates, and the ticket
  ID cannot be learnt without a query.
- **Safely recoverable:** some valid non-HOLD action has evidence obtainable within the horizon
  in this hidden state.
- **HOLD required:** HOLD is the only valid action (C05, C06).

| Metric | Numerator | Eligibility | Per policy / total |
|---|---|---|---|
| Duplicate Effect Rate | ledger `committed_effect_count > 1` | all primary | 13 / 52 |
| Correct Recovery Decision Rate | every terminal decision valid | all primary | 13 / 52 |
| Recovery Completion Rate | `committed_effect_count == 1` and every resumer recorded that ticket | safely recoverable | 11 / 44 |
| Hindsight Completion Rate (secondary) | same | hindsight recoverable | 12 / 48 |
| Unnecessary Hold Rate | any HOLD | HOLD invalid | 10 / 40 |
| Required-Hold Compliance | HOLD | HOLD required (C05, C06) | 2 / 8 |
| Information-forced holds (cost of safety) | HOLD | information_forced (C06) | 1 / 4 |
| Unauthorized Effect Rate | — | 0 eligible trials | **not evaluated** (requires F7); never reported as 0% |
| Dispatch count | ledger `dispatch_count`, total and recovery-only (total − 1) | per trial | — |
| Committed-effect count | ledger `committed_effect_count` | per trial | — |
| Recovery decision latency | wall-clock `perf_counter_ns` inside `next_action`, summed per trial; excludes harness I/O and simulated waits | per trial, descriptive | — |
| Simulated wait | simulated seconds advanced by WAIT_UNTIL | per trial, separate from latency | — |

Notes:
- Completion is not required where HOLD is valid. C09 is in the completion denominator, and a
  valid HOLD there lowers completion; this is reported as a trade-off, not an error.
- **Repetitions:** each trial is executed k = 5 times (260 executions). These are deterministic
  replays used as a reproducibility check (outcome rows must hash identically). They are not
  independent samples and do not raise N. No confidence intervals or significance tests.

## 6. Reproducibility and development history

- **Anchor:** the local commit on `research/elcon2027-recovery` that first contains this file at
  version 1.0 (parent `a0fe2f612c4814a6b6b1891ec5cd84cb8c89c26a`). `SHA256SUMS` covers the protocol
  files; `README.md` lists the code hashes.
- **Planned outputs, only under `research/elcon2027/results/<run_id>/`:**
  - `run_metadata.json`: anchor SHA, protocol version, SHA-256 of `oracle_table.json` and
    `SHA256SUMS`, command, UTC timestamp, Python/SQLite versions, k;
  - `trials.csv`: per trial and per resume decision, including the evidence predicates true at
    decision time;
  - `determinism.json`.
- **Exploratory analysis during protocol development (2026-11-09).** Disclosed; none was saved
  to the repository, and none counts as a result.
  1. Scratch probes of the effect service: reused operation IDs, per-process clocks, a fault
     after commit, file locations. These motivated S1, S2 and S6.
  2. Mutation runs against the oracle consistency tests.
  3. A hand trace of the B0/B1/B2/P pseudocode over the v0.2 matrix.
  4. One scratch simulation of the v0.2 pseudocode against the service, run to check that the
     definitions and oracle agree. It matched the hand trace.
  5. Two `/code-review` passes over the service and tests. The second led to the
     initialisation guards, the oracle ack-state fix and the ledger-executed hidden-state check
     (`service_review.md`).

  The v1.0 completion-bound correction changes no decision in the matrix, because every case
  declares `completion_bound_s = 0`. No harness, policy module, runner or results directory
  exists at freeze. Final policy-comparison results have not been generated.

## 7. Freeze record

| Condition | Status |
|---|---|
| Blocking service issues S1, S2, S6, S8, S9, S10 resolved with regression tests | met: executed tests |
| Simulator completion bound (no late commit) tested | met: `test_dispatch_is_terminal_when_submit_returns` |
| Acceptance tests and full suite pass; ruff clean | met at freeze |
| Oracle internally consistent; C05/C06 indistinguishable; stress excluded; denominators from metadata | met: `tests/test_elcon_protocol_oracle.py` |
| Policy definitions consistent with oracle | hand trace and one exploratory scratch run (§6). Executable check comes with the policy implementation |
| Scope matches implemented functionality | met: F5v only; F5c, F7, F8 deferred and labelled |
| Reviewer decisions 1–4 | approved 2026-11-09 |

## 8. Limitations and claims

- F5v only. Late or in-flight commits (F5c) are not modelled, so the completion-bound rule is
  specified and tested in the oracle but never decisive in the matrix.
- Single-active-resumer is assumed, not enforced (C11a/C12 stress).
- C11b's second resumer computes authority from a stale `last_dispatch_at`. This is safe only
  because both bounds are 0 there.
- No F7, F8, or cross-process simulated time. The Unauthorized Effect Rate cannot be evaluated.
- The request fingerprint covers `capability` and `machine_id` only, the service's only
  parameters.
- `MaintenanceClient` still holds the service object (S4). Isolation relies on the `next_action`
  interface and a harness test.
- One fault queue per database (S7), so each trial needs its own database.
- Read-only ledger behaviour after a crash (S11) is inferred, not tested.
- **Claims are limited to:** which recovery decisions keep at most one committed effect per
  operation ID in this simulator under F5v, at what completion and wait cost, and whether
  declared contract fields change decisions relative to B2.
- **Not claimed:** exactly-once, certified or industrial safety, live PLC/OPC UA, production
  readiness, pipeline integration, LangGraph default behaviour, or a new general-purpose waiting
  algorithm.
