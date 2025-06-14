# Emoji Smith 🎨

> **AI-powered custom emoji generator for Slack workspaces**

Emoji Smith is a Slack bot that automatically generates custom emojis using OpenAI's DALL-E, triggered by message actions. Simply right-click any Slack message, choose "Create Reaction," describe the emoji you want, and watch as AI creates the perfect custom emoji reaction.

## ✨ Features

- **🎯 Context-Aware Generation**: Analyzes the original message for relevant emoji creation
- **🎨 Style Customization**: Choose from cartoon, realistic, minimalist, or pixel art styles
- **⚡ Instant Application**: Generated emoji is automatically added as a reaction
- **🔒 Secure Deployment**: AWS Lambda with proper secrets management
- **🚀 Zero Downtime**: Serverless architecture scales automatically

## 🏗️ Architecture

```mermaid
graph LR
    A[Slack Message] --> B[Right-Click Action]
    B --> C[Modal Dialog]
    C --> D[AWS Lambda]
    D --> E[OpenAI DALL-E]
    E --> F[Generated Emoji]
    F --> G[Upload to Slack]
    G --> H[Apply as Reaction]
```

**Tech Stack:**
- **Backend**: Python 3.12 + FastAPI + Slack Bolt
- **AI Services**: OpenAI GPT-4 (prompt enhancement) + DALL-E (image generation)
- **Infrastructure**: AWS Lambda + API Gateway + Secrets Manager
- **Deployment**: AWS CDK + GitHub Actions
- **Security**: Bandit SAST scanning + least-privilege IAM

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- AWS Account with CDK bootstrapped
- Slack workspace (admin access)
- OpenAI API key

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
pytest -q && black --check src/ && bandit -r src/
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
# Bootstrap AWS CDK (one-time)
cdk bootstrap

# Deploy infrastructure
cd infra && cdk deploy

# Configure GitHub secrets for CI/CD
gh secret set AWS_ACCESS_KEY_ID -b "<from-cdk-output>"
gh secret set AWS_SECRET_ACCESS_KEY -b "<from-cdk-output>"

# Store production secrets in AWS Secrets Manager
aws secretsmanager create-secret --name "emoji-smith/production" --secret-string '{...}'
```

## 📖 Usage

1. **Find a message** in Slack that needs a reaction
2. **Right-click** the message → **More actions** → **Create Reaction**
3. **Describe the emoji** you want in the modal dialog
4. **Choose style** (cartoon, realistic, minimalist, pixel art)
5. **Submit** and wait 5-10 seconds for AI generation
6. **Emoji appears** as a reaction on the original message!

### Example Use Cases

- **"facepalm but cute"** on deployment failure messages
- **"celebrating with confetti"** on successful releases  
- **"this is fine dog"** on system alerts
- **"mind blown explosion"** on brilliant ideas
- **"typing furiously"** on coding discussions

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

### Quality Checks

All code must pass these checks before merging:

```bash
black --check src/ tests/     # Code formatting
flake8 src/ tests/           # Style linting  
mypy src/                    # Type checking
bandit -r src/               # Security scanning
pytest --cov=src tests/      # Tests with 90%+ coverage
```

### CI/CD Pipeline

**Stage 1: Code Quality** → **Stage 2: Security** → **Stage 3: Testing** → **Stage 4: Build** → **Stage 5: Deploy**

- **Pull Requests**: Run stages 1-3 for validation
- **Main Branch**: Run all stages including production deployment
- **Deployment**: Automatic via AWS CDK when main branch updated

## 🔒 Security

- **🚫 No hardcoded secrets**: All credentials via environment variables or AWS Secrets Manager
- **🔍 SAST scanning**: Bandit security analysis on every commit
- **🔐 Least privilege**: IAM roles with minimal required permissions
- **📝 Explicit commits**: Never use `git add .` - always specify files explicitly
- **🛡️ Branch protection**: All changes require pull request review

## 📁 Project Structure

```
emoji-smith/
├── src/emojismith/          # Main application code
│   ├── handlers/            # Slack event handlers
│   ├── services/            # Business logic (emoji generation)
│   ├── repositories/        # External service abstractions
│   └── models/              # Domain models and types
├── tests/                   # Test suite (unit + integration)
├── infra/                   # AWS CDK infrastructure code
├── .github/workflows/       # CI/CD pipeline definitions
└── docs/                    # Additional documentation
```

## 🤝 Contributing

1. **Read the guidelines**: See [CLAUDE.md](./CLAUDE.md) for development standards
2. **Follow security rules**: Never commit secrets, always use explicit file adds
3. **Write tests**: Test-driven development with 90%+ coverage
4. **Use feature branches**: All changes via pull request
5. **Run quality checks**: Ensure all tools pass before committing

## 📄 License

MIT License - see [LICENSE](./LICENSE) for details.

## 🆘 Support

- **Setup Issues**: See [SETUP.md](./SETUP.md) for detailed instructions
- **Development**: See [CLAUDE.md](./CLAUDE.md) for coding guidelines  
- **Bug Reports**: [Open an issue](https://github.com/willtech3/emoji-smith/issues)
- **Feature Requests**: [Start a discussion](https://github.com/willtech3/emoji-smith/discussions)

---

**Made with ❤️ and AI** • Powered by OpenAI DALL-E • Deployed on AWS Lambda
