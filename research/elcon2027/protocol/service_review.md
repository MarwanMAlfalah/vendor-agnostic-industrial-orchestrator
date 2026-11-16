# Effect service review — 2026-11-09

Scope: `app/integration/maintenance_effect_service.py` (sha256 `bd72e311…cd4c`) and
`tests/test_maintenance_effect_service.py` (sha256 `61ce16b2…d0c6`), both untracked at HEAD
`a0fe2f6`. Labels: confirmed from code | executed test | executed probe | inferred.

## Acceptance requirements (audit Section I)

| # | Requirement | Covered by | Source lines | Status |
|---|---|---|---|---|
| 1 | Two requests without dedup → two effects | `test_redispatch_without_deduplication_commits_duplicate_effect` (test L100) | insert with `dedup_key=NULL` never conflicts, L194–205 | executed test |
| 2 | Same operation ID with service dedup → one effect | `test_redispatch_with_deduplication_commits_once` (L116); `test_deduplication_is_atomic_under_concurrent_submits` (L130), 8 writers | `BEGIN IMMEDIATE` L186; `ON CONFLICT(dedup_key) DO NOTHING` L197; UNIQUE `dedup_key` in schema L62 | executed test |
| 3 | Lost ack after commit → one effect | `test_commit_with_lost_ack_raises_but_effect_is_committed` (L84) | commit before ack decision L226 then raise L230–231 | executed test |
| 4 | Failure before commit → zero effects | `test_failure_before_commit_leaves_ledger_empty` (L68) | `outcome = "failed"` with no insert, L191–192 | executed test |
| 5 | Delayed visibility → `not_found` although committed | `test_delayed_visibility_query_cannot_rule_out_commit` (L161, ×2); `test_not_found_is_identical_for_uncommitted_and_invisible_commit` (L184) | `visible_at = now + delay` L202; query filter `visible_at <= now` L250 | executed test |
| 6 | Separate OS process reads persisted ledger | `test_ledger_and_fault_schedule_persist_across_processes` (L221) | file-backed DB, one connection per call L124–127; fault queue in table L48–54 | executed test |
| 7 | Service-created files stay inside the temp directory | **no test** | `mkdir(parents=True)` on the given path only, L144 | executed probe only (S10) |

Probe for #7: the test file was run with `--basetemp` in the session scratchpad. `find -newer`
over the repository (excluding `.git` and `.venv`) found no new or modified file, and every
service-created file was an `effects.db` under the basetemp. Rollback-journal files are transient.

## Findings

| ID | Severity | Finding | Evidence | Recommended correction |
|---|---|---|---|---|
| S1 | must-fix before runs | Dedup on + `commit=False` fault on an already-committed operation returns `failed`, ticket `None`, while the ledger holds 1 effect | executed probe P3; code L191 | Apply the dedup lookup before the commit fault (a real idempotent service answers from its key store), or forbid that schedule in the harness |
| S2 | must-fix before pipeline integration | `operation_id` reuse with different parameters is silently conflated: under dedup, `op-1/M2` returns `deduplicated` with ticket `MT-M1-000001`; without dedup, the M2 effect is counted as a duplicate of op-1 | executed probe P1 | Request fingerprint per dispatch/effect; mismatch under dedup → status `conflict`, no commit; without dedup, the ledger flags fingerprint mismatch |
| S3 | modelling decision (document) | A `deduplicated` reply returns the ticket while the query still says `not_found` | confirmed from code L214–220 | Keep; state it: dedup store strongly consistent, query index eventually consistent |
| S4 | risk | `MaintenanceClient` holds the full service (`_service`); separation is by convention only | confirmed from code L262 | Protocol: policies get no client at all, only `Observation` + evidence; the harness executes actions |
| S5 | minor | Clock read before `BEGIN IMMEDIATE`; under contention timestamps may precede lock acquisition | confirmed from code L184–186 | Read the clock after `BEGIN IMMEDIATE` (irrelevant with the single-process fake clock) |
| S6 | must-fix before cross-process trials | Visibility depends on each process's own clock: the same committed effect is `not_found` at fake t=1010 and `found` under `time.time` | executed probe P2 | Store simulated time in the database (`advance_clock`), or keep trials single-process |
| S7 | risk | One global FIFO fault queue; with interleaved operations, fault assignment depends on scheduling | confirmed from code L235–244 | One database per trial (protocol); later key faults by `(operation_id, attempt)` |
| S8 | minor | `FaultSpec` accepts NaN/inf delays and non-bool flags | confirmed from code L102–104 | `math.isfinite` and `isinstance(..., bool)` checks |
| S9 | test hygiene | Concurrency test has no barrier timeout or exception propagation; `pid_a != pid_b != parent` never compares `pid_a` with the parent; read-only test leaks a connection | confirmed from code, test L141, L254, L288 | Barrier timeout and exception collection; explicit inequalities; `closing(...)` |
| S10 | must-fix before runs | Acceptance requirement 7 has no automated test | see table above | Add a test that lists files under `tmp_path` and asserts nothing else was created |
| S11 | inferred | After a writer crash leaves a hot journal, a `mode=ro` ledger connection cannot roll it back and may fail | inferred (not executed) | Oracle reads only after a read-write service instance has reopened the DB; add a test if crash trials are added |

