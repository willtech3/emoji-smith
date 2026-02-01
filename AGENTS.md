# AGENTS.md - Emoji Smith AI Coding Agent Guidelines

> **Purpose:** This file provides comprehensive guidance for AI coding agents (like Google Jules) to understand and work effectively with this codebase.

## 📋 Project Overview

**Emoji Smith** is an AI-powered Slack bot that generates custom emojis using multiple AI providers (OpenAI + Google). It uses Domain-Driven Design (DDD) with a layered architecture deployed on **GCP Cloud Run**.

## 🛠️ Development Setup

```bash
# Activate virtual environment
source .venv/bin/activate

# Install all dependencies
uv sync --all-extras
# OR
pip install -e ".[dev]"

# Run quality checks
just qa
# OR manually:
ruff format src/ tests/ && ruff check src/ tests/ && mypy src/ && pytest tests/
```

## 🚨 CRITICAL RULES - NEVER VIOLATE

1. **🔐 NEVER commit secrets** - No API keys, tokens, or `.env` files
2. **📁 NEVER use `git add .`** - Always specify files explicitly
3. **🐍 ALWAYS activate venv first** - `source .venv/bin/activate`
4. **🧪 ALWAYS write tests first** - TDD is mandatory
5. **💉 ALWAYS use dependency injection** - No hardcoded dependencies
6. **🚀 ALWAYS use CI for deployment** - Never deploy manually
7. **🌿 ALWAYS use feature branches** - Never commit directly to main
8. **🔄 ALWAYS create pull requests** - All changes go through PR review

## 🏗️ Architecture

### Fixed Production Entry Points (GCP)
```
src/emojismith/infrastructure/gcp/webhook_app.py  # < 3s response (Slack)
src/emojismith/infrastructure/gcp/worker_app.py   # async processing (Pub/Sub)
```

### Layer Dependencies (One Direction Only)
```
Domain ← Application ← Infrastructure ← Presentation
(Pure)   (Use Cases)   (External)      (UI/API)
```

### Directory Structure
```
src/
├── domain/           # Zero dependencies, pure Python only
├── application/      # Orchestrates domain objects
├── infrastructure/   # External world (GCP, Slack, OpenAI, Gemini)
└── presentation/     # HTTP/API endpoints

tests/
├── unit/             # Fast, isolated tests by layer
├── integration/      # Tests with real dependencies
└── fixtures/         # Shared test data
```

### Architecture Red Flags
- ❌ Importing cloud provider SDKs in domain/
- ❌ Direct `os.environ` access outside config
- ❌ Concrete classes in domain/repositories/
- ❌ Missing `__init__.py` files
- ❌ Tests that only test mocks
- ❌ Working directly on main branch

---

## 🔐 Security Guidelines

### Secret Management
```python
# ❌ WRONG - Never hardcode secrets
API_KEY = "sk-1234567890abcdef"

# ✅ CORRECT - Load from environment
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY required")
```

### Git Security
```bash
# ✅ CORRECT - Explicit file specification
git add src/emojismith/new_feature.py tests/unit/test_new_feature.py

# ❌ WRONG - Could commit secrets
git add .
git add -A
```

### Input Validation
- Sanitize all user input before processing
- Limit input lengths (max 500 chars for descriptions)
- Remove potential injection characters
- Validate file uploads (type, size, content)

### GCP Security
- Use least-privilege IAM for Cloud Run and Pub/Sub service accounts
- Store secrets in GCP Secret Manager and inject them into Cloud Run as env vars
- Keep worker endpoints private/protected (Pub/Sub push with OIDC)

---

## 📐 Domain Layer Guidelines

### Core Principles
- **Zero Dependencies**: Domain layer imports NOTHING from other layers
- **No Framework Code**: Pure Python only (no Django/FastAPI/etc)
- **No Infrastructure**: No database, API, or file system access
- **Protocol Interfaces**: Use Python protocols for repository interfaces

### Domain Patterns

**Entities** - Objects with identity:
```python
@dataclass
class EmojiTemplate:
    id: str
    name: str
    prompt_template: str
    usage_count: int = 0

    def increment_usage(self) -> None:
        self.usage_count += 1
```

**Value Objects** - Immutable, defined by attributes:
```python
@dataclass(frozen=True)
class StylePreferences:
    style: str = "cartoon"
    color_scheme: str = "vibrant"

    def with_style(self, new_style: str) -> "StylePreferences":
        return StylePreferences(style=new_style, color_scheme=self.color_scheme)
```

**Repository Protocols** - Interfaces only in domain:
```python
class EmojiTemplateRepository(Protocol):
    async def get_by_id(self, template_id: str) -> Optional[EmojiTemplate]: ...
    async def save(self, template: EmojiTemplate) -> None: ...
```

