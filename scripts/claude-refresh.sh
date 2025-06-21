#!/bin/bash
echo "=== CLAUDE.md Core Rules ==="
cat CLAUDE.md
echo -e "\n=== Current Context ==="
cat .claude/context.md 2>/dev/null || echo "No active context"
