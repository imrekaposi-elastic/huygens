.PHONY: compose-up compose-down compose-logs compose-ps test test-unit test-iam test-registry test-inventory test-projects

compose-up:
	docker compose up -d --build

compose-down:
	docker compose down

compose-logs:
	docker compose logs -f --tail=100

compose-ps:
	docker compose ps

compose-kafka:
	docker compose --profile kafka up -d --build

test: test-unit

test-unit: test-iam test-registry test-inventory test-projects

test-iam:
	$(MAKE) -C services/iam test

test-registry:
	$(MAKE) -C services/registry test

test-inventory:
	$(MAKE) -C services/inventory test

test-projects:
	$(MAKE) -C services/projects test
