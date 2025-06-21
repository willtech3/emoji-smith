# AGENTS Development Guidelines for Emoji Smith

This document provides **concise rules** for **AI-powered coding agents** (ChatGPT, Claude, Copilot, etc.) contributing to *Emoji Smith*.

> **If conflicting with `CLAUDE.md`, defer to `CLAUDE.md`.**

---

## 1. Critical Environment Setup

**⚠️ BEFORE ANY COMMAND, activate the virtual environment:**

```bash
source .venv/bin/activate  # Linux/Mac (REQUIRED!)
# or
.venv\Scripts\activate     # Windows (REQUIRED!)

# After branch switches or pulls:
uv sync --all-extras
```

**Without activation, you WILL encounter type errors and missing dependencies!**

## 2. Environment & Tooling

1. **Python 3.12** is mandatory
2. Use **uv** for dependency management
3. Virtual environment **must** be activated before any operation
4. All quality checks must pass:
   ```bash
   black --check src/ tests/
   flake8 src/ tests/
   mypy src/
   bandit -r src/
   pytest --cov=src --cov-fail-under=80 tests/
   ```

## 3. Architecture Rules

1. Follow **Domain-Driven Design (DDD)**:
   - Domain layer: Zero external dependencies
   - Repository interfaces in domain, implementations in infrastructure
   - Dependency injection everywhere
2. **Lambda handlers** stay in `infrastructure/aws/` (deployment constraint)
3. **No `os.environ`** access outside infrastructure layer
4. All external calls through **repository interfaces**

## 4. Coding Standards

1. **PEP-8** via black formatter
2. **Type hints** on all functions and class attributes
3. **Dataclasses** for data structures
4. **Protocols** for interfaces/abstract contracts
5. Test **behavior**, not implementation

## 5. Test-Driven Development

1. **Red → Green → Refactor** for every feature
2. Test pyramid: Many unit tests, few integration, minimal E2E
3. Mock only external services (AWS, Slack, OpenAI)
4. Never mock domain logic or value objects
5. Coverage: 80% overall, 90% domain, 85% application

## 6. Security Rules (Non-Negotiable)

1. **NEVER** use `git add .` - specify files explicitly
2. **NEVER** commit secrets, tokens, or `.env` files
3. Run **bandit** and fix all medium/high findings
4. Secrets: `.env` locally, AWS Secrets Manager in production

## 7. Git Workflow

1. Feature branches: `feature/description`
2. Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`
3. Squash-merge to main after review
4. Main auto-deploys via CDK

## 8. Quick Commands

```bash
# Setup (once)
uv venv && source .venv/bin/activate
uv sync --all-extras
pre-commit install

# Before every commit
source .venv/bin/activate  # CRITICAL!
black src/ tests/
flake8 src/ tests/
mypy src/
bandit -r src/
pytest --cov=src tests/

# Commit (explicit files only)
git add src/specific_file.py tests/test_specific.py
git commit -m "feat: add specific feature"
```

## 9. PR Checklist

- [ ] Virtual environment was activated
- [ ] All tests pass with coverage ≥ 80%
- [ ] No security warnings from bandit
- [ ] Type checking passes (mypy)
- [ ] Code formatted (black)
- [ ] No linting errors (flake8)
- [ ] Only intended files staged (no `git add .`)
- [ ] No secrets in code

## 10. Lambda & Deployment Notes

- Entry point: `src/emojismith/infrastructure/aws/webhook_handler.py`
- Uses **Mangum** to adapt FastAPI → Lambda
- Two lambdas: webhook (fast response) and worker (image generation)
- CI/CD: code quality → security → tests → Docker → CDK deploy

## 11. Common Gotchas

1. **Mypy errors** → Activate venv and run `uv sync --all-extras`
2. **Import errors** → Check if dependency is in correct group
3. **Test failures** → Don't over-mock; test real behavior
4. **CDK deploy fails** → Lambda handlers must stay in `infrastructure/aws/`

---

### Single-Line Rules for Prompts

* "Always activate .venv before any command"
* "Use Python 3.12, format with black, type everything"
* "Write tests first, coverage ≥ 80%"
* "Never use `git add .` or commit secrets"
* "Mock only external services, inject all dependencies"
* "Domain layer has zero framework dependencies"

---

**Maintained in sync with CLAUDE.md**
