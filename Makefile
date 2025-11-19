# Benz Sent Filter Development Makefile
# Use uv as the package manager for all operations

.PHONY: help install dev test test-verbose test-cov lint format check clean serve

help: ## Show available commands
	@echo "Benz Sent Filter Development Commands:"
	@echo "======================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

install: ## Install production dependencies
	uv sync --no-dev

dev: ## Install all dependencies including development tools
	uv sync --all-extras

test: ## Run unit tests
	PYTHONPATH=src uv run pytest tests/ -v

test-verbose: ## Run unit tests with verbose output
	PYTHONPATH=src uv run pytest tests/ -vv

test-cov: ## Run unit tests with coverage reporting
	PYTHONPATH=src uv run pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing

test-file: ## Run specific test file (use FILE=path/to/test.py)
	PYTHONPATH=src uv run pytest $(FILE) -v -o addopts=""

test-integration: ## Run integration tests (slower tests that interact with external systems)
	PYTHONPATH=src uv run pytest integration/ -v

lint: ## Run code linting with ruff
	uv run ruff check src tests integration

format: ## Format code with ruff
	uv run ruff format src tests integration
	uv run ruff check --fix src tests integration

check: ## Run full code quality check (lint + test)
	make lint
	make test

clean: ## Clean build artifacts and cache
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

serve: ## Start server with multiple workers
	uv run python -m benz_sent_filter --port 8002
