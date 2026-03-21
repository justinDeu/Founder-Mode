---
name: fm:run-prompt
description: Execute a prompt with Claude or other AI models
argument-hint: <prompt-file> [--model ?|claude|codex|gemini|...] [--background] [--worktree] [--loop] [--two-stage]
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Task
  - AskUserQuestion
---

# Run Prompt

Execute a prompt file. Default: runs immediately in Claude with no menus, no confirmations.

## Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `<prompt-file>` | positional | required | Path to prompt .md file (absolute or relative) |
| `--model` | option | (interactive) | Model to use. Omit or use `?` to select interactively. |
| `--background` | flag | false | Run in background |
| `--worktree` | flag | false | Create isolated git worktree |
| `--worktree-cleanup` | flag | false | Remove worktree after execution (with --worktree) |
| `--cwd` | option | repo root | Working directory for execution |
| `--log` | option | auto | Log file path (non-Claude only) |
| `--verbose` | flag | false | Show detailed execution metadata |
| `--loop` | flag | false | Enable verification loop (non-Claude only) |
| `--two-stage` | flag | false | Enable two-stage verification (requires --loop) |

## Fast Path

<critical>
When `--model` is provided, skip Step 1 (model selection).
When `--cwd` is provided, skip Step 2 (worktree creation).
When both are provided, skip directly to Step 3 (Execution).
</critical>

This is the common path when called by other commands (e.g., fix-gh-issue) that have already handled model selection and worktree setup.

## Execution Flow

### Step 1: Model Selection

If `--model` is provided, skip this step.

If `--model` is omitted or set to `?`, ask the user:

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

Wait for user response before proceeding.

### Step 2: Worktree Creation (only if --worktree)

Skip if `--worktree` is not set. If `--cwd` is provided without `--worktree`, use that directory as-is.

See `references/worktree-management.md` for full details.

```bash
COMMON_DIR=$(git rev-parse --git-common-dir | sed 's|/\.git$||; s|/\.bare$||')
```

Read `worktree_dir` and `worktree_naming.prompt` from founder_mode_config.
Defaults: `worktree_dir: ./`, naming: `prompt-{number}-{slug}`

```bash
PROMPT_NUMBER=$(basename "$prompt_file" .md | grep -oE '^[0-9]+')
PROMPT_SLUG=$(basename "$prompt_file" .md | sed 's/^[0-9]*-//')
WORKTREE_NAME="prompt-${PROMPT_NUMBER}-${PROMPT_SLUG}"

case "$WORKTREE_DIR_CONFIG" in
  /*|~*) WORKTREE_BASE="${WORKTREE_DIR_CONFIG/#\~/$HOME}" ;;
  *)     WORKTREE_BASE="$COMMON_DIR/$WORKTREE_DIR_CONFIG" ;;
esac

WORKTREE_PATH="$WORKTREE_BASE/$WORKTREE_NAME"
```

If currently in a worktree (cwd != common dir), confirm the path with the user.

Create the worktree:

```bash
mkdir -p "$(dirname "$WORKTREE_PATH")"

if git branch --list "$WORKTREE_NAME" | grep -q .; then
    git worktree add "$WORKTREE_PATH" "$WORKTREE_NAME"
else
    git worktree add "$WORKTREE_PATH" -b "$WORKTREE_NAME" main
fi
```

Set `cwd` to `$WORKTREE_PATH` for execution.

If `--worktree-cleanup` is set, remove the worktree after execution completes:
```bash
git worktree remove "$WORKTREE_PATH"
```

### Step 3: Execution

Determine mode from `--model`:

- **Claude** (`claude`): Execute via Task subagent
- **Non-Claude** (everything else): Execute via executor.py

#### Claude Execution

Read prompt file content and spawn Task subagent.

**Foreground (default):**

```
Task(
  prompt: """
<task>
{prompt_content}
</task>

<working_directory>{cwd}</working_directory>

Execute completely. Summarize what was accomplished.
""",
  subagent_type: "general-purpose"
)
```

**Background (`--background`):**

```
Task(
  prompt: """
<task>
{prompt_content}
</task>

<working_directory>{cwd}</working_directory>

<completion_protocol>
When finished, write {cwd}/COMPLETION.md with:

# Completion Status
**Status:** SUCCESS | FAILED | PARTIAL
**Finished:** {timestamp}

## Summary
[What was accomplished]

## Files Changed
- path/to/file - description
</completion_protocol>

Execute the task completely, then write COMPLETION.md.
""",
  subagent_type: "general-purpose",
  run_in_background: true
)
```

Report background task location:
```
Background task started.
Working directory: {cwd}
Check status: cat {cwd}/COMPLETION.md
```

#### Non-Claude Execution

Locate executor.py:
```bash
PLUGIN_ROOT=$(git rev-parse --git-common-dir 2>/dev/null | sed 's|/\.bare$||; s|/\.git$||')
EXECUTOR="$PLUGIN_ROOT/scripts/executor.py"
```

Run:
```bash
python3 "$EXECUTOR" \
  --prompt "$prompt_file" \
  --cwd "$cwd" \
  --model "$model"
```

Additional flags passed through: `--background`, `--loop`, `--two-stage`, `--log`.

Parse JSON result from executor and report status.

### Step 4: Report

**Foreground:**
```
Execution Complete
Model: {model}
Prompt: {prompt_file}
Working Directory: {cwd}
{summary}
```

**Background:**
```
Background Execution Started
Model: {model}
Log: {log_path}
Monitor: tail -f {log_path}
```

**Worktree (append to either):**
```
Worktree: {worktree_path}
Branch: {branch_name}
Clean up when done: git worktree remove {worktree_path}
```

## Verification Loop (--loop)

For non-Claude models only. executor.py handles the loop internally.

`--two-stage` adds two-pass verification:
1. Spec compliance (marker: `SPEC_COMPLIANCE_VERIFIED`)
2. Code quality (marker: `QUALITY_VERIFIED`)

## Model Reference

| Model | Type | CLI |
|-------|------|-----|
| `claude` | Task subagent | claude |
| `codex` | executor.py | codex |
| `codex-high` | executor.py | codex (high reasoning) |
| `codex-xhigh` | executor.py | codex (max reasoning) |
| `gemini` | executor.py | gemini |
| `gemini-high` | executor.py | gemini (2.5 Pro) |
| `gemini-xhigh` | executor.py | gemini (3 Pro) |
| `zai` | executor.py | zai |
| `opencode` | executor.py | opencode |
| `opencode-zai` | executor.py | opencode (Z.AI) |
| `opencode-codex` | executor.py | opencode (codex) |
| `claude-zai` | executor.py | claude (Z.AI backend) |
| `local` | executor.py | lmstudio |

## Error Handling

- **Prompt not found:** List available prompts in the prompts directory
- **Task subagent fails:** Report error, suggest checking prompt content
- **Executor not found:** Check plugin install path
- **Model not recognized:** List supported models from the table above
