#!/bin/bash
# Quick test runner script for different test categories

set -e

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default to running unit tests
TEST_TYPE=${1:-unit}

echo -e "${GREEN}🧪 Emoji Smith Test Runner${NC}"
echo -e "${YELLOW}Running $TEST_TYPE tests...${NC}\n"

case $TEST_TYPE in
  unit)
    echo "Running fast unit tests..."
    pytest -m unit -v
    ;;

  integration)
    echo "Running integration tests..."
    pytest -m integration -v
    ;;

  contract)
    echo "Running API contract tests..."
    pytest -m contract -v
    ;;

  security)
    echo "Running security tests..."
    pytest -m security -v
    ;;

  performance)
    echo "Running performance tests..."
    pytest -m performance -v
    ;;

  e2e)
    echo "Running end-to-end tests..."
    pytest -m e2e -v
    ;;

  fast)
    echo "Running all fast tests (unit + contract)..."
    pytest -m "unit or contract" -v
    ;;

  all)
    echo "Running ALL tests..."
    pytest -v
    ;;

  coverage)
    echo "Running all tests with coverage report..."
    pytest --cov=src --cov-report=html --cov-report=term-missing
    echo -e "\n${GREEN}Coverage report generated in htmlcov/index.html${NC}"
    ;;

  *)
    echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
    echo -e "\nAvailable options:"
    echo "  ./scripts/run-tests.sh unit         # Run unit tests (default)"
    echo "  ./scripts/run-tests.sh integration  # Run integration tests"
    echo "  ./scripts/run-tests.sh contract     # Run contract tests"
    echo "  ./scripts/run-tests.sh security     # Run security tests"
    echo "  ./scripts/run-tests.sh performance  # Run performance tests"
    echo "  ./scripts/run-tests.sh e2e         # Run end-to-end tests"
    echo "  ./scripts/run-tests.sh fast        # Run fast tests (unit + contract)"
    echo "  ./scripts/run-tests.sh all         # Run all tests"
    echo "  ./scripts/run-tests.sh coverage    # Run all tests with coverage"
    exit 1
    ;;
esac

echo -e "\n${GREEN}✅ Test run complete!${NC}"
