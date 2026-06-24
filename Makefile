.DEFAULT_GOAL := help

COMPOSE := docker compose
BACKEND_DIR := src/backend
FRONTEND_DIR := src/frontend
VENV := $(BACKEND_DIR)/.venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

# Host port the dockerized Postgres is published on (see docker-compose.yml).
DB_PORT ?= 5433
LOCAL_DATABASE_URL := postgresql+asyncpg://ner:ner@localhost:$(DB_PORT)/ner_manager

.PHONY: help up down build rebuild restart logs ps clean test venv \
        db db-down dev-backend dev-frontend frontend-install

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

## --- Full stack in Docker ---

up: ## Build (if needed) and start the full stack
	$(COMPOSE) up --build

down: ## Stop and remove containers
	$(COMPOSE) down

build: ## Build all images
	$(COMPOSE) build

rebuild: ## Rebuild images from scratch (no cache)
	$(COMPOSE) build --no-cache

restart: down up ## Restart the full stack

logs: ## Follow logs from all services
	$(COMPOSE) logs -f

ps: ## Show running services
	$(COMPOSE) ps

clean: ## Stop stack and remove volumes (drops the database)
	$(COMPOSE) down -v

## --- Local development (no image rebuilds) ---

db: ## Start only the Postgres container (detached)
	$(COMPOSE) up -d db

db-down: ## Stop the Postgres container
	$(COMPOSE) stop db

dev-backend: venv db ## Run the backend locally with hot reload (uses dockerized DB)
	cd $(BACKEND_DIR) && DATABASE_URL=$(LOCAL_DATABASE_URL) .venv/bin/uvicorn app.main:app --reload --port 8000

frontend-install: ## Install frontend dependencies
	cd $(FRONTEND_DIR) && npm install

dev-frontend: frontend-install ## Run the frontend locally with hot reload
	cd $(FRONTEND_DIR) && PUBLIC_API_URL=http://localhost:8000 npm run dev

## --- Tooling ---

venv: ## Create backend virtualenv and install dependencies
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r $(BACKEND_DIR)/requirements-dev.txt

test: venv ## Run backend test suite
	cd $(BACKEND_DIR) && .venv/bin/python -m pytest
