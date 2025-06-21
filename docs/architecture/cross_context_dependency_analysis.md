# Cross-Context Dependency Analysis

## Summary of Findings

### ✅ Positive Findings

1. **No Direct Cross-Context Imports**: The `webhook` context does not import from `emojismith` context, and `emojismith` context does not import from `webhook` context. This maintains proper bounded context independence.

2. **Shared Domain Layer**: Both contexts correctly use a shared domain layer (`src/shared/`) for common entities and value objects:
   - `SlackMessage` entity
   - `EmojiGenerationJob` entity
   - `EmojiStylePreferences` and `EmojiSharingPreferences` value objects
   - Repository interfaces (`SlackModalRepository`, `JobQueueProducer`)

3. **Proper Use of Protocols**: The `emojismith` context uses protocol/interface pattern for signature validation, avoiding direct dependency on webhook infrastructure.

4. **Anti-Corruption Layers**: The shared domain entities act as anti-corruption layers between contexts, providing clean data transfer objects.

### ❌ Architecture Violations

1. **Infrastructure Import in Application Layer**:
   - **File**: `src/emojismith/application/services/emoji_service.py`
   - **Violation**: Lines 16-22 import `SlackFileSharingRepository` directly from infrastructure
   ```python
   try:
       from emojismith.infrastructure.slack.slack_file_sharing import (
           SlackFileSharingRepository,
       )
   except ImportError:
       # For tests when aiohttp is not available
       SlackFileSharingRepository = None  # type: ignore
   ```
   - **Impact**: This violates the Dependency Inversion Principle and makes the application layer dependent on infrastructure details.

2. **Duplicate WebhookRequest Value Objects**:
   - `src/emojismith/domain/value_objects/webhook_request.py`
   - `src/webhook/domain/webhook_request.py`
   - **Issue**: Having duplicate value objects in different contexts could lead to confusion and maintenance issues.

### 🔍 Detailed Analysis

#### 1. Shared Domain Entities Usage

Both contexts properly use shared domain entities for communication:

**Webhook Context** creates `EmojiGenerationJob`:
```python
# webhook/handler.py
job = EmojiGenerationJob.create_new(
    user_description=description,
    message_text=metadata["message_text"],
    # ... other fields
)
await self._job_queue.enqueue_job(job)
```

**Emojismith Context** consumes `EmojiGenerationJob`:
```python
# emojismith/application/services/emoji_service.py
async def process_emoji_generation_job(self, job: EmojiGenerationJob) -> None:
    # Process the job
```

#### 2. Repository Pattern Implementation

Both contexts correctly use repository interfaces from the shared domain:

**Shared Repository Interfaces**:
- `shared/domain/repositories/slack_repository.py`
- `shared/domain/repositories/job_queue_repository.py`

**Infrastructure Implementations**:
- `webhook/infrastructure/slack_api.py` implements `SlackModalRepository`
- `webhook/infrastructure/sqs_job_queue.py` implements `JobQueueProducer`
- `emojismith/infrastructure/slack/slack_api.py` implements `SlackRepository`
- `emojismith/infrastructure/jobs/sqs_job_queue.py` implements `JobQueueRepository`

## Recommendations

### 1. Fix Infrastructure Import Violation

Create a repository interface for file sharing in the domain layer:

```python
# src/emojismith/domain/repositories/file_sharing_repository.py
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass
from emojismith.domain.entities.generated_emoji import GeneratedEmoji
from shared.domain.value_objects import EmojiSharingPreferences

@dataclass
class FileSharingResult:
    success: bool
    thread_ts: Optional[str] = None
    file_url: Optional[str] = None
    error: Optional[str] = None

class FileSharingRepository(ABC):
    @abstractmethod
    async def share_emoji_file(
        self,
        emoji: GeneratedEmoji,
        channel_id: str,
        preferences: EmojiSharingPreferences,
        requester_user_id: str,
        original_message_ts: str,
    ) -> FileSharingResult:
        """Share emoji as a file with instructions."""
        pass
```

Then update the application service to use the interface:
```python
# src/emojismith/application/services/emoji_service.py
from emojismith.domain.repositories.file_sharing_repository import FileSharingRepository

class EmojiCreationService:
    def __init__(
        self,
        slack_repo: SlackRepository,
        emoji_generator: EmojiGenerationService,
        job_queue: Optional[JobQueueRepository] = None,
        file_sharing_repo: Optional[FileSharingRepository] = None,  # Use interface
        sharing_service: Optional[EmojiSharingService] = None,
    ) -> None:
        # ...
```

### 2. Consolidate WebhookRequest Value Objects

Consider moving the `WebhookRequest` value object to the shared domain if both contexts need it, or keep it only in the context where it's actually used.

### 3. Document Bounded Context Boundaries

Create clear documentation about:
- What belongs in each bounded context
- What should be in the shared domain
- How contexts communicate (through shared domain entities)
- Anti-corruption layer patterns being used

### 4. Strengthen Anti-Corruption Layers

Consider creating explicit anti-corruption layer classes that translate between external API payloads and domain entities, rather than having direct conversions in handlers.

## Conclusion

The architecture generally follows good bounded context separation with no direct cross-context imports. The main violation is the infrastructure import in the application layer, which should be fixed by introducing a proper repository interface. The shared domain layer serves well as an anti-corruption layer between contexts, facilitating clean communication through well-defined domain entities.
