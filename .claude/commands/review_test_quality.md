# Test Quality Review Command

This command instructs Claude to perform a comprehensive test quality review of the emoji-smith codebase with an aggressive stance on deleting low-value tests.

## Core Philosophy: Developer Confidence Over Coverage

**Coverage is the LEAST important metric.** A test suite with 50% coverage of high-quality, behavior-focused tests is far superior to 100% coverage filled with brittle, mock-heavy tests that break on every refactor.

## Step 1: Read and Understand Testing Standards

1. Read `tests/CLAUDE.md` for testing-specific guidelines
2. Read `docs/testing/testing-guidelines.md` for detailed testing standards and quality criteria
3. Focus specifically on:
   - Testing philosophy (TDD approach)
   - Mock usage guidelines (what to mock vs what not to mock)
   - Test naming conventions (descriptive behavior-focused names)
   - Arrange-Act-Assert pattern requirements
   - **Note: Coverage requirements are secondary to test quality**

## Step 2: Count Tests Accurately

First, get an accurate test count using this method:
```bash
# Count test functions (not including parameterized expansions)
find tests -name "test_*.py" -o -name "*_test.py" | xargs grep -h "^\s*\(async \)\?def test_" | wc -l
```

Note: This counts test FUNCTIONS, not test INSTANCES. Parameterized tests will be counted as 1 function even though they may run multiple times with different parameters.

## Step 3: Review Every Test in the Repository

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

## Step 4: Check Previous Reports

Before generating the new report, check for the most recent test quality review in `docs/testing/historical/` to:
- Note the previous quality score
- Identify which recommendations were implemented
- Track progress on systemic issues
- Calculate improvement or regression metrics

## Step 5: Generate Quality Review Report

Create a comprehensive test quality review report at:
`docs/testing/historical/test_quality_review_MM_DD_YYYY.md`

The report MUST include:

### 1. **Executive Summary**
- **Overall Test Suite Quality Score: X.X/10** (objective metric)
- **Change from Previous Report**: +X.X or -X.X (with date of previous report)
- Number of tests recommended for DELETION
- Number of high-value tests that build developer confidence
- Most problematic test patterns found
- **DO NOT focus on coverage metrics**

### Key Strengths
- ✅ List what's working well (e.g., excellent domain test isolation)
- ✅ Highlight best practices being followed
- ✅ Note areas of improvement since last review
- ✅ Call out exemplary test patterns worth replicating

### Current Issues
- ⚠️ Primary problems affecting test quality
- ⚠️ Systemic issues that need addressing
- ⚠️ Areas where tests provide false confidence
- ⚠️ Missing critical test scenarios

### 2. **Quality Score Breakdown** (following the pattern from architecture reports)
```
Test Suite Quality Score: X.X/10

Scoring Criteria:
- Behavior Focus (3.0): How well tests verify behavior vs implementation
- Mock Usage (2.0): Appropriate use of mocks vs over-mocking
- Test Clarity (2.0): Clear test names and intent
- Maintenance Burden (2.0): How brittle/stable the tests are
- Bug Detection (1.0): Ability to catch real bugs

Layer Breakdown:
- Domain Tests: X.X/10
- Application Tests: X.X/10
- Infrastructure Tests: X.X/10
- Integration Tests: X.X/10
- Security Tests: X.X/10
```

### 3. **Comparison with Previous Report**
- Previous Score: X.X/10 (date)
- Current Score: X.X/10
- Improvement/Regression: +/-X.X
- Implemented Recommendations: List what was done
- Outstanding Issues: What remains from previous report

### 4. **Tests Recommended for Deletion**
- Group by reason (mock-only, implementation details, etc.)
- Provide specific file paths and test names
- Include brief explanation of why each provides no value
- **Be ruthless - if in doubt, recommend deletion**

### 5. **Tests Recommended for Improvement**
- Specific tests that could be valuable with changes
- What changes would make them valuable
- Priority order for improvements

### 6. **High-Value Tests (Examples of What We Want)**
- Tests that clearly map to user functionality
- Tests that would catch real regressions
- Tests that serve as living documentation
- Tests that give developers confidence to refactor

### 7. **Systemic Issues**
- Patterns of low-value testing across modules
- Over-reliance on mocks in certain areas
- Tests that exist solely to boost coverage metrics
- Progress on issues from previous report

### 8. **Action Plan**
- Immediate: Which tests to delete TODAY
- Short-term: Patterns to stop using
- Long-term: Cultural shift needed in testing approach

### 9. **Test Distribution by Category**

Create a table showing test distribution across layers:
```
| Category | File Count | Test Count | Quality | Tests to Delete |
|----------|------------|------------|---------|-----------------|
| Domain Layer | XX | XX | X.X/10 | XX |
| Application Layer | XX | XX | X.X/10 | XX |
| Infrastructure Layer | XX | XX | X.X/10 | XX |
| Integration Tests | XX | XX | X.X/10 | XX |
| Security Tests | XX | XX | X.X/10 | XX |
| Performance Tests | XX | XX | X.X/10 | XX |
| E2E Tests | XX | XX | X.X/10 | XX |
| Contract Tests | XX | XX | X.X/10 | XX |
| Presentation Layer | XX | XX | X.X/10 | XX |
| Other/Fixtures | XX | XX | N/A | XX |
| **TOTAL** | **XX** | **XXX** | **X.X/10** | **XX** |
```

### 10. **Metrics Summary**
```
Before Cleanup:
- Total Tests: XXX (counted as test functions, not instances)
- Mock-Only Tests: XX (X%)
- Implementation Detail Tests: XX (X%)
- High-Value Tests: XXX (X%)

After Proposed Cleanup:
- Total Tests: XXX (-XX)
- Mock-Only Tests: 0 (0%)
- Implementation Detail Tests: 0 (0%)
- High-Value Tests: XXX (100%)

Test Counting Method:
- Test functions: XXX (using grep "def test_")
- Parameterized tests: XX functions (expand to ~XX instances at runtime)
- Total runtime tests: ~XXX (approximate, varies based on parameters)
```

### 11. **The Bottom Line**
- Estimated reduction in test count after deletions
- Expected IMPROVEMENT in test suite quality
- Time saved in maintenance by removing brittle tests
- Path to next quality level (e.g., "To reach 9.0/10, focus on...")

## Execution Note

When executing this command, Claude should:
1. Use the TodoWrite tool to track progress through the review
2. **ALWAYS count tests using the specified method** (grep for test functions, not runtime instances)
3. Check previous reports to calculate improvement metrics
4. Process tests systematically by directory/module
5. Provide specific, actionable feedback
6. Calculate an objective quality score based on defined criteria
7. Focus on improving test quality, not coverage numbers
8. Bias strongly toward deleting low-value tests
9. **Ensure consistency**: Every report should use the same counting method and scoring criteria

### Test Count Consistency:
- **Always report test FUNCTIONS** (what developers write), not test instances (what pytest runs)
- **Note parameterized tests separately** to explain any discrepancy with CI
- **Example**: "331 test functions (342 instances when parameterized tests expand)"
- This ensures every report uses the same baseline for comparison
