#!/bin/bash
# Quick development environment setup

set -e

echo "🚀 Setting up Emoji Smith development environment..."

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    uv venv
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Check Python version
PYTHON_VERSION=$(python --version | cut -d' ' -f2 | cut -d'.' -f1,2)
if [ "$PYTHON_VERSION" != "3.12" ]; then
    echo "❌ ERROR: Python 3.12 required, found $PYTHON_VERSION"
    exit 1
fi
echo "✓ Python $PYTHON_VERSION detected"

# Install dependencies
echo "📥 Installing dependencies..."
uv sync --all-extras

# Install pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
pre-commit install

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file template..."
    cat > .env << 'EOF'
# Emoji Smith Environment Variables
# Copy to .env and fill in your values

# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret

# OpenAI Configuration
OPENAI_API_KEY=sk-your-api-key

# AWS Configuration (for local testing)
AWS_REGION=us-east-2
SQS_QUEUE_URL=https://sqs.us-east-2.amazonaws.com/123456789/emoji-smith-queue

# Development Settings
LOG_LEVEL=INFO
EOF
    echo "⚠️  Please edit .env with your actual values"
else
    echo "✓ .env file already exists"
fi

echo ""
echo "✅ Development environment ready!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your API keys"
echo "2. Run tests: pytest"
echo "3. Start dev server: python -m src.emojismith.dev_server"
echo ""
echo "Remember to always activate the virtual environment:"
echo "  source .venv/bin/activate"
