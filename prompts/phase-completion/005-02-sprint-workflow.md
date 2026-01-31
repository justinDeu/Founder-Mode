# Sprint Workflow Command

## Objective

Implement the `/fm:run-sprint` command that automates sprint planning and execution.

## Prerequisites

- 005-01-parallel-execution.md complete
- commands/fix-issues.md exists
- commands/list-github-issues.md exists
- commands/list-jira-tickets.md exists

## Context Files to Read

```
commands/fix-issues.md          # Parallel execution patterns
commands/list-github-issues.md  # Issue fetching
commands/list-jira-tickets.md   # Ticket fetching
```

## Deliverables

### 1. Sprint Configuration Reference

Create `references/sprint-config.md`:

```markdown
# Sprint Configuration

How to configure sprint automation in founder-mode.

## Sprint Configuration Schema

Add to `.founder-mode/config.json`:

```json
{
  "sprint": {
    "source": "github",
    "filters": {
      "labels": ["sprint-current"],
      "assignee": "@me",
      "state": "open"
    },
    "max_issues": 10,
    "parallel_limit": 3,
    "pr_strategy": "individual",
    "branch_prefix": "sprint-",
    "auto_pr": true,
    "auto_assign": true
  }
}
```

## Field Definitions

### source
- `"github"`: Use GitHub Issues
- `"jira"`: Use Jira tickets
- `"mixed"`: Support both (specify per-ticket)

### filters
Standard filters for the issue source:
- GitHub: labels, assignee, state, milestone
- Jira: project, status, sprint, assignee

### max_issues
Maximum issues to include in sprint run (default: 10).
Safety limit to prevent runaway execution.

### parallel_limit
Maximum concurrent tasks (default: 3).
Higher = faster but more resource intensive.

### pr_strategy
- `"individual"`: One PR per issue
- `"batched"`: Group related issues into PRs
- `"single"`: All changes in one PR

### branch_prefix
Prefix for branch names (default: "fix/").
Sprint mode uses: `{prefix}{issue-id}`

### auto_pr
Automatically create PRs (default: true).
Set false to just commit locally.

### auto_assign
Automatically assign PRs to self (default: true).

## Per-Sprint Configuration

Create `.founder-mode/sprint.json` for sprint-specific settings:

```json
{
  "name": "Sprint 23",
  "goals": [
    "Fix all P1 bugs",
    "Complete auth feature"
  ],
  "issues": [123, 456, 789],
  "excluded": [101],
  "notes": "Focus on stability this sprint"
}
```

## Integration with Issue Trackers

### GitHub Sprint (via Milestones)

```json
{
  "sprint": {
    "source": "github",
    "filters": {
      "milestone": "Sprint 23",
      "assignee": "@me"
    }
  }
}
```

### Jira Sprint

```json
{
  "sprint": {
    "source": "jira",
    "filters": {
      "project": "PROJ",
      "sprint": "Sprint 23",
      "assignee": "currentUser()"
    }
  }
}
```
```

### 2. Run Sprint Command

Create `commands/run-sprint.md`:

```markdown
---
name: founder-mode:run-sprint
description: Run a sprint - fetch issues, plan, and execute in parallel
argument-hint: "[--dry-run] [--interactive] [--max N]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - Task
  - AskUserQuestion
---

# Run Sprint

Automated sprint execution: fetch → plan → execute → report.

## Arguments

Parse from $ARGUMENTS:
- `--dry-run`: Show what would be done without executing
- `--interactive`: Confirm each issue before starting
- `--max N`: Override max_issues from config
- `--source`: Override source (github/jira)
- `--filter`: Additional filter (e.g., --filter "label:priority:high")

## Process

### Step 1: Load Configuration

```bash
# Load sprint config
if [ -f .founder-mode/sprint.json ]; then
  SPRINT_CONFIG=$(cat .founder-mode/sprint.json)
  SPRINT_NAME=$(echo "$SPRINT_CONFIG" | jq -r '.name // "Current Sprint"')
  EXPLICIT_ISSUES=$(echo "$SPRINT_CONFIG" | jq -r '.issues // []')
