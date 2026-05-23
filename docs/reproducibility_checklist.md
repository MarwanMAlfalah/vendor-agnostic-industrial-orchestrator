# Reproducibility Checklist

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]" --python .venv/bin/python
```

## Optional Hosted LangSmith

```bash
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=<your-langsmith-api-key>
export LANGSMITH_PROJECT=vendor-agnostic-industrial-orchestrator
```

`LANGSMITH_ENDPOINT` is optional and should be set only when explicitly needed.

## Experiment Commands

```bash
.venv/bin/python -m app.evaluation.run_comparison
.venv/bin/python -m app.evaluation.run_langgraph_comparison
.venv/bin/python -m app.evaluation.run_mixed_workflow_comparison
.venv/bin/python -m app.evaluation.run_post_approval_comparison
.venv/bin/python -m app.evaluation.run_crash_restart_demo
```

## Optional Docker Demo

```bash
docker compose -f docker-compose.demo.yml up --build
```

## Expected Output Files

- `data/results/comparison_results.csv`
- `data/results/baseline_summary.json`
- `data/results/langgraph_comparison_results.csv`
- `data/results/langgraph_summary.json`
- `data/results/mixed_comparison_results.csv`
- `data/results/post_approval_comparison_results.csv`
- `data/results/post_approval_summary.json`
- `data/results/crash_restart_demo_summary.json`
- `data/results/final_unified_metrics.csv`
- `data/results/final_unified_metrics.json`
- `docs/final_unified_evaluation_report.md`

## Tests

```bash
.venv/bin/pytest
```

Expected current result:

```text
20 passed
```

## Do Not Commit

- `.env`
- API keys
- `.venv/`
- cache files such as `__pycache__/` and `.pytest_cache/`
- local checkpoint databases unless intentionally included for a demo artifact
- private credentials or hosted service tokens

