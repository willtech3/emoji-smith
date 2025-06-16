# Claude Development Guidelines for Emoji Smith

## Project Overview
Emoji Smith is a Slack bot that generates custom emojis using AI based on message context and user descriptions. It uses a modal dialog flow for enhanced user experience and deploys as a serverless Lambda function.

## Development Environment & Tooling

### Python Environment
- **Python Version**: 3.12
- **Package Manager**: `uv` for fast dependency management
- **Virtual Environment**: `.venv` directory (excluded from git)

### Code Quality Tools
- **Formatter**: `black` - PEP 8 compliant code formatting
- **Linter**: `flake8` - code style and error checking
- **Type Checker**: `mypy` - static type analysis
- **Security Scanner**: `bandit` - SAST security analysis
- **Testing**: `pytest` with coverage reporting

### Development Commands
```bash
# Environment setup
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv pip install -r requirements-dev.lock

# CRITICAL: Always activate virtual environment before any commands
source .venv/bin/activate  # Must be activated for correct Python version (3.12)

# Code quality checks (run before committing)
black --check src/ tests/
flake8 src/ tests/
mypy src/
bandit -r src/
pytest --cov=src tests/

# Local development
python -m src.emojismith.dev_server  # Local FastAPI server for testing
```

## Code Style Guidelines

### Python Style (Idiomatic Python)
- Follow PEP 8 conventions (enforced by black)
- Use type hints for all function signatures and class attributes
- Prefer dataclasses for simple data containers
- Use context managers for resource management
- Leverage Python's built-in functions and libraries
- Use list/dict comprehensions where they improve readability
- Follow naming conventions: `snake_case` for functions/variables, `PascalCase` for classes

### Example Code Patterns
```python
from dataclasses import dataclass
from typing import Optional, Dict, Any
import logging

@dataclass
class EmojiRequest:
    message_text: str
    user_description: str
    style_preferences: Dict[str, Any]
    user_id: str

class EmojiGenerator:
    def __init__(self, ai_client: AIClient) -> None:
        self._ai_client = ai_client
        self._logger = logging.getLogger(__name__)

    async def generate_emoji(self, request: EmojiRequest) -> EmojiResult:
        """Generate emoji based on message context and user preferences."""
        try:
            # Implementation details...
            pass
        except Exception as e:
            self._logger.error(f"Failed to generate emoji: {e}")
            raise EmojiGenerationError(f"Generation failed: {e}") from e
```

## Test-Driven Development (TDD)

### Testing Philosophy
- **Test behavior, not implementation** - Focus on public interfaces and contracts
- **Red-Green-Refactor cycle** - Write failing test, make it pass, refactor
- **Test pyramid** - More unit tests, fewer integration tests, minimal E2E tests
- **Fast feedback** - Tests should run quickly and provide clear failure messages

### Test Structure
```
tests/
├── unit/                    # Fast, isolated unit tests
│   ├── test_emoji_generator.py
│   ├── test_slack_handlers.py
│   └── test_ai_integration.py
├── integration/            # Tests with external dependencies
│   ├── test_slack_api.py
│   └── test_webhook_flow.py
└── fixtures/               # Test data and mocks
    ├── slack_payloads.py
    └── mock_responses.py
```

### Testing Guidelines
- Test public interfaces and behaviors, not private methods
- Use descriptive test names: `test_emoji_generation_includes_user_style_preferences`
- Use pytest fixtures for reusable test data
- Mock external dependencies (Slack API, AI services)
- Assert on outcomes, not implementation details
- Test edge cases and error conditions

### Example Test Patterns
```python
import pytest
from unittest.mock import Mock, AsyncMock
from src.emojismith.emoji_generator import EmojiGenerator, EmojiRequest

class TestEmojiGenerator:
    @pytest.fixture
    def mock_ai_client(self):
        return AsyncMock()

    @pytest.fixture
    def emoji_generator(self, mock_ai_client):
        return EmojiGenerator(mock_ai_client)

    async def test_generate_emoji_includes_message_context_in_prompt(
        self, emoji_generator, mock_ai_client
    ):
        # Arrange
        request = EmojiRequest(
            message_text="Just deployed on Friday",
            user_description="facepalm reaction",
            style_preferences={"style": "cartoon"},
            user_id="U123456"
        )

        # Act
        await emoji_generator.generate_emoji(request)

        # Assert
        mock_ai_client.generate_image.assert_called_once()
        call_args = mock_ai_client.generate_image.call_args
        prompt = call_args[0][0]
        assert "Just deployed on Friday" in prompt
        assert "facepalm" in prompt
        assert "cartoon" in prompt
```

## Domain-Driven Design (DDD)

### Why Repository Pattern & Dependency Injection

