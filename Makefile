.PHONY: help install dev test lint format typecheck build clean ci

help: ## Show this help message
	@echo "SynthDB Development Commands (using uv)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies with uv
	uv sync

dev: ## Setup development environment
	python scripts/dev.py setup

test: ## Run tests
	uv run pytest -v --cov=synthdb

lint: ## Run linting
	uv run ruff check synthdb/

format: ## Format code
	uv run ruff format synthdb/

typecheck: ## Run type checking
	uv run mypy synthdb/

build: ## Build package
	uv build

clean: ## Clean build artifacts
	python scripts/dev.py clean

ci: ## Run full CI workflow (lint + typecheck + test + build)
	python scripts/dev.py ci

# Database-specific targets  
install-config: ## Install with configuration file support
	uv sync --extra config

# Quick development workflow
quick-test: ## Run tests quickly (no coverage)
	uv run pytest -x

watch-test: ## Run tests in watch mode (requires pytest-watch)
	uv run ptw

demo: ## Run the demo
	uv run python examples/demo.py

# Package management
update: ## Update all dependencies
	uv lock --upgrade

outdated: ## Check for outdated dependencies  
	uv tree --outdated