# GitHub Integration

## Objective

Implement GitHub issue fetching and the `/founder-mode:list-github-issues` command. This is the foundation for the /fix-gh-issue workflow.

## Prerequisites

- Phase 3 complete
- commands/ directory with project management commands

## Context Files to Read

```
commands/execute-phase.md   # For command pattern
```

## Deliverables

### 1. Issue Types

Create `lib/issue-types.md`:

```markdown
# Issue Types

Normalized issue interface used across GitHub and Jira integrations.

## NormalizedIssue

```typescript
interface NormalizedIssue {
  source: "github" | "jira";
  id: string;           // "123" or "PROJ-123"
  url: string;          // Full URL to issue
  title: string;
  body: string;
  labels: string[];
  assignees: string[];
  milestone?: string;
  created: string;      // ISO timestamp
  updated: string;      // ISO timestamp
  // Source-specific fields
  status?: string;      // Jira status
  priority?: string;    // Jira priority
  issueType?: string;   // Bug, Story, Task
}
```

## Parsing GitHub Response

From `gh issue view --json`:

```json
{
  "number": 123,
  "title": "Fix login redirect",
  "body": "Steps to reproduce...",
  "labels": [{"name": "bug"}],
  "assignees": [{"login": "user"}],
  "milestone": {"title": "v1.0"},
  "createdAt": "2026-01-18T10:00:00Z",
  "updatedAt": "2026-01-18T12:00:00Z"
}
```

Map to NormalizedIssue:

```
source: "github"
id: number.toString()
url: "https://github.com/{owner}/{repo}/issues/{number}"
title: title
body: body
labels: labels.map(l => l.name)
assignees: assignees.map(a => a.login)
milestone: milestone?.title
created: createdAt
updated: updatedAt
```
```

### 2. List GitHub Issues Command

Create `commands/list-github-issues.md`:

```markdown
---
name: founder-mode:list-github-issues
description: List GitHub issues with filtering
argument-hint: "[--assignee @me] [--label bug] [--state open]"
allowed-tools:
  - Bash
  - Read
---

# List GitHub Issues

Fetch and display GitHub issues with filtering options.

## Arguments

Parse from $ARGUMENTS:
- `--assignee`: Filter by assignee (default: @me)
- `--label`: Filter by label (repeatable)
- `--state`: open | closed | all (default: open)
- `--limit`: Max issues (default: 20)
- `--repo`: Override repo (default: current repo)

## Process

### Step 1: Check gh CLI

```bash
command -v gh >/dev/null 2>&1 || {
  echo "ERROR: gh CLI not installed"
  echo "Install: https://cli.github.com/"
  exit 1
}
```

### Step 2: Check Authentication

```bash
gh auth status >/dev/null 2>&1 || {
  echo "ERROR: Not authenticated"
  echo "Run: gh auth login"
  exit 1
}
```

### Step 3: Build Query

```bash
# Base command
CMD="gh issue list --json number,title,body,labels,assignees,milestone,createdAt,updatedAt"

# Add filters
[ -n "$ASSIGNEE" ] && CMD="$CMD --assignee $ASSIGNEE"
[ -n "$LABEL" ] && CMD="$CMD --label $LABEL"
[ -n "$STATE" ] && CMD="$CMD --state $STATE"
[ -n "$LIMIT" ] && CMD="$CMD --limit $LIMIT"
[ -n "$REPO" ] && CMD="$CMD --repo $REPO"
```

### Step 4: Fetch Issues

```bash
ISSUES=$(eval $CMD)
```

### Step 5: Parse and Display

Parse JSON output and display in scannable format:

```
GitHub Issues ({count} {state}, assigned to {assignee})

#123 [bug] Fix login redirect loop
     Labels: bug, priority:high
     Created: 2 days ago

#456 [feature] Add dark mode support
     Labels: enhancement, ui
     Created: 1 week ago

#789 [bug] API timeout on large requests
     Labels: bug, backend
     Created: 3 days ago

Commands:
  /founder-mode:fix-gh-issue 123         Fix issue #123
  /founder-mode:fix-gh-issue 123 456 789 Fix multiple issues
```

### Step 6: Handle Errors

**gh not installed:**
```
GitHub CLI (gh) not installed.

Install from: https://cli.github.com/

macOS:  brew install gh
Ubuntu: sudo apt install gh
Windows: winget install GitHub.cli
```

**Not authenticated:**
```
GitHub CLI not authenticated.

Run: gh auth login
```

**No repo context:**
```
Not in a git repository with GitHub remote.

Options:
1. cd to repository root
2. Use --repo owner/name flag
```

**Rate limiting:**
```
GitHub API rate limited.

Wait {time} before retrying.
Current limit: {remaining}/{total}
```

## Success Criteria

- [ ] gh CLI presence checked
- [ ] Authentication verified
- [ ] Filters work correctly
- [ ] Output scannable and useful
- [ ] Error messages actionable
```

### 3. GitHub Utilities Reference

Create `references/github-utilities.md`:

```markdown
# GitHub Utilities

Common gh CLI patterns for founder-mode.

## Listing Issues

```bash
# Assigned to current user
gh issue list --assignee @me --state open

# With specific labels
gh issue list --label "bug" --label "priority:high"

# JSON output for parsing
gh issue list --json number,title,body,labels,assignees,milestone
```

## Viewing Issue Details

```bash
# Full details
gh issue view 123

# JSON for parsing
gh issue view 123 --json title,body,labels,comments
```

## Creating Issues

```bash
gh issue create --title "Bug: X" --body "Steps to reproduce..."
```

## Searching Issues

```bash
# By text
gh issue list --search "login redirect"

# By author
gh issue list --author @me
```

## Working with PRs

```bash
# Create PR
gh pr create --title "Fix: {title}" --body "Fixes #{number}"

# Link to issue
gh pr create --body "Closes #123"
```

## Error Handling

```bash
# Check if authenticated
gh auth status

# Check rate limit
gh api rate_limit

# Current repo
gh repo view --json nameWithOwner
```
```

## Instructions

### Step 1: Create lib/ Directory

```bash
mkdir -p lib
mkdir -p references
```

### Step 2: Create Files

- lib/issue-types.md
- commands/list-github-issues.md
- references/github-utilities.md

### Step 3: Test gh CLI Integration

Verify gh CLI patterns work:
```bash
gh issue list --json number,title --limit 5
```

## Verification

- [ ] lib/issue-types.md exists with NormalizedIssue interface
- [ ] commands/list-github-issues.md exists
- [ ] gh CLI installation instructions included
- [ ] Authentication check included
- [ ] Filtering documented
- [ ] Error handling covers common cases
- [ ] references/github-utilities.md exists

## Rollback

```bash
rm lib/issue-types.md
rm commands/list-github-issues.md
rm references/github-utilities.md
git checkout -- lib/ commands/ references/
```
