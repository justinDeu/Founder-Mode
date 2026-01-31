---
name: founder-mode:fix-gh-issue
description: Fix a GitHub issue end-to-end from issue to PR
argument-hint: "<issue-number> [--no-worktree] [--no-pr] [--draft] [--model ?|claude|codex|...]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - Skill
  - AskUserQuestion
---

# Fix GitHub Issue

Compose first-principle commands to fix GitHub issues. Fetches issues, generates prompts, delegates execution to `/fm:run-prompt` or `/fm:orchestrate`, then creates PRs.

## Arguments

Parse from $ARGUMENTS:
- Issue number(s): Single (123) or multiple (123 456 789)
- `--no-worktree`: Skip worktree creation (default: creates worktree)
- `--branch`: Custom branch name (default: uses github naming template)
- `--no-pr`: Skip PR creation, just commit
- `--draft`: Create draft PR
- `--model`: Model to use. Omit or use `?` to select interactively.

## Composition Pattern

This command composes first-principle commands:

```
/fm:fix-gh-issue 123 456
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Step 1: Fetch Issues (gh CLI)                          │
│  gh issue view 123 --json title,body,labels             │
│  gh issue view 456 --json title,body,labels             │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Step 2: Dependency Analysis (multiple issues only)     │
│  Analyze issues to determine conceptual dependencies    │
│  Present analysis + execution plan to user              │
│  User verifies or adjusts the analysis                  │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Step 3: Generate Prompts (inline)                      │
│  Create prompt files in .founder-mode/prompts/gh-issues │
│  → gh-123-{slug}.md                                     │
│  → gh-456-{slug}.md                                     │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Step 4: Model Selection (MANDATORY)                    │
│  AskUserQuestion: "Which model for execution?"          │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Step 5: Execute via Orchestration                      │
│                                                         │
│  Single issue:                                          │
│    Skill(skill: "run-prompt", args: "... --worktree")   │
│                                                         │
│  Multiple issues:                                       │
│    Skill(skill: "orchestrate", args: "... --worktree")  │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Step 6: Create PRs (gh CLI)                            │
│  For each completed worktree:                           │
│    git push -u origin {branch}                          │
│    gh pr create --title "Fix: {issue title}"            │
└─────────────────────────────────────────────────────────┘
```

## Process

### Step 1: Fetch Issue(s)

For each issue number:

```bash
# Fetch issue details
ISSUE=$(gh issue view $NUMBER --json title,body,labels,comments,url)

# Parse fields
TITLE=$(echo "$ISSUE" | jq -r '.title')
BODY=$(echo "$ISSUE" | jq -r '.body')
LABELS=$(echo "$ISSUE" | jq -r '.labels[].name' | tr '\n' ', ')
URL=$(echo "$ISSUE" | jq -r '.url')
```

Display issue summary:
```
Fetched Issue #{number}

Title: {title}
Labels: {labels}
URL: {url}

{body preview, first 300 chars}
```

Store parsed issues in memory for prompt generation.

### Step 2: Dependency Analysis (multiple issues only)

Skip this step for single issues.

**Analyze the issues to determine dependencies:**

Read each issue's title, body, and scope of work. Determine if any issue conceptually depends on another:
- Does issue B's solution require changes that issue A would introduce?
- Does issue B build upon functionality that issue A creates?
- Is there a logical ordering where one must come before the other?

<important>
Dependency means conceptual relationship: one issue's solution requires or builds upon another's changes.

Dependency does NOT mean issues happen to touch the same files. File overlap from parallel development is not a dependency. That's just a merge conflict to resolve later if it occurs.
</important>

**If no dependencies found:**

Present analysis and proceed:

```
Dependency Analysis
===================

Issue #123: {title}
Issue #456: {title}

Analysis: These issues are independent. They address separate concerns
and neither requires changes from the other.

Execution Plan: Parallel worktrees, separate PRs.
```

**If dependencies found:**

Present the analysis and proposed execution plan for user verification:

