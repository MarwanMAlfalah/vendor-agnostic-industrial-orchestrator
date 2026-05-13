# Vendor-Agnostic Industrial Orchestrator

Research prototype for a supervisory, vendor-agnostic multi-agent LLM
orchestrator for industrial operations.

The project is intentionally minimal. It starts with a small FastAPI backend and
a package layout that can grow later to include agents, adapters, registries,
industrial scenarios, traces, and orchestration services.

## Setup

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -e ".[dev]"
```

## Run

Run the app locally:

```bash
uvicorn app.main:app --reload
```

Then check the health endpoint:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "vendor-agnostic-industrial-orchestrator",
  "environment": "research"
}
```
