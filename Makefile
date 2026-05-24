.PHONY: install
.PHONY: test lint format
.PHONY: run-api
.PHONY: eval-journal eval-aligned eval-crash-restart

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -e ".[dev]"


test:
	$(PYTHON) -m pytest --cov=app --cov-report=term-missing


lint:
	$(PYTHON) -m ruff check app tests


format:
	$(PYTHON) -m black app tests
	$(PYTHON) -m ruff check --fix app tests


run-api:
	$(PYTHON) -m uvicorn app.main:app --reload


eval-journal:
	$(PYTHON) -m app.evaluation.run_scaled_evaluation --profile journal


eval-aligned:
	$(PYTHON) -m app.evaluation.run_aligned_scaled_evaluation --profile journal


eval-crash-restart:
	$(PYTHON) -m app.evaluation.run_crash_restart_demo
