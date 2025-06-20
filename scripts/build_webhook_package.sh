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

# Copy webhook source code
echo -e "${YELLOW}Copying webhook source code...${NC}"
cp -r src/webhook "$TEMP_DIR/"
cp -r src/shared "$TEMP_DIR/"
cp src/emojismith/infrastructure/aws/webhook_handler.py "$TEMP_DIR/"
cp src/emojismith/infrastructure/aws/secrets_loader.py "$TEMP_DIR/"
cp src/__init__.py "$TEMP_DIR/"

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

echo -e "${GREEN}✅ Webhook package built successfully: webhook_package.zip${NC}"
echo -e "${GREEN}   Package size: $(du -h webhook_package.zip | cut -f1)${NC}"
