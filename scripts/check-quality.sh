#!/bin/bash
# Run all code quality checks

set -e  # Exit on first error

echo "🔍 Running code quality checks..."

# Ensure we're in virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "❌ ERROR: Virtual environment not activated!"
    echo "Please run: source .venv/bin/activate"
    exit 1
fi

echo "✓ Virtual environment active: $VIRTUAL_ENV"
echo ""

# Ruff formatting
echo "⚫ Running Ruff formatter check..."
ruff format --check src/ tests/
echo "✓ Ruff formatting check passed"
echo ""

# Ruff linting
echo "🔍 Running Ruff linter..."
ruff check src/ tests/
echo "✓ Ruff linting passed"
echo ""

# Test naming conventions
echo "🔍 Checking test naming conventions..."
scripts/check-test-names.py
echo "✓ Test naming conventions passed"
echo ""

# Pytest with coverage
echo "🧪 Running tests with coverage..."
pytest --cov=src tests/
echo "✓ All tests passed"
echo ""

echo "✅ All quality checks passed! Ready to commit."
