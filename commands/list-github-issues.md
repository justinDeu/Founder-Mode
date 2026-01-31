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
  /fm:fix-gh-issue 123         Fix issue #123
  /fm:fix-gh-issue 123 456 789 Fix multiple issues
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
