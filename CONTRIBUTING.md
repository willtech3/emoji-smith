# Contributing to Emoji Smith

Thank you for considering a contribution! This project follows strict development guidelines. Make sure to read `CLAUDE.md` and `AGENTS.md` before you start.

## Test Naming Conventions

All test functions must follow the pattern:

```
test_<unit_under_test>_<scenario>_<expected_outcome>
```

Example:

```
def test_slack_client_when_rate_limited_retries_three_times():
    ...
```

This convention keeps tests self-documenting and easier to understand. A custom lint check enforces this rule. Run `./scripts/check-quality.sh` before committing to ensure compliance.