```
Dependency Analysis
===================

Issue #123: {title}
Issue #456: {title}

Analysis: Issue #456 depends on #123.
Reason: {explain why - e.g., "#456 adds validation to the auth flow that #123 creates"}

Proposed Execution Plan:

Phase 1: Issue #123 (upstream)
  → Worktree: gh-123-{slug}
  → Creates the foundation needed by #456

Phase 2: Issue #456 (downstream)
  → Worktree: gh-456-{slug}
  → Starts in parallel, merges #123 when ready
  → Merge trigger: #123 has substantive commits + tests passing

Separate PRs will be created for each issue.
```

Then ask user to verify:

```
AskUserQuestion(
  questions: [{
    question: "Does this dependency analysis look correct?",
    header: "Verify",
    options: [
      { label: "Correct", description: "Proceed with this execution plan" },
      { label: "Actually independent", description: "No dependency, run fully in parallel" },
      { label: "Reverse dependency", description: "The other issue should be upstream" }
    ]
  }]
)
```

Adjust execution plan based on user feedback.

### Step 3: Generate Prompts

For each issue, generate a prompt file. Do NOT call `/fm:create-prompt` (too heavyweight for issue context). Generate inline using this template:

<issue_prompt_template>
```markdown
# Fix GitHub Issue #{number}

<objective>
Fix issue #{number}: {title}

{issue body}
</objective>

<context>
Repository: {repo from git remote}
Issue URL: {url}
Labels: {labels}
Type: {bug|feature|enhancement inferred from labels}
</context>

<requirements>
{Requirements parsed from issue body:}
{For bugs: reproduction steps, expected vs actual behavior}
{For features: what needs to be built}
{For refactors: what needs to change}
</requirements>

<implementation>
1. Search codebase for files related to issue
2. Analyze affected components
3. Implement the fix/feature
4. Add or update tests to cover the change
5. Verify tests pass
6. Verify lint checks pass
</implementation>

<output>
On completion, create a commit:
- Message format: fix: {issue title}\n\nFixes #{number}\n\n- {change 1}\n- {change 2}
- Stage only relevant files (not git add -A)
</output>

<verification>
Before declaring complete:
- [ ] Issue requirements addressed
- [ ] Tests pass (run test command)
- [ ] Lint passes (run lint command)
- [ ] Changes committed with proper message
</verification>
```
</issue_prompt_template>

Save prompts to `.founder-mode/prompts/gh-issues/`:

```bash
mkdir -p .founder-mode/prompts/gh-issues

# Generate slug from title
SLUG=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/ /g' | \
  tr ' ' '\n' | grep -vE '^(a|an|the|in|on|at|to|for|of)$' | head -5 | \
  tr '\n' '-' | sed 's/--*/-/g' | sed 's/-$//' | cut -c1-30)

PROMPT_FILE=".founder-mode/prompts/gh-issues/gh-${NUMBER}-${SLUG}.md"
```

Write the generated prompt content to `$PROMPT_FILE`.

Report generation:
```
Generated Prompts
=================

{For each issue:}
- gh-{number}-{slug}.md → Issue #{number}: {title (truncated to 50 chars)}

Saved to: .founder-mode/prompts/gh-issues/
```

### Step 4: Model Selection (MANDATORY)

<critical>
ALWAYS ask the user to select a model before execution. This step is MANDATORY.
The only exception is when `--model` is explicitly provided in the arguments.
</critical>

If no `--model` specified (or `--model ?`):

```
AskUserQuestion(
  questions: [{
    question: "Which model should execute these prompts?",
    header: "Model",
    options: [
      { label: "claude", description: "Claude in current session (Recommended)" },
      { label: "codex", description: "OpenAI gpt-5.2-codex via codex CLI" },
      { label: "gemini", description: "Gemini 3 Flash via gemini CLI" },
      { label: "claude-zai", description: "Claude CLI with Z.AI backend" }
    ]
  }]
)
```

Wait for user selection before proceeding.

### Step 5: Execute via Orchestration

Route based on issue count:

<single_issue>
**Single issue → run-prompt**

Invoke run-prompt skill with generated prompt:

