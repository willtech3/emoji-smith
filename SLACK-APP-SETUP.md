# Slack App Setup Guide

## Step 1: Create Slack App

1. **Go to Slack API Console**
   - Visit [api.slack.com/apps](https://api.slack.com/apps)
   - Click **"Create New App"**
   - Choose **"From scratch"**
   - App Name: `Emoji Smith`
   - Workspace: Select your development workspace

## Step 2: Configure OAuth Scopes

Navigate to **"OAuth & Permissions"** and add these Bot Token Scopes:

**Required Scopes:**
- `emoji:write` - Upload custom emojis to workspace
- `reactions:write` - Add emoji reactions to messages  
- `commands` - Create slash commands
- `chat:write` - Send messages (for notifications)

## Step 3: Configure Message Actions

1. **Navigate to "Interactive Components"**
   - Enable **"Interactive Components"**
   - Request URL: `https://your-ngrok-url.ngrok.io/slack/events` (will update during development)

2. **Create Message Action**
   - Click **"Create New Action"** 
   - Type: **"On messages"**
   - Name: `Create Reaction`
   - Description: `Generate custom emoji reaction`
   - Callback ID: `create_emoji_reaction`

## Step 4: Install App to Workspace

1. **Navigate to "Install App"**
   - Click **"Install to Workspace"**
   - Review permissions and click **"Allow"**

2. **Copy Credentials**
   - **Bot User OAuth Token**: Starts with `xoxb-` (copy to .env as `SLACK_BOT_TOKEN`)
   - **Signing Secret**: From "Basic Information" → "App Credentials" (copy to .env as `SLACK_SIGNING_SECRET`)

## Step 5: Test Message Action

1. **Find any message in Slack**
2. **Right-click the message**
3. **Look for "Create Reaction" in the "More actions" menu**
   - If visible: ✅ Setup successful
   - If missing: ❌ Check message action configuration

## Environment Variables

Add these to your `.env` file:

```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here

# OpenAI Configuration  
OPENAI_API_KEY=your-openai-api-key-here

# Development Settings
LOG_LEVEL=DEBUG
ENVIRONMENT=development
```

## Next Steps

Once Slack app is configured:
1. Start local development server
2. Expose via ngrok
3. Update Slack app webhook URL
4. Test message action triggers webhook

## Troubleshooting

**Message action not appearing:**
- Check OAuth scopes are saved
- Verify message action callback ID
- Ensure app is installed to workspace
- Try refreshing Slack client

**Webhook not receiving events:**
- Verify ngrok is running and URL is correct
- Check Slack app webhook URL matches ngrok
- Look for errors in ngrok web interface (localhost:4040)