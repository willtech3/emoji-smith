#!/bin/bash
# Build webhook package for Lambda deployment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Building webhook package for Lambda deployment...${NC}"

# Determine project root first (before changing directories)
if [ -d "scripts" ]; then
    # Running from project root
    PROJECT_ROOT=$(pwd)
else
    # Running from scripts directory
    PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

# Create temporary directory
TEMP_DIR=$(mktemp -d)
echo "Using temporary directory: $TEMP_DIR"

# Install dependencies to temp directory
echo -e "${YELLOW}Installing webhook dependencies...${NC}"
uv pip install -r requirements-webhook.lock --target "$TEMP_DIR" --no-deps

# Copy webhook source code maintaining directory structure
echo -e "${YELLOW}Copying webhook source code...${NC}"
# Copy webhook and shared modules to root for correct import paths
cp -r src/webhook "$TEMP_DIR/"
cp -r src/shared "$TEMP_DIR/"

# Copy emojismith module to root so Lambda can import it directly
mkdir -p "$TEMP_DIR/emojismith/infrastructure/aws"
cp -r src/emojismith/domain "$TEMP_DIR/emojismith/"
cp -r src/emojismith/application "$TEMP_DIR/emojismith/"
cp -r src/emojismith/infrastructure "$TEMP_DIR/emojismith/"
cp src/emojismith/__init__.py "$TEMP_DIR/emojismith/"
# Ensure all __init__.py files exist
touch "$TEMP_DIR/emojismith/infrastructure/__init__.py"
touch "$TEMP_DIR/emojismith/infrastructure/aws/__init__.py"

# Copy secrets_loader to root for Lambda package imports
cp src/emojismith/infrastructure/aws/secrets_loader.py "$TEMP_DIR/"

# Copy top-level webhook_handler.py for Lambda entry point
cp src/webhook_handler.py "$TEMP_DIR/"

# Create package zip
echo -e "${YELLOW}Creating webhook package zip...${NC}"
cd "$TEMP_DIR"
# Create zip with compression and exclude unnecessary files
zip -rq webhook_package.zip . -x "*.pyc" "*__pycache__*" "*.git*"

# Move package to project root
mv webhook_package.zip "$PROJECT_ROOT/"
cd "$PROJECT_ROOT"

# Cleanup
rm -rf "$TEMP_DIR"

# Validate the package can be imported correctly
echo -e "${YELLOW}Validating Lambda handler import...${NC}"
if unzip -q webhook_package.zip -d /tmp/webhook_test_$$ && \
   cd /tmp/webhook_test_$$ && \
   python3 -c "
import os
# Set dummy env vars for validation only
os.environ['SLACK_BOT_TOKEN'] = 'dummy'
os.environ['SLACK_SIGNING_SECRET'] = 'dummy'
os.environ['SQS_QUEUE_URL'] = 'dummy'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'  # Required for boto3
try:
    import webhook_handler
    assert hasattr(webhook_handler, 'handler')
    print('✅ Handler imports correctly')
except Exception as e:
    print(f'❌ Import failed: {e}')
    exit(1)
" 2>&1; then
    echo -e "${GREEN}✅ Lambda handler validation passed${NC}"
    cd "$PROJECT_ROOT"
    rm -rf /tmp/webhook_test_$$
else
    echo -e "${RED}❌ Lambda handler import validation failed${NC}"
    cd "$PROJECT_ROOT"
    rm -rf /tmp/webhook_test_$$
    exit 1
fi

echo -e "${GREEN}✅ Webhook package built successfully: webhook_package.zip${NC}"
echo -e "${GREEN}   Package size: $(du -h webhook_package.zip | cut -f1)${NC}"
