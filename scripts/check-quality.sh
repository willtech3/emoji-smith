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

# Black formatting
echo "⚫ Running Black formatter check..."
black --check src/ tests/
echo "✓ Black formatting check passed"
echo ""

# Flake8 linting
echo "🔍 Running Flake8 linter..."
flake8 src/ tests/
echo "✓ Flake8 linting passed"
echo ""

# Test naming conventions
echo "🔍 Checking test naming conventions..."
scripts/check-test-names.py
echo "✓ Test naming conventions passed"
echo ""

# MyPy type checking
echo "🔍 Running MyPy type checker..."
mypy src/
echo "✓ MyPy type checking passed"
echo ""

# Bandit security scanning
echo "🔒 Running Bandit security scanner..."
bandit -r src/
echo "✓ Bandit security scan passed"
echo ""

# Pytest with coverage
echo "🧪 Running tests with coverage..."
pytest --cov=src --cov-fail-under=80 tests/
echo "✓ All tests passed with sufficient coverage"
echo ""

echo "✅ All quality checks passed! Ready to commit."
