# Emoji Smith 🎨

[![Coverage Status](https://codecov.io/gh/willtech3/emoji-smith/branch/main/graph/badge.svg)](https://codecov.io/gh/willtech3/emoji-smith)

> **AI-powered custom emoji generator for Slack workspaces**

Emoji Smith is a Slack bot that automatically generates custom emojis using OpenAI's gpt-image-1, triggered by message actions. Simply right-click any Slack message, choose "Create Reaction," describe the emoji you want, and watch as AI creates the perfect custom emoji reaction.

## ✨ Features

- **🎯 Context-Aware Generation**: Analyzes the original message for relevant emoji creation
- **🎨 Style Customization**: Choose from cartoon, realistic, minimalist, or pixel art styles
- **🔄 Multi-Provider Support**: Choose between OpenAI GPT-Image or Google Gemini for image generation
- **⚡ Instant Application**: Generated emoji is automatically added as a reaction
- **🔒 Secure Deployment**: Google Cloud Run with proper secrets management
- **🚀 Zero Downtime**: Serverless architecture scales automatically

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────────────────────────────────┐
│ Slack Workspace │     │              GCP Infrastructure              │
│ Events/Actions  │────▶│ Cloud Run ──▶ Pub/Sub ──▶ Cloud Run Worker  │
└─────────────────┘     │ (webhook)     (OIDC)      (private)          │
                        └──────────────────────────────────────────────┘
                                                    │
                        ┌───────────────────────────┴───────────────────────────┐
                        │                   AI Generation                       │
                        │  ┌─────────────┐                    ┌──────────────┐  │
                        │  │ OpenAI      │◀── Provider ──────▶│ Google       │  │
                        │  │ gpt-image-1 │    Selection       │ Gemini       │  │
                        │  └──────┬──────┘                    └──────┬───────┘  │
                        │         └────────── Upload & React ────────┘          │
                        └───────────────────────────────────────────────────────┘
```

**Flow:**
1. Slack events hit the **Webhook Cloud Run** service (public, responds in <3s)
2. Webhook publishes job to **Pub/Sub** topic
3. Pub/Sub push subscription (with OIDC auth) triggers **Worker Cloud Run** service (private)
4. Worker generates image via OpenAI or Gemini, then uploads/reacts in Slack

For detailed architecture documentation, see [docs/architecture/](./docs/architecture/).

**Tech Stack:**
- **Backend**: Python 3.12 + FastAPI + Slack Bolt
- **AI Services**:
  - OpenAI GPT-5 with fallback to gpt-4/gpt-3.5 (prompt enhancement)
  - OpenAI gpt-image-1 with fallback to gpt-image-1-mini (image generation)
  - Google Gemini with fallback models (alternative image generation)
- **Infrastructure**: Google Cloud Run + Pub/Sub + Secret Manager
- **Deployment**: GitHub Actions CI/CD with Workload Identity Federation (keyless)
- **IaC**: Terraform
- **Monitoring**: Cloud Logging + health check endpoint (`/health`)
- **Security**: Bandit SAST scanning + least-privilege service accounts

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- GCP project with billing enabled
- Terraform installed
- Slack workspace (admin access)
- OpenAI API key (and optionally Google API key for Gemini)

### 1. Local Development Setup

```bash
# Clone and setup environment
git clone https://github.com/willtech3/emoji-smith.git
cd emoji-smith
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your Slack and OpenAI credentials

# Verify setup
pytest -q && ruff check src/ tests/
```

### 2. Slack App Configuration

1. Create new Slack app at [api.slack.com/apps](https://api.slack.com/apps)
2. Add bot scopes: `emoji:write`, `reactions:write`, `commands`, `chat:write`
3. Create message action: "Create Reaction" with callback ID `create_emoji_reaction`
4. Install app to workspace and copy tokens to `.env`

### 3. Local Testing

```bash
# Terminal 1: Start development server
python -m src.emojismith.dev_server

# Terminal 2: Expose via ngrok
ngrok http 8000

# Update Slack app webhook URL to ngrok HTTPS URL
```

### 4. Production Deployment

```bash
# Initialize Terraform (one-time)
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your GCP project details

terraform init
terraform plan
terraform apply

# Configure GitHub for keyless deployment (Workload Identity Federation)
# Set these GitHub repository variables:
#   GCP_PROJECT_ID, GCP_PROJECT_NUMBER, GCP_WORKLOAD_IDENTITY_PROVIDER, GCP_CICD_SERVICE_ACCOUNT

# Store secrets in GCP Secret Manager (Terraform creates the secret resources)
gcloud secrets versions add slack-bot-token --data-file=-
gcloud secrets versions add openai-api-key --data-file=-
```

## 📖 Usage

1. **Find a message** in Slack that needs a reaction
2. **Right-click** the message → **More actions** → **Create Reaction**
3. **Describe the emoji** you want in the modal dialog
4. **Choose sharing options**:
   - Where to share (new thread, existing thread, or direct message)
   - Who sees instructions (everyone or just you)
   - Image size (emoji size 128x128 or full size 1024x1024)
5. **Submit** and wait 5-10 seconds for AI generation
6. **For Enterprise Grid**: Emoji automatically uploaded and added as reaction
7. **For Standard Workspaces**: Emoji shared as file with easy upload instructions

### Example Use Cases

- **"facepalm but cute"** on deployment failure messages
- **"celebrating with confetti"** on successful releases
- **"this is fine dog"** on system alerts
- **"mind blown explosion"** on brilliant ideas
- **"typing furiously"** on coding discussions

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default | Values |
|----------|-------------|---------|---------|
| `SLACK_BOT_TOKEN` | Slack bot user OAuth token | Required | `xoxb-...` |
| `SLACK_SIGNING_SECRET` | Slack app signing secret | Required | `...` |
| `OPENAI_API_KEY` | OpenAI API key for gpt-image-1 | Required | `sk-...` |
| `OPENAI_CHAT_MODEL` | Chat model for prompt enhancement | `gpt-5` | `gpt-5`, `gpt-4`, `gpt-3.5-turbo` |
| `GOOGLE_API_KEY` | Google API key for Gemini image generation | Optional | `...` |
| `EMOJISMITH_FORCE_ENTERPRISE` | Force Enterprise Grid mode | `false` | `true`, `false` |
| `PUBSUB_TOPIC` | Pub/Sub topic for job queue (GCP) | None | `projects/.../topics/...` |
| `SLACK_TEST_BOT_TOKEN` | Bot token for Slack integration tests | None | `xoxb-...` |
| `SLACK_TEST_CHANNEL_ID` | Channel ID for Slack integration tests | None | `CXXXXXX` |
| `SLACK_TEST_USER_ID` | User ID for Slack integration tests | None | `UXXXXXX` |

**Note on `GOOGLE_API_KEY`**: This environment variable is optional. When set, users can select Google Gemini as an alternative image generation provider in the Slack modal. Get your API key from [Google AI Studio](https://aistudio.google.com/).

**Note on `EMOJISMITH_FORCE_ENTERPRISE`**: This environment variable allows you to simulate Enterprise Grid workspace behavior in development/testing. When set to `true`, the bot will attempt direct emoji uploads. Invalid values (anything other than `true` or `false`) will log a warning and default to `false`.

## 🛠️ Development

### Feature Branch Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes with security in mind
git add src/specific/files.py tests/specific/test_files.py  # NEVER use 'git add .'
git commit -m "feat: your descriptive message"

# Push and create PR
git push origin feature/your-feature-name
gh pr create --title "Your Feature" --body "Description"
```

### Dependency Injection Quickstart

When embedding Emoji Smith in another FastAPI or async context, simply provide your own Slack client and inject a `SlackFileSharingRepository`:

```python
from slack_sdk.web.async_client import AsyncWebClient
from emojismith.infrastructure.slack.slack_file_sharing import SlackFileSharingRepository

slack_client = AsyncWebClient(token="xoxb-…")
file_sharing_repo = SlackFileSharingRepository(slack_client)
# pass `file_sharing_repo` into `EmojiCreationService`
```

If you don’t provide one, `create_app()` auto-constructs a default instance for the dev server.

### Quality Checks

All code must pass these checks before merging:

```bash
ruff format --check src/ tests/  # Code formatting
ruff check src/ tests/           # Linting + security scanning
mypy src/                        # Type checking
pytest --cov=src tests/      # Tests with 90%+ coverage
```

### CI/CD Pipeline

**Stage 1: Code Quality** → **Stage 2: Testing** → **Stage 3: Build Docker Images** → **Stage 4: Deploy to Cloud Run**

- **Pull Requests**: Run stages 1-2 for validation
- **Main Branch**: Run all stages including production deployment
- **Deployment**: Automatic via GitHub Actions with Workload Identity Federation (keyless auth to GCP)

## 🔒 Security

- **🚫 No hardcoded secrets**: All credentials via environment variables or cloud secret managers
- **🔍 SAST scanning**: Bandit security analysis on every commit
- **🔐 Least privilege**: IAM roles with minimal required permissions
- **📝 Explicit commits**: Never use `git add .` - always specify files explicitly
- **🛡️ Branch protection**: All changes require pull request review

## 📁 Project Structure (DDD Architecture)

```
emoji-smith/
├── src/
│   ├── emojismith/         # Main application (Clean Architecture)
│   │   ├── domain/         # 🏛️  Domain Layer (pure business logic)
│   │   │   ├── entities/   # Core business objects
│   │   │   ├── value_objects/  # Immutable domain concepts
│   │   │   ├── services/   # Domain business rules
│   │   │   ├── repositories/   # Repository interfaces (abstractions)
│   │   │   ├── protocols/  # Domain protocol definitions
│   │   │   ├── errors.py   # Domain-specific errors
│   │   │   └── exceptions.py   # Domain exceptions
│   │   ├── application/    # 🎯 Application Layer (use cases)
│   │   │   ├── services/   # Application services (orchestration)
│   │   │   ├── handlers/   # Slack webhook handlers
│   │   │   ├── use_cases/  # Application use cases
│   │   │   └── create_webhook_app.py  # Webhook app factory
│   │   ├── infrastructure/ # 🔧 Infrastructure Layer (external concerns)
│   │   │   ├── slack/      # Slack API implementations
│   │   │   ├── openai/     # OpenAI API implementations
│   │   │   ├── image/      # Image processing implementations
│   │   │   ├── jobs/       # Job queue implementations
│   │   │   ├── security/   # Security implementations
│   │   │   └── gcp/        # GCP service integrations
│   │   │       ├── webhook_app.py      # Cloud Run webhook service
│   │   │       └── worker_app.py       # Cloud Run worker service
│   │   ├── presentation/   # 🌐 Presentation Layer
│   │   │   └── web/
│   │   │       └── slack_webhook_api.py  # API endpoints
│   │   ├── app.py         # FastAPI application factory
│   │   └── dev_server.py  # Local development server
│   ├── shared/            # Shared domain code
│   │   └── domain/
│   │       ├── entities/
│   │       ├── repositories/
│   │       └── value_objects.py
│   └── webhook/           # Legacy webhook code (deprecated)
│       ├── domain/
│       ├── infrastructure/
│       └── handler.py
├── tests/                 # 🧪 Test Suite (TDD)
│   ├── unit/             # Domain and application logic tests
│   ├── integration/      # Infrastructure integration tests
│   ├── contract/         # Contract tests for external services
│   ├── e2e/             # End-to-end tests
│   ├── security/        # Security-focused tests
│   ├── performance/     # Performance tests
│   ├── fixtures/        # Test data and mocks
│   └── conftest.py      # Pytest configuration
├── terraform/           # ☁️  GCP Terraform Infrastructure
│   ├── cloud_run_*.tf  # Cloud Run services (webhook + worker)
│   ├── pubsub.tf       # Pub/Sub topic & subscription
│   ├── secrets.tf      # Secret Manager config
│   ├── iam.tf          # Service accounts & IAM
│   └── workload_identity.tf  # GitHub Actions OIDC auth
├── docs/                # 📚 Documentation
│   ├── adr/            # Architecture Decision Records
│   ├── architecture/   # Architecture documentation
│   ├── testing/        # Testing documentation
│   ├── claude/         # Claude AI-specific templates
│   └── backup/         # Backup documentation
├── scripts/            # 🛠️  Development scripts
│   ├── build_webhook_package.sh
│   ├── check-quality.sh
│   ├── claude-refresh.sh
│   ├── dev-setup.sh
│   └── run-tests.sh
├── .github/            # 🚀 GitHub configuration
│   └── workflows/      # CI/CD pipelines
├── .claude/            # 🤖 Claude AI configuration
│   └── commands/       # Claude command definitions
├── stubs/              # Type stubs
└── Configuration files
    ├── .pre-commit-config.yaml
    ├── pyproject.toml
    ├── requirements-webhook.lock
    └── run_dev.sh
```

## 📚 Documentation Structure

- `CLAUDE.md` - Core development rules (always read first)
- Co-located `CLAUDE.md` files in each directory:
  - `src/CLAUDE.md` - Security guidelines
  - `src/emojismith/domain/CLAUDE.md` - Domain layer guidelines
  - `src/emojismith/infrastructure/CLAUDE.md` - Infrastructure guidelines
  - `tests/CLAUDE.md` - Testing guidelines
  - `.github/CLAUDE.md` - Deployment and CI/CD guidelines
- `.claude/context.md` - Current task tracking (git-ignored)
- `scripts/claude-refresh.sh` - Quick context refresh

For AI agents: Always start by reading root CLAUDE.md, then follow the hierarchy to the relevant local CLAUDE.md files.

## 🤝 Contributing

1. **Read the guidelines**: See [CLAUDE.md](./CLAUDE.md) for development standards
2. **Follow security rules**: Never commit secrets, always use explicit file adds
3. **Write tests**: Test-driven development with 90%+ coverage
4. **Use feature branches**: All changes via pull request
5. **Run quality checks**: Ensure all tools pass before committing

## 🆘 Support

- **Development**: See [CLAUDE.md](./CLAUDE.md) for coding guidelines
- **Architecture**: See [docs/architecture/](./docs/architecture/) for design documentation
- **Testing**: See [docs/testing/testing-guidelines.md](./docs/testing/testing-guidelines.md) for test standards
- **Bug Reports**: [Open an issue](https://github.com/willtech3/emoji-smith/issues)