**Repository Pattern Benefits:**
- **Testability** - Mock `SlackRepository` and `OpenAIRepository` in unit tests without real API calls
- **Flexibility** - Easy to swap between OpenAI models (o3, DALL-E) without changing business logic
- **Clean boundaries** - Domain logic doesn't know about HTTP clients, API specifics, or external service details

**Dependency Injection Benefits:**
- **Unit testing** - Inject mocks instead of real services for isolated testing
- **Configuration flexibility** - Different implementations for different environments
- **Single Responsibility** - Classes focus on core logic, not creating dependencies

**Example:**
```python
# Without DI - hard to test, tightly coupled
class EmojiGenerator:
    def __init__(self):
        self.ai_client = OpenAIClient(api_key=os.environ["OPENAI_KEY"])  # Hard to mock

# With DI - easy to test, flexible
class EmojiGenerator:
    def __init__(self, ai_service: AIServiceRepository):
        self.ai_service = ai_service  # Can inject mock for testing
```

### Domain Model
The core domain revolves around **emoji creation** triggered by **user interactions** in **Slack conversations**.

### Domain Entities
```python
# Core domain objects
@dataclass
class SlackMessage:
    text: str
    user_id: str
    channel_id: str
    timestamp: str

@dataclass
class EmojiSpecification:
    description: str
    style: str
    format_type: str  # 'static', 'gif', 'meme'
    size_constraints: Dict[str, int]

@dataclass
class GeneratedEmoji:
    name: str
    image_data: bytes
    format: str
    size_bytes: int
    created_at: datetime
```

### Domain Services
```python
class EmojiCreationService:
    """Orchestrates the emoji creation process."""

    async def create_emoji_from_message_action(
        self,
        message: SlackMessage,
        user_input: UserEmojiRequest
    ) -> CreatedEmoji:
        """Main domain workflow for emoji creation."""
        pass

class AIPromptService:
    """Builds AI prompts from domain context."""

    def build_generation_prompt(
        self,
        message_context: str,
        user_description: str,
        style_preferences: StylePreferences
    ) -> str:
        """Creates optimized prompt for AI emoji generation."""
        pass
```

### Bounded Contexts
1. **Slack Integration Context** - Handles webhook events, modal dialogs, API calls
2. **Emoji Generation Context** - AI integration, image processing, format conversion
3. **User Interaction Context** - Message actions, style preferences, user feedback

### Repository Pattern for External Services
```python
from abc import ABC, abstractmethod

class SlackRepository(ABC):
    @abstractmethod
    async def upload_emoji(self, emoji: GeneratedEmoji, workspace_id: str) -> str:
        """Upload emoji to Slack workspace."""
        pass

    @abstractmethod
    async def add_reaction(self, emoji_name: str, message_ref: MessageRef) -> None:
        """Add emoji reaction to message."""
        pass

class OpenAIRepository(ABC):
    @abstractmethod
    async def generate_emoji_image(self, prompt: str, style_params: Dict) -> bytes:
        """Generate emoji image using OpenAI DALL-E."""
        pass

    @abstractmethod
    async def enhance_prompt(self, context: str, description: str) -> str:
        """Use o3 to enhance emoji generation prompt."""
        pass
```

## Architecture Patterns

### Dependency Injection
Use dependency injection for testability and flexibility:
```python
class SlackWebhookHandler:
    def __init__(
        self,
        emoji_service: EmojiCreationService,
        slack_repo: SlackRepository
    ) -> None:
        self._emoji_service = emoji_service
        self._slack_repo = slack_repo
```

### Error Handling
Define domain-specific exceptions:
```python
class EmojiSmithError(Exception):
    """Base exception for emoji smith domain."""
    pass

class EmojiGenerationError(EmojiSmithError):
    """Failed to generate emoji."""
    pass

class SlackIntegrationError(EmojiSmithError):
    """Failed to interact with Slack API."""
    pass
```

## Security Guidelines

### Critical Security Rules

1. **NEVER use `git add .`** - Always specify files explicitly
   ```bash
   # ✅ CORRECT - Explicit file specification
   git add src/emojismith/new_feature.py tests/unit/test_new_feature.py

   # ❌ WRONG - Could accidentally commit secrets
   git add .
   ```

2. **Never commit secrets or sensitive information**
   - API keys, tokens, passwords
   - `.env` files (always in `.gitignore`)
   - AWS credentials or IAM keys
   - Personal information or internal URLs

3. **Security Scanning with Bandit**
   ```bash
   # Run bandit security scan (must pass)
   bandit -r src/

   # Check for high-severity issues
   bandit -r src/ -ll
   ```

4. **Pre-commit Security Checks**
   - Always run security scan before committing
   - Review bandit output for security vulnerabilities
   - Fix any medium/high severity issues immediately