No finding blocks writing the protocol. The matrix avoids S1, S2, S6 and S7 by construction
(single process, one database and one operation per trial, `commit=False` only on the first
dispatch), and S4 is removed by the policy interface. S1, S9 and S10 must be resolved before
results are generated (protocol §7).

## Resolution (2026-11-09, protocol v0.2)

The line references above describe the reviewed v1 file. Corrections were made by TDD: each red
run failed for the expected reason before implementation.

| ID | Resolution | Regression tests (executed) |
|---|---|---|
| S1 | Responses are attempt-scoped and documented as such. In one `BEGIN IMMEDIATE` transaction, the order is: consume fault → fingerprint binding → existing-effect lookup (dedup only) → commit fault. An already committed operation is answered `deduplicated` even under a `commit=False` fault. | `test_dedup_retry_with_fail_before_commit_fault_reports_existing_effect`, `test_non_dedup_failed_retry_reports_the_attempt_only` |
| S2 | `request_fingerprint(capability, parameters)` = SHA-256 of canonical JSON (sorted keys, compact separators, UTF-8). The first dispatch binds `operation_id` → fingerprint (table `operations`), even if it failed. A mismatch returns `conflict` and commits nothing, in both configurations. Fingerprints are stored on dispatches and effects. Schema version 2 is checked on reopen. | `test_request_fingerprint_is_canonical_sha256`, `test_identical_request_is_not_a_conflict[×2]`, `test_conflicting_request_is_rejected_without_effect[×2]`, `test_operation_binding_is_set_by_first_dispatch_even_if_it_failed[×2]` |
| S5 | The clock is now read under the write lock (side effect of S6). | covered by the S6 tests |
| S6 | `SimulatedClock` (explicit, finite, non-negative advance) is required; wall clocks are rejected, so simulated and real time never mix. `ClockRegression` is raised when a caller's clock is behind time already recorded in the database. Cross-process simulated time is excluded from claims; the cross-process test claims ledger and fault-queue persistence only. | `test_simulated_clock_rejects_invalid_advance[×3]`, `test_simulated_clock_rejects_invalid_start[×4]`, `test_service_rejects_non_simulated_clock[×3]`, `test_clock_behind_recorded_time_is_rejected` |
| S8 | `FaultSpec` requires bool flags and a finite, non-negative real delay (bool rejected), and rejects a delay on a non-committing fault. | `test_invalid_fault_spec_is_rejected[×9]` |
| S9 | Barrier timeout, abort and exception collection; thread join timeout; PID compared only with the parent; read-only test closes its connection. | modified tests (concurrency, cross-process, read-only) |
| S10 | Automated: after service use with a relative-path working directory inside `tmp_path`, `tmp_path` contains only `svc/effects.db` and the repository file set is unchanged. | `test_service_files_stay_inside_temporary_directory` |
| S3 | Kept as a modelling decision (strongly consistent dedup store, lagging query index); documented in protocol C10. | — |
| S4, S7, S11 | Not changed. Mitigated by the protocol (no client in policies; one database per trial; no crash trials). Listed in protocol §8. | — |

## Freeze review (2026-11-09, protocol v1.0)

Second `/code-review` pass over the corrected service and both test files. Triage:

| Finding | Action | Tests (executed) |
|---|---|---|
| Constructor stamped schema v2 into any existing SQLite file (old-schema or unrelated database accepted) | Fixed: a non-empty database must already contain `service_config` with the current `schema_version`, otherwise `ValueError`. All initialisation happens in one transaction, so a rejected file is left untouched. | `test_unrelated_existing_database_is_rejected_untouched`, `test_database_without_schema_version_is_rejected` |
| `deduplicate` not type-checked | Fixed: must be `bool` | `test_deduplicate_must_be_bool[×4]` |
| Oracle test labelled a commit-and-ack reply as a failure reply | Fixed: `received` / `failure_received` / `missing` derived from both flags | `test_fault_schedules_are_implemented_and_contracts_truthful` |
| Oracle hidden state not executed against the service | Fixed: each case's schedule is run and checked against `EffectLedger` and query visibility | `test_hidden_state_matches_the_service_ledger` |
| Files-stay-inside test compared names only | Fixed: compares size and mtime, so in-place rewrites are detected. Data/docs content is still covered by the SHA-256 evidence guard. | `test_service_files_stay_inside_temporary_directory` |
| Subprocess failure lost the child's traceback | Fixed: stderr asserted on non-zero exit | cross-process test |
| Global FIFO fault queue (S7) | Guarded: every matrix schedule has exactly one entry, consumed by the initial dispatch | `test_each_schedule_has_one_fault_for_the_initial_dispatch` |
| R5 not modelled in the oracle test | Guarded: the matrix must declare every contract field | `test_every_contract_declares_every_field` |
| ClockRegression ignores query times | Documented in `SimulatedClock`: one shared clock per trial is required, not merely checked | — |
| Deduplicated reply reveals the ticket before query visibility (S3) | Unchanged modelling decision (protocol C10) | — |

Simulator completion bound: `test_dispatch_is_terminal_when_submit_returns[×5]`, a characterisation
test (it passed without code change). A dispatch commits inside `submit()` or never; later time
changes visibility only.
