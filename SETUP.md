# Emoji Smith Development Setup

> 🚀 **Quick Start Goal:** Get a local development environment running in under 10 minutes

## Prerequisites

### Required Software

1. **Python 3.12+**
   ```bash
   # Check if you have Python 3.12
   python3 --version
   
   # If not installed, use pyenv (recommended):
   curl https://pyenv.run | bash
   pyenv install 3.12.3
   pyenv global 3.12.3
   
   # Or install via system package manager:
   # macOS: brew install python@3.12
   # Ubuntu: sudo apt install python3.12 python3.12-venv
   ```

2. **uv Package Manager** (fast Python package installer)
   ```bash
   # Install uv
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Verify installation
   uv --version
   ```

3. **Git & GitHub CLI**
   ```bash
   # Install GitHub CLI
   # macOS: brew install gh
   # Ubuntu: sudo apt install gh
   
   # Authenticate with GitHub
   gh auth login
   ```

4. **ngrok** (for local webhook testing)
   ```bash
   # macOS: brew install ngrok
   # Or download from: https://ngrok.com/download
   
   # Sign up and get auth token from https://dashboard.ngrok.com/auth
   ngrok authtoken YOUR_TOKEN_HERE
   ```

## Quick Start Checklist

### 1. Clone and Setup Environment (2 minutes)

```bash
# Clone the repository
git clone https://github.com/willtech3/emoji-smith.git
cd emoji-smith

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e ".[dev]"
```

### 2. Verify Development Tools (1 minute)

```bash
# Run the verification suite
pytest -q                    # Should pass 1 test
black --check src/ tests/    # Should show "All done!"
flake8 src/ tests/          # Should show no errors
mypy src/                   # Should show "Success: no issues found"
```

### 3. Environment Configuration (3 minutes)

Create `.env` file for local development:

```bash
# Copy example environment file
cp .env.example .env

# Edit with your credentials
nano .env  # or use your preferred editor
```

Required environment variables:
```bash
# Slack Bot Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here

# AI Service (choose one)
ANTHROPIC_API_KEY=your-claude-api-key      # For Claude AI
OPENAI_API_KEY=your-openai-api-key         # For OpenAI

# Development Settings
LOG_LEVEL=DEBUG
ENVIRONMENT=development
```

### 4. Slack App Configuration (4 minutes)

