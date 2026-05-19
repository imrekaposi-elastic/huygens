.PHONY: compose-up compose-down compose-logs compose-ps test-iam

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

test-iam:
	$(MAKE) -C services/iam test