### Anti-Patterns to AVOID
```python
# ❌ WRONG - Infrastructure in domain
class User:
    def save(self):
        db.session.add(self)  # NO!

# ❌ WRONG - Anemic models (no behavior)
@dataclass
class Product:
    id: str
    price: float
    # No methods, no business logic

# ✅ CORRECT - Rich models with behavior
@dataclass
class Product:
    id: str
    price: float

    def apply_discount(self, percentage: float) -> float:
        if percentage > 50:
            raise ValueError("Discount cannot exceed 50%")
        return self.price * (1 - percentage / 100)
```

---

## 🔧 Infrastructure Layer Guidelines

### Responsibilities
- GCP service integration (Cloud Run, Pub/Sub, Secret Manager)
- External API clients (Slack, OpenAI, Google Gemini)
- Repository implementations
- Configuration management

### Key Patterns

**Repository Implementation:**
```python
class ExternalEmojiTemplateRepository:
    """Infrastructure repository implementation (example pattern)."""

    def __init__(self, client):
        self._client = client  # injected dependency

    async def get_by_id(self, template_id: str) -> Optional[EmojiTemplate]:
        item = await self._client.get(template_id)
        if not item:
            return None
        return self._deserialize(item)
```

**Error Handling with Retries:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def call_external_api(self, data: dict) -> dict:
    response = await self._client.post("/api/endpoint", json=data)
    if response.status_code >= 500:
        raise TemporaryError("Server error")
    return response.json()
```

**Cloud Run Handler Pattern (FastAPI):**
```python
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/slack/events")
async def slack_events(request: Request) -> dict:
    body = await request.body()
    headers = dict(request.headers)
    # Validate Slack signature, enqueue to Pub/Sub, respond quickly (< 3s)
    return {"status": "ok"}
```

---

## 🧪 Testing Guidelines

### Core Principles
1. **Test behavior, not implementation**
2. **Test public interfaces only**
3. **Use Arrange-Act-Assert pattern**
4. **TDD is mandatory** - write failing test first

### Coverage Targets
| Layer | Target | Rationale |
|-------|--------|-----------|
| Domain | 90% | Core business logic |
| Application | 85% | Use case orchestration |
| Infrastructure | 70% | External dependencies |
| Overall | 80% | Project baseline |

### Mock Usage

**When to Mock:**
- External APIs (Slack, OpenAI, Gemini)
- GCP services (Pub/Sub publisher, Cloud Run HTTP calls, Secret Manager)
- File system operations
- Time-dependent operations

**When NOT to Mock:**
- Domain entities
- Value objects
- Pure functions
- Data transformations

### Red Flag: Mock-Only Tests
```python
# ❌ DELETE THIS - provides no value
def test_calls_repository():
    mock_repo = Mock()
    service = Service(mock_repo)
    service.do_something()
    mock_repo.method.assert_called_once()

# ✅ KEEP - tests actual behavior
def test_enriches_data_before_saving():
    mock_repo = Mock()
    service = Service(mock_repo)
    service.process_user_data({"name": "John"})
    saved_data = mock_repo.save.call_args[0][0]
    assert saved_data["name"] == "John"
    assert "processed_at" in saved_data
```

### Test Commands
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src/emojismith tests/

# Run specific layer
pytest tests/unit/domain/

# Run linting
ruff check src/ tests/
```

---

## 🚀 CI/CD & Deployment

### Golden Rule
**All deployments happen through CI/CD. Manual deployments are forbidden.**

### Dual Service Architecture
```
Slack → Cloud Run (webhook, < 3s) → Pub/Sub → Cloud Run (worker, async)
```

### Workflow
```bash
# 1. Create feature branch
git checkout -b feature/your-feature

# 2. Make changes, write tests
# 3. Run quality checks
just qa

# 4. Commit specific files
git add src/file.py tests/test_file.py
git commit -m "feat(scope): description"

# 5. Push and create PR
git push origin feature/your-feature
gh pr create --title "feat: description"

# 6. CI/CD handles deployment after merge
```

### Terraform Commands (Infrastructure Changes)
```bash
# Terraform lives in terraform/
terraform plan
terraform apply
```

### Rollback
```bash
git revert HEAD
git push origin main
# CI/CD will deploy previous version
```

---

## 🧠 Quick Reference

### Before ANY Task
- [ ] Virtual environment active? (`echo $VIRTUAL_ENV`)
- [ ] On feature branch? (`git branch` - NOT main)
- [ ] Latest changes pulled?
- [ ] Failing test written?
- [ ] Correct architecture layer?

### Before ANY Commit
```bash
ruff format src/ tests/
ruff check src/ tests/
mypy src/
pytest tests/
git add <specific-files>
git commit -m "type(scope): description"
```

### Memory Aid: E.M.O.J.I.S.
- **E**nvironment activated
- **M**ock external services only  
- **O**rchestrate in application layer
- **J**ust domain logic in domain/
- **I**nject all dependencies
- **S**peak about changes

---

## 📚 Additional Documentation

- `docs/` - Feature specifications and migration guides
- `terraform/` - GCP infrastructure as code
- `pyproject.toml` - Project configuration and dependencies
- `justfile` - Common development commands
