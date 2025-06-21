# Review Multiple PRs Command

## Purpose
Review multiple pull requests that attempt to address the same issue and select the best implementation.

## Parameters
- **Issue**: The issue number or description being addressed by the pull requests
- **PR Count**: The number of pull requests to review

## Review Process

### 1. Gather PR Information
- List all pull requests related to the specified issue
- Identify the branch names and PR numbers
- Note the authors and current status of each PR

### 2. Prepare Branches
For each pull request:
```bash
# Fetch the latest changes
git fetch origin

# Checkout the PR branch
git checkout <pr-branch-name>

# Rebase with latest main
git rebase origin/main

# Handle any conflicts if they arise
```

### 3. Evaluate Each PR

#### Code Quality Criteria
- **CLAUDE.md Compliance**
  - Uses Python 3.12
  - Follows TDD approach
  - Uses dependency injection
  - No hardcoded dependencies
  - Proper virtual environment usage

- **Security**
  - No hardcoded secrets
  - Proper environment variable usage
  - Passes bandit security scan
  - Uses explicit file specification in git commands

#### Architecture Compliance
- **Domain-Driven Design**
  - Correct layer separation: Infrastructure → Application → Domain
  - Repository pattern for external services
  - No framework coupling in domain layer
  - Immutable value objects using frozen dataclasses

- **File Organization**
  - Domain entities in `src/domain/entities/`
  - Application services in `src/application/services/`
  - Infrastructure implementations in `src/infrastructure/`
  - Proper separation of concerns

#### Testing Standards
- **Test Quality**
  - Tests behavior, not implementation
  - Uses descriptive test names
  - Follows Arrange-Act-Assert pattern
  - Mocks only external dependencies
  - Tests provide meaningful validation
  - No tests that only assert on mocks

- **Test Coverage**
  - Adequate coverage for critical paths
  - Focus on quality over quantity
  - All edge cases tested

#### Design & Simplicity
- **Code Readability**
  - Clear variable and function names
  - Minimal complexity
  - Follows existing patterns
  - Proper error handling

- **Performance Considerations**
  - Efficient async operations
  - Proper use of concurrent execution
  - Lambda optimization for cold starts

### 4. Comparison Matrix

Create a comparison matrix for all PRs:

| Criteria | PR #1 | PR #2 | PR #3 |
|----------|-------|-------|-------|
| Addresses Issue | ✅/❌ | ✅/❌ | ✅/❌ |
| Code Quality | Score/10 | Score/10 | Score/10 |
| Architecture | Score/10 | Score/10 | Score/10 |
| Test Quality | Score/10 | Score/10 | Score/10 |
| Security | Pass/Fail | Pass/Fail | Pass/Fail |
| Simplicity | Score/10 | Score/10 | Score/10 |

### 5. Selection Criteria

The best PR should:
1. **Fully address the issue** without introducing new problems
2. **Follow all architectural patterns** defined in CLAUDE.md
3. **Have high-quality tests** that validate behavior effectively
4. **Be the simplest effective solution** avoiding over-engineering
5. **Pass all quality checks** (black, flake8, mypy, bandit)

### 6. Provide Feedback

Create a detailed review comment on the selected PR:

```markdown
## Pull Request Review

### Summary
This PR was selected as the best implementation for issue #[ISSUE] after reviewing [PR_COUNT] pull requests.

### Why This PR Was Selected
- [Specific strengths of this implementation]
- [How it best addresses the issue]
- [Superior architectural decisions]

### Required Improvements Before Merging
1. **[Category]**: [Specific improvement needed]
   ```python
   # Example code suggestion if applicable
   ```

2. **[Category]**: [Another improvement]

### Optional Enhancements
- [Nice-to-have improvements that could be addressed in follow-up PRs]

### Comparison with Other PRs
- PR #X: [Why it wasn't selected]
- PR #Y: [Why it wasn't selected]

### Final Recommendation
✅ **Approved with changes** - Please address the required improvements above before merging.
```

## Example Usage

```bash
# Review 3 PRs that address issue #225
claude review_prs 225 3

# Review 2 PRs that address "modal validation error"
claude review_prs "modal validation error" 2
```

## Checklist for Review

- [ ] All PRs have been fetched and rebased with main
- [ ] Each PR has been evaluated against all criteria
- [ ] Test quality has been assessed for each PR
- [ ] Security scans have been run
- [ ] Comparison matrix has been completed
- [ ] Best PR has been selected with clear rationale
- [ ] Detailed feedback has been provided on the selected PR
