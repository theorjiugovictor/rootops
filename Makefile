.PHONY: up down logs build clean pull status ps web web-logs web-shell web-audit dev pull-model pull-embeddings list-models

# ── Quick Start ──────────────────────────────────────────────────
up: ## Pull latest images and start everything (Postgres, Ollama, API, Web)
	@cp -n .env.example .env 2>/dev/null || true
	docker compose pull api web
	docker compose up -d
	@echo ""
	@echo "Waiting for Ollama to be ready..."
	@for i in $$(seq 1 30); do \
		docker compose exec -T ollama curl -sf http://localhost:11434/ > /dev/null 2>&1 && break; \
		sleep 2; \
	done
	@$(MAKE) pull-model --no-print-directory
	@echo ""
	@echo "RootOps is ready."
	@echo ""
	@echo "  Dashboard:  http://localhost:3000"
	@echo "  API:        http://localhost:8000"
	@echo "  API Docs:   http://localhost:8000/docs"
	@echo ""
	@echo "  Embedding model downloads automatically on first query (~600 MB)."

down: ## Stop everything
	docker compose down

clean: ## Stop everything and delete all data (database, models, etc.)
	docker compose down -v
	@echo "All data removed."

# ── Development (build from source) ─────────────────────────────
dev: ## Build from source with hot-reload for API and Web
	@cp -n .env.example .env 2>/dev/null || true
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

build: ## Rebuild source images (for development)
	docker compose -f docker-compose.yml -f docker-compose.dev.yml build --no-cache

# ── Observability ────────────────────────────────────────────────
logs: ## Follow all service logs
	docker compose logs -f

logs-api: ## Follow API logs only
	docker compose logs -f api

logs-web: ## Follow Web UI logs
	docker compose logs -f web

ps: ## Show running services
	docker compose ps

status: ## Show service health
	@docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

# ── Model Management ────────────────────────────────────────────
pull-model: ## Pull the configured Ollama LLM model
	@MODEL=$$(grep -E '^OLLAMA_MODEL=' .env 2>/dev/null | cut -d= -f2 || echo "llama3"); \
	echo "Pulling LLM model: $$MODEL (this may take a few minutes on first run)..."; \
	docker compose exec -T ollama ollama pull $$MODEL

pull-embeddings: ## Pre-download the embedding model to host cache (~600 MB)
	@MODEL=$$(grep -E '^EMBEDDING_MODEL_NAME=' .env 2>/dev/null | cut -d= -f2 || echo "jinaai/jina-embeddings-v2-base-code"); \
	echo "Pre-downloading embedding model: $$MODEL"; \
	docker compose exec -T api uv run --no-project python -c \
		"from sentence_transformers import SentenceTransformer; SentenceTransformer('$$MODEL', trust_remote_code=True); print('Done.')"

list-models: ## List downloaded Ollama models
	docker compose exec ollama ollama list

# ── Web (Next.js) ────────────────────────────────────────────────
web: ## Start ONLY the Next.js frontend (+ API + DB)
	docker compose up web api db -d
	@echo ""
	@echo "  Web UI:  http://localhost:3000"
	@echo "  API:     http://localhost:8000"

web-logs: ## Follow Next.js container logs
	docker compose logs -f web

web-shell: ## Open a shell inside the web container (for debugging)
	docker compose exec web sh

web-audit: ## Run npm audit inside the web container
	docker compose exec web npm audit

# ── Help ─────────────────────────────────────────────────────────
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
