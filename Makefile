.PHONY: dev-up dev-down dev-status test test-api

dev-up:
	@echo "Starting AgentNet development environment..."
	docker compose up --build -d
	@echo "Frontend: http://localhost:3000"
	@echo "API: http://localhost:8000"
	@echo "API docs: http://localhost:8000/docs"

dev-down:
	docker compose down

dev-status:
	docker compose ps

test-api:
	docker compose exec api pytest -v

logs:
	docker compose logs -f

db-shell:
	docker compose exec db psql -U agentnet agentnet

redis-shell:
	docker compose exec redis redis-cli
