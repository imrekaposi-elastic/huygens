.PHONY: install test run lint

install:
	pip install -e ".[dev]"

test:
	pytest -q

run:
	huy-iam

lint:
	ruff check src tests
