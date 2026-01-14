# Contributing to Python Debugger MCP

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/wilfoa/python-debugger-mcp.git
   cd python-debugger-mcp
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install development dependencies** (this also installs pre-commit hooks)
   ```bash
   make install-dev
   ```

4. **Run tests to verify setup**
   ```bash
   make test
   ```

5. **Verify pre-commit hooks**
   ```bash
   make pre-commit
   ```

## Development Workflow

### Running Tests

```bash
# Run all tests
make test

# Run specific test categories
make test-unit
make test-integration
make test-e2e

# Run with coverage
make test-cov
```

### Code Quality

We use pre-commit hooks to ensure code quality. They run automatically on commit, but you can also run them manually:

```bash
# Run all pre-commit hooks
make pre-commit

# Or run individual checks:
make lint       # Run ruff linter
make format     # Format code with ruff
make typecheck  # Run mypy type checker
```

Pre-commit hooks include:
- **ruff** - Linting and formatting
- **mypy** - Type checking
- **codespell** - Spell checking
- **trailing-whitespace** - Remove trailing whitespace
- **check-yaml/toml/json** - Validate config files
- **detect-private-key** - Prevent committing secrets

### Running the Server

```bash
# Start HTTP server
make run

# Start MCP server
make run-mcp
```

## Pull Request Process

1. **Fork the repository** and create a feature branch from `main`
2. **Make your changes** with clear, descriptive commits
3. **Add tests** for any new functionality
4. **Ensure all tests pass** and code quality checks succeed
5. **Update documentation** if needed
6. **Submit a pull request** with a clear description of changes

### CI Requirements

All pull requests must pass the following checks before merging:

- **Tests** - Must pass on Python 3.10, 3.11, and 3.12
- **Lint** - Code must pass ruff linting and formatting checks
- **Type Check** - Code must pass mypy type checking
- **CI Success** - Aggregated status check that ensures all jobs pass

The `main` branch is protected and requires:
- All CI checks to pass
- At least 1 approving review
- Branch to be up-to-date with main
- All conversations to be resolved

### Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/) for automatic versioning:

- `feat: add new feature` - Triggers minor version bump
- `fix: resolve bug` - Triggers patch version bump
- `docs: update readme` - No version bump
- `chore: update deps` - No version bump

Examples:
```
feat: add conditional breakpoint support
fix: handle timeout in DAP client
docs: improve installation instructions
refactor: simplify session state machine
```

### Code Style

- Follow PEP 8 guidelines (enforced by ruff)
- Use type hints for all function signatures
- Write docstrings for public functions and classes
- Keep functions focused and small

## Reporting Issues

When reporting issues, please include:

- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs or error messages

## Questions?

Feel free to open an issue for questions or discussions.
