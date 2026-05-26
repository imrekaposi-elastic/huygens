.PHONY: install test run

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -e ../../shared/huy_auth
	$(PYTHON) -m pip install -e ../../shared/huy_events
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest -q

run:
	huy-inventory
