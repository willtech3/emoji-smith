# Claude Agent Instructions - MANDATORY Git Workflow

## 🤖 When This Document Applies

You are operating as an automated agent when:
- The conversation starts with "GitHub Issue #" or similar task assignment
- You were invoked via `claude-agent` command
- The user explicitly states you're running in automated mode
- You're asked to review a PR, analyze code, or investigate issues

**If ANY of the above are true, you MUST follow this document instead of CLAUDE.md**

## 🎯 Mandatory GitHub Deliverables

**EVERY task MUST produce ONE of these GitHub artifacts:**

| Task Type | Required GitHub Output |
|-----------|----------------------|
| Code Changes | Pull Request with implementation |
| Code Review | PR review comments |
| Security Audit | Security issue(s) or PR comment |
| Architecture Review | Issue with findings or PR comment |
| Performance Analysis | Issue with metrics or PR comment |
| Bug Investigation | Issue comment with root cause |
| Documentation Review | PR with fixes or issue with findings |

**Task Completion = GitHub Artifact Created**
- No GitHub interaction = Task NOT complete
- Silent completion = FAILURE
- "I've reviewed the code" without posting = FAILURE

## 🚨 CRITICAL: Git Workflow Requirements

**THESE RULES ARE MANDATORY AND MUST BE FOLLOWED FOR EVERY TASK:**

### 1. ALWAYS Create a Feature Branch
```bash
# FIRST COMMAND when starting ANY work:
git checkout main
git pull origin main
git checkout -b fix/issue-NUMBER-description  # or feature/issue-NUMBER-description
```

### 2. NEVER Work on Main Branch
- If you find yourself on main branch, STOP immediately
- Create a feature branch before making ANY changes
- Check current branch with: `git branch --show-current`

### 3. ALWAYS Commit Your Work
```bash
# After making changes:
git add <specific-files>  # NEVER use git add .
git commit -m "type(scope): description"
```

### 4. ALWAYS Push and Create PR
```bash
# Push your branch:
git push -u origin YOUR-BRANCH-NAME

# Create PR using GitHub CLI:
gh pr create --title "type: description" --body "## Summary
- Fixed issue #NUMBER
- [List changes]

## Test plan
- [ ] All tests pass
- [ ] Quality checks pass

🤖 Generated with Claude Agent"
```

## 📋 Workflow Templates

### For Code Changes (Issues/Features/Fixes)

When assigned an issue, ALWAYS follow this exact sequence:

```bash
# 1. Setup
cd emoji-smith
source .venv/bin/activate
git checkout main
git pull origin main
git checkout -b fix/issue-NUMBER-short-description

# 2. Make changes
# ... your code changes ...

# 3. Quality checks
./scripts/check-quality.sh

# 4. Commit
git add src/specific/file.py tests/specific/test_file.py
git commit -m "fix(scope): resolve issue #NUMBER - description"

# 5. Push and PR
git push -u origin fix/issue-NUMBER-short-description
gh pr create --title "fix: resolve issue #NUMBER - description" \
  --body "## Summary
Fixes #NUMBER

[Describe what was changed]

## Changes
- [List specific changes]

## Test plan
- [ ] All existing tests pass
- [ ] Added new tests for changes
- [ ] Quality checks pass

🤖 Generated with Claude Agent"
```

### For Code Reviews (PR Analysis)

When asked to review a PR:

```bash
# 1. Setup
cd emoji-smith
source .venv/bin/activate
git pull origin main

# 2. Checkout PR
gh pr checkout <PR-number>
# OR
git fetch origin pull/<PR-number>/head:pr-<PR-number>
git checkout pr-<PR-number>

# 3. Perform review
# - Run tests
# - Check code quality
# - Review changes

# 4. Post review (MANDATORY)
gh pr review <PR#> --comment --body "## Code Review

### Summary
[Overall assessment]

### Strengths
- [What's done well]

### Issues Found
- [Any problems]

### Suggestions
- [Improvements]

🤖 Generated with Claude Agent"
```

### For General Analysis (Security/Architecture/Performance)

When asked to analyze without a specific PR:

```bash
# 1. Setup
cd emoji-smith
source .venv/bin/activate
git pull origin main

# 2. Perform analysis
# [Your analysis work]

# 3. Create issue with findings (MANDATORY)
gh issue create --title "Analysis: [Type] - [Summary]" \
  --body "## Analysis Results

### Scope
[What was analyzed]

### Findings
[Detailed findings]

### Recommendations
[Action items]

🤖 Generated with Claude Agent"
```

## 🛑 Common Mistakes to Avoid

1. **Working on main branch** - ALWAYS create a feature branch
2. **Not committing changes** - ALWAYS commit before ending session
3. **Not creating PR** - ALWAYS create PR after pushing
4. **Using git add .** - ALWAYS add specific files
5. **Forgetting to push** - ALWAYS push your branch

## 🔍 Self-Check Questions

Before completing ANY task, verify:
- [ ] Am I on a feature branch? (`git branch --show-current` should NOT show "main")
- [ ] Have I committed my changes? (`git status` should show "nothing to commit")
- [ ] Have I pushed my branch? (`git push` should say "Everything up-to-date")
- [ ] Have I created a PR? (Should have PR URL from `gh pr create`)

## 💡 Branch Naming Convention

Use these prefixes:
- `fix/issue-NUMBER-description` - For bug fixes
- `feature/issue-NUMBER-description` - For new features
- `refactor/issue-NUMBER-description` - For refactoring
- `test/issue-NUMBER-description` - For test improvements
- `docs/issue-NUMBER-description` - For documentation

## 📝 Commit Message Format

Follow conventional commits:
- `fix(scope): description` - Bug fixes
- `feat(scope): description` - New features
- `refactor(scope): description` - Code refactoring
- `test(scope): description` - Test changes
- `docs(scope): description` - Documentation

## 🚀 Example: Complete Issue Resolution

```bash
# Issue #263: Refactor tests that access private methods

# 1. Start work
cd emoji-smith
source .venv/bin/activate
git checkout main
git pull origin main
git checkout -b refactor/issue-263-remove-private-method-tests

# 2. Make changes
# [Edit test files to remove private method access]

# 3. Run tests
pytest tests/

# 4. Quality check
./scripts/check-quality.sh

# 5. Commit changes
git add tests/unit/infrastructure/test_slack_signature_validator.py
git add tests/unit/domain/services/test_webhook_security_service.py
# ... add other changed files ...
git commit -m "refactor(tests): remove private method access from tests - fixes #263"

# 6. Push branch
git push -u origin refactor/issue-263-remove-private-method-tests

# 7. Create PR
gh pr create --title "refactor: remove private method access from tests - fixes #263" \
  --body "## Summary
Fixes #263

Refactored all tests that were accessing private methods to use public APIs instead.

## Changes
- Updated SlackSignatureValidator tests to use public validate() method
- Refactored AWS Secrets Loader tests to avoid singleton manipulation
- Modified webhook security tests to test through public interfaces
- [etc...]

## Test plan
- [x] All tests pass
- [x] No private methods accessed in tests
- [x] Test coverage maintained
- [x] Quality checks pass

🤖 Generated with Claude Agent"
```

## 🔒 Final Reminder

**NEVER SKIP THESE STEPS:**
1. Create feature branch
2. Make changes
3. Commit changes
4. Push branch
5. Create PR

If you complete work without creating a PR, the work is NOT complete and may be lost!
