# CLAUDE Domain Guidelines for Emoji Smith

**Context:** This document should be loaded when working on domain entities, value objects, or business logic.

## Domain-Driven Design Principles

### Core Concepts
- **Entities**: Objects with identity that persist over time
- **Value Objects**: Immutable objects defined by their attributes
- **Aggregates**: Cluster of entities and value objects with defined boundaries
- **Repositories**: Interfaces for accessing aggregates (protocols only in domain layer)
- **Domain Services**: Stateless operations that don't belong to entities

### Layer Rules
1. **Zero Dependencies**: Domain layer imports NOTHING from other layers
2. **No Framework Code**: Pure Python only, no Django/FastAPI/etc
3. **No Infrastructure**: No database, API, or file system access
4. **Protocol Interfaces**: Use Python protocols for repository interfaces

### Example Entity
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class EmojiTemplate:
    """Reusable emoji template entity."""
    id: str
    name: str
    prompt_template: str
    created_at: datetime
    usage_count: int = 0

    def increment_usage(self) -> None:
        """Track template usage."""
        self.usage_count += 1

    def can_be_deleted(self) -> bool:
        """Business rule: only unused templates can be deleted."""
        return self.usage_count == 0
```

### Example Value Object
```python
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass(frozen=True)
class StylePreferences:
    """Immutable style preferences."""
    style: str = "cartoon"
    color_scheme: str = "vibrant"
    additional: Dict[str, Any] = field(default_factory=dict)

    def with_style(self, new_style: str) -> "StylePreferences":
        """Return new instance with updated style."""
        return StylePreferences(
            style=new_style,
            color_scheme=self.color_scheme,
            additional=self.additional
        )
```

### Example Repository Protocol
```python
from typing import Protocol, Optional, List
from domain.entities.emoji_template import EmojiTemplate

class EmojiTemplateRepository(Protocol):
    """Protocol for emoji template persistence."""

    async def get_by_id(self, template_id: str) -> Optional[EmojiTemplate]:
        """Retrieve template by ID."""
        ...

    async def list_by_usage(self, min_usage: int = 0) -> List[EmojiTemplate]:
        """List templates filtered by usage count."""
        ...

    async def save(self, template: EmojiTemplate) -> None:
        """Persist template."""
        ...
```

### Domain Service Example
```python
class EmojiPromptBuilder:
    """Domain service for building emoji prompts."""

    def build_prompt(
        self,
        template: EmojiTemplate,
        context: MessageContext,
        preferences: StylePreferences
    ) -> str:
        """Build prompt from template and context."""
        prompt = template.prompt_template.format(
            message=context.text,
            user=context.user_name
        )
        return f"{prompt} in {preferences.style} style"
```

## Common Patterns

### Factory Pattern
```python
class EmojiRequestFactory:
    """Factory for creating emoji requests."""

    @staticmethod
    def from_slack_command(command_data: Dict[str, str]) -> EmojiRequest:
        """Create request from Slack command."""
        return EmojiRequest(
            user_id=command_data["user_id"],
            description=command_data["text"],
            channel_id=command_data["channel_id"]
        )
```

### Specification Pattern
```python
class HighUsageTemplateSpec:
    """Specification for high-usage templates."""

    def __init__(self, threshold: int = 100):
        self.threshold = threshold

    def is_satisfied_by(self, template: EmojiTemplate) -> bool:
        """Check if template meets high usage criteria."""
        return template.usage_count >= self.threshold
```

## Anti-Patterns to Avoid

### ❌ Infrastructure in Domain
```python
# WRONG - Domain accessing database
class User:
    def save(self):
        db.session.add(self)  # NO!
```

### ❌ Framework Dependencies
```python
# WRONG - Domain using framework
from fastapi import HTTPException  # NO!

class Order:
    def validate(self):
        if not self.items:
            raise HTTPException(400, "Empty order")  # NO!
```

### ❌ Anemic Domain Models
```python
# WRONG - No behavior, just data
@dataclass
class Product:
    id: str
    name: str
    price: float
    # No methods, no business logic
```

### ✅ Rich Domain Models
```python
# CORRECT - Encapsulates behavior
@dataclass
class Product:
    id: str
    name: str
    price: float

    def apply_discount(self, percentage: float) -> float:
        """Apply discount with business rules."""
        if percentage > 50:
            raise ValueError("Discount cannot exceed 50%")
        return self.price * (1 - percentage / 100)
```

## Testing Domain Logic

### Focus on Business Rules
```python
def test_template_cannot_be_deleted_when_used():
    """Used templates should not be deletable."""
    template = EmojiTemplate(
        id="tmpl_123",
        name="Popular",
        prompt_template="{message} emoji",
        created_at=datetime.now(),
        usage_count=5
    )

    assert not template.can_be_deleted()
```

### Test Value Object Immutability
```python
def test_style_preferences_immutable():
    """Style preferences should not be modifiable."""
    prefs = StylePreferences(style="cartoon")
    new_prefs = prefs.with_style("realistic")

    assert prefs.style == "cartoon"  # Original unchanged
    assert new_prefs.style == "realistic"  # New instance
```

## Quick Reference

**Before writing domain code, verify:**
- [ ] No imports from infrastructure/application/presentation
- [ ] Using protocols for external dependencies
- [ ] Rich models with encapsulated behavior
- [ ] Immutable value objects
- [ ] Clear aggregate boundaries
