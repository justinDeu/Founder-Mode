# Jira Integration

## Objective

Implement Jira ticket fetching and the `/founder-mode:list-jira-tickets` command.

## Prerequisites

- 004-01-github-integration.md complete
- lib/issue-types.md exists with NormalizedIssue interface

## Context Files to Read

```
lib/issue-types.md          # NormalizedIssue interface
commands/list-github-issues.md  # Pattern to follow
```

## Deliverables

### 1. Update Issue Types

Update `lib/issue-types.md` to add Jira-specific fields:

```markdown
## Jira-Specific Fields

The NormalizedIssue interface includes optional fields for Jira:

```typescript
interface NormalizedIssue {
  // ... common fields ...

  // Jira-specific
  status?: string;      // "To Do", "In Progress", "Done"
  priority?: string;    // "High", "Medium", "Low"
  issueType?: string;   // "Bug", "Story", "Task"
  sprint?: string;      // Sprint name
  project?: string;     // Project key (PROJ)
}
```

## Parsing Jira Response

From Jira REST API:

```json
{
  "key": "PROJ-123",
  "fields": {
    "summary": "Fix login redirect",
    "description": "Steps to reproduce...",
    "labels": ["bug"],
    "assignee": { "displayName": "User" },
    "status": { "name": "To Do" },
    "priority": { "name": "High" },
    "issuetype": { "name": "Bug" },
    "created": "2026-01-18T10:00:00.000+0000",
    "updated": "2026-01-18T12:00:00.000+0000"
  }
}
```

Map to NormalizedIssue:

```
source: "jira"
id: key
url: "https://{domain}.atlassian.net/browse/{key}"
title: fields.summary
body: fields.description
labels: fields.labels
assignees: [fields.assignee?.displayName]
status: fields.status.name
priority: fields.priority.name
issueType: fields.issuetype.name
created: fields.created
updated: fields.updated
```
```

### 2. Jira Configuration Reference

Create `references/jira-config.md`:

```markdown
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
```

### 3. List Jira Tickets Command

Create `commands/list-jira-tickets.md`:

```markdown
---
name: founder-mode:list-jira-tickets
description: List Jira tickets with filtering
argument-hint: "[--project PROJ] [--assignee me] [--status 'To Do']"
allowed-tools:
  - Bash
  - Read
---

# List Jira Tickets

Fetch and display Jira tickets with filtering options.

## Arguments

Parse from $ARGUMENTS:
- `--project`: Jira project key (required or from config)
- `--assignee`: Filter by assignee (default: currentUser())
- `--status`: Filter by status (e.g., "To Do", "In Progress")
- `--type`: Filter by issue type (Bug, Story, Task)
- `--sprint`: Filter by sprint name
- `--limit`: Max tickets (default: 20)

## Process

### Step 1: Load Configuration

```bash
# Check env vars first
if [ -n "$JIRA_DOMAIN" ] && [ -n "$JIRA_EMAIL" ] && [ -n "$JIRA_API_TOKEN" ]; then
  echo "Using environment configuration"
# Then check user config
elif [ -f ~/.config/founder-mode/jira.json ]; then
  JIRA_DOMAIN=$(jq -r '.domain' ~/.config/founder-mode/jira.json)
  JIRA_EMAIL=$(jq -r '.email' ~/.config/founder-mode/jira.json)
  # Token must come from env
  [ -z "$JIRA_API_TOKEN" ] && {
    echo "ERROR: JIRA_API_TOKEN not set"
    exit 1
  }
# Then check project config
elif [ -f .founder-mode/jira.json ]; then
  JIRA_DOMAIN=$(jq -r '.domain' .founder-mode/jira.json)
  JIRA_PROJECT=$(jq -r '.project' .founder-mode/jira.json)
  JIRA_EMAIL=$(jq -r '.email' .founder-mode/jira.json)
  [ -z "$JIRA_API_TOKEN" ] && {
    echo "ERROR: JIRA_API_TOKEN not set"
    exit 1
  }
