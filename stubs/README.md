# Type Stubs Directory

This directory contains custom type stubs for third-party libraries that lack official type definitions or have incomplete type coverage.

## Why Custom Stubs?

These stubs are necessary because:
- Some dependencies don't provide official type stubs
- Existing stubs may be incomplete or outdated
- We need precise type checking for better code quality and IDE support

## Included Stubs

### slack_sdk
- **Purpose**: Provides type hints for Slack SDK async client and response objects
- **Reason**: Official stubs are incomplete for async operations
- **Files**:
  - `errors.pyi`: Exception types with proper response typing
  - `web/async_client.pyi`: Async web client methods
  - `web/async_slack_response.pyi`: Response object structure

### dotenv
- **Purpose**: Type hints for python-dotenv library
- **Reason**: No official stubs available
- **Files**:
  - `dotenv.pyi`: Basic load_dotenv function signature

### Other Libraries
- `fastapi`, `mangum`, `openai`, `uvicorn`: Basic stubs for import resolution

## Maintenance

When updating these stubs:
1. Check if official stubs have become available first
2. Keep stubs minimal - only include what the codebase actually uses
3. Update stubs when new library methods are used
4. Remove stubs when official support becomes available

## Usage

These stubs are automatically discovered by mypy through the `MYPYPATH=stubs` configuration in our type checking commands.
