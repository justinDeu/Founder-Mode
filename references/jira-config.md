# Jira Configuration

How to set up Jira integration for founder-mode.

## Authentication Options

### Option 1: Environment Variables (Recommended)

```bash
export JIRA_DOMAIN="your-domain.atlassian.net"
export JIRA_EMAIL="you@example.com"
export JIRA_API_TOKEN="your-api-token"
```

Get API token from: https://id.atlassian.com/manage-profile/security/api-tokens

### Option 2: Config File

Create `~/.config/founder-mode/jira.json`:

```json
{
  "domain": "your-domain.atlassian.net",
  "email": "you@example.com",
  "api_token": "your-api-token"
}
```

### Option 3: Per-Project Config

Create `.founder-mode/jira.json`:

```json
{
  "domain": "your-domain.atlassian.net",
  "project": "PROJ",
  "email": "you@example.com"
}
```

Note: API token should NOT be in project config (use env var).

## API Token Generation

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Name it "founder-mode" or similar
4. Copy the token (only shown once)
5. Store in JIRA_API_TOKEN env var

## Testing Configuration

```bash
# Test with curl
curl -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "https://$JIRA_DOMAIN/rest/api/3/myself"

# Should return your user info
```

## Common Issues

**401 Unauthorized:**
- Check email matches Jira account
- Regenerate API token
- Verify domain is correct

**403 Forbidden:**
- Check project permissions
- Verify API token has correct scopes

**404 Not Found:**
- Check domain format (no https://)
- Verify project key exists
