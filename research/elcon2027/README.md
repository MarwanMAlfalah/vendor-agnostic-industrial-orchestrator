# ElCon-EE 2027 recovery study

**Question:** how should a checkpointed workflow recover when a command to an external service may
already have taken effect but its outcome was not received?

The study adds contract-based recovery rules to the orchestration prototype as opt-in modules.
- **Evidence label:** in-repository, service-level deterministic simulation.
- **Not part of this study:** the governance-aware evaluation in `data/results/` and `docs/` (240- and 500-scenario profiles). Its counts, baselines and metrics must not be combined with the counts here.

## Two parts, kept separate

| | Original study | In-flight extension x1.0 |
|---|---|---|
| Protocol | `protocol/` (v1.0: `protocol.md`, `oracle_table.json`, `service_review.md`, `README.md`, `SHA256SUMS`) | `extension_v1/protocol/` (`protocol.md`, `cases.json`, `FREEZE_MANIFEST.txt`) |
| Code | `app/integration/maintenance_effect_service.py`, `maintenance_effect_adapter.py`, `recovery_guard.py`, `recovery_journal.py`, `recovery_policies.py`, `recovery_experiment.py`; opt-in step identity in `app/agents/execution_agent.py` | `app/integration/inflight/` (reuses the original modules listed in `FREEZE_MANIFEST.txt`) |
| Tests | `tests/test_elcon_*.py`, `tests/test_maintenance_effect_service.py` | `tests/test_ext_*.py` |
| Formal run | `results/20261110T132939Z-fb77698/` (authoritative; two earlier runs kept as superseded, see `results/README.md`) | `extension_v1/results/20261112T114244Z-x1.0/` |
| Size | (13 primary cases + 2 stress cases) × 4 policies × 5 repetitions = **300 executions**; separately, a LangGraph pipeline cross-check of **18 runs** (6 cases × 3 policies) | **720 service-level executions** (24 cases × 6 policies × 5 repetitions) and, separately, **100 graph runs** (4 replay cases × 5 modes × 5 repetitions) |
| Independent verifier | `submission_v2/release_candidate/verification/verify_results.py` | `extension_v1/verification/verify_extension.py` |

**Notes on the folders:**
- **Original verifier path:** the verifier sits under `submission_v2/release_candidate/` because the run index cites that path. No manuscript files are published there.
- **Extension notes:** `extension_v1/README.md` and `DEVELOPMENT_LOG.md` are kept byte-for-byte as written on 2026-11-12. They describe the files as "untracked" because they were when written. They also mention a baseline manifest and an evidence outline that are not published; neither is needed to verify the results.

**Provenance:** this study was added to the public history as a later publication snapshot. The
local commits that froze the protocol (`33ea97c`) and produced the original runs (`fb77698`) are
not in this history. [`PUBLICATION_PROVENANCE.md`](PUBLICATION_PROVENANCE.md) lists every
transferred file with its SHA-256 and states which checks need those commits.

## Check labels used below
- **[executed 2026-11-15]:** run on this publication snapshot before it was committed, in a fresh virtual environment built with `constraints-recorded-20261111.txt`, on macOS arm64 with Python 3.11.0.
- **[historical]:** recorded earlier by the authors and not rerun for publication.
- **[untested]:** not run for publication.

## Verify the published records (no simulation is rerun)

Run from the repository root. The verifiers need Python 3 and the standard library only.

```sh
# Frozen-file checksums                                                [executed 2026-11-15]
(cd research/elcon2027/protocol && shasum -a 256 -c SHA256SUMS)              # 4 x OK
grep -v '^#' research/elcon2027/extension_v1/protocol/FREEZE_MANIFEST.txt \
  | shasum -a 256 -c -                                                       # 27 x OK

# Original study: recompute every reported number from raw records + oracle   [executed 2026-11-15]
python3 research/elcon2027/submission_v2/release_candidate/verification/verify_results.py \
  --run research/elcon2027/results/20261110T132939Z-fb77698 \
  --oracle research/elcon2027/protocol/oracle_table.json                     # exit 0, "problems": []

# Extension: recompute assessment and summary from raw event logs and ledgers [executed 2026-11-15]
python3 research/elcon2027/extension_v1/verification/verify_extension.py \
  research/elcon2027/extension_v1/results/20261112T114244Z-x1.0 \
  research/elcon2027/extension_v1/protocol                                   # exit 0, ALL CHECKS PASSED
```

