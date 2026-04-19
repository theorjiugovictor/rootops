.PHONY: up down logs build clean pull status ps web web-logs web-shell web-audit dev pull-model pull-embeddings list-models \
       cloud-deploy cloud-update cloud-ssh cloud-logs cloud-status cloud-test cloud-pull-model demo

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

# ── Remote Management ────────────────────────────────────────────
# Manage a RootOps instance running on any remote host over SSH.
# Set in .env or pass on the command line:
#
#   DEPLOY_HOST  — SSH target, e.g. user@203.0.113.10
#   DEPLOY_DIR   — App directory on the remote (default: /opt/rootops)
#   DEPLOY_URL   — Public URL for running tests
#
# Examples:
#   make cloud-ssh   DEPLOY_HOST=user@ip
#   make cloud-logs  DEPLOY_HOST=user@ip
#   make cloud-test  DEPLOY_URL=https://rootops.example.com

DEPLOY_HOST ?= $(shell grep -E '^DEPLOY_HOST=' .env 2>/dev/null | cut -d= -f2)
DEPLOY_DIR  ?= $(shell grep -E '^DEPLOY_DIR=' .env 2>/dev/null | cut -d= -f2 || echo "/opt/rootops")
DEPLOY_URL  ?= $(shell grep -E '^DEPLOY_URL=' .env 2>/dev/null | cut -d= -f2)

define _require_host
	@if [ -z "$(DEPLOY_HOST)" ]; then \
		echo "Error: DEPLOY_HOST not set. Add it to .env or run:"; \
		echo "  make $@ DEPLOY_HOST=user@ip"; \
		exit 1; \
	fi
endef

REPO_URL ?= $(shell grep -E '^REPO_URL=' .env 2>/dev/null | cut -d= -f2 || echo "https://github.com/Intelligent-IDP/rootops.git")

cloud-deploy: ## Bootstrap RootOps on a fresh remote host over SSH
	$(_require_host)
	@echo "═══ Deploying RootOps to $(DEPLOY_HOST) ═══"
	@echo ""
	@echo "Step 1/4 — Installing Docker..."
	ssh $(DEPLOY_HOST) "command -v docker >/dev/null 2>&1 \
		|| { curl -fsSL https://get.docker.com | sudo sh \
		&& sudo usermod -aG docker \$$USER; }"
	@echo ""
	@echo "Step 2/4 — Cloning repository..."
	ssh $(DEPLOY_HOST) "if [ -d $(DEPLOY_DIR) ]; then \
		cd $(DEPLOY_DIR) && git pull --ff-only 2>/dev/null || true; \
	else \
		sudo git clone $(REPO_URL) $(DEPLOY_DIR) \
		&& sudo chown -R \$$USER:\$$USER $(DEPLOY_DIR); \
	fi"
	@echo ""
	@echo "Step 3/4 — Uploading .env..."
	scp .env $(DEPLOY_HOST):$(DEPLOY_DIR)/.env
	@echo ""
	@echo "Step 4/4 — Starting services..."
	ssh $(DEPLOY_HOST) "cd $(DEPLOY_DIR) && docker compose pull && docker compose up -d"
	@echo ""
	@echo "✓ RootOps deployed to $(DEPLOY_HOST)"
	@echo "  Run 'make cloud-status' to check services."
	@echo "  Run 'make cloud-test' to verify endpoints."

cloud-update: ## Pull latest images and restart on the remote host
	$(_require_host)
	ssh $(DEPLOY_HOST) "cd $(DEPLOY_DIR) && git pull --ff-only && docker compose pull && docker compose up -d"

cloud-ssh: ## SSH into the remote host
	$(_require_host)
	ssh $(DEPLOY_HOST)

cloud-logs: ## Stream service logs from the remote host
	$(_require_host)
	ssh $(DEPLOY_HOST) "cd $(DEPLOY_DIR) && docker compose logs -f"

cloud-status: ## Show service status on the remote host
	$(_require_host)
	ssh $(DEPLOY_HOST) "cd $(DEPLOY_DIR) && docker compose ps"

cloud-test: ## Run endpoint health checks against the deployment
	@if [ -z "$(DEPLOY_URL)" ]; then \
		echo "Error: DEPLOY_URL not set. Add it to .env or run:"; \
		echo "  make cloud-test DEPLOY_URL=https://your-domain.com"; \
		exit 1; \
	fi
	@echo "Testing $(DEPLOY_URL) ..."
	@curl -sf "$(DEPLOY_URL)/health" > /dev/null && echo "  ✓ /health" || echo "  ✗ /health"
	@curl -sf "$(DEPLOY_URL)/api/repos" > /dev/null && echo "  ✓ /api/repos" || echo "  ✗ /api/repos"
	@curl -sf "$(DEPLOY_URL)/api/ingest/status" > /dev/null && echo "  ✓ /api/ingest/status" || echo "  ✗ /api/ingest/status"
	@curl -sf "$(DEPLOY_URL)/" > /dev/null && echo "  ✓ / (web)" || echo "  ✗ / (web)"

cloud-pull-model: ## Pull the Ollama LLM model on the remote host
	$(_require_host)
	@MODEL=$$(grep -E '^OLLAMA_MODEL=' .env 2>/dev/null | cut -d= -f2 || echo "llama3"); \
	echo "Pulling $$MODEL on remote host..."; \
	ssh $(DEPLOY_HOST) "cd $(DEPLOY_DIR) && docker compose exec -T ollama ollama pull $$MODEL"

# ── Demo ────────────────────────────────────────────────────────
demo: ## Seed synthetic logs + ingest a small public repo for a live demo
	@echo "Seeding RootOps demo data..."
	@python api/scripts/seed_demo.py --api-url http://localhost:8000

# ── Help ─────────────────────────────────────────────────────────
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
