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
