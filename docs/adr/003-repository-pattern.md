# ADR-003: Repository Pattern with Python Protocols

## Status
Accepted

## Context
We need to abstract external service dependencies (Slack, OpenAI, AWS) to:
- Enable unit testing without real API calls
- Support switching providers (e.g., OpenAI to Anthropic)
- Keep domain logic free of infrastructure concerns
- Provide clear contracts for external integrations

Python offers several approaches:
- Abstract Base Classes (ABC)
- Duck typing
- Protocols (PEP 544)

## Decision
Use Python Protocols for repository interfaces:

```python
from typing import Protocol

class EmojiRepository(Protocol):
    """Repository for emoji storage."""

    async def save(self, emoji: Emoji) -> None:
        """Save emoji to storage."""
        ...

    async def get_by_name(self, name: str) -> Optional[Emoji]:
        """Retrieve emoji by name."""
        ...
```

Rationale for Protocols over ABCs:
1. No inheritance required (structural subtyping)
2. Better for testing (any object matching interface works)
3. More Pythonic (duck typing with type safety)
4. No runtime overhead

## Consequences

### Positive
- Clear separation between interface and implementation
- Easy to create test doubles
- Type checker validates interface compliance
- Can gradually type existing code
- Multiple implementations possible (S3, local, etc.)

### Negative
- Requires Python 3.8+ (not an issue with 3.12)
- Less explicit than ABC (no forced implementation)
- IDEs may have weaker support than ABC

### Mitigation
- Use mypy in strict mode to catch protocol violations
- Document expected behavior in protocol docstrings
- Provide reference implementations

## Implementation Examples

### Domain Layer (Protocol Definition)
```python
# src/domain/repositories/slack_repository.py
from typing import Protocol

class SlackRepository(Protocol):
    """Repository for Slack operations."""

    async def open_modal(self, trigger_id: str, view: dict) -> None:
        """Open a modal dialog."""
        ...

    async def upload_emoji(self, name: str, image: bytes) -> str:
        """Upload custom emoji to workspace."""
        ...

    async def add_reaction(
        self,
        emoji: str,
        channel: str,
        timestamp: str
    ) -> None:
        """Add emoji reaction to message."""
        ...
```

### Infrastructure Layer (Implementation)
```python
# src/infrastructure/slack/slack_api_repository.py
from slack_sdk.web.async_client import AsyncWebClient
from domain.repositories.slack_repository import SlackRepository

class SlackAPIRepository:
    """Slack API implementation of SlackRepository."""

    def __init__(self, client: AsyncWebClient):
        self._client = client

    async def open_modal(self, trigger_id: str, view: dict) -> None:
        await self._client.views_open(
            trigger_id=trigger_id,
            view=view
        )

    # ... other methods
```

### Testing (Mock Implementation)
```python
# tests/mocks/mock_slack_repository.py
from unittest.mock import AsyncMock

class MockSlackRepository:
    """Test double for SlackRepository."""

    def __init__(self):
        self.open_modal = AsyncMock()
        self.upload_emoji = AsyncMock(return_value="emoji_url")
        self.add_reaction = AsyncMock()
```

### Dependency Injection
```python
# src/application/services/emoji_service.py
class EmojiCreationService:
    def __init__(
        self,
        slack_repo: SlackRepository,  # Protocol type
        openai_repo: OpenAIRepository,  # Protocol type
    ):
        self._slack = slack_repo
        self._openai = openai_repo
```

## Best Practices

1. **Keep protocols minimal** - Only required methods
2. **Use async methods** - Consistency across I/O operations
3. **Document behavior** - Protocols define structure, not behavior
4. **One protocol per concern** - Don't create mega-interfaces

## Alternatives Considered

1. **Abstract Base Classes**
   - More explicit but requires inheritance
   - Rejected for less flexibility

2. **Duck typing only**
   - No type safety
   - Rejected for lack of IDE support

3. **Dependency injection framework**
   - Too heavyweight for our needs
   - Rejected for added complexity

## References
- PEP 544 - Protocols: Structural subtyping
- Python typing documentation
- "Clean Architecture" by Robert C. Martin
