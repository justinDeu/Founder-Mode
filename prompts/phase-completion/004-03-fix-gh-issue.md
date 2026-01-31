# Fix GitHub Issue Command

## Objective

Implement the end-to-end `/fm:fix-gh-issue` workflow that goes from issue to PR.

## Prerequisites

- 004-01-github-integration.md complete
- lib/issue-types.md exists
- references/github-utilities.md exists

## Context Files to Read

```
commands/list-github-issues.md  # GitHub patterns
lib/issue-types.md              # NormalizedIssue interface
commands/run-prompt.md          # For execution patterns
```

## Deliverables

### 1. Issue Workflow Utilities

Create `references/issue-workflow.md`:

```markdown
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
```

### 2. Fix GitHub Issue Command

Create `commands/fix-gh-issue.md`:

```markdown
---
name: founder-mode:fix-gh-issue
description: Fix a GitHub issue end-to-end from issue to PR
argument-hint: "<issue-number> [--worktree] [--no-pr] [--draft]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - Task
  - AskUserQuestion
---

# Fix GitHub Issue

Complete workflow: fetch issue → analyze → fix → test → PR.

## Arguments

Parse from $ARGUMENTS:
- Issue number(s): Single (123) or multiple (123 456 789)
- `--worktree`: Create isolated worktree for fix
- `--branch`: Custom branch name (default: fix/issue-{number})
- `--no-pr`: Skip PR creation, just commit
- `--draft`: Create draft PR

## Process

### Step 1: Fetch Issue

```bash
# Fetch issue details
ISSUE=$(gh issue view $NUMBER --json title,body,labels,comments)

# Parse fields
TITLE=$(echo "$ISSUE" | jq -r '.title')
BODY=$(echo "$ISSUE" | jq -r '.body')
LABELS=$(echo "$ISSUE" | jq -r '.labels[].name' | tr '\n' ', ')
```

**Display issue summary:**
```
Fixing Issue #{number}

Title: {title}
Labels: {labels}
Type: {bug|feature inferred from labels}

{body preview, first 500 chars}
```

### Step 2: Analyze Issue

Parse issue to understand:
- **Reproduction steps**: For bugs, extract steps from body
- **Requirements**: For features, extract what's needed
- **Affected areas**: Files, components mentioned
- **Acceptance criteria**: What success looks like

**For bugs:**
```bash
# Look for common patterns in issue body
REPRO_STEPS=$(echo "$BODY" | grep -A 20 -i "steps to reproduce\|repro\|how to reproduce")
EXPECTED=$(echo "$BODY" | grep -A 5 -i "expected\|should")
ACTUAL=$(echo "$BODY" | grep -A 5 -i "actual\|instead\|but")
```

**Determine scope:**
- Single file fix: Simple, proceed directly
- Multi-file fix: Create mini-plan

### Step 3: Create Worktree (if --worktree)

```bash
# Get worktree directory from config
WORKTREE_DIR=$(cat .founder-mode/config.json 2>/dev/null | jq -r '.worktree_dir // ".worktrees"')

mkdir -p "$WORKTREE_DIR"

# Create worktree with branch
BRANCH="${BRANCH_ARG:-fix/issue-$NUMBER}"
git worktree add "$WORKTREE_DIR/issue-$NUMBER" -b "$BRANCH"

# Switch context
cd "$WORKTREE_DIR/issue-$NUMBER"
```

### Step 4: Codebase Analysis

Using issue content as guide:

```bash
# Search for error messages mentioned in issue
grep -r "error message from issue" src/

# Search for function/component names mentioned
grep -r "mentioned_function" src/

