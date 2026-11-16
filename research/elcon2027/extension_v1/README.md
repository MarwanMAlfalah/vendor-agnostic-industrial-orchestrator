# ElCon-EE 2027 extension x1.0: in-flight commits, changing governance, two-step replay

This is a separate extension of the original frozen study, which stays unchanged:
- protocol v1.0 at `33ea97c`;
- code `fb77698`;
- run `20261110T132939Z-fb77698`.

New case IDs (E, V, G, R) and a separate protocol are used. Nothing here is committed to git.

| Path | Content |
|---|---|
| `baseline_manifest.txt` | SHA-256 of the original evidence, manuscripts v2–v5, packages, `app/` and `tests/` before any extension work |
| `protocol/protocol.md`, `protocol/cases.json` | Extension protocol x1.0 and case matrix (24 service-level cases, 4 replay cases) |
| `protocol/FREEZE_MANIFEST.txt` | Local timestamped freeze: SHA-256 of the protocol, the extension code and tests, and the original modules it reuses. This is not an external preregistration. |
| `DEVELOPMENT_LOG.md` | Pilot runs, defects fixed before the freeze, and departures from test-first |
| `MANUSCRIPT_EVIDENCE_OUTLINE.md` | The evidence outline the v6 text was written from |
| `results/20261112T114244Z-x1.0/` | Formal run. Raw per-execution records (events, ledger, decisions, hashes), CSV, `summary.json`, regression check, `manifest.json` |
| `verification/verify_extension.py` + `.log` | Independent verification (stdlib only, imports nothing from `app/`) |

**Source:**
- extension code: `app/integration/inflight/` (service, policies, runner, assessor, pipeline_replay,
  experiment);
- tests: `tests/test_ext_*.py`.

Both are new untracked files; no existing file was modified.

## Reproduce
Requirements: Python 3.11 (tested with 3.11.0, SQLite 3.38.4) and the repository's dependencies.
The tested versions are langgraph 1.2.1, langgraph-checkpoint 4.1.1, langgraph-checkpoint-sqlite
3.1.0, langchain-core 1.4.0, pydantic 2.13.4 and PyYAML 6.0.3, on macOS 26.5.1 (arm64).

```sh
export LANGSMITH_TRACING=false
.venv/bin/python -m pytest -p no:cacheprovider -q            # 224 passed expected (194 original + 30 extension)
.venv/bin/python -m app.integration.inflight.experiment --run-id <new id> \
    --results-root <dir outside the repo> --scratch-root <tmp dir>
python3 research/elcon2027/extension_v1/verification/verify_extension.py <dir>/<new id> research/elcon2027/extension_v1/protocol
```

**Notes on running:**
- The driver refuses to run if any frozen file has changed.
- It never overwrites an existing run directory.
- Outputs are deterministic apart from timestamps, `git status` and wall-clock fields in
  `manifest.json`.
