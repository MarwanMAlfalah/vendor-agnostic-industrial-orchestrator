# ElCon-EE 2027 extension protocol x1.0 (separate from the frozen study protocol v1.0)

This protocol defines an **extension** of the original study (protocol v1.0, frozen at `33ea97c`;
authoritative run `20261110T132939Z-fb77698`). It does not change the original cases C01–C12,
policies, oracle, denominators or results. Case matrix: `cases.json` (same folder).

**Development history (disclosed):** the simulator, runner and matrix were developed on
2026-11-12. Unit tests and two pilot runs (all cases, one replay, output kept outside the results
folder) were used to check the simulator semantics before the freeze. Formal runs start only
after the freeze manifest is written. This is a local timestamped freeze, not an external
preregistration.

## 1. Research questions
- **RQ1:** how do the recovery policies behave when the original operation can commit **after
  recovery begins** (genuine in-flight commit, Δ > 0)?
- **RQ2:** what changes when the authorization or a simulated process precondition changes
  between the initial dispatch and recovery?
- **RQ3:** does whole-node replay of a two-step workflow repeat an already completed external
  operation?

## 2. Policies
- **Original policies:** B0, B1, B2 and P are the original functions, imported unchanged.
- **Added: R_LI.** A transparent single-operation reference for Li's bounded-wait principle: wait
  until t_d + Δ + λ, query once, adopt if found, otherwise re-dispatch. It holds if a bound is
  undeclared or lies beyond the horizon. It shares B2/P's governance, conflict, failure-reply and
  deduplication rules so that every policy receives the same inputs. It is not a reproduction of
  Li's benchmark.
- **Added: P_A.** Equal to P except under a non-ALLOW revalidation: it may query and adopt an
  already visible effect, otherwise it holds. It never dispatches under non-ALLOW.
- **Comparison:** all policies run on every case, with the same observation, contract and
  revalidation.

## 3. Simulator semantics (`app/integration/inflight/service.py`)
**Events:** acceptance (at submit), commit (accepted_at + commit_after, or never), visibility
(committed_at + visibility_after), acknowledgment (delivered or lost), abort (accepted_at +
abort_after for a request that never commits).

**Bounds:**
- Δ (completion bound) bounds commit_at − accepted_at.
- λ (visibility bound) bounds visible_at − committed_at.
- Both are inclusive.
- A compliant contract satisfies both bounds for the first dispatch; a violated contract does not.

**Time:** whole simulated seconds held in floats, shared by all components of an execution.
Boundary offsets are ±1 s, so no fractional comparison occurs.

**Ordering:**
- Before any submit, query or drain at time t, all events scheduled at or before t are applied,
  ordered by (time, priority, sequence) with commit/abort before visible.
- A query at t therefore observes events scheduled at t.
- Queries never cause commits.
- A re-dispatch never cancels or alters a pending request.

**Re-dispatches** use the default fault: immediate commit, acknowledgment delivered.

**Deduplication:** a submit for an operation ID with a pending or committed request is answered
`deduplicated` with that ticket, and no new request is accepted. Under deduplication an accepted
request always commits; "accepted but never commits" cases therefore run without deduplication.

**Provider authorization (`auth_check`):**
- `none`: the provider never checks.
- `acceptance`: a request arriving while invalid is rejected with a delivered `failed` reply.
- `commit`: additionally, a pending request due while invalid is aborted.
- In every mode, a recovery-time HOLD or BLOCK does not cancel an accepted request.

**Assessment horizon:** after the terminal decision is executed, every event scheduled up to
t = 1600 s is applied. A request still pending then is **censored**, and duplicate freedom is
not established for that execution.

## 4. Observable information
Policies receive only what the original guard builds:
- the journal (number of attempts, last dispatch time, acknowledgment state);
- the declared contract;
- query replies;
- the GovernanceAgent revalidation decision.

They never see the fault schedule, future events, the authorization timeline, the ledger, the
case ID or expected answers.

## 5. Governance change (RQ2)
- **Timing:** at t = 1005 s (after the dispatch at 1000 s, before the recovery at 1010 s) the
  simulated precondition/authorization state becomes invalid.
- **Revalidation:** runs the real CapabilityMatchingAgent and GovernanceAgent on the harness plan,
  with one substituted input: a registry snapshot in which
  `create_maintenance_ticket.availability` equals that state. GovernanceAgent then returns
  SAFE_ABORT (`capability_unavailable`).
- **What the model does not cover:** the transition is injected by the harness, so it is a model
  of authorization revocation or precondition loss, not an approval-expiry mechanism (which the
  prototype does not implement).
- **Permissions reported separately:**
  1. a new request after invalidation (dispatch while invalid);
  2. commit of a previously accepted request while invalid (provider contract);
  3. evidence that an effect occurred (query `found`);
  4. adoption of an observed result (P_A only).

## 6. Metrics (independent assessor, `app/integration/inflight/assessor.py`)
**Per execution:**
- effects at decision and eventual effects;
- duplicate (eventual effects > 1) and late duplicate (absent at decision);
- censored;
- workflow outcome: completed, held, or not completed;
- completed with a single effect, where the recorded ticket must be that effect;
- missing effect;
- adoption consistency;
- dispatches, queries and simulated waiting;
- dispatches while invalid, effects while invalid, and commits after a hold.

**Aggregation:** counts over eligible executions, per policy and per set:
- the compliant set E01–E16;
- the violation stress set V01–V02;
- the governance set G01–G06;
- the replay set R01–R04, per step.

Sets are never pooled. Censored executions are excluded from duplicate-freedom counts and
reported separately.

## 7. Expected properties (stated before the formal run)
1. **B2 in Δ > 0 cases:** where the first query precedes the commit (E02, E03, E05, E06, E08,
   E11, E13), B2 produces a duplicate; in E02–E06, E11 and E13 it is a late duplicate.
2. **P and R_LI, compliant cases:** no duplicates where both bounds are declared and lie within
   the horizon. They hold where Δ is undeclared (E11, E12, E16) or beyond the horizon (E13); in
   those holds a pending request can still commit after the hold.
3. **Deduplication cases (E14, E15):** every policy commits one effect.
4. **Violation cases (V01, V02):** P and R_LI can duplicate. This shows dependence on truthful
   contracts.
5. **G cases:** policies that revalidate (B1, B2, P, R_LI) hold under SAFE_ABORT. B0
   re-dispatches while invalid. P_A adopts only when the effect is already visible (G01, G06).
   Pending requests commit after a hold unless the provider checks at commit (G03).
6. **R cases:** unprotected replay repeats s1 without deduplication. The guard adopts s1 from its
   acknowledged reply. The s2 result follows the single-operation behaviour.

## 8. Reporting and exclusion
- **Replays:** each execution is repeated 5 times with fresh databases. Replays establish
  determinism only.
- **Exclusions:** none planned. An execution that raises is recorded as an error.
- **Bug found in a formal run:** the failed run is retained, the defect is documented, the code
  or protocol is versioned, and the complete matrix is rerun.
- **Regression check:** the original single-resumer primary cases are re-run on the extension
  simulator and labelled as a regression check, not as evidence of the original study.