**E16.** E16 remained pending at the assessment horizon and is censored. The verifier’s historical E01–E16 message reports no observed duplicate within that horizon; it does not establish eventual duplicate freedom for E16. The assessable compliant-case result is therefore 15 cases.

**Run manifests** [executed 2026-11-15]: 86 of the 88 SHA-256 values recorded in the run manifests
match the published files. The other 2 belong to the superseded first run: they record
uncommitted versions of two files that differ from the versions in `fb77698`. The exact source versions corresponding to these two hashes were not recovered from the inspected checkout or Git history.
The two mismatches are kept visible and explained in `PUBLICATION_PROVENANCE.md`.

**What "independent" means:**
- The two verifiers were written separately from the policies and runners, and recompute everything from the stored records.
- They share the simulator's event model and the protocol's definitions. They therefore check consistency with the specification, not against an independent model of a real provider.

## Unit tests

```sh
python3.11 -m venv .venv
.venv/bin/pip install -c research/elcon2027/constraints-recorded-20261111.txt -e ".[dev]"
LANGSMITH_TRACING=false .venv/bin/python -m pytest -p no:cacheprovider -q
.venv/bin/python -m ruff check app tests --no-cache
```

**Results:**
- [executed 2026-11-15]: 246 passed; ruff reported no issues.
- [historical]: 194 passed at `fb77698` (2026-11-11); 224 passed with the extension (2026-11-12).

**About the tests:**
- Several tests run the recovery simulation on small inputs in temporary directories. They exercise the code; they are not a new formal experimental run, and they write nothing into `research/`.
- Two tests call `git` and need a Git checkout.
- The constraints file repeats the versions recorded on 2026-11-11. The dependency ranges in `pyproject.toml` are unchanged.

## Rerunning the simulations [untested for publication]

**Before rerunning:**
- Always pass output directories outside the repository; the original runner's default output is `research/elcon2027/results/`.
- Never overwrite the published runs.
- Outputs are expected to be deterministic apart from timestamps, wall-clock fields and Git state. Compare them with the published runs.

**Commands:**
- **Original study:** `app.integration.recovery_experiment.run_experiment(run_id=..., results_root=<dir>, scratch_root=<dir>)`.
  - It checks the frozen protocol by SHA-256.
  - In this public history it records `anchor_is_ancestor_or_head: false`, because commit `33ea97c` is not in this history. The value is recorded, not enforced. [executed 2026-11-15: `code_revision()` returns `false`.]
- **Extension:** `python -m app.integration.inflight.experiment --run-id <id> --results-root <dir> --scratch-root <tmp>`.
  - It refuses to run if any file in `FREEZE_MANIFEST.txt` has changed.

## Limitations

- **Simulation only:**
  - authored cases;
  - one simulated maintenance capability;
  - no language-model inference;
  - no PLC, OPC UA, equipment or production service.
- **Contract assumptions:** the bound-aware policies trust the provider's declared completion and visibility bounds; when the bounds are false, every policy duplicates the effect.
- **Eligibility, not authorization:** eligibility changes are injected by marking the capability unavailable in the registry. Approval expiry and real authorization revocation are neither implemented nor tested.
- **Repetitions are not samples:** deterministic repetitions check repeatability.
- **Freeze timing:** the protocol freezes were local and timestamped by the authors. They are not external preregistrations.
- **No general claims:** no general exactly-once claim and no industrial-safety claim.