```
Skill(
  skill: "run-prompt",
  args: "{prompt_file} --model {selected_model} {--worktree unless --no-worktree}"
)
```

The run-prompt command handles:
- Worktree creation (with proper naming from config)
- Claude execution (via Task subagent) or non-Claude (via executor.py)
- Result collection (COMPLETION.md or executor output)

Wait for completion and collect result.
</single_issue>

<multiple_issues>
**Multiple issues → Always separate worktrees**

<critical>
Each issue ALWAYS gets its own worktree and its own PR by default.
Never combine issues into a single worktree or PR without explicit user confirmation.
</critical>

Build comma-separated prompt list and invoke orchestrate:

```bash
PROMPT_LIST=$(ls .founder-mode/prompts/gh-issues/gh-*.md | tr '\n' ',' | sed 's/,$//')
```

```
Skill(
  skill: "orchestrate",
  args: "{prompt_list} --model {selected_model} {--worktree unless --no-worktree}"
)
```

The orchestrate command handles:
- One worktree per issue (always isolated)
- Parallel execution for non-Claude models
- Spawning `readonly-log-watcher` monitors for background executions
- Progress reporting per wave
- Result collection

**Monitoring happens automatically:**
- Orchestrate spawns `readonly-log-watcher` agents for background non-Claude executions
- Monitors report progress every 30 seconds
- Stall detection at 10/20/30 minute thresholds
- User sees wave completion reports

Wait for orchestration to complete and collect all results.

**Dependent issues workflow:**

<important>
Dependencies are determined by analyzing the issues in Step 2, then verified by the user.

A dependency means issues are conceptually related: one issue's solution requires or builds upon another's changes. File overlap from parallel development is NOT a dependency.
</important>

When analysis determines issues have dependencies (e.g., issue B requires changes from issue A):

1. **Analysis verified:** Dependency analysis presented in Step 2, user verified the execution plan
2. **Parallel start:** Both issues begin in separate worktrees simultaneously
3. **Merge timing:** Monitor upstream issue (A) for merge-ready state:
   - Core implementation committed (not just scaffolding)
   - Tests passing for the implemented portion
   - No uncommitted changes blocking the merge
4. **Merge and continue:** When A reaches merge-ready state, merge into B's worktree and resume B's agent
5. **Separate PRs:** Create PRs with dependency notes

**Merge-ready detection:**

The orchestrator monitors each issue's worktree for merge-ready signals:
```bash
# Check if issue A has substantive commits beyond initial setup
COMMITS=$(git -C "$WORKTREE_A" log --oneline main..HEAD | wc -l)
TESTS_PASS=$(git -C "$WORKTREE_A" diff --quiet && run_tests_in_worktree "$WORKTREE_A")

if [ "$COMMITS" -gt 0 ] && [ "$TESTS_PASS" = "true" ]; then
  # A is merge-ready, trigger merge into B
  git -C "$WORKTREE_B" merge gh-{A-number}-{slug}
fi
```

**Sub-agent coordination:**

For dependent issues with sub-agents:
1. **Decompose prompts:** Split each issue into phases if needed (setup, core impl, integration)
2. **Phase-based merging:** Merge after upstream completes a phase, not necessarily the entire issue
3. **Agent restart:** After merge, the downstream agent may need to restart with updated context:
   - Re-read affected files to see upstream changes
   - Adjust implementation approach if upstream introduced different patterns
   - Continue from where it left off, not from scratch
4. **Conflict handling:** If merge conflicts occur, pause downstream agent and surface to user

```bash
# In issue B's worktree, after A reaches merge-ready:
git merge gh-{A-number}-{slug}  # or git rebase
# Continue with B's implementation
```

Note: Since worktrees share the same repository, local branches are directly accessible without fetching from origin.
</multiple_issues>

### Step 6: Collect Results

After execution completes, collect results from each issue's worktree:

