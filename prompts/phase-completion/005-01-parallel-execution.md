# Parallel Execution Infrastructure

## Objective

Implement parallel issue execution using worktrees and the `/fm:fix-issues` command.

## Prerequisites

- Phase 4 complete
- commands/fix-gh-issue.md exists
- Worktree support documented

## Context Files to Read

```
commands/fix-gh-issue.md        # Single issue workflow
references/issue-workflow.md    # Workflow patterns
commands/run-prompt.md          # Background execution
```

## Deliverables

### 1. Parallel Execution Reference

Create `references/parallel-execution.md`:

```markdown
# Parallel Execution

How founder-mode handles parallel work across multiple worktrees.

## Worktree Model

Each parallel task gets its own git worktree:
- Isolated file system
- Independent branch
- No interference between tasks
- Commits don't conflict

## Architecture

```
Main repo/
├── .git/                 # Shared git database
├── src/                  # Main working tree
└── .worktrees/          # Parallel worktrees
    ├── issue-123/       # Working on #123
    │   ├── src/
    │   └── TASK.md
    ├── issue-456/       # Working on #456
    │   ├── src/
    │   └── TASK.md
    └── issue-789/       # Working on #789
        ├── src/
        └── TASK.md
```

## Task Agent Pattern

Each issue gets a Task subagent:

```
Task(
  prompt: "Fix issue #{number} in worktree at {path}

  Issue: @{issue_file}
  Working directory: {worktree_path}

  Execute the fix, commit, and report completion.",
  subagent_type: "general-purpose",
  run_in_background: true
)
```

## Parallel Spawning

Spawn multiple tasks with single message:

```
Task(prompt="Fix #123 in {path1}", subagent_type="general-purpose", run_in_background=true)
Task(prompt="Fix #456 in {path2}", subagent_type="general-purpose", run_in_background=true)
Task(prompt="Fix #789 in {path3}", subagent_type="general-purpose", run_in_background=true)
```

All three run in parallel in their own worktrees.

## Completion Tracking

Each task writes COMPLETION.md to its worktree:

```markdown
# Completion Status

**Status:** SUCCESS | FAILED | PARTIAL
**Finished:** {timestamp}

## Summary
{What was accomplished}

## Files Changed
- {file} - {description}

## Verification
- [x] Tests passed
- [x] Lint clean
- [x] Build successful

## PR
{pr_url or "Skipped"}
```

Monitor completion:
```bash
for dir in .worktrees/issue-*; do
  [ -f "$dir/COMPLETION.md" ] && echo "DONE: $dir" || echo "RUNNING: $dir"
done
```

## Conflict Prevention

**Before parallel execution:**
1. Analyze issues for overlap
2. If files overlap, warn user
3. Offer sequential or manual merge

**Overlap detection:**
```bash
# Get files changed in recent commits on each branch
for branch in fix/issue-*; do
  git diff --name-only main...$branch
done | sort | uniq -d  # Duplicates = conflicts
```

## Cleanup

After all tasks complete:
```bash
for dir in .worktrees/issue-*; do
  git worktree remove "$dir"
done
```

Or keep successful worktrees until PRs merge.
```

### 2. Fix Issues Command

Create `commands/fix-issues.md`:

```markdown
---
name: founder-mode:fix-issues
description: Fix multiple issues in parallel using worktrees
argument-hint: "<issue-numbers...> [--sequential] [--max-parallel N]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - Task
  - AskUserQuestion
---

# Fix Issues (Parallel)

Fix multiple issues simultaneously using isolated worktrees.

## Arguments

Parse from $ARGUMENTS:
- Issue numbers: Space-separated (123 456 789) or comma-separated (123,456,789)
- `--sequential`: Run one at a time (no parallelism)
- `--max-parallel N`: Limit concurrent tasks (default: 3)
- `--no-overlap-check`: Skip file overlap detection
- `--no-pr`: Skip PR creation for all
- `--source`: "github" (default) or "jira"

## Process

### Step 1: Parse Issues

```bash
# Split issue numbers
ISSUES=$(echo "$ARGS" | grep -oE '[0-9]+' | tr '\n' ' ')
COUNT=$(echo "$ISSUES" | wc -w)

echo "Fixing $COUNT issues: $ISSUES"
```

### Step 2: Fetch All Issues

Parallel fetch for speed:

```bash
for number in $ISSUES; do
  gh issue view $number --json title,body,labels > /tmp/issue-$number.json &
done
wait  # Wait for all fetches
```

Parse and display issue summary table:

```
Issues to fix:

| # | Title | Type | Est. Scope |
|---|-------|------|------------|
| 123 | Fix login redirect | bug | small |
| 456 | Add dark mode | feature | medium |
| 789 | API timeout | bug | small |
```

### Step 3: Check for Overlap

Unless `--no-overlap-check`:

```bash
# Analyze each issue for affected files
for number in $ISSUES; do
  # Use codebase search based on issue content
  body=$(cat /tmp/issue-$number.json | jq -r '.body')

  # Extract file mentions
  files=$(echo "$body" | grep -oE '[a-zA-Z0-9_/-]+\.(ts|js|py|go)' | sort -u)

  echo "$number: $files" >> /tmp/file-map.txt
done

# Check for duplicates
CONFLICTS=$(cat /tmp/file-map.txt | cut -d: -f2 | tr ' ' '\n' | sort | uniq -d)
```

**If overlap detected:**

```
Potential file conflicts detected:

Files:
- src/auth/login.ts: issues 123, 456
- src/api/client.ts: issues 456, 789

