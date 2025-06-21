# Testing Guidelines for Emoji Smith

This document outlines testing best practices derived from our comprehensive test review and ongoing development experience.

## Table of Contents
- [Testing Philosophy](#testing-philosophy)
- [Test Quality Standards](#test-quality-standards)
- [Mock Usage Guidelines](#mock-usage-guidelines)
- [Coverage Requirements](#coverage-requirements)
- [Test Organization](#test-organization)
- [Common Anti-Patterns](#common-anti-patterns)
- [Best Practices by Layer](#best-practices-by-layer)

## Testing Philosophy

### Core Principles
1. **Test behavior, not implementation** - Focus on what the code does, not how it does it
2. **Test public interfaces only** - Private methods are tested through public ones
3. **Use descriptive test names** - Test names should describe the scenario and expected outcome
4. **Arrange-Act-Assert pattern** - Keep tests organized and readable

### Test Pyramid
```
         /\
        /  \    E2E Tests (Few)
       /    \
      /------\  Integration Tests (Some)
     /        \
    /----------\ Unit Tests (Many)
```

## Test Quality Standards

### High-Quality Test Characteristics
- **Clear intent**: The test name and implementation clearly express what is being tested
- **Focused**: Each test verifies one specific behavior
- **Deterministic**: Tests produce consistent results
- **Fast**: Unit tests should run in milliseconds
- **Independent**: Tests don't depend on execution order

### Example of a Good Test
```python
async def test_generate_emoji_includes_message_context_in_prompt(
    self, emoji_generator, mock_ai_client
):
    """Generated emoji should incorporate the original message context."""
    # Arrange
    request = EmojiRequest(
        message_text="Just deployed on Friday",
        user_description="facepalm reaction",
        style_preferences={"style": "cartoon"}
    )

    # Act
    await emoji_generator.generate_emoji(request)

    # Assert
    mock_ai_client.generate_image.assert_called_once()
    prompt = mock_ai_client.generate_image.call_args[0][0]
    assert "Just deployed on Friday" in prompt
    assert "facepalm" in prompt
```

## Mock Usage Guidelines

### When to Mock
| What to Mock | Reason |
|--------------|--------|
| External APIs (Slack, OpenAI) | Avoid network calls, ensure deterministic behavior |
| AWS services (S3, SQS) | Prevent AWS costs and dependencies |
| File system operations | Maintain test isolation |
| Time-dependent operations | Control time for predictable tests |

### When NOT to Mock
| What NOT to Mock | Reason |
|------------------|--------|
| Domain entities | Core business logic should be tested directly |
| Value objects | Immutable and contain business rules |
| Pure functions | No side effects, test actual behavior |
| Data structures | Test real transformations |

### Red Flag: Mock-Only Tests
If a test only contains mocks and assertions on those mocks, **delete it**. These tests provide no value:

```python
# ❌ BAD - Mock-only test
def test_calls_repository():
    mock_repo = Mock()
    service = Service(mock_repo)
    service.do_something()
    mock_repo.method.assert_called_once()  # Only tests that mock was called

# ✅ GOOD - Tests actual behavior
def test_enriches_data_before_saving():
    mock_repo = Mock()
    service = Service(mock_repo)

    service.process_user_data({"name": "John"})

    saved_data = mock_repo.save.call_args[0][0]
    assert saved_data["name"] == "John"
    assert "processed_at" in saved_data  # Verifies enrichment logic
```

## Coverage Requirements

### By Layer
| Layer | Minimum Coverage | Rationale |
|-------|------------------|-----------|
| Domain | 90% | Core business logic must be thoroughly tested |
| Application | 85% | Use case orchestration needs high confidence |
| Infrastructure | 70% | External dependencies make 100% impractical |
| Overall | 80% | Enforced by CI pipeline |

### Coverage Guidelines
- **Focus on behavior coverage**, not line coverage
- **Don't chase 100%** - Some code (like simple getters) doesn't need tests
- **Prioritize critical paths** - Payment processing, security, core features
- **Test edge cases** - Null values, empty collections, boundary conditions

## Test Organization

### Directory Structure
```
tests/
├── unit/                    # Fast, isolated tests
│   ├── domain/             # Business logic tests
│   ├── application/        # Use case tests
│   └── infrastructure/     # Repository tests with mocks
├── integration/            # Tests with real dependencies
│   ├── test_dual_lambda_e2e.py
│   └── test_slack_integration.py
└── fixtures/              # Shared test data
    ├── slack_payloads.py
    └── sample_images.py
```

### Naming Conventions
- Test files: `test_<module_name>.py`
- Test classes: `Test<ClassName>`
- Test methods: `test_<scenario>_<expected_outcome>`

## Common Anti-Patterns

### 1. Testing Implementation Details
```python
# ❌ BAD - Tests private method
def test_private_calculation():
    calculator = Calculator()
    result = calculator._internal_method(5)
    assert result == 10

# ✅ GOOD - Tests through public interface
def test_calculates_total_with_tax():
    calculator = Calculator()
    result = calculator.calculate_total(100, tax_rate=0.1)
    assert result == 110
```

### 2. Overly Complex Test Setup
```python
# ❌ BAD - Too much setup obscures test intent
def test_complex_scenario():
    # 50 lines of setup...

# ✅ GOOD - Extract to fixtures or builders
@pytest.fixture
def configured_service():
    return ServiceBuilder().with_default_config().build()

def test_simple_scenario(configured_service):
    result = configured_service.process("data")
    assert result.status == "success"
```

### 3. Multiple Assertions per Test
```python
# ❌ BAD - Tests multiple behaviors
def test_user_creation():
    user = create_user("John", "john@example.com")
    assert user.name == "John"
    assert user.email == "john@example.com"
    assert user.is_active == True
    assert user.created_at is not None

# ✅ GOOD - Separate tests for each behavior
def test_user_creation_sets_name():
    user = create_user("John", "john@example.com")
    assert user.name == "John"

def test_user_creation_activates_by_default():
    user = create_user("John", "john@example.com")
    assert user.is_active == True
```

## Best Practices by Layer

### Domain Layer Tests
- Test business rules and invariants
- Use real domain objects, not mocks
- Verify state transitions
- Test edge cases and validation

### Application Layer Tests
- Test use case orchestration
- Mock infrastructure dependencies
- Verify correct delegation to domain services
- Test error handling and compensation

### Infrastructure Layer Tests
- Mock external services (AWS, APIs)
- Test data mapping and transformation
- Verify error handling and retries
- Test configuration and initialization

### Integration Tests
- Test actual integration points
- Use test doubles for external services when needed
- Verify end-to-end workflows
- Keep these minimal and focused
- Slack integration tests require a dedicated workspace. Set `SLACK_TEST_BOT_TOKEN`,
  `SLACK_TEST_CHANNEL_ID` and `SLACK_TEST_USER_ID` environment variables or the
  tests will be skipped.

## Testing Async Code

### Best Practices
```python
# Use pytest-asyncio
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
    assert result == expected

# Mock async dependencies
mock_client = AsyncMock()
mock_client.fetch_data.return_value = {"status": "ok"}

# Test concurrent operations
results = await asyncio.gather(
    service.process_item(1),
    service.process_item(2),
    service.process_item(3)
)
```

## Performance Testing Considerations

### Response Time Requirements
- Webhook handlers: < 3 seconds (Slack timeout)
- Background jobs: Reasonable for user experience
- Unit tests: < 100ms per test
- Integration tests: < 5s per test

### Load Testing
- Use tools like locust for API endpoints
- Test with realistic data volumes
- Monitor memory usage in long-running processes

## Continuous Improvement

### Regular Test Review
1. **Quarterly test audit** - Review test quality and coverage
2. **Remove obsolete tests** - Delete tests for removed features
3. **Refactor test code** - Apply same quality standards as production code
4. **Update test data** - Keep fixtures relevant and minimal

### Test Metrics to Track
- Coverage percentage by layer
- Test execution time
- Flaky test frequency
- Tests per feature

## Conclusion

Good tests are an investment in code quality and team productivity. They should:
- Give confidence when refactoring
- Document system behavior
- Catch regressions early
- Run quickly and reliably

Remember: **If a test doesn't make you more confident in your code, it's not a good test.**
