# Changelog

All notable changes to the Emoji Smith project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive testing guidelines extracted from test review
- Documentation reorganization with clear structure
- Type stubs for third-party libraries (slack_sdk, dotenv)
- OpenTelemetry-based tracing + metrics with GCP exporters (Cloud Trace + Cloud Monitoring)

### Changed
- Reorganized documentation into topic-based directories
- Updated docs and guidance for GCP (Cloud Run + Pub/Sub) production deployment
- Structured JSON logs now include Cloud Logging trace correlation fields when tracing is enabled

### Removed
- Deleted 5 mock-only tests that provided no value (#262)
- Removed obsolete .old.md documentation files

## [2.0.0] - 2026-01-31

### Added
- GCP production architecture documentation (in README.md)
- ADR-004 documenting migration to GCP
- Unit tests for GCP Pub/Sub + Cloud Run adapters

### Changed
- Production deployment target is now GCP (Cloud Run + Pub/Sub)
- Local dev server runs the Cloud Run webhook app

### Removed
- AWS infrastructure and deployment artifacts (CDK, Lambda handlers, SQS queue, AWS GitHub Actions workflows)

## [1.2.0] - 2024-06-21

### Added
- Dual Lambda architecture for improved performance and scalability
- SQS queue integration for asynchronous emoji generation
- Comprehensive troubleshooting documentation
- Architecture Decision Records (ADRs) for key design choices
- Helper scripts for development workflow

### Changed
- Split webhook and worker handlers into separate Lambda functions
- Improved cold start performance with minimal webhook dependencies
- Enhanced error handling and retry mechanisms

### Fixed
- Resolved all high-priority DDD violations from architecture review
- Fixed circular dependencies between bounded contexts
- Corrected test coverage gaps identified in test review

## [1.1.0] - 2024-06-19

### Architecture Improvements (from arch_quality_report_06_19.md)

#### ✅ Resolved Issues
- **Fixed Repository Abstraction Violations**: All repositories now properly implement abstract interfaces
- **Eliminated Direct Infrastructure Access**: Domain layer no longer imports from infrastructure
- **Proper Async Patterns**: All async methods properly awaited and error handled
- **Consistent Error Handling**: Domain-specific exceptions implemented across all layers

#### ⚠️ Partially Resolved
- **Bounded Context Separation**: Significant improvements made, some minor coupling remains
- **Test Quality**: Removed mock-only tests, improved behavior testing

#### 📋 Still Pending
- **Value Object Immutability**: Some entities still need conversion to frozen dataclasses
- **Service Layer Orchestration**: Additional refactoring needed for complex workflows

## [1.0.0] - 2024-06-12

### Initial Release
- Basic Slack app integration
- OpenAI gpt-image-1 emoji generation
- Modal-based user interface
- Single Lambda deployment
- Core domain model implementation

## Test Review Status (from test_review_06_19.md)

### Test Quality Improvements
- **Deleted**: 5 mock-only tests that tested implementation rather than behavior
- **Refactored**: 15 tests to focus on behavior verification
- **Added**: Integration tests for dual Lambda architecture
- **Coverage**: Maintained >90% coverage after cleanup

### Ongoing Test Initiatives
- Continuous test quality monitoring
- Regular removal of obsolete tests
- Focus on behavior-driven testing

## DDD Compliance Status (from github_issues_ddd_compliance.md)

### Completed Refactoring
- ✅ Issue #1: Repository pattern implementation
- ✅ Issue #2: Bounded context separation
- ✅ Issue #3: Infrastructure abstraction
- ✅ Issue #4: Webhook handler modularization
- ✅ Issue #5: Domain event implementation

### Architecture Decisions
See [Architecture Decision Records](./adr/) for detailed rationale behind major design choices:
- [ADR-001](./adr/001-use-ddd-architecture.md): Domain-Driven Design adoption
- [ADR-002](./adr/002-two-lambda-separation.md): Separate webhook and worker services
- [ADR-003](./adr/003-repository-pattern.md): Repository pattern implementation
- [ADR-004](./adr/004-migrate-to-gcp.md): Migration to GCP (Cloud Run + Pub/Sub)

## Migration Guide

### From 1.0.0 to 1.2.0
1. Update CDK deployment to use dual Lambda configuration
2. Configure SQS queue for async processing
3. Update environment variables for both Lambda functions
4. Review and update webhook timeout settings

## Future Roadmap

### Planned Improvements
- [ ] Implement caching layer for frequently used emojis
- [ ] Add support for animated emoji generation
- [ ] Implement rate limiting per workspace
- [ ] Add emoji usage analytics
- [ ] Support for custom emoji templates

### Technical Debt Backlog
- [ ] Complete value object immutability refactoring
- [ ] Implement comprehensive domain events
- [ ] Add performance monitoring and alerting
- [ ] Enhance integration test coverage

---

For detailed architecture documentation, see [docs/architecture/](./architecture/).
For testing guidelines, see [docs/guides/testing.md](./guides/testing.md).
