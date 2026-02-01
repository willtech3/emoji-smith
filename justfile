# Common development and CI-aligned commands (uv-based)

# Create venv and install all dependencies (including dev and extras)
setup:
	uv venv
	uv sync --all-extras --dev

# Formatting
format:
	uv run ruff format src/ tests/

format-check:
	uv run ruff format --check src/ tests/

# Linting (ruff-based)
lint:
	uv run ruff check src/ tests/

lint-fix:
	uv run ruff check --fix src/ tests/

# Security scanning
security:
	uv run ruff check --select S src/ tests/

# Tests
test:
	uv run pytest -q

# Run the full quality gate (matches CI order)
qa:
	set -e
	just format-check
	just lint
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

# Clean up caches and temporary artifacts
clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov build dist *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.py[co]" -delete
	find . -type f -name '*$py.class' -delete
