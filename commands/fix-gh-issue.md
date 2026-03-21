---
name: fm:fix-gh-issue
description: Fix a GitHub issue end-to-end from issue to PR
argument-hint: "<issue-number> [--no-worktree] [--no-pr] [--draft] [--model ?|claude|codex|...]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - Skill
  - Task
  - AskUserQuestion
---

# Fix GitHub Issue

Fix GitHub issues end-to-end: fetch issue, create worktree, generate prompt, execute via `/fm:run-prompt`, create PR.

## Arguments

Parse from $ARGUMENTS:
- Issue number(s): Single (123) or multiple (123 456 789)
- `--no-worktree`: Skip worktree creation (work in current directory)
- `--branch`: Custom branch name (default: `gh-{number}-{slug}`)
- `--no-pr`: Skip PR creation, just commit
- `--draft`: Create draft PR
- `--model`: Model to use. Omit or use `?` to select interactively.

## Single Issue Flow

### 1. Fetch Issue

```bash
gh issue view $NUMBER --json title,body,labels,comments,url
```

Display:
```
Issue #{number}: {title}
Labels: {labels}
URL: {url}

{body preview, first 300 chars}
```

### 2. Create Worktree (unless --no-worktree)

Create worktree before anything else. This is the working context for the fix.

Read `worktree_dir` from founder_mode_config (default: `./`).

```bash
COMMON_DIR=$(git rev-parse --git-common-dir | sed 's|/\.git$||; s|/\.bare$||')

# Generate slug from title
SLUG=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/ /g' | \
  tr ' ' '\n' | grep -vE '^(a|an|the|in|on|at|to|for|of)$' | head -5 | \
  tr '\n' '-' | sed 's/--*/-/g' | sed 's/-$//' | cut -c1-30)

BRANCH="gh-${NUMBER}-${SLUG}"

case "$WORKTREE_DIR_CONFIG" in
  /*|~*) WORKTREE_BASE="${WORKTREE_DIR_CONFIG/#\~/$HOME}" ;;
  *)     WORKTREE_BASE="$COMMON_DIR/$WORKTREE_DIR_CONFIG" ;;
esac

WORKTREE_PATH="$WORKTREE_BASE/$BRANCH"

git worktree add "$WORKTREE_PATH" -b "$BRANCH" main
```

Report:
```
Created worktree: {WORKTREE_PATH}
Branch: {BRANCH}
```

### 3. Generate Prompt

Generate a prompt file for the issue. Save to the main repo (not the worktree) so prompts survive worktree cleanup.

```bash
PROMPT_DIR="$COMMON_DIR/main/.founder-mode/prompts/gh-issues"
mkdir -p "$PROMPT_DIR"
PROMPT_FILE="$PROMPT_DIR/gh-${NUMBER}-${SLUG}.md"
```

Write using this template:

```markdown
# Fix GitHub Issue #{number}

<objective>
Fix issue #{number}: {title}

{full issue body}
</objective>

<context>
Repository: {repo from git remote}
Issue URL: {url}
Labels: {labels}
</context>

<requirements>
{Requirements parsed from issue body}
</requirements>

<implementation>
1. Search codebase for files related to issue
2. Analyze affected components
3. Implement the fix/feature
4. Verify changes work correctly
</implementation>

<output>
On completion, create a commit:
- Message: {type}: {description}\n\nFixes #{number}\n\n- {change 1}\n- {change 2}
- Stage only relevant files
</output>
```

Report:
```
Generated prompt: {PROMPT_FILE}
```

### 4. Model Selection

<critical>
ALWAYS ask unless `--model` is explicitly provided.
</critical>

```
AskUserQuestion(
  questions: [{
    question: "Which model should execute this prompt?",
    header: "Model",
    options: [
      { label: "claude", description: "Claude in current session" },
      { label: "codex", description: "OpenAI gpt-5.2-codex via codex CLI" },
      { label: "gemini", description: "Gemini 3 Flash via gemini CLI" },
      { label: "claude-zai", description: "Claude CLI with Z.AI backend" }
    ]
  }]
)
```

### 5. Execute

