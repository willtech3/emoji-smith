# GitHub Issues for DDD Compliance - Emoji Smith

## Epic: DDD Architecture Compliance and Domain Model Enhancement

**Epic Description**: Achieve full Domain-Driven Design compliance by fixing architectural violations, enhancing domain models, and implementing advanced patterns to improve maintainability and testability.

**Success Criteria**:
- Zero infrastructure imports in domain/application layers
- All Lambda handlers properly placed in infrastructure layer
- Domain models enriched with appropriate business logic
- Architecture tests preventing future violations

---

## Priority 1: Critical Architecture Violations (Sprint 1)

### Issue #1: Fix Application Layer Infrastructure Import
**Type**: Bug
**Priority**: Critical
**Labels**: `architecture`, `tech-debt`, `ddd-violation`
**Estimate**: 1-2 days

**Description**:
The application layer directly imports infrastructure implementation, violating the Dependency Inversion Principle.

**Current State**:
```python
# src/emojismith/application/services/emoji_service.py:15-21
try:
    from emojismith.infrastructure.slack.slack_file_sharing import (
        SlackFileSharingRepository,
    )
except ImportError:
    SlackFileSharingRepository = None  # type: ignore
```

**Acceptance Criteria**:
- [ ] Create `FileSharingRepository` protocol in domain layer
- [ ] Move infrastructure import to composition root (app.py)
- [ ] Update `EmojiService` to accept protocol interface
- [ ] All tests pass with new abstraction
- [ ] No infrastructure imports in application layer

**Implementation Tasks**:
1. Create `src/emojismith/domain/repositories/file_sharing_repository.py`
2. Define protocol with `share_emoji()` method
3. Update `emoji_service.py` constructor to accept protocol
4. Update app factory to inject concrete implementation
5. Run tests and fix any failures

---

### Issue #2: Move Lambda Handlers to Infrastructure Layer
**Type**: Enhancement
**Priority**: High
**Labels**: `architecture`, `refactoring`, `clean-architecture`
**Estimate**: 2-3 days

**Description**:
Lambda handlers are currently at the root level, mixing infrastructure concerns with application bootstrapping.

**Files to Move**:
- `src/lambda_handler.py`
- `src/webhook_handler.py`
- `src/worker_handler.py`

**Acceptance Criteria**:
- [ ] Create `src/emojismith/infrastructure/aws/` directory structure
- [ ] Move all Lambda handlers to infrastructure layer
- [ ] Extract AWS Secrets Manager logic to separate class
- [ ] Update import paths in CDK/deployment scripts
- [ ] Deployment still works correctly

**Implementation Tasks**:
1. Create new directory structure
2. Move handler files maintaining functionality
3. Create `AWSSecretsLoader` class for secrets management
4. Update all import references
5. Test Lambda deployment locally
6. Update CDK stack with new handler paths

---

### Issue #3: Remove Environment Variable Access from Domain Service
**Type**: Bug
**Priority**: Medium
**Labels**: `architecture`, `domain-purity`, `tech-debt`
**Estimate**: 0.5-1 day

**Description**:
Domain service directly accesses environment variables, creating infrastructure coupling.

**Current Code**:
```python
# src/emojismith/domain/services/emoji_sharing_service.py
def detect_workspace_type(self) -> WorkspaceType:
    env_type = os.getenv("WORKSPACE_TYPE", "").lower()
```

**Acceptance Criteria**:
- [ ] Remove `os.getenv` from domain service
- [ ] Accept workspace type via constructor injection
- [ ] Update app factory to provide configuration
- [ ] Domain service has no environment dependencies

**Implementation Tasks**:
1. Add `workspace_type` parameter to constructor
2. Remove `detect_workspace_type()` method
3. Update app factory to read env and inject value
4. Update all service instantiations
5. Verify tests still pass

---

## Priority 2: Domain Model Enrichment (Sprint 2)

### Issue #4: Enrich Anemic Domain Models
**Type**: Enhancement
**Priority**: Medium
**Labels**: `domain-modeling`, `ddd`, `code-quality`
**Estimate**: 2-3 days

**Description**:
Several domain entities lack behavior and are too anemic, particularly `QueueMessage` and `GeneratedEmoji`.

**Acceptance Criteria**:
- [ ] `QueueMessage` has retry logic methods
- [ ] `GeneratedEmoji` has size validation behavior
- [ ] `AIPromptService` contains actual business logic
- [ ] All entities have appropriate domain methods

**Implementation Tasks**:
1. Add `should_retry()` and `with_retry()` to `QueueMessage`
2. Add `needs_resizing()` and `validate_size()` to `GeneratedEmoji`
3. Enhance `AIPromptService` with prompt building strategies
4. Add domain methods for common operations
5. Update tests for new behavior

**Code Examples**:
```python
# QueueMessage enhancements
def should_retry(self) -> bool:
    """Determine if message should be retried."""
    return self.retry_count < self.MAX_RETRIES

def with_retry(self) -> "QueueMessage":
    """Create new message with incremented retry."""
    return replace(self, retry_count=self.retry_count + 1)

# GeneratedEmoji enhancements
def needs_resizing(self) -> bool:
    """Check if emoji exceeds Slack size limits."""
    return len(self.image_data) > self.MAX_SIZE

def validate_format(self) -> bool:
    """Validate emoji format is acceptable."""
    return self.format in ['png', 'gif', 'jpg']
```