5. **Environment Variable Security**
   ```python
   # ✅ CORRECT - Secure environment loading
   api_key = os.environ.get("OPENAI_API_KEY")
   if not api_key:
       raise ValueError("OPENAI_API_KEY environment variable required")

   # ❌ WRONG - Hardcoded secrets
   api_key = "sk-1234567890abcdef"  # Never do this!
   ```

6. **AWS Secrets Management**
   - Local development: Use `.env` files (never committed)
   - Production: AWS Secrets Manager only
   - CDK manages IAM permissions with least privilege

## Configuration & Secrets Management

### Local Development (.env files)
```python
@dataclass
class Config:
    slack_bot_token: str
    slack_signing_secret: str
    openai_api_key: str
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Config":
        """Load from .env for local development."""
        return cls(
            slack_bot_token=os.environ["SLACK_BOT_TOKEN"],
            slack_signing_secret=os.environ["SLACK_SIGNING_SECRET"],
            openai_api_key=os.environ["OPENAI_API_KEY"],
            log_level=os.environ.get("LOG_LEVEL", "INFO")
        )
```

### Production (AWS Secrets Manager)
```python
    @classmethod
    async def from_aws_secrets(cls) -> "Config":
        """Load from AWS Secrets Manager for Lambda runtime."""
        secrets_client = boto3.client('secretsmanager')

        # Get all secrets in one call for efficiency
        secret_value = await secrets_client.get_secret_value(
            SecretId='emoji-smith/production'
        )
        secrets = json.loads(secret_value['SecretString'])

        return cls(
            slack_bot_token=secrets["SLACK_BOT_TOKEN"],
            slack_signing_secret=secrets["SLACK_SIGNING_SECRET"],
            openai_api_key=secrets["OPENAI_API_KEY"],
            log_level=secrets.get("LOG_LEVEL", "INFO")
        )
```

### Configuration Factory
```python
async def create_config() -> Config:
    """Create config based on environment."""
    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        # Running in Lambda - use Secrets Manager
        return await Config.from_aws_secrets()
    else:
        # Local development - use .env
        return Config.from_env()
```

## Testing & Deployment Strategy

### Single Production Workspace
- **No separate dev/staging Slack workspaces** - only one production workspace
- **Local testing** - Use ngrok to expose local server to Slack webhooks during development
- **Production testing** - Deploy to Lambda and test directly in production workspace
- **Rollback capability** - Keep previous Lambda versions for quick rollback if issues arise

### Testing Approach
1. **Unit Tests** - Mock all external services (Slack API, AI services)
2. **Integration Tests** - Test against real services in controlled scenarios
3. **Local Development** - Use ngrok tunnel for Slack webhook testing
4. **Manual Testing** - Deploy to production Lambda and verify functionality

### Development Workflow - Feature Branch Model
```bash
# 1. Create feature branch from main
git checkout main
git pull origin main
git checkout -b feature/your-feature-name

# 2. Local development with webhook testing
ngrok http 8000  # Expose local server
# Update Slack app webhook URL to ngrok URL
python -m src.emojismith.dev_server

# 3. Commit changes to feature branch
git add src/specific/files.py tests/specific/test_files.py  # NEVER use 'git add .'
git commit -m "feat: your descriptive commit message"
git push origin feature/your-feature-name

# 4. Create pull request for review
gh pr create --title "Your PR Title" --body "Description of changes"

# 5. After PR approval and merge, main branch auto-deploys
# Monitor CloudWatch logs for deployment issues
```

## CDK Infrastructure & Deployment

### CDK Bootstrap (One-time Setup)

```bash
# 1. Install AWS CDK
npm install -g aws-cdk

# 2. Configure AWS credentials
aws configure

# 3. Bootstrap CDK in your AWS account (one-time)
cdk bootstrap

# 4. Initialize CDK infrastructure
mkdir infra && cd infra
cdk init app --language python
source .venv/bin/activate
pip install -r requirements.txt
```

### CDK Stack Components

1. **IAM Deployment User** (created by CDK)
   - Least privilege permissions for GitHub Actions
   - Policies for Lambda, API Gateway, Secrets Manager
   - Access keys stored in GitHub Secrets

2. **Lambda Function**
   - Container image from ECR
   - Environment variables from Secrets Manager
   - Appropriate memory and timeout settings

3. **API Gateway**
   - HTTP API for Slack webhook endpoints
   - Custom domain (optional)
   - Request validation and CORS

4. **AWS Secrets Manager**
   - Production secrets (Slack tokens, OpenAI API key)
   - Automatic rotation capabilities
   - IAM access control

### GitHub Actions Staged Pipeline

**Stage 1: Code Quality**
```yaml
- name: Code Formatting
  run: black --check src/ tests/
- name: Linting
  run: flake8 src/ tests/
- name: Type Checking
  run: mypy src/
```

**Stage 2: Security Scanning**
```yaml
- name: Security Analysis
  run: bandit -r src/
```

