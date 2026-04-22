UV ?= uv

.PHONY: venv install install-dev hooks-install lint lint-docs type-check format test test-critical check

venv:
	$(UV) venv .venv

install:
	$(UV) pip install -r requirements.txt

install-dev: venv
	$(UV) pip install -r requirements-dev.txt

hooks-install:
	$(UV) run pre-commit install
	$(UV) run pre-commit install --hook-type pre-push

lint:
	$(UV) run ruff check app tests

lint-docs:
	$(UV) run ruff check app tests --select D,DOC

type-check:
	$(UV) run mypy app

format:
	$(UV) run ruff format app tests

test:
	$(UV) run pytest

test-critical:
	$(UV) run pytest

check: lint test
