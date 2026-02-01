#!/bin/bash
# AI Agent Environment Setup
# Compatible with: Google Jules, OpenAI Codex, Claude Code (cloud)
#
# This script bootstraps the development environment in cloud agent sandboxes.
# These environments typically:
# - Have Python pre-installed
# - Already have the repo cloned
# - Don't need virtual environment creation
# - Don't need .env files (secrets handled by the agent/platform)

set -e

echo "🤖 Emoji Smith - AI Agent Environment Setup"
echo "============================================"

# Detect package manager
if command -v uv &> /dev/null; then
    PKG_MANAGER="uv"
elif command -v pip &> /dev/null; then
    PKG_MANAGER="pip"
else
    echo "❌ No Python package manager found (need pip or uv)"
    exit 1
fi

echo "📦 Using package manager: $PKG_MANAGER"

# Install dependencies
echo "📥 Installing dependencies..."
if [ "$PKG_MANAGER" = "uv" ]; then
    uv sync --all-extras
else
    pip install -e ".[dev]"
fi

# Verify installation
echo "🔍 Verifying installation..."
python -c "import emojismith; print(f'✓ emojismith package: {emojismith.__file__}')"

# Run quick validation (optional, fast tests only)
if [ "${SKIP_VALIDATION:-}" != "1" ]; then
    echo "🧪 Running quick validation..."
    python -c "
from emojismith.domain.entities import EmojiGenerationJob, GenerationProvider
print('✓ Domain entities importable')
"
fi

echo ""
echo "✅ Agent environment ready!"
echo ""
echo "Available commands:"
echo "  pytest tests/                    # Run all tests"
echo "  pytest tests/unit/               # Run unit tests only"
echo "  ruff check src/ tests/           # Run linter"
echo "  mypy src/                        # Type checking"
