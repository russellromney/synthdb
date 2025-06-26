.PHONY: help install dev test lint format typecheck build clean ci

help: ## Show this help message
	@echo "SynthDB Development Commands (using uv)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies with uv
	uv sync

dev: ## Setup development environment
	uv run python scripts/dev.py setup

test: ## Run tests
	uv run pytest -vv --cov=synthdb

lint: ## Run linting
	uv run ruff check synthdb/

format: ## Format code
	uv run ruff format synthdb/

typecheck: ## Run type checking
	uv run mypy synthdb/

build: ## Build package
	uv build

clean: ## Clean build artifacts
	uv run python scripts/dev.py clean

ci: ## Run full CI workflow (lint + typecheck + test + build)
	uv run python scripts/dev.py ci

# Database-specific targets  
install-config: ## Install with configuration file support
	uv sync --extra config

install-docs: ## Install with documentation dependencies
	uv sync --extra docs

install-all: ## Install with all optional dependencies
	uv sync --extra config --extra docs

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

# Documentation targets
docs-check: ## Check documentation dependencies
	uv run python scripts/build_docs.py check

docs-build: ## Build all documentation
	uv run python scripts/build_docs.py build

docs-serve: ## Serve documentation for development
	uv run python scripts/build_docs.py serve

docs-sphinx: ## Build only Sphinx documentation
	uv run python scripts/build_docs.py build --no-mkdocs

docs-mkdocs: ## Build only MkDocs documentation
	uv run python scripts/build_docs.py build --no-sphinx

docs-clean: ## Clean documentation build directories
	uv run python scripts/build_docs.py clean

docs-deploy: ## Deploy documentation to GitHub Pages
	uv run python scripts/build_docs.py deploy