#!/bin/bash
# Quick test runner for development

set -e

# Ensure virtual environment is active
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "🔌 Activating virtual environment..."
    source .venv/bin/activate
fi

# Parse arguments
TEST_PATH=${1:-tests/}
VERBOSE=""

if [[ "$2" == "-v" ]] || [[ "$1" == "-v" ]]; then
    VERBOSE="-vv"
fi

# Run tests
echo "🧪 Running tests..."

if [ "$TEST_PATH" == "tests/" ]; then
    # Running all tests
    pytest $VERBOSE --cov=src --cov-report=term-missing $TEST_PATH
else
    # Running specific test
    pytest $VERBOSE $TEST_PATH
fi
