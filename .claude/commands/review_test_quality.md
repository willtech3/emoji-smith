# Test Quality Review Command

This command instructs Claude to perform a comprehensive test quality review of the emoji-smith codebase with an aggressive stance on deleting low-value tests.

## Core Philosophy: Developer Confidence Over Coverage

**Coverage is the LEAST important metric.** A test suite with 50% coverage of high-quality, behavior-focused tests is far superior to 100% coverage filled with brittle, mock-heavy tests that break on every refactor.

## Step 1: Read and Understand Testing Standards

1. Read `CLAUDE.md` and focus specifically on:
   - Testing philosophy (TDD approach)
   - Mock usage guidelines (what to mock vs what not to mock)
   - Test naming conventions (descriptive behavior-focused names)
   - Arrange-Act-Assert pattern requirements
   - **Note: Coverage requirements are secondary to test quality**

2. Read `docs/testing/testing-guidelines.md` for additional testing standards and quality criteria

## Step 2: Review Every Test in the Repository

Analyze each test file in the `tests/` directory and evaluate against these quality criteria:

### Tests Recommended for IMMEDIATE DELETION:
- **Mock-only tests** - Tests that only assert mock was called with certain arguments
- **Implementation detail tests** - Tests that break when refactoring without changing behavior
- **Private method tests** - Any test accessing private/protected methods
- **Tautological tests** - Tests that can never fail or test framework behavior
- **Over-specified tests** - Tests with excessive assertions on internal state

### Red Flags for Deletion:
- Test has more mock setup than actual business logic
- Test name describes HOW not WHAT (e.g., "test_calls_repository_save" vs "test_user_registration_persists_data")
- Test would pass even if the feature was completely broken
- Test only verifies method calls, not outcomes
- Test couples to specific implementation choices

### The Developer Confidence Test:
Ask for EVERY test: **"If this test fails, would a developer immediately understand what user-facing functionality is broken?"**
- If NO → **DELETE IT**
- If MAYBE → Probably delete it
- If YES → Keep and potentially improve

### Review Checklist for Each Test:
- [ ] Does this test increase developer confidence? If no → **DELETE**
- [ ] Would this test catch a real bug that affects users? If no → **DELETE**
- [ ] Does this test only assert on mocks? If yes → **DELETE**
- [ ] Would this test break if we refactored without changing behavior? If yes → **DELETE**
- [ ] Is this testing a private method or internal implementation? If yes → **DELETE**
- [ ] Does the test name clearly describe user-facing behavior? If no → Fix or **DELETE**

## Step 3: Generate Quality Review Report

Create a comprehensive test quality review report at:
`docs/testing/historical/test_quality_review_MM_DD_YYYY.md`

The report should follow the format of `docs/testing/historical/test_review_06_19.md` and include:

1. **Executive Summary**
   - Number of tests recommended for DELETION
   - Number of high-value tests that build developer confidence
   - Most problematic test patterns found
   - **DO NOT focus on coverage metrics**

2. **Tests Recommended for Deletion**
   - Group by reason (mock-only, implementation details, etc.)
   - Provide specific file paths and test names
   - Include brief explanation of why each provides no value
   - **Be ruthless - if in doubt, recommend deletion**

3. **High-Value Tests (Examples of What We Want)**
   - Tests that clearly map to user functionality
   - Tests that would catch real regressions
   - Tests that serve as living documentation
   - Tests that give developers confidence to refactor

4. **Systemic Issues**
   - Patterns of low-value testing across modules
   - Over-reliance on mocks in certain areas
   - Tests that exist solely to boost coverage metrics

5. **Action Plan**
   - Immediate: Which tests to delete TODAY
   - Short-term: Patterns to stop using
   - Long-term: Cultural shift needed in testing approach

6. **The Bottom Line**
   - Estimated reduction in test count after deletions
   - Expected IMPROVEMENT in test suite quality
   - Time saved in maintenance by removing brittle tests

## Execution Note

When executing this command, Claude should:
1. Use the TodoWrite tool to track progress through the review
2. Process tests systematically by directory/module
3. Provide specific, actionable feedback
4. Focus on improving test quality, not just finding problems
