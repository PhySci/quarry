.DEFAULT_GOAL := help

COMPOSE := docker compose
BACKEND_DIR := src/backend
VENV := $(BACKEND_DIR)/.venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: help up down build rebuild restart logs ps clean test venv

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

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

venv: ## Create backend virtualenv and install dev dependencies
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r $(BACKEND_DIR)/requirements-dev.txt

test: venv ## Run backend test suite
	cd $(BACKEND_DIR) && .venv/bin/python -m pytest
