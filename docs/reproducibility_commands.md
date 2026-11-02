# Reproducibility Commands

These commands support local review and reproduction of the current deterministic prototype.
They do not imply production deployment, certified safety, or live PLC integration.

## Environment Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
make install
```

Equivalent direct command:

```bash
python3 -m pip install -e ".[dev]"
```

## Quality Gates

Run tests with coverage:

```bash
make test
```

Run lint:

```bash
make lint
```

Format Python files:

```bash
make format
```

## API

Run the local FastAPI service:

```bash
make run-api
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Deterministic Evaluation

Run the 240-scenario journal profile:

```bash
make eval-journal
```

Equivalent direct command:

```bash
python3 -m app.evaluation.run_scaled_evaluation --profile journal
```

Run runtime-specific aligned metrics:

```bash
make eval-aligned
```

Equivalent direct command:

```bash
python3 -m app.evaluation.run_aligned_scaled_evaluation --profile journal
```

Run the local LangGraph crash/restart checkpoint demonstration:

```bash
make eval-crash-restart
```

Equivalent direct command:

```bash
python3 -m app.evaluation.run_crash_restart_demo
```

## Docker Demo

Run the crash/restart demo through Docker Compose:

```bash
docker compose -f docker-compose.demo.yml up --build
```

The Docker demo mounts `./data` and `./docs` so summaries and checkpoint evidence remain on
the host. It is local prototype evidence only.

## Expected Artifact Locations

- Scenario JSON files: `data/scenarios/`
- Scaled result tables and summaries: `data/results/`
- Evaluation reports and manuscript documentation: `docs/`
- Local LangGraph checkpoint database: `data/langgraph/checkpoints.db`

## Result Integrity Notes

The repository currently includes generated evaluation artifacts. Do not change result values
without explicitly rerunning, reviewing, and documenting the scientific implications. Formatting,
linting, and documentation updates should not alter result values.

## P0 correction evidence refresh

The checkpoint demo runs entirely within one Python process. Its historical script
and Make target names remain compatible; they do not imply an OS crash/restart.

After the journal command above, regenerate the other affected deterministic evidence:

```bash
python3 -m app.evaluation.run_scaled_evaluation --profile default
python3 -m app.evaluation.run_scaled_evaluation --profile extended
python3 -m app.evaluation.run_scaled_error_audit --profile extended
python3 -m app.evaluation.run_scaled_error_audit --profile journal
python3 -m app.evaluation.statistical_analysis --profile journal
python3 -m app.evaluation.run_ablation_study
python3 -m app.evaluation.run_comparison
python3 -m app.evaluation.run_langgraph_comparison
python3 -m app.evaluation.run_mixed_workflow_comparison
python3 -m app.evaluation.run_post_approval_comparison
make eval-aligned
make eval-crash-restart
python3 -m app.evaluation.refresh_evidence_artifacts
python3 -m pytest tests/test_evidence_artifact_integrity.py
```

Run extended diagnostics before journal diagnostics so shared manuscript reports
end on the journal profile. The refresh command copies generated source metrics
into consolidated tables and refreshes actual SHA-256 hashes/byte counts in the
existing indexes and manifest. No reusable refresh implementation was retained in
the earlier repository; this command makes that operation reproducible. Original
indexing provenance is retained with explicit refresh metadata. Refreshed normalized
rows use a worktree run ID and the base commit SHA, not a claim that the correction
is committed. Historical Docker/kind/LangSmith logs remain captured evidence;
this local correction does not rerun those environments or hosted traces.
