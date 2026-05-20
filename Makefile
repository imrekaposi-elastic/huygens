.PHONY: compose-up compose-down compose-logs compose-ps test test-unit test-huy-events test-iam test-registry test-inventory test-projects test-web

compose-up:
	docker compose up -d --build

compose-down:
	docker compose down

compose-logs:
	docker compose logs -f --tail=100

compose-ps:
	docker compose ps

test: test-unit

test-unit: test-huy-events test-iam test-registry test-inventory test-projects test-web

test-huy-events:
	cd shared/huy_events && pip install -q -e . && pytest -q

test-iam:
	$(MAKE) -C services/iam test

test-registry:
	$(MAKE) -C services/registry test

test-inventory:
	$(MAKE) -C services/inventory test

test-projects:
	$(MAKE) -C services/projects test

test-web:
	cd web && npm install && npm test