1. **Create Slack App**
   - Go to [api.slack.com/apps](https://api.slack.com/apps)
   - Click "Create New App" → "From scratch"
   - Name: "Emoji Smith" 
   - Choose your development workspace

2. **Configure Permissions**
   - Go to "OAuth & Permissions"
   - Add Bot Token Scopes:
     - `emoji:write` (upload custom emojis)
     - `reactions:write` (add reactions to messages)
     - `commands` (slash commands)
     - `chat:write` (send messages)

3. **Set up Message Actions**
   - Go to "Interactive Components"
   - Enable Interactive Components
   - Request URL: `https://your-ngrok-url.ngrok.io/slack/events`
   - Create Message Action:
     - Name: "Create Reaction"
     - Description: "Generate custom emoji reaction"
     - Callback ID: `create_emoji_reaction`

4. **Install to Workspace**
   - Go to "Install App"
   - Click "Install to Workspace"
   - Copy the "Bot User OAuth Token" to your `.env` file
   - Copy "Signing Secret" from "Basic Information" to your `.env` file

## Development Workflow

### Local Development Server

```bash
# Terminal 1: Start local development server
source .venv/bin/activate
python -m src.emojismith.dev_server

# Terminal 2: Expose local server via ngrok
ngrok http 8000

# Update Slack app webhook URL to the ngrok HTTPS URL
```

### Testing Workflow

```bash
# Run all quality checks before committing
black src/ tests/           # Format code
flake8 src/ tests/          # Check style
mypy src/                   # Type checking
pytest --cov=src tests/     # Run tests with coverage

# Or use the shortcut script
./scripts/check-quality.sh
```

### Development Commands

```bash
# Install new dependency
uv pip install package-name
uv pip freeze > requirements.lock  # Update lock file

# Install new dev dependency  
uv pip install package-name
echo "package-name>=1.0.0" >> pyproject.toml  # Add to dev dependencies
uv pip freeze > requirements-dev.lock

# Run specific test
pytest tests/unit/test_specific_file.py -v

# Run tests with specific marker
pytest -m "not slow" -v

# Generate coverage report
pytest --cov=src --cov-report=html tests/
open htmlcov/index.html  # View coverage report
```

## AWS Configuration (for Deployment)

### Prerequisites

1. **AWS CLI**
   ```bash
   # Install AWS CLI
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install
   
   # Configure credentials
   aws configure
   ```

2. **AWS CDK**
   ```bash
   # Install CDK
   npm install -g aws-cdk
   
   # Bootstrap CDK (first time only)
   cdk bootstrap
   ```

### Deployment Setup

```bash
# Initialize CDK infrastructure
cd infra/
cdk init app --language python
source .venv/bin/activate
pip install -r requirements.txt

# Deploy to AWS
cdk synth  # Generate CloudFormation
cdk deploy  # Deploy to AWS
```

## Project Structure

```
emoji-smith/
├── src/emojismith/          # Main application code
│   ├── __init__.py
│   ├── app.py              # Slack Bolt application
│   ├── handlers/           # Slack event handlers
│   ├── services/           # Business logic services
│   ├── repositories/       # External service abstractions
│   └── models/             # Domain models
├── tests/                   # Test suite
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── fixtures/           # Test data
├── infra/                   # AWS CDK infrastructure
├── .github/workflows/       # CI/CD pipelines
├── pyproject.toml          # Project configuration
├── requirements.lock       # Pinned runtime dependencies
├── requirements-dev.lock   # Pinned dev dependencies
├── CLAUDE.md              # Development guidelines
└── SETUP.md               # This file
```

## Troubleshooting

### Common Issues

**1. Python version not found**
```bash
# Solution: Install Python 3.12
pyenv install 3.12.3
pyenv local 3.12.3
```

**2. uv command not found**
```bash
# Solution: Restart terminal or source profile
source ~/.bashrc  # or ~/.zshrc
# Or reinstall uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**3. Virtual environment activation fails**
```bash
# Solution: Recreate virtual environment
rm -rf .venv
uv venv --python 3.12
source .venv/bin/activate
```

**4. Tests fail with import errors**
```bash
# Solution: Install package in development mode
uv pip install -e .
```

**5. Slack webhook not receiving events**
```bash
# Check ngrok is running and URL is correct
ngrok http 8000
# Update Slack app webhook URL to ngrok HTTPS URL
# Check ngrok web interface: http://localhost:4040
```

**6. AI service errors**
```bash
# Verify API keys are set correctly
echo $ANTHROPIC_API_KEY  # Should show your key
# Check API quotas and billing
```

### Getting Help

- **Development Guidelines**: See `CLAUDE.md`
- **GitHub Issues**: [Project Issues](https://github.com/willtech3/emoji-smith/issues)
- **Slack API Docs**: [api.slack.com](https://api.slack.com/)
- **ngrok Docs**: [ngrok.com/docs](https://ngrok.com/docs)

## Quick Verification

After setup, verify everything works:

```bash
# 1. Environment check
python --version     # Should be 3.12+
uv --version        # Should show version
source .venv/bin/activate
pytest -q          # Should pass tests

# 2. Start development server
python -m src.emojismith.dev_server

# 3. In another terminal, test webhook
curl http://localhost:8000/health
# Should return: {"status": "healthy"}

# 4. Expose via ngrok
ngrok http 8000
# Should show forwarding URLs
```

✅ **You're ready to develop!** The environment is properly configured when all verification steps pass.

## Next Steps

1. **Complete Slack app setup** with your ngrok webhook URL
2. **Test the message action** in your Slack workspace  
3. **Start implementing features** following the phase plan in GitHub issues
4. **Deploy to AWS** when ready for production testing

---

> 💡 **Tip**: Keep this setup guide updated as the project evolves. New team members should be able to follow this guide and have a working environment quickly.