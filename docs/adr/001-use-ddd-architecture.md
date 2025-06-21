# ADR-001: Use Domain-Driven Design Architecture

## Status
Accepted

## Context
Emoji Smith needs a maintainable architecture that:
- Separates business logic from infrastructure concerns
- Enables easy testing without external dependencies
- Allows swapping implementations (e.g., OpenAI to Anthropic)
- Scales with growing feature complexity

## Decision
We will use Domain-Driven Design (DDD) with clean architecture layers:

1. **Domain Layer** - Pure business logic, zero external dependencies
2. **Application Layer** - Use case orchestration
3. **Infrastructure Layer** - External service implementations
4. **Presentation Layer** - User interfaces (HTTP, CLI, etc.)

Key patterns:
- Repository pattern with Protocol interfaces
- Dependency injection throughout
- Value objects for immutable domain concepts
- Domain services for business logic that spans entities

## Consequences

### Positive
- Business logic is isolated and easily testable
- External services can be swapped without touching domain code
- Clear boundaries prevent architectural drift
- New developers understand where code belongs

### Negative
- More initial boilerplate (interfaces, implementations)
- Requires discipline to maintain layer boundaries
- Can feel over-engineered for simple features

### Mitigation
- Provide clear examples in documentation
- Use code generation for boilerplate where possible
- Regular architecture reviews to ensure compliance

## Examples

```python
# Domain layer - pure business logic
@dataclass(frozen=True)
class EmojiSpecification:
    description: str
    style: StylePreferences

# Domain repository interface
class EmojiRepository(Protocol):
    async def save(self, emoji: Emoji) -> None: ...

# Infrastructure implementation
class S3EmojiRepository:
    def __init__(self, s3_client: S3Client):
        self._s3 = s3_client

    async def save(self, emoji: Emoji) -> None:
        # S3-specific implementation
```

## References
- Eric Evans: Domain-Driven Design (2003)
- Clean Architecture by Robert C. Martin
- Dependency Injection Principles, Practices, and Patterns