---

### Issue #5: Implement Domain Events
**Type**: Feature
**Priority**: Medium
**Labels**: `domain-events`, `ddd`, `architecture`
**Estimate**: 2 days

**Description**:
Implement domain events for better decoupling between bounded contexts and to capture important business moments.

**Acceptance Criteria**:
- [ ] Create base `DomainEvent` class
- [ ] Implement key events (EmojiCreated, EmojiShared, GenerationFailed)
- [ ] Add event publishing to domain services
- [ ] Create event handler infrastructure
- [ ] Document event flow

**Implementation Tasks**:
1. Create `src/shared/domain/events/` directory
2. Define base `DomainEvent` with timestamp and correlation ID
3. Create specific event classes
4. Add event collection to aggregates
5. Implement event dispatcher pattern

**Code Example**:
```python
@dataclass(frozen=True)
class EmojiCreatedEvent(DomainEvent):
    emoji_id: str
    workspace_id: str
    created_by: str
    style: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
```

---

## Priority 3: Testing and Quality Assurance (Sprint 2-3)

### Issue #6: Implement Architecture Fitness Functions
**Type**: Feature
**Priority**: Medium
**Labels**: `testing`, `architecture`, `ci-cd`
**Estimate**: 2 days

**Description**:
Add automated tests to prevent future architecture violations and maintain DDD principles.

**Acceptance Criteria**:
- [ ] Architecture tests for layer dependencies
- [ ] Pre-commit hooks for violation detection
- [ ] CI/CD integration with architecture checks
- [ ] Documentation of architecture rules

**Implementation Tasks**:
1. Create `tests/architecture/` directory
2. Write tests for dependency rules
3. Add pre-commit configuration
4. Update GitHub Actions workflow
5. Create architecture decision records (ADRs)

**Test Examples**:
```python
def test_no_infrastructure_imports_in_domain():
    """Domain should not import from infrastructure."""
    domain_files = Path("src/emojismith/domain").rglob("*.py")
    for file in domain_files:
        content = file.read_text()
        assert "from emojismith.infrastructure" not in content

def test_application_imports_only_domain():
    """Application should only import from domain."""
    app_files = Path("src/emojismith/application").rglob("*.py")
    for file in app_files:
        content = file.read_text()
        assert "from emojismith.infrastructure" not in content
```

---

## Priority 4: Advanced Patterns (Sprint 3)

### Issue #7: Implement CQRS for Webhook Processing
**Type**: Feature
**Priority**: Low
**Labels**: `cqrs`, `architecture`, `enhancement`
**Estimate**: 2 days

**Description**:
Implement Command Query Responsibility Segregation for cleaner webhook processing.

**Acceptance Criteria**:
- [ ] Separate command and query interfaces
- [ ] Command handlers for emoji creation
- [ ] Query handlers for status checks
- [ ] Clear separation of read/write models

**Implementation Tasks**:
1. Create command classes (CreateEmojiCommand, ShareEmojiCommand)
2. Create command handler interface
3. Implement command handlers
4. Create query interfaces
5. Refactor webhook handler to use CQRS

---

### Issue #8: Add Event-Driven Communication Between Contexts
**Type**: Feature
**Priority**: Low
**Labels**: `event-driven`, `architecture`, `bounded-contexts`
**Estimate**: 3 days

**Description**:
Implement event-driven communication to reduce coupling between bounded contexts.

**Acceptance Criteria**:
- [ ] Event bus abstraction in shared kernel
- [ ] Webhook context publishes events
- [ ] Emoji context subscribes to relevant events
- [ ] Asynchronous event handling
- [ ] Event store for audit trail

**Implementation Tasks**:
1. Create event bus protocol
2. Implement in-memory event bus for testing
3. Implement SQS-based event bus for production
4. Add event publishers to webhook handlers
5. Add event subscribers to emoji services

---

## Monitoring and Metrics

### Issue #9: Architecture Metrics Dashboard
**Type**: Feature
**Priority**: Low
**Labels**: `monitoring`, `metrics`, `architecture`
**Estimate**: 1 day

**Description**:
Create dashboard to track architecture health metrics.

**Metrics to Track**:
- Infrastructure imports in domain/application (target: 0)
- Domain model richness score (target: 90%)
- Test coverage by layer
- Architecture test pass rate
- Technical debt trends

---

## Definition of Done for Epic

- [ ] All critical and high priority issues completed
- [ ] Zero architecture violations in automated checks
- [ ] Domain models have appropriate business logic (>90% richness score)
- [ ] Architecture tests integrated into CI/CD pipeline
- [ ] Documentation updated with new patterns
- [ ] Team trained on DDD principles and new patterns
- [ ] Deployment scripts updated and tested

---

## Issue Creation Script

```bash
# Create epic
gh issue create \
  --title "Epic: DDD Architecture Compliance and Domain Model Enhancement" \
  --body "See full epic description in docs/github_issues_ddd_compliance.md" \
  --label "epic,architecture,ddd" \
  --milestone "DDD Compliance"

# Create individual issues with epic reference
# Add epic number to each issue body as "Part of #EPIC_NUMBER"
```
