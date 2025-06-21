# Architecture Review Command

## Purpose
Perform a comprehensive review of the codebase's adherence to Domain-Driven Design (DDD) architecture principles, balancing architectural purity with practical simplicity for a personal project.

## Review Process

### Step 1: Review Architecture Guidance
First, thoroughly read and understand the architecture guidance in `CLAUDE.md`, paying special attention to:
- The Domain-Driven Design principles section
- Architecture rules and constraints
- Known architecture limitations
- The balance between clean architecture and practical implementation

### Step 2: Review Architecture Decision Records
Read all ADR (Architecture Decision Record) files in `docs/adr/` to understand:
- Historical architectural decisions
- Trade-offs that were considered
- Context behind current design choices
- Evolution of the architecture over time

### Step 3: Comprehensive Codebase Assessment
Analyze the entire codebase with focus on:

#### Domain Layer Analysis
- Check for business logic purity (no external dependencies)
- Verify proper use of entities and value objects
- Assess domain service implementations
- Review repository interfaces (protocols)

#### Application Layer Analysis
- Evaluate use case orchestration
- Check for proper separation of concerns
- Verify dependency injection patterns
- Review application service implementations

#### Infrastructure Layer Analysis
- Assess external service integrations
- Check for proper abstraction of AWS services
- Review Slack and OpenAI implementations
- Verify repository implementations

#### Presentation Layer Analysis
- Review HTTP/API layer organization
- Check for proper request/response handling
- Verify separation from business logic

#### Cross-Cutting Concerns
- Dependency direction compliance (Infrastructure → Application → Domain)
- Framework coupling assessment
- Test coverage and quality
- Security best practices adherence

### Step 4: Generate Report
Create a detailed report in `docs/architecture/historical/arch_quality_report_<month>_<day>_<year>.md` following the format of existing reports (e.g., `arch_quality_report_06_19.md`).

## Report Structure

The report should include:

1. **Executive Summary**
   - Overall architecture health score
   - Key findings
   - Critical issues requiring attention

2. **Layer-by-Layer Analysis**
   - Current state assessment
   - Compliance with DDD principles
   - Identified violations or concerns
   - Recommendations for improvement

3. **Positive Findings**
   - Well-implemented patterns
   - Good architectural decisions
   - Areas demonstrating proper DDD principles

4. **Areas for Improvement**
   - Architectural violations
   - Technical debt
   - Overly complex abstractions
   - Pragmatic simplifications needed

5. **Recommendations**
   - Priority-ordered list of improvements
   - Balance between ideal architecture and practical implementation
   - Specific refactoring suggestions

## Important Considerations

### Pragmatic Balance
Remember that this is a personal project. The review should:
- Avoid recommending overly complex decouplings that add little value
- Focus on maintainability and clarity over architectural purity
- Consider the cost/benefit of architectural changes
- Prioritize changes that improve code quality without adding unnecessary complexity

### Red Flags to Watch For
- Business logic in infrastructure layer
- Direct framework dependencies in domain layer
- Missing or improper dependency injection
- Overly complex abstractions for simple problems
- Circular dependencies between layers

### Green Flags to Highlight
- Clear separation of concerns
- Testable code structure
- Proper use of repository pattern
- Clean dependency flow
- Pragmatic simplifications that maintain clarity

## Usage
To execute this architecture review:
```
/claude review_arch
```

The review will analyze the entire codebase and generate a comprehensive report documenting the current state of the architecture and recommendations for improvement.
