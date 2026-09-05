.PHONY: install dev backend frontend demo test lint format docker-up docker-down clean help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install Python dependencies
	pip install -r backend/requirements.txt
	cd frontend && npm install

dev: ## Start development (backend + frontend)
	@echo "Starting IBVAP development server..."
	PYTHONPATH=. uvicorn backend.app.main:app --reload --port 8001 &
	cd frontend && npm run dev

backend: ## Start backend only
	PYTHONPATH=. uvicorn backend.app.main:app --reload --port 8001

frontend: ## Start frontend only
	cd frontend && npm run dev

demo: ## Seed demo incidents
	@echo "Seeding all demo scenarios..."
	PYTHONPATH=. python -c " \
import requests; \
r = requests.post('http://localhost:8000/api/v1/demo/seed/all'); \
print(r.json())" 2>/dev/null || echo "Backend not running. Start with 'make backend' first."

test: ## Run all tests
	PYTHONPATH=. pytest backend/tests/ -v

lint: ## Run linting (if available)
	@echo "Linting not configured. Install flake8/black for linting."

format: ## Format code (if available)
	@echo "Formatting not configured. Install black for formatting."

docker-up: ## Start with Docker Compose
	docker compose up --build -d

docker-down: ## Stop Docker Compose
	docker compose down

clean: ## Clean build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache frontend/dist frontend/node_modules
	rm -f *.db