Options:
1. Proceed anyway - I'll resolve conflicts after
2. Run sequentially - Fix one at a time
3. Abort - Let me regroup
```

Use AskUserQuestion for choice.

### Step 4: Create Worktrees

```bash
WORKTREE_DIR=$(cat .founder-mode/config.json 2>/dev/null | jq -r '.worktree_dir // ".worktrees"')
mkdir -p "$WORKTREE_DIR"

for number in $ISSUES; do
  BRANCH="fix/issue-$number"
  PATH="$WORKTREE_DIR/issue-$number"

  git worktree add "$PATH" -b "$BRANCH" 2>/dev/null || {
    echo "Worktree exists for $number, reusing"
  }

  # Copy issue details to worktree
  cp /tmp/issue-$number.json "$PATH/ISSUE.json"
done
```

### Step 5: Spawn Parallel Tasks

Build task prompts and spawn in parallel:

```
for number in $ISSUES; do
  ISSUE_DATA=$(cat /tmp/issue-$number.json)
  WORKTREE_PATH="$WORKTREE_DIR/issue-$number"

  Task(
    prompt: "Fix GitHub issue #${number} in worktree.

    Working directory: ${WORKTREE_PATH}

    Issue:
    ${ISSUE_DATA}

    Instructions:
    1. cd to working directory
    2. Analyze issue and codebase
    3. Implement fix
    4. Add/update tests
    5. Verify (tests, lint, build)
    6. Commit with message: fix: {title}

Fixes #{number}
    7. Create PR (unless issues detected)
    8. Write COMPLETION.md with status

    Report completion status in COMPLETION.md.",
    subagent_type: "general-purpose",
    run_in_background: true,
    description: "Fix issue #${number}"
  )
done
```

If `--max-parallel N`:
- Spawn N tasks initially
- When one completes, spawn next
- Continue until all done

### Step 6: Monitor Progress

```bash
# Poll completion status
while true; do
  DONE=0
  RUNNING=0

  for number in $ISSUES; do
    if [ -f "$WORKTREE_DIR/issue-$number/COMPLETION.md" ]; then
      DONE=$((DONE + 1))
    else
      RUNNING=$((RUNNING + 1))
    fi
  done

  echo "Progress: $DONE/$COUNT complete, $RUNNING running"

  [ $DONE -eq $COUNT ] && break
  sleep 5
done
```

Display progress:
```
Parallel Execution Progress

[##########----------] 50% (2/4 complete)

| # | Status | Duration | PR |
|---|--------|----------|-----|
| 123 | SUCCESS | 2m 34s | #45 |
| 456 | RUNNING | 1m 12s | - |
| 789 | SUCCESS | 1m 45s | #46 |
| 101 | PENDING | - | - |
```

### Step 7: Aggregate Results

Read each COMPLETION.md and aggregate:

```
Parallel Execution Complete

| # | Status | PR | Notes |
|---|--------|-----|-------|
| 123 | SUCCESS | #45 | Clean fix |
| 456 | SUCCESS | #46 | Added 3 tests |
| 789 | FAILED | - | Tests failing |

Summary:
- 3 issues attempted
- 2 succeeded
- 1 failed

Failed issues:
- #789: Tests failing in api.test.ts (see .worktrees/issue-789/)

Worktrees:
  SUCCESS: cleaned up
  FAILED: preserved for debugging
```

### Step 8: Cleanup

For successful fixes:
```bash
for number in $SUCCESS_ISSUES; do
  git worktree remove "$WORKTREE_DIR/issue-$number"
done
```

Preserve failed worktrees for debugging.

## Sequential Mode (--sequential)

If `--sequential` flag:
- Don't create worktrees
- Run in main repo
- One issue at a time
- Commit each before starting next

## Error Handling

**Worktree creation fails:**
```
Failed to create worktree for issue #{number}.

Error: {error}

Possible causes:
- Branch already exists
- Uncommitted changes in main

Try: git worktree prune
```

**Task timeout:**
```
Issue #{number} timed out after 10 minutes.

The worktree is preserved at: {path}

Debug:
  cd {path}
  git status
  cat COMPLETION.md  # May have partial status
```

**Merge conflict:**
```
Multiple issues modified the same files.

Conflicts in:
- {file1}
- {file2}

Options:
1. Resolve manually - I'll show git commands
2. Prioritize one - Keep only {number}'s changes
3. Abort parallel - Switch to sequential
```

## Success Criteria

- [ ] All issues fetched successfully
- [ ] Overlap detection completed (unless skipped)
- [ ] Worktrees created for each issue
- [ ] Tasks spawned in parallel (or sequential if requested)
- [ ] Progress monitored and displayed
- [ ] Results aggregated
- [ ] Successful worktrees cleaned up
- [ ] Failed worktrees preserved
- [ ] User shown final status with PR URLs
```

## Instructions

### Step 1: Create Reference

Create references/parallel-execution.md.

### Step 2: Create Command

Create commands/fix-issues.md with parallel execution workflow.

### Step 3: Verify Worktree Patterns

Ensure worktree creation and cleanup is robust.

## Verification

- [ ] references/parallel-execution.md exists
- [ ] commands/fix-issues.md exists
- [ ] Worktree model documented
- [ ] Overlap detection documented
- [ ] Parallel spawning pattern clear
- [ ] Progress monitoring documented
- [ ] Cleanup documented
- [ ] Error handling comprehensive
- [ ] --sequential fallback exists

## Rollback

```bash
rm references/parallel-execution.md
rm commands/fix-issues.md
git checkout -- references/ commands/
```
