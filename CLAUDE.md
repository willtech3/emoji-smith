# Claude Development Guidelines for Emoji Smith - Core Document

## 🧠 Context Management
**For long conversations, review this document:**
- Before starting any new task
- When switching between layers (domain/infra/app)
- If you feel context drifting (~3000 tokens)
- Before any git operations or deployments

## 🚨 CRITICAL RULES - NEVER VIOLATE

1. **🔐 NEVER commit secrets** - No API keys, tokens, or `.env` files
2. **📁 NEVER use `git add .`** - Always specify files explicitly
3. **🐍 ALWAYS activate venv first** - `source .venv/bin/activate`
4. **🧪 ALWAYS write tests first** - TDD is mandatory
5. **💉 ALWAYS use dependency injection** - No hardcoded dependencies
6. **📝 ALWAYS explain changes** - Before making (auto-accept off) or after (auto-accept on)
7. **🚀 ALWAYS use CI for deployment** - Never deploy manually if CI exists
8. **🌿 ALWAYS use feature branches** - Never commit directly to main
9. **🔄 ALWAYS create pull requests** - All changes go through PR review

## 🏗️ Architecture Constraints (IMMUTABLE)

### Fixed Lambda Handler Locations
```
src/emojismith/infrastructure/aws/webhook_handler.py  # < 3s response
src/emojismith/infrastructure/aws/worker_handler.py   # async processing
```
**These paths are hardcoded in CDK - DO NOT MOVE**

### Layer Dependencies (One Direction Only)
```
Domain ← Application ← Infrastructure ← Presentation
(Pure)   (Use Cases)   (External)      (UI/API)
```

### Quick Validation
```bash
pwd                    # Should be in project root
which python           # Should show .venv/bin/python
echo $VIRTUAL_ENV      # Should show .venv path
git branch             # Should NOT be on main
```

## 📋 Task Router

**What are you working on?**

| Task Type | Required Reading | Command |
|-----------|------------------|---------|
| Writing Tests | `CLAUDE-TESTING.md` | `cat docs/CLAUDE-TESTING.md` |
| AWS/Infrastructure | `CLAUDE-INFRASTRUCTURE.md` | `cat docs/CLAUDE-INFRASTRUCTURE.md` |
| Domain Logic | `CLAUDE-DOMAIN.md` | `cat docs/CLAUDE-DOMAIN.md` |
| Deployment | `CLAUDE-DEPLOYMENT.md` | `cat docs/CLAUDE-DEPLOYMENT.md` |
| Security Review | `CLAUDE-SECURITY.md` | `cat docs/CLAUDE-SECURITY.md` |
| Debugging Issues | `TROUBLESHOOTING.md` | `cat TROUBLESHOOTING.md` |

## 🔄 Common Workflows

### Starting ANY Work
```bash
cd emoji-smith
source .venv/bin/activate
uv sync --all-extras
git pull origin main
git checkout -b feature/your-feature  # NEVER work on main
```

### Before ANY Commit
```bash
# Explain what you're about to commit
echo "Changes: [describe what you're committing]"

# Run quality checks
./scripts/check-quality.sh  # Must pass

# Add specific files only
git add src/specific/file.py tests/specific/test_file.py

# Commit with conventional message
git commit -m "type(scope): description"
```

### Creating a Pull Request
```bash
# Push feature branch
git push origin feature/your-feature

# Create PR (never merge locally)
gh pr create --title "type: description" --body "Details of changes"

# Let CI handle deployment - NEVER deploy manually
```

### Quick Quality Check
```bash
black src/ tests/ && \
flake8 src/ tests/ && \
mypy src/ && \
bandit -r src/ && \
pytest --cov=src tests/
```

## 🎯 Current Focus Tracking

When working on a feature, maintain context:
```python
# CURRENT TASK: Implementing emoji template feature
# STATUS: Writing tests for domain entity
# NEXT: Implement repository interface
# BLOCKERS: None
```

## 🚦 Go/No-Go Checklist

Before implementing ANYTHING:
- [ ] Is virtual environment active?
- [ ] Am I on a feature branch (not main)?
- [ ] Have I pulled latest changes?
- [ ] Do I have a failing test?
- [ ] Am I in the correct layer?
- [ ] Have I read the relevant CLAUDE-*.md file?
- [ ] Have I explained what I'm about to do?

## 🔍 Architecture Quick Reference

```
src/
├── domain/           # Zero dependencies, pure Python
├── application/      # Orchestrates domain objects
├── infrastructure/   # External world (AWS, Slack, OpenAI)
└── presentation/     # HTTP/API endpoints
```

**Red Flags:**
- Importing `boto3` in domain/
- Direct `os.environ` access outside config
- Concrete classes in domain/repositories/
- Missing `__init__.py` files
- Tests that only test mocks
- Working directly on main branch
- Manual deployments when CI exists

## 🆘 When Stuck

1. Check: Am I on a feature branch?
2. Check: Is venv active?
3. Check: Did I read the task-specific guide?
4. Check: Am I following the architecture layers?
5. Check: Do my tests actually test behavior?
6. Check: Have I explained my approach?

If still stuck: Review `TROUBLESHOOTING.md`

## 📝 Memory Aid

**E.M.O.J.I.S.**
- **E**nvironment activated
- **M**ock external services only
- **O**rchestrate in application layer
- **J**ust domain logic in domain/
- **I**nject all dependencies
- **S**peak about changes (explain them)

---

**Remember:** This document contains ONLY the essential rules. For detailed guidance on specific tasks, always consult the appropriate CLAUDE-*.md file from the Task Router above.
