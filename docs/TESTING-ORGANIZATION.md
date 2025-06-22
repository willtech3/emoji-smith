# Test Organization Guide

## Overview

The Emoji Smith test suite is organized by test categories to enable:
- Faster feedback loops during development
- Optimized CI/CD pipeline execution
- Clear test boundaries and responsibilities
- Easier test maintenance and discovery

## Test Categories

### 1. Unit Tests (`tests/unit/`)
**Purpose**: Test individual components in isolation with no external dependencies.

**Characteristics**:
- Fast execution (< 100ms per test)
- No network calls, file I/O, or database access
- All external dependencies mocked
- Focus on single class/function behavior

**Run**: `pytest -m unit`

### 2. Integration Tests (`tests/integration/`)
**Purpose**: Test interaction between components and with external services (using mocks/stubs).

**Characteristics**:
- Test multiple components working together
- May use mocked AWS services (via moto)
- May use test containers or in-memory databases
- Focus on integration points and data flow

**Run**: `pytest -m integration`

### 3. Contract Tests (`tests/contract/`)
**Purpose**: Validate API contracts and message formats with external services.

**Characteristics**:
- Verify request/response schemas
- Validate Slack webhook payload structures
- Check OpenAI API message formats
- Ensure backward compatibility

**Run**: `pytest -m contract`

### 4. Security Tests (`tests/security/`)
**Purpose**: Test security controls and validate against common vulnerabilities.

**Subcategories**:
- `authentication/`: Signature validation, auth mechanisms
- `validation/`: Input validation, injection prevention

**Run**: `pytest -m security`

### 5. Performance Tests (`tests/performance/`)
**Purpose**: Measure and validate performance characteristics.

**Characteristics**:
- Test concurrent request handling
- Measure response times
- Validate resource usage
- May be slower to run

**Run**: `pytest -m performance`

### 6. End-to-End Tests (`tests/e2e/`)
**Purpose**: Test complete user workflows from start to finish.

**Characteristics**:
- Test entire application flow
- May require real services or staging environment
- Slowest tests to run
- Most comprehensive validation

**Run**: `pytest -m e2e`

## Directory Structure

```
tests/
├── unit/              # Fast, isolated unit tests
│   ├── domain/        # Domain logic tests
│   ├── application/   # Application service tests
│   ├── infrastructure/# Infrastructure tests (with mocks)
│   └── presentation/  # API endpoint tests
├── integration/       # Component interaction tests
│   ├── aws/          # AWS service integration
│   ├── slack/        # Slack API integration
│   └── openai/       # OpenAI API integration
├── contract/         # API contract validation
│   ├── slack/        # Slack webhook contracts
│   └── openai/       # OpenAI API contracts
├── security/         # Security-focused tests
│   ├── validation/   # Input validation tests
│   └── authentication/ # Auth/signature tests
├── performance/      # Performance tests
│   └── concurrency/  # Concurrent request tests
├── e2e/             # End-to-end workflow tests
└── fixtures/        # Shared test data

```

## Running Tests

### By Category
```bash
# Run only unit tests (fastest)
pytest -m unit

# Run integration tests
pytest -m integration

# Run multiple categories
pytest -m "unit or contract"

# Run all except slow tests
pytest -m "not performance"

# Run security and contract tests together
pytest -m "security or contract"
```

### By Directory
```bash
# Run all tests in a specific category
pytest tests/unit/

# Run tests for a specific component
pytest tests/unit/domain/
```

### With Coverage
```bash
# Run unit tests with coverage
pytest -m unit --cov=src --cov-report=html

# Run all tests with coverage report
pytest --cov=src --cov-report=term-missing
```

## CI/CD Pipeline Integration

The GitHub Actions workflow runs test categories in parallel:

1. **Unit Tests**: Run first, must pass
2. **Integration Tests**: Run in parallel with unit tests
3. **Contract & Security Tests**: Run together
4. **Performance Tests**: Run with `continue-on-error` (non-blocking)

This allows for:
- Fast feedback from unit tests
- Parallel execution for efficiency
- Non-critical tests don't block deployment

## Best Practices

### 1. Test Placement
- Place tests in the appropriate category directory
- If unsure, prefer unit tests over integration
- Security-related tests go in `security/` even if they're unit-style

### 2. Test Markers
- All tests are automatically marked based on their directory
- Additional markers can be added:
  ```python
  @pytest.mark.slow
  @pytest.mark.unit
  def test_complex_calculation():
      pass
  ```

### 3. Test Dependencies
- Unit tests should have NO external dependencies
- Integration tests should mock external services
- Only E2E tests should use real services

### 4. Performance Considerations
- Keep unit tests under 100ms
- Mark slow tests with `@pytest.mark.slow`
- Consider test parallelization for large test suites

## Adding New Test Categories

1. Create the directory: `mkdir -p tests/new_category`
2. Add `__init__.py`: `touch tests/new_category/__init__.py`
3. Update `pytest.ini` to add the marker
4. Update CI/CD workflow if needed
5. Document the category in this file

## Troubleshooting

### Tests Not Being Discovered
- Ensure test files start with `test_`
- Check that `__init__.py` exists in all directories
- Verify pytest.ini is in the project root

### Marker Warnings
- Use `--strict-markers` to catch typos
- All markers must be defined in pytest.ini

### Coverage Issues
- Use `--cov-report=term-missing` to see uncovered lines
- Exclude test files from coverage in pytest.ini