**Stage 3: Testing**
```yaml
- name: Unit Tests
  run: pytest --cov=src tests/
- name: Coverage Check
  run: pytest --cov=src --cov-fail-under=80 tests/
```

**Stage 4: Lambda Build** (main branch only)
```yaml
- name: Build Docker Image
  run: docker build -t emoji-smith .
- name: Push to ECR
  run: |
    aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_URI
    docker tag emoji-smith:latest $ECR_URI:$GITHUB_SHA
    docker push $ECR_URI:$GITHUB_SHA
```

**Stage 5: CDK Deploy** (main branch only)
```yaml
- name: CDK Deploy
  run: |
    cd infra
    cdk deploy --require-approval never
```

## Deployment & Infrastructure

### Lambda Handler
```python
# src/emojismith/lambda_handler.py
from mangum import Mangum
from .app import create_app

app = create_app()
handler = Mangum(app)  # ASGI adapter for Lambda
```

### Environment Detection
```python
def is_lambda_environment() -> bool:
    """Check if running in AWS Lambda."""
    return bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

def is_development() -> bool:
    """Check if running in local development."""
    return not is_lambda_environment()
```

## Development Workflow - TDD & DDD First

### Test-Driven Development Cycle

**Red-Green-Refactor for every feature:**

1. **🔴 RED: Write Failing Tests**
   ```bash
   # Write domain model tests first
   pytest tests/unit/test_emoji_generation.py::test_emoji_specification_validation -v
   # Test should fail - domain models don't exist yet
   ```

2. **🟢 GREEN: Make Tests Pass**
   ```bash
   # Implement minimal domain logic to pass tests
   # Focus on business rules and domain invariants
   ```

3. **🔵 REFACTOR: Improve Design**
   ```bash
   # Clean up code while keeping tests green
   # Apply DDD patterns and dependency injection
   ```

### Domain-Driven Design Implementation

**Start with Domain Models (Inside-Out):**
1. **Domain Entities** - Core business objects (EmojiRequest, GeneratedEmoji)
2. **Value Objects** - Immutable concepts (StylePreferences, EmojiSpecification)
3. **Domain Services** - Business logic that doesn't fit in entities
4. **Repository Interfaces** - Abstract external dependencies
5. **Application Services** - Orchestrate use cases
6. **Infrastructure** - Implement repository interfaces

### Feature Development Process

1. **Design Session (5-10 min)**
   - Identify bounded context and aggregates
   - Define domain models and their relationships
   - Plan repository interfaces for external dependencies

2. **Domain Layer (TDD)**
   - Write tests for domain entities and value objects
   - Implement pure business logic (no external dependencies)
   - Write tests for domain services
   - Implement business rules and validation

3. **Application Layer (TDD)**
   - Write tests for use case orchestration
   - Implement application services
   - Define repository interfaces (abstractions)

4. **Infrastructure Layer (TDD)**
   - Write tests for repository implementations
   - Implement external service integrations
   - Add framework-specific code (FastAPI, Slack SDK, etc.)

5. **Integration & Deployment**
   - Test locally with ngrok webhook tunnel
   - Run full test suite with coverage validation
   - Create PR following security guidelines

### Code Quality & Security

```bash
# Pre-commit workflow (never use 'git add .')
black src/ tests/                    # Format code
flake8 src/ tests/                  # Lint code
mypy src/                           # Type checking
bandit -r src/                      # Security scan
pytest --cov=src --cov-fail-under=90 tests/  # Tests with coverage

# Explicit file staging
git add src/emojismith/specific_file.py tests/unit/test_specific.py
git commit -m "feat: implement emoji generation domain model"
```

### Pull Request Process

1. **Feature Branch Development** (TDD/DDD cycle)
2. **Quality Gates** - All tools must pass
3. **Code Review** - Focus on domain design and test coverage
4. **Integration** - Squash merge to main
5. **Deployment** - Automatic CI/CD pipeline

### Production Deployment

- **Automatic on main** - CDK deploys to AWS Lambda
- **Monitoring** - CloudWatch logs with structured correlation IDs
- **Rollback** - Lambda versioning for quick recovery

## Notes for Claude Code Assistant

When implementing features:
1. **Start with tests** - Write the test that describes the expected behavior
2. **Use repository pattern** - Abstract external services for testability and flexibility
3. **Apply dependency injection** - Make classes easy to test and configure
4. **Focus on domain logic** - Keep business rules separate from infrastructure
5. **Use type hints** - Help catch errors early and improve code clarity
6. **Test public interfaces** - Don't test implementation details
7. **Handle secrets properly** - .env for local, Secrets Manager for production
8. **Single workspace approach** - Test locally with ngrok, deploy to production for validation

Remember: The goal is maintainable, testable code that clearly expresses the domain of emoji creation for Slack conversations, with a simple but robust architecture that handles the single production workspace reality.
