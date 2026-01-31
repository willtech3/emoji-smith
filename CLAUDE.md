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
10. **📖 ALWAYS read documentation hierarchy** - Root → intermediate → local CLAUDE.md files

## 🏗️ Architecture Constraints (IMMUTABLE)

### Fixed Production Entry Points (GCP)
These are the deployed Cloud Run apps and should remain stable:
```
src/emojismith/infrastructure/gcp/webhook_app.py  # < 3s response (Slack)
src/emojismith/infrastructure/gcp/worker_app.py   # async processing (Pub/Sub)
```

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

## 📖 Documentation Hierarchy

**CLAUDE.md files are now co-located with the code they describe:**

```
/CLAUDE.md                    # Root - Core rules (this file)
├── src/
│   ├── CLAUDE.md            # Security guidelines for all source
│   └── emojismith/
│       ├── domain/
│       │   └── CLAUDE.md    # Domain layer guidelines
│       └── infrastructure/
│           └── CLAUDE.md    # Infrastructure guidelines
├── tests/
│   └── CLAUDE.md            # Testing guidelines
└── .github/
    └── CLAUDE.md            # Deployment and CI/CD guidelines
```

### Reading Order (MANDATORY)
1. **Always start with root CLAUDE.md** (this file) - contains critical rules
2. **Read intermediate CLAUDE.md files** along your path
3. **Read the most specific CLAUDE.md** for your current work

### Rule Precedence
- More specific rules extend general ones
- CRITICAL RULES from root are NEVER overridden
- Each CLAUDE.md clearly marks its inheritance

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
ruff format src/ tests/ && \
ruff check src/ tests/ && \
mypy src/ && \
pytest tests/
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
- [ ] Have I read the relevant CLAUDE.md files (root → intermediate → local)?
- [ ] Have I explained what I'm about to do?

## 🔍 Architecture Quick Reference

```
src/
├── domain/           # Zero dependencies, pure Python
├── application/      # Orchestrates domain objects
├── infrastructure/   # External world (GCP, Slack, OpenAI, Gemini)
└── presentation/     # HTTP/API endpoints
```

**Red Flags:**
- Importing cloud provider SDKs in domain/
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

**Remember:** This document contains ONLY the essential rules. For detailed guidance on specific tasks, always consult the appropriate CLAUDE.md file in the relevant directory following the documentation hierarchy.
