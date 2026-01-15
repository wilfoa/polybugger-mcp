.PHONY: help install install-dev clean lint format typecheck test test-unit test-integration test-e2e test-cov run run-mcp build pre-commit pre-commit-install shell lock update

# Default target
help:
	@echo "Python Debugger MCP - Available commands:"
	@echo ""
	@echo "  install          Install production dependencies"
	@echo "  install-dev      Install all dependencies (including dev)"
	@echo "  lock             Update poetry.lock file"
	@echo "  update           Update dependencies"
	@echo "  shell            Activate virtual environment"
	@echo "  clean            Remove build artifacts and caches"
	@echo ""
	@echo "  lint             Run ruff linter"
	@echo "  format           Format code with ruff"
	@echo "  typecheck        Run mypy type checker"
	@echo "  pre-commit       Run all pre-commit hooks"
	@echo "  pre-commit-install  Install pre-commit hooks"
	@echo ""
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-e2e         Run end-to-end tests only"
	@echo "  test-cov         Run tests with coverage report"
	@echo ""
	@echo "  run              Start the HTTP debug server"
	@echo "  run-mcp          Start the MCP server"
	@echo "  build            Build the package"

# Installation
install:
	poetry install --only main

install-dev:
	poetry install
	poetry run pre-commit install

lock:
	poetry lock

update:
	poetry update

shell:
	poetry shell

# Cleaning
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf src/*.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Linting and formatting
lint:
	poetry run ruff check src/ tests/

format:
	poetry run ruff format src/ tests/
	poetry run ruff check --fix src/ tests/

typecheck:
	poetry run mypy src/

# Pre-commit
pre-commit:
	poetry run pre-commit run --all-files

pre-commit-install:
	poetry run pre-commit install

# Testing
test:
	poetry run pytest tests/ -v

test-unit:
	poetry run pytest tests/unit/ -v

test-integration:
	poetry run pytest tests/integration/ -v

test-e2e:
	poetry run pytest tests/e2e/ -v

test-cov:
	poetry run pytest tests/ --cov=src/pybugger_mcp --cov-report=term-missing --cov-report=html

# Running
run:
	poetry run python -m pybugger_mcp.main

run-mcp:
	poetry run python -m pybugger_mcp.mcp_server

# Building
build: clean
	poetry build