Delegate to run-prompt. Pass the absolute prompt path, selected model, and worktree path as cwd. Do NOT pass `--worktree` (worktree already created in step 2).

```
Skill(
  skill: "founder-mode:run-prompt",
  args: "{PROMPT_FILE} --model {model} --cwd {WORKTREE_PATH}"
)
```

If `--no-worktree` was set, omit `--cwd` (run-prompt uses repo root).

### 6. Create PR (unless --no-pr)

After execution completes, check for changes in the worktree:

```bash
cd "$WORKTREE_PATH"

# Verify there are commits
COMMITS=$(git log --oneline main..HEAD | wc -l)
if [ "$COMMITS" -eq 0 ]; then
    echo "No commits found. Skipping PR creation."
    # report and exit
fi

git push -u origin "$BRANCH"

gh pr create \
  ${DRAFT:+--draft} \
  --title "fix: {issue title}" \
  --body "$(cat <<'PREOF'
## Summary
Fixes #{number}

{brief description of changes}

## Changes
{output of git diff --stat main..HEAD}
PREOF
)"
```

### 7. Report

```
Issue #{number}: {title}
  Status: {SUCCESS|FAILED}
  Branch: {BRANCH}
  PR: {pr_url}
  Worktree: {WORKTREE_PATH}

Clean up when done:
  git worktree remove {WORKTREE_PATH}
```

---

## Multiple Issue Flow

### 1. Fetch Issues

Fetch all issues:
```bash
for NUMBER in $ISSUE_NUMBERS; do
  gh issue view $NUMBER --json title,body,labels,comments,url
done
```

Display summary of each issue.

### 2. Dependency Analysis

Analyze the issues to determine if any depend on each other.

<important>
Dependency means one issue's solution requires or builds upon another's changes.
File overlap from parallel development is NOT a dependency.
</important>

If dependencies found, present the analysis and ask user to verify:

```
AskUserQuestion(
  questions: [{
    question: "Does this dependency analysis look correct?",
    header: "Verify",
    options: [
      { label: "Correct", description: "Proceed with this plan" },
      { label: "Actually independent", description: "No dependency, run in parallel" },
      { label: "Reverse dependency", description: "Swap the dependency direction" }
    ]
  }]
)
```

### 3. Generate Prompts

Generate one prompt file per issue using the same template as single-issue step 3.

### 4. Model Selection

Same as single-issue step 4. One model selection applies to all issues.

### 5. Execute

<critical>
Each issue ALWAYS gets its own worktree and its own PR.
Never combine issues without explicit user confirmation.
</critical>

Delegate to orchestrate for parallel execution. Orchestrate handles worktree creation per prompt.

```bash
PROMPT_LIST=$(echo $PROMPT_FILES | tr ' ' ',')
```

```
Skill(
  skill: "founder-mode:orchestrate",
  args: "{PROMPT_LIST} --model {model} --worktree"
)
```

If `--no-worktree` was set, omit `--worktree`.

### 6. Collect Results

Check each worktree for commits:
```bash
for WORKTREE in $WORKTREE_PATHS; do
  COMMITS=$(git -C "$WORKTREE" log --oneline main..HEAD | wc -l)
  CHANGES=$(git -C "$WORKTREE" diff --stat main..HEAD)
done
```

If any failed, offer retry or skip.

### 7. Create PRs (unless --no-pr)

Create one PR per issue using the same logic as single-issue step 6.

### 8. Report

```
Issues Fixed
============

{For each issue:}
Issue #{number}: {title}
  Status: {SUCCESS|FAILED}
  Branch: {branch}
  PR: {pr_url}

Summary: {success_count}/{total} succeeded

Clean up worktrees:
  {for each: git worktree remove {path}}
```

## Worktree Management

See `references/worktree-management.md` for details.

Naming uses the `github` template: `gh-{number}-{slug}`
Location from `worktree_dir` config (default: `./` relative to git common dir).

## Error Handling

- **Issue not found:** Check issue number, repo access, gh auth
- **Prompt generation failed:** Try `gh issue view {number}` manually
- **Execution failed:** Check log output, offer retry or skip
- **PR creation failed:** Show manual `gh pr create` command
