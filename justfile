# Common development and CI-aligned commands (uv-based)

# Create venv and install all dependencies (including dev and extras)
setup:
	uv venv
	uv sync --all-extras --dev

# Formatting
format:
	uv run black src/ tests/

format-check:
	uv run black --check src/ tests/

# Linting (ruff-based)
lint:
	uv run ruff check src/ tests/

lint-fix:
	uv run ruff check --fix src/ tests/

# Type checking
typecheck:
	uv run mypy src/

# Security scanning
security:
	uv run bandit -r src/

# Tests
test:
	uv run pytest -q

# Run the full quality gate (matches CI order)
qa:
	set -e
	just format-check
	just lint
	just typecheck
	just security
	just test

# Pre-commit helpers
pre-commit-install:
	uv run pre-commit install

pre-commit-all:
	uv run pre-commit run --all-files

# Local dev server
dev:
	uv run python -m src.emojismith.dev_server
