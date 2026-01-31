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
  echo "See: /fm:help jira-setup"
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
  /fm:fix-jira-ticket PROJ-123
  /fm:fix-issues PROJ-123 PROJ-456  (parallel)
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
