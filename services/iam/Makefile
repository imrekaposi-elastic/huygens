.PHONY: install test run lint

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest -q

run:
	huy-iam

lint:
	ruff check src tests