fi

# Load general config
if [ -f .founder-mode/config.json ]; then
  CONFIG=$(cat .founder-mode/config.json)
  SOURCE=$(echo "$CONFIG" | jq -r '.sprint.source // "github"')
  MAX_ISSUES=$(echo "$CONFIG" | jq -r '.sprint.max_issues // 10')
  PARALLEL_LIMIT=$(echo "$CONFIG" | jq -r '.sprint.parallel_limit // 3')
  FILTERS=$(echo "$CONFIG" | jq -r '.sprint.filters // {}')
fi
```

### Step 2: Fetch Sprint Issues

**If explicit issues in sprint.json:**
```bash
ISSUES="$EXPLICIT_ISSUES"
```

**Otherwise, fetch from source:**

For GitHub:
```bash
gh issue list \
  --json number,title,labels \
  --label "$LABEL_FILTER" \
  --assignee "$ASSIGNEE_FILTER" \
  --state open \
  --limit "$MAX_ISSUES"
```

For Jira:
```bash
# Use JQL from filters
JQL="project = $PROJECT AND sprint = '$SPRINT' AND assignee = currentUser()"
curl ... # Jira API call
```

### Step 3: Display Sprint Plan

```
Sprint: {sprint_name}

{count} issues to fix:

| # | Title | Type | Priority | Est. |
|---|-------|------|----------|------|
| 123 | Fix login redirect | bug | high | S |
| 456 | Add dark mode toggle | feature | medium | M |
| 789 | API timeout handling | bug | high | S |
| 101 | Update user profile | feature | low | S |

Execution Plan:
- Wave 1: 123, 789 (small bugs, parallel)
- Wave 2: 456 (medium feature)
- Wave 3: 101 (low priority)

Estimated time: {estimate}
```

### Step 4: Dry Run Check

**If `--dry-run`:**
```
Dry run - no changes made.

Would execute:
1. Create 4 worktrees
2. Spawn 3 parallel tasks (wave 1+2)
3. Create 4 PRs

To execute: /fm:run-sprint
```
Exit without executing.

### Step 5: Interactive Confirmation

**If `--interactive`:**

For each issue, use AskUserQuestion:
- header: "Issue #{number}"
- question: "Include '{title}' in sprint?"
- options:
  - "Include" - Add to sprint
  - "Skip" - Exclude this time
  - "Defer" - Move to next sprint

Build final issue list from selections.

**If not interactive:**
```
Starting sprint execution in 5 seconds...
(Ctrl+C to abort, or add --interactive for per-issue confirmation)
```

### Step 6: Execute Sprint

Use parallel execution infrastructure:

```
Task(
  prompt: "/fm:fix-issues {issue_numbers}

  Sprint: {sprint_name}
  Max parallel: {parallel_limit}

  Execute all sprint issues.",
  subagent_type: "general-purpose",
  description: "Execute sprint"
)
```

Or spawn individual tasks with orchestration:

```bash
# Wave-based execution
for wave in "${WAVES[@]}"; do
  echo "Executing wave: $wave"

  # Spawn wave in parallel
  for issue in $wave; do
    spawn_task "$issue"
  done

  # Wait for wave completion
  wait_for_completions "$wave"
done
```

### Step 7: Monitor Progress

Display live progress:

```
Sprint Progress: {sprint_name}

