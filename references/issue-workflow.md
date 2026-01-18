# Issue Workflow Utilities

Patterns for the issue-to-PR workflow.

## Issue Analysis

When fixing an issue, analyze:

1. **Type**: Bug fix or feature?
2. **Scope**: Single file or multi-file?
3. **Tests**: Tests needed?
4. **Breaking**: Breaking change?

## Bug Fix Pattern

1. Parse reproduction steps from issue body
2. Search codebase for related code
3. Identify root cause
4. Plan fix
5. Implement fix
6. Add regression test
7. Verify fix

## Feature Pattern

1. Parse requirements from issue body
2. Identify affected files
3. Plan implementation
4. Implement feature
5. Add tests
6. Verify feature

## Worktree Pattern

For isolated work:

```bash
# Get worktree directory
WORKTREE_DIR=$(cat .founder-mode/config.json | jq -r '.worktree_dir // ".worktrees"')

# Create worktree
git worktree add "$WORKTREE_DIR/issue-{number}" -b fix/issue-{number}

# Work in worktree
cd "$WORKTREE_DIR/issue-{number}"

# After completion
git worktree remove "$WORKTREE_DIR/issue-{number}"
```

## Commit Message Format

```
fix: {issue title}

Fixes #{number}

- {change 1}
- {change 2}
```

## PR Creation

```bash
gh pr create \
  --title "Fix: {issue title}" \
  --body "## Summary
Fixes #{number}

## Changes
- {change 1}
- {change 2}

## Testing
- {how tested}" \
  --assignee @me
```