else
  echo "ERROR: Jira not configured"
  echo "See: /founder-mode:help jira-setup"
  exit 1
fi
```

### Step 2: Validate Project

```bash
# Project from args or config
PROJECT=${PROJECT_ARG:-$JIRA_PROJECT}

[ -z "$PROJECT" ] && {
  echo "ERROR: No project specified"
  echo "Use --project PROJ or set in config"
  exit 1
}
```

### Step 3: Build JQL Query

```bash
# Base query
JQL="project = $PROJECT"

# Add filters
[ -n "$ASSIGNEE" ] && {
  if [ "$ASSIGNEE" = "me" ]; then
    JQL="$JQL AND assignee = currentUser()"
  else
    JQL="$JQL AND assignee = '$ASSIGNEE'"
  fi
}

[ -n "$STATUS" ] && JQL="$JQL AND status = '$STATUS'"
[ -n "$TYPE" ] && JQL="$JQL AND issuetype = '$TYPE'"
[ -n "$SPRINT" ] && JQL="$JQL AND sprint = '$SPRINT'"

# URL encode
JQL_ENCODED=$(echo "$JQL" | jq -sRr @uri)
```

### Step 4: Fetch Tickets

```bash
RESPONSE=$(curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "https://$JIRA_DOMAIN/rest/api/3/search?jql=$JQL_ENCODED&maxResults=$LIMIT&fields=summary,status,priority,issuetype,assignee,labels,created,updated")
```

### Step 5: Parse and Display

Parse JSON response and display:

```
Jira Tickets ($PROJECT, {count} results)

PROJ-123 [Bug] Fix login redirect loop
         Status: To Do | Priority: High
         Sprint: Sprint 23

PROJ-456 [Story] Add dark mode support
         Status: In Progress | Priority: Medium
         Sprint: Sprint 23

PROJ-789 [Task] Update documentation
         Status: To Do | Priority: Low
         Sprint: Sprint 24

Commands:
  /founder-mode:fix-jira-ticket PROJ-123
  /founder-mode:fix-issues PROJ-123 PROJ-456  (parallel)
```

### Step 6: Handle Errors

**Not configured:**
```
Jira not configured.

Set up with environment variables:
  export JIRA_DOMAIN="your-domain.atlassian.net"
  export JIRA_EMAIL="you@example.com"
  export JIRA_API_TOKEN="your-api-token"

Get API token: https://id.atlassian.com/manage-profile/security/api-tokens
```

**Invalid credentials:**
```
Jira authentication failed (401).

Check:
1. Email matches your Jira account
2. API token is valid (regenerate if needed)
3. Domain format is correct (no https://)
```

**Project not found:**
```
Project '{PROJECT}' not found.

Available projects:
{list from API}
```

**Rate limiting:**
```
Jira API rate limited.

Wait {time} before retrying.
```

## Success Criteria

- [ ] Configuration loading works (env > user config > project config)
- [ ] JQL query built correctly
- [ ] Filtering works
- [ ] Output scannable and useful
- [ ] Error messages guide user to fix
```

## Instructions

### Step 1: Update Issue Types

Add Jira-specific fields to lib/issue-types.md.

### Step 2: Create Reference

Create references/jira-config.md with setup instructions.

### Step 3: Create Command

Create commands/list-jira-tickets.md.

### Step 4: Test Configuration Loading

Verify configuration priority:
1. Environment variables
2. User config (~/.config/founder-mode/jira.json)
3. Project config (.founder-mode/jira.json)

## Verification

- [ ] lib/issue-types.md updated with Jira fields
- [ ] references/jira-config.md exists
- [ ] commands/list-jira-tickets.md exists
- [ ] Configuration loading documented
- [ ] API token instructions included
- [ ] JQL query building documented
- [ ] Error handling covers auth, project, rate limit

## Rollback

```bash
rm references/jira-config.md
rm commands/list-jira-tickets.md
# Restore lib/issue-types.md to GitHub-only version
git checkout -- lib/issue-types.md
```
