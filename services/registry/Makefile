.PHONY: install test run

install:
	pip install -e ../../shared/huy_auth
	pip install -e ".[dev]"

test:
	pytest -q

run:
	huy-registry