```bash
# For each issue
WORKTREE_PATH=$(git worktree list | grep "gh-${NUMBER}" | awk '{print $1}')

if [ -f "$WORKTREE_PATH/COMPLETION.md" ]; then
    STATUS=$(grep "Status:" "$WORKTREE_PATH/COMPLETION.md" | sed 's/.*Status: //')
    SUMMARY=$(grep -A 5 "## Summary" "$WORKTREE_PATH/COMPLETION.md" | tail -n +2)
fi
```

Report results:
```
Execution Results
=================

{For each issue:}
Issue #{number}: {STATUS}
  Worktree: {worktree_path}
  Branch: {branch_name}
  {Summary snippet}

Overall: {success_count}/{total_count} succeeded
```

If any failed, offer retry:
```
{N} issue(s) failed. Options:
1. Retry failed issues
2. Continue to PR creation for successful ones
3. Abort
```

### Step 7: Create PRs (unless --no-pr)

For each successful issue worktree:

```bash
cd "$WORKTREE_PATH"

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

{summary from COMPLETION.md}

## Changes
{files changed from git diff --stat}

## Verification
- [x] Tests pass
- [x] Lint clean
EOF
)" \
  --assignee @me
```

Capture PR URL for each issue.

### Step 8: Report Completion

```
GitHub Issues Fixed
===================

{For each issue:}
Issue #{number}: {title}
  Status: {SUCCESS|FAILED}
  Branch: {branch}
  PR: {pr_url}
  Worktree: {worktree_path}

Summary:
- Issues processed: {total}
- PRs created: {pr_count}
- Failed: {failed_count}

{If worktrees used:}
Clean up worktrees when done:
  git worktree remove {path1}
  git worktree remove {path2}
```

## Worktree Management

See `references/worktree-management.md` for full details.

Worktree naming uses the `github` template from config:
- Default: `gh-{number}-{slug}`
- Example: `gh-123-fix-login-redirect`

Worktree location from `worktree_dir` config (default: `./` relative to git common dir).

## Error Handling

**Issue not found:**
```
Issue #{number} not found.

Check:
- Issue number is correct
- You have access to the repository
- gh CLI is authenticated
```

**Prompt generation failed:**
```
Failed to generate prompt for issue #{number}.

Error: {error}

Try fetching the issue manually:
  gh issue view {number}
```

**Execution failed:**
```
Execution failed for issue #{number}.

Status: {error from result}
Log: {log path if available}

Options:
1. Retry this issue
2. Skip and continue
3. Abort
```

**PR creation failed:**
```
PR creation failed for issue #{number}.

Error: {error}

Manual creation:
  cd {worktree_path}
  git push -u origin {branch}
  gh pr create --title "Fix: {title}" --body "Fixes #{number}"
```

## Examples

**Fix single issue:**
```
/founder-mode:fix-gh-issue 123
```
→ Asks for model, generates prompt, runs via run-prompt, creates PR

**Fix multiple issues (always separate worktrees):**
```
/founder-mode:fix-gh-issue 123 456 789
```
→ Creates 3 separate worktrees, generates 3 prompts, runs via orchestrate, creates 3 separate PRs

**Fix dependent issues:**
```
/founder-mode:fix-gh-issue 100 101  # where 101 depends on 100
```
→ Creates separate worktrees, works in parallel, merges 100 into 101's worktree when ready, creates 2 PRs

**Fix with specific model:**
```
/founder-mode:fix-gh-issue 123 --model codex
```
→ Skips model selection, uses codex

**Fix without worktree:**
```
/founder-mode:fix-gh-issue 123 --no-worktree
```
→ Works in current directory instead of isolated worktree

**Fix as draft PR:**
```
/founder-mode:fix-gh-issue 123 --draft
```
→ Creates draft PR instead of ready-for-review

## Success Criteria

- [ ] Issue(s) fetched and parsed
- [ ] Prompt(s) generated in .founder-mode/prompts/gh-issues/
- [ ] User selected model (or provided via --model)
- [ ] Execution delegated to run-prompt (single) or orchestrate (multiple)
- [ ] Results collected from worktrees
- [ ] PR(s) created with proper references
- [ ] User shown completion summary with PR URLs
