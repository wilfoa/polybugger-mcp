.PHONY: help install install-dev clean lint format typecheck test test-unit test-integration test-e2e test-cov run run-mcp build pre-commit pre-commit-install

# Default target
help:
	@echo "Python Debugger MCP - Available commands:"
	@echo ""
	@echo "  install          Install production dependencies"
	@echo "  install-dev      Install development dependencies"
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
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

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
	ruff check src/ tests/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

typecheck:
	mypy src/

# Pre-commit
pre-commit:
	pre-commit run --all-files

pre-commit-install:
	pre-commit install

# Testing
test:
	pytest tests/ -v

test-unit:
	pytest tests/unit/ -v -m unit

test-integration:
	pytest tests/integration/ -v -m integration

test-e2e:
	pytest tests/e2e/ -v -m e2e

test-cov:
	pytest tests/ --cov=src/python_debugger_mcp --cov-report=term-missing --cov-report=html

# Running
run:
	python -m python_debugger_mcp.main

run-mcp:
	python -m python_debugger_mcp.mcp_server

# Building
build: clean
	python -m build
