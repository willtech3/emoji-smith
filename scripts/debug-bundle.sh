#!/bin/bash
# Generate debug bundle for troubleshooting

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BUNDLE_DIR="debug_bundle_$TIMESTAMP"
BUNDLE_ZIP="debug_bundle_$TIMESTAMP.zip"

echo "🔍 Generating debug bundle..."

# Create bundle directory
mkdir -p "$BUNDLE_DIR"

# System information
echo "📋 Collecting system information..."
{
    echo "=== System Information ==="
    echo "Date: $(date)"
    echo "User: $(whoami)"
    echo "Directory: $(pwd)"
    echo ""
    echo "=== Python Environment ==="
    echo "Python: $(python --version 2>&1)"
    echo "Virtual env: $VIRTUAL_ENV"
    echo ""
    echo "=== Git Information ==="
    echo "Branch: $(git branch --show-current)"
    echo "Last commit: $(git log -1 --oneline)"
    echo "Status:"
    git status --short
} > "$BUNDLE_DIR/system_info.txt"

# Installed packages
echo "📦 Listing installed packages..."
uv pip list > "$BUNDLE_DIR/installed_packages.txt"

# Environment variables (sanitized)
echo "🔐 Collecting environment variables (sanitized)..."
{
    echo "=== Environment Variables (sanitized) ==="
    env | grep -E "(PYTHON|VIRTUAL|PUBSUB_|LOG_LEVEL|ENVIRONMENT)" | sort
    echo ""
    echo "=== Sensitive variables (existence only) ==="
    for var in SLACK_BOT_TOKEN SLACK_SIGNING_SECRET OPENAI_API_KEY GOOGLE_API_KEY; do
        if [ -n "${!var}" ]; then
            echo "$var: [SET]"
        else
            echo "$var: [NOT SET]"
        fi
    done
} > "$BUNDLE_DIR/environment.txt"

# Recent error logs
echo "📋 Collecting recent test failures..."
if [ -f ".pytest_cache/lastfailed" ]; then
    cp .pytest_cache/lastfailed "$BUNDLE_DIR/last_failed_tests.json"
fi

# Configuration files (no secrets)
echo "📄 Copying configuration files..."
for file in pyproject.toml .flake8 .pre-commit-config.yaml; do
    if [ -f "$file" ]; then
        cp "$file" "$BUNDLE_DIR/"
    fi
done

# MyPy cache issues
echo "🔍 Checking for mypy cache issues..."
if [ -d ".mypy_cache" ]; then
    find .mypy_cache -name "*.json" -type f -newer .mypy_cache -exec ls -la {} \; > "$BUNDLE_DIR/mypy_cache_info.txt"
fi

# Create zip
echo "📦 Creating zip archive..."
zip -r "$BUNDLE_ZIP" "$BUNDLE_DIR" > /dev/null

# Cleanup
rm -rf "$BUNDLE_DIR"

echo ""
echo "✅ Debug bundle created: $BUNDLE_ZIP"
echo ""
echo "This bundle contains:"
echo "  - System and Python environment info"
echo "  - Installed packages list"
echo "  - Sanitized environment variables"
echo "  - Configuration files"
echo "  - Recent test failure info"
echo ""
echo "Share this file when requesting help."