[##########-----------] 45% (4/9 complete)

| # | Title | Status | Duration | PR |
|---|-------|--------|----------|-----|
| 123 | Fix login | SUCCESS | 2m | #45 |
| 789 | API timeout | SUCCESS | 3m | #46 |
| 456 | Dark mode | RUNNING | 5m | - |
| 101 | User profile | PENDING | - | - |

Wave 1: COMPLETE (2/2)
Wave 2: IN PROGRESS (0/1)
Wave 3: PENDING

ETA: ~8 minutes remaining
```

Update every 5 seconds.

### Step 8: Handle Failures

**If task fails:**
1. Log failure details
2. Continue with other tasks
3. Preserve failed worktree
4. Report in final summary

**Retry option:**
```
Issue #789 failed: Tests failing

Options:
1. Retry - Try fixing again
2. Skip - Continue without this issue
3. Pause - Stop sprint, debug manually
```

### Step 9: Sprint Summary

```
Sprint Complete: {sprint_name}

Results:
| Status | Count | Issues |
|--------|-------|--------|
| SUCCESS | 7 | #123, #456, #789, ... |
| FAILED | 1 | #101 |
| SKIPPED | 1 | #102 |

PRs Created:
- #45: Fix login redirect (fixes #123)
- #46: API timeout handling (fixes #789)
- #47: Add dark mode toggle (fixes #456)
...

Time: 23m 45s
Velocity: 3.4 issues/hour

Failed Issues:
- #101: Test failures in profile.test.ts
  Worktree: .worktrees/issue-101/
  Debug: cd .worktrees/issue-101/ && npm test

Next Steps:
1. Review PRs for merge
2. Debug failed issues manually
3. Run /fm:run-sprint --filter "label:sprint-next"
```

### Step 10: Update Sprint Tracking

**If Jira:**
```bash
# Transition completed issues
for issue in $SUCCESS_ISSUES; do
  curl -X POST "https://$JIRA_DOMAIN/rest/api/3/issue/$issue/transitions" \
    -H "Content-Type: application/json" \
    -d '{"transition": {"id": "done_transition_id"}}'
done
```

**If GitHub:**
```bash
# Close issues (PRs will auto-close on merge)
# Or add labels
for issue in $SUCCESS_ISSUES; do
  gh issue edit $issue --add-label "fix-pending-review"
done
```

## Wave Planning Algorithm

Issues are grouped into waves for efficient execution:

1. **Priority sort**: High priority first
2. **Size sort**: Small issues first (quick wins)
3. **Dependency check**: Issues depending on others go to later waves
4. **Overlap check**: Conflicting files go to separate waves
5. **Limit enforcement**: Max {parallel_limit} per wave

## Error Handling

**Config missing:**
```
Sprint configuration not found.

Create .founder-mode/config.json with sprint settings:

{
  "sprint": {
    "source": "github",
    "filters": { "labels": ["sprint-current"] }
  }
}

Or specify issues directly: /fm:fix-issues 123 456 789
```

**No issues found:**
```
No issues match sprint filters.

Filters applied:
- Source: github
- Labels: sprint-current
- Assignee: @me
- State: open

Check:
1. Issues have correct labels
2. Issues are assigned to you
3. Issues are open
```

**Too many issues:**
```
Found {count} issues, limit is {max_issues}.

Options:
1. Increase limit: --max {higher}
2. Add filters: --filter "label:priority:high"
3. Run in batches
```

## Success Criteria

- [ ] Sprint config loaded
- [ ] Issues fetched from source
- [ ] Sprint plan displayed
- [ ] Dry run works correctly
- [ ] Interactive mode works
- [ ] Parallel execution runs
- [ ] Progress monitored
- [ ] Failures handled gracefully
- [ ] Summary generated
- [ ] Issue tracker updated (if configured)
```

## Instructions

### Step 1: Create Reference

Create references/sprint-config.md.

### Step 2: Create Command

Create commands/run-sprint.md.

### Step 3: Verify Integration

Ensure run-sprint uses:
- fix-issues for parallel execution
- list-github-issues / list-jira-tickets for fetching

## Verification

- [ ] references/sprint-config.md exists
- [ ] commands/run-sprint.md exists
- [ ] Config schema documented
- [ ] GitHub integration documented
- [ ] Jira integration documented
- [ ] Wave planning algorithm documented
- [ ] Progress monitoring documented
- [ ] Error handling comprehensive
- [ ] Issue tracker update documented

## Rollback

```bash
rm references/sprint-config.md
rm commands/run-sprint.md
git checkout -- references/ commands/
```