# Find related test files
ls **/test*${component}* **/*${component}*test*
```

Read files that will need modification.

### Step 5: Plan Fix

**For simple fixes (single file, obvious change):**
Skip formal planning, proceed to fix.

**For complex fixes:**
Create lightweight plan:
- Files to modify
- Changes to make
- Verification steps

### Step 6: Execute Fix

Make code changes using Edit/Write tools.

**Self-healing retry (Ralph Wiggums pattern):**
If execution fails:
1. Check error output
2. Diagnose issue
3. Retry with fix
4. Max 3 attempts

### Step 7: Add/Update Tests

```bash
# Check if test file exists
TEST_FILE=$(find . -name "*${component}*.test.*" -o -name "*${component}*.spec.*" | head -1)

if [ -n "$TEST_FILE" ]; then
  # Update existing tests
  echo "Updating: $TEST_FILE"
else
  # Create new test file
  echo "Creating test for: $component"
fi
```

Add test cases that:
- Cover the bug fix (regression test)
- Or cover the new feature

### Step 8: Verify Fix

```bash
# Run tests
npm test || pytest || go test ./...

# Run linting
npm run lint || ruff check . || go vet ./...

# Run build
npm run build || python -m build || go build ./...
```

**If tests fail:**
- Show failure output
- Offer retry or abort
- Max 3 fix attempts

### Step 9: Commit

```bash
git add .
git commit -m "$(cat <<'EOF'
fix: {issue title}

Fixes #{number}

- {change 1}
- {change 2}
EOF
)"
```

### Step 10: Create PR (unless --no-pr)

```bash
# Push branch
git push -u origin "$BRANCH"

# Create PR
PR_FLAGS=""
[ "$DRAFT" = true ] && PR_FLAGS="--draft"

gh pr create $PR_FLAGS \
  --title "Fix: {issue title}" \
  --body "$(cat <<'EOF'
## Summary
Fixes #{number}

{brief description of fix}

## Changes
- {change 1}
- {change 2}

## Testing
- {how it was tested}

## Verification
- [x] Tests pass
- [x] Lint clean
- [x] Build successful
EOF
)" \
  --assignee @me
```

### Step 11: Report Completion

```
Issue #{number} fixed!

Branch: {branch}
PR: {pr_url}

Changes made:
- {file1}: {description}
- {file2}: {description}

Verification:
- [x] Tests pass ({N} passed, 0 failed)
- [x] Lint clean
- [x] Build successful

{If worktree used:}
Worktree: {worktree_path}
To clean up: git worktree remove {worktree_path}
```

## Multiple Issues

When multiple issue numbers provided:

```
/fm:fix-gh-issue 123 456 789
```

**Step 1: Dependency Analysis (before execution)**
Analyze issues to determine conceptual dependencies. Dependency means one issue's solution requires or builds upon another's changes. File overlap from parallel development is NOT a dependency.

Present analysis and proposed execution plan to user for verification. User can confirm, mark as independent, or reverse the dependency direction.

**Default behavior (independent issues):**
Create separate worktree per issue, work in parallel, create separate PR per issue.

Never combine issues into a single worktree or PR without explicit user confirmation.

**For dependent issues (analysis verified by user):**
After user verifies dependency analysis and execution plan:
- Work in parallel worktrees with intelligent merge timing
- Monitor upstream issue for merge-ready state (substantive commits, tests passing)
- Merge into downstream worktree when upstream reaches a stable point
- Downstream agent restarts with updated context after merge
- If conflicts occur, pause and surface to user
- Create separate PRs with dependency notes

## Error Handling

**Issue not found:**
```
Issue #{number} not found.

Check:
- Issue number is correct
- You have access to the repository
- gh CLI is authenticated
```

**Worktree conflict:**
```
Worktree already exists for issue #{number}.

Options:
1. Remove existing: git worktree remove {path}
2. Use existing: cd {path}
3. Use different branch: --branch fix/issue-{number}-v2
```

**Tests fail after fix:**
```
Tests failing after fix attempt.

Failures:
{test output}

Options:
1. Retry fix - Attempt another fix
2. Skip tests - Commit anyway (--no-verify)
3. Abort - Don't commit
```

**PR creation fails:**
```
PR creation failed.

Error: {error}

Manual creation:
  git push -u origin {branch}
  gh pr create --title "Fix: {title}" --body "Fixes #{number}"
```

## Success Criteria

- [ ] Issue fetched and parsed
- [ ] Codebase analyzed for relevant files
- [ ] Fix implemented
- [ ] Tests added/updated
- [ ] Verification passed (tests, lint, build)
- [ ] Committed with proper message
- [ ] PR created (unless --no-pr)
- [ ] User shown result with PR URL
```

## Instructions

### Step 1: Create Reference

Create references/issue-workflow.md with common patterns.

### Step 2: Create Command

Create commands/fix-gh-issue.md with full workflow.

### Step 3: Verify Workflow Flow

Ensure the flow is:
1. Fetch → 2. Analyze → 3. Worktree (optional) → 4. Read code → 5. Plan → 6. Fix → 7. Test → 8. Verify → 9. Commit → 10. PR → 11. Report

## Verification

- [ ] references/issue-workflow.md exists
- [ ] commands/fix-gh-issue.md exists
- [ ] Issue fetching documented
- [ ] Analysis patterns documented
- [ ] Worktree creation documented
- [ ] Self-healing retry documented
- [ ] Test addition documented
- [ ] PR creation documented
- [ ] Error handling comprehensive

## Rollback

```bash
rm references/issue-workflow.md
rm commands/fix-gh-issue.md
git checkout -- references/ commands/
```
