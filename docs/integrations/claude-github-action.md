# Claude GitHub Action Setup

## Overview
This repository includes a GitHub Action that enables AI-powered assistance through Claude. You can tag `@claude` in issues, pull requests, and comments to get help with code reviews, implementations, and questions.

## Setup Required

### 1. Anthropic API Key
Add your Anthropic API key to repository secrets:
1. Go to repository Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `ANTHROPIC_API_KEY`
4. Value: Your Anthropic API key

### 2. Claude GitHub App (Optional but Recommended)
For enhanced functionality, install the Claude GitHub App:
1. Visit [Claude GitHub App installation page](https://github.com/apps/claude-code)
2. Install to this repository
3. This provides additional permissions and better integration

## How to Use

### Tag @claude in Issues
```markdown
I need help implementing the modal field separation described in issue #170.

@claude can you create a feature branch and implement the two-field modal
with separate emoji name and description fields?
```

### Tag @claude in Pull Request Reviews
```markdown
@claude please review this PR for:
- Compliance with CLAUDE.md coding standards
- Proper test coverage
- Security best practices
```

### Tag @claude in Comments
```markdown
@claude explain how Pub/Sub retries work for the worker service in this codebase
```

## What Claude Can Do

### ✅ Capabilities
- **Code Review**: Analyze PR changes for quality, security, and standards compliance
- **Implementation**: Write code to fix bugs or implement features
- **Explanation**: Explain complex code patterns and architecture decisions
- **Testing**: Generate unit tests following TDD principles
- **Documentation**: Create or update documentation
- **Debugging**: Help diagnose issues and suggest solutions
- **Refactoring**: Improve code structure while maintaining functionality

### ❌ Limitations
- **No Direct Deployment**: Cannot deploy to GCP or trigger production actions directly
- **No Secrets Access**: Cannot view or modify repository secrets
- **No External Services**: Cannot directly interact with Slack, OpenAI, or other APIs
- **Rate Limited**: Subject to API rate limits and GitHub Actions usage limits
- **Beta Software**: Features may change as the integration is in beta

## Best Practices

### 1. Be Specific in Requests
```markdown
# Good
@claude implement the SlackChannel.from_dict() method following the pattern
established in SlackUser.from_dict(), including comprehensive unit tests

# Less helpful
@claude fix the slack stuff
```

### 2. Reference Context
```markdown
@claude looking at issue #172, can you remove the modal opening logic
from the worker service and ensure it only handles emoji generation?
```

### 3. Request Incremental Changes
```markdown
@claude create a feature branch for issue #169 and update just the
instruction text to match current Slack UI
```

## Project-Specific Configuration

Claude is configured to understand this project's specific requirements:
- **Emoji Smith Architecture**: Slack bot with AI emoji generation
- **Tech Stack**: Python 3.12, FastAPI, GCP Cloud Run, Pub/Sub, OpenAI/Google
- **Code Quality**: TDD, DDD, dependency injection, repository patterns
- **Security**: No hardcoded secrets, proper validation, least privilege

## Cost Considerations

- Each `@claude` interaction uses Anthropic API credits
- GitHub Actions minutes are consumed for each run
- Consider using `max_turns: 5` limit to prevent runaway costs
- Monitor usage in repository Insights → Actions

## Troubleshooting

### Action Not Triggering
- Ensure `@claude` is included in your comment/issue
- Check that `ANTHROPIC_API_KEY` secret is configured
- Verify repository permissions allow Actions to run

### Limited Functionality
- Install the Claude GitHub App for full capabilities
- Check GitHub Actions logs for error messages
- Ensure proper permissions in the workflow file

## Security Notes

- Claude can only access public repository content
- Private repository secrets are never exposed to Claude
- All interactions are logged in GitHub Actions for audit trails
- Follow principle of least privilege for any suggested changes
