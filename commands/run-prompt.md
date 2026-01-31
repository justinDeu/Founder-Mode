---
name: founder-mode:run-prompt
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
| `<prompt-file>` | positional | required | Path to prompt .md file |
| `--model` | option | (prompt) | Model to use. Omit or use `?` to select interactively. |
| `--background` | flag | false | Run in background |
| `--worktree` | flag | false | Create isolated git worktree |
| `--worktree-cleanup` | flag | false | Remove worktree after execution (with --worktree) |
| `--cwd` | option | repo root | Working directory |
| `--log` | option | auto | Log file path (non-Claude only) |
| `--verbose` | flag | false | Show detailed execution metadata |
| `--loop` | flag | false | Enable verification loop (non-Claude only) |
| `--two-stage` | flag | false | Enable two-stage verification (requires --loop) |

## Flags

### --two-stage

Enable two-stage verification (requires `--loop`):

1. **Stage 1: Spec Compliance**
   - Does output match requirements?
   - Are all features implemented?
   - Do tests pass?
   - Marker: `SPEC_COMPLIANCE_VERIFIED`

2. **Stage 2: Code Quality** (only runs if Stage 1 passes)
   - Is code well-organized?
   - Is error handling complete?
   - Any obvious improvements?
   - Marker: `QUALITY_VERIFIED`

Use for complex prompts where both correctness and quality matter.

Example:
```bash
/fm:run-prompt my-feature --model codex --loop --two-stage
```

Result JSON includes:
```json
{
  "status": "success",
  "two_stage": true,
  "stages_completed": ["spec", "quality"]
}
```

## Model Selection (REQUIRED)

<critical>
ALWAYS ask the user to select a model before execution. This step is MANDATORY and must NEVER be skipped, even if it seems obvious which model to use.

The only exception is when `--model` is explicitly provided in the arguments.
</critical>

When no `--model` is specified (or `--model ?` is used):

1. Read prompt content
2. **MUST** ask user to select a model using AskUserQuestion
3. Wait for user selection
4. Execute with chosen model
5. Show result

```
/fm:run-prompt prompts/fix-bug.md
```

To skip the model selection prompt, specify a model explicitly:
```
/fm:run-prompt prompts/fix-bug.md --model claude
```

## Execution Flow

<mode_detection>
Determine execution mode based on `--model`:

**Claude models** (default): `claude`
- Execute via Task subagent
- Prompt content injected directly into Task prompt

**Non-Claude models**: `codex`, `codex-high`, `codex-xhigh`, `gemini`, `gemini-high`, `gemini-xhigh`, `zai`, `opencode`, `opencode-zai`, `opencode-codex`, `claude-zai`, `local`, etc.
- Execute via executor.py script
- Parse JSON result and report status
</mode_detection>

### Step 1: Parse Arguments

```
prompt_file = first positional argument (required)
model = --model value or null (not specified)
background = --background flag present
worktree = --worktree flag present
cwd = --cwd value or current repo root
log = --log value or auto-generated
```

Validate prompt file exists:
```bash
test -f "$prompt_file" && echo "exists" || echo "missing"
```

### Step 2: Model Selection (MANDATORY unless --model provided)

<critical>
If `model` is null or `?`, you MUST use AskUserQuestion to ask the user which model to use. Do NOT proceed to execution without explicit user selection. Do NOT assume "claude" or any other default.
</critical>

```
AskUserQuestion(
  questions: [{
    question: "Which model should execute this prompt?",
    header: "Model",
    options: [
      { label: "claude", description: "Claude in current session" },
      { label: "claude-zai", description: "Claude CLI with Z.AI backend" },
      { label: "codex", description: "OpenAI gpt-5.2-codex via codex CLI" },
      { label: "gemini", description: "Gemini 3 Flash via gemini CLI" }
    ]
  }]
)
```

**Wait for user response before proceeding to Step 3.**

### Step 3: Worktree Creation (if --worktree)

Create isolated git worktree for execution. This happens in the skill layer, not executor.

See `references/worktree-management.md` for full details.

**Step 3a: Detect Location**

```bash
COMMON_DIR=$(git rev-parse --git-common-dir | sed 's|/\.git$||')
CURRENT_DIR=$(pwd)
```

**Step 3b: Read Config**

Read `worktree_dir` and `worktree_naming.prompt` from founder_mode_config.

Defaults:
- `worktree_dir: ./` (flat layout in common directory)
- `worktree_naming.prompt: prompt-{number}-{slug}`

**Step 3c: Generate Name**

```bash
# Extract prompt number from filename (e.g., 001 from 001-setup.md)
PROMPT_NUMBER=$(basename "$prompt_file" .md | grep -oE '^[0-9]+')

# Generate slug from prompt title or filename
PROMPT_SLUG=$(basename "$prompt_file" .md | sed 's/^[0-9]*-//')

# Apply naming template
WORKTREE_NAME="prompt-${PROMPT_NUMBER}-${PROMPT_SLUG}"
```

**Step 3d: Compute Path**

```bash
# Resolve worktree_dir relative to common directory
case "$WORKTREE_DIR_CONFIG" in
  /*|~*) WORKTREE_BASE="${WORKTREE_DIR_CONFIG/#\~/$HOME}" ;;
  *)     WORKTREE_BASE="$COMMON_DIR/$WORKTREE_DIR_CONFIG" ;;
esac

WORKTREE_PATH="$WORKTREE_BASE/$WORKTREE_NAME"
```

**Step 3e: Check Location and Confirm**

If `CURRENT_DIR != COMMON_DIR` (user is in a worktree), ask for confirmation:

```
AskUserQuestion(
  questions: [{
    question: "You're in worktree '{current_worktree}'. Create new worktree at {WORKTREE_PATH}?",
    header: "Worktree Path",
    options: [
      { label: "Yes, create there", description: "New worktree at {path}" },
      { label: "Change location", description: "Specify a different path" },
      { label: "Cancel", description: "Don't create a worktree" }
    ]
  }]
)
```

**Step 3f: Create Worktree**

```bash
# Create parent directory if needed
mkdir -p "$(dirname "$WORKTREE_PATH")"

# Check if branch exists
if git branch --list "$WORKTREE_NAME" | grep -q .; then
    git worktree add "$WORKTREE_PATH" "$WORKTREE_NAME"
else
    git worktree add "$WORKTREE_PATH" -b "$WORKTREE_NAME" main
fi

# Copy prompt as TASK.md
cp "$prompt_file" "$WORKTREE_PATH/TASK.md"
```

Update `cwd` to `$WORKTREE_PATH` for subsequent execution.

**Step 3g: Cleanup (if --worktree-cleanup)**

If `--worktree-cleanup` flag was specified, remove worktree after execution:

```bash
git worktree remove "$WORKTREE_PATH"
git worktree prune
```

By default, worktrees are kept for review. Report location after execution:

```
Worktree: {WORKTREE_PATH}
Branch: {WORKTREE_NAME}

Clean up when done:
  git worktree remove {WORKTREE_PATH}
```

### Step 4a: Claude Execution

Read prompt content and spawn Task subagent.

```
1. Read prompt file content
2. Build Task prompt with injected content
3. Spawn Task subagent
```

<claude_foreground>
**Default foreground execution (no flags):**

```
Task(
  prompt: """
<task>
{prompt_content}
</task>

Execute completely. Summarize what was accomplished.
""",
  subagent_type: "general-purpose"
)
```

Output for default case:
```
Running: {prompt_file}

{Task result/summary}
```

If `--verbose` flag is set, also show:
```
Model: claude
Working Directory: {cwd}
Duration: {elapsed}
```
</claude_foreground>

<claude_background>
**Background execution (`--background`):**

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

## Verification
- [x] or [ ] Build passed
- [x] or [ ] Tests passed

## Issues (if any)
[Problems encountered]
</completion_protocol>

Execute the task completely, then write COMPLETION.md.
""",
  subagent_type: "general-purpose",
  run_in_background: true
)
```

Report to user:
```
Background task started.

Working directory: {cwd}

Check status:
  cat {cwd}/COMPLETION.md

Watch progress:
  watch -n 5 'test -f {cwd}/COMPLETION.md && cat {cwd}/COMPLETION.md || echo "Still running..."'
```
</claude_background>

<worktree_background>
**Worktree + Background combination (`--worktree --background`):**

1. Create worktree first (sync operation)
2. Spawn background task in worktree
3. COMPLETION.md written to worktree directory
4. After completion, changes are in isolated branch

Report to user:
```
Background task started in worktree.

Worktree: {worktree_path}
Branch: {branch_name}

Check status:
  cat {worktree_path}/COMPLETION.md

After completion:
  cd {worktree_path}
  git log --oneline -5
```
</worktree_background>

<non_claude_background>
**Non-Claude background execution:**

For non-Claude models with `--background`, executor.py handles logging.

Report to user:
```
Background task started.

Model: {model}
Log: {log_path}

Watch progress:
  tail -f {log_path}

Check process:
  ps -p {pid}
```
</non_claude_background>

### Step 4b: Non-Claude Execution

Call executor.py for non-Claude models.

<executor_path>
Locate executor.py from the plugin's install path:
```bash
# Get plugin root from installed_plugins.json
PLUGIN_ROOT=$(jq -r '.plugins."founder-mode@local"[0].installPath // empty' ~/.claude/plugins/installed_plugins.json 2>/dev/null)

# Fallback: check if we're in the plugin directory
if [ -z "$PLUGIN_ROOT" ]; then
    PLUGIN_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
fi

EXECUTOR="$PLUGIN_ROOT/scripts/executor.py"
```
</executor_path>

<executor_call>
Build and execute command:

```bash
python3 "$EXECUTOR" \
  --prompt "$prompt_file" \
  --cwd "$cwd" \
  --model "$model"
```

If `--log` specified:
```bash
python3 "$EXECUTOR" \
  --prompt "$prompt_file" \
  --cwd "$cwd" \
  --model "$model" 2>&1 | tee "$log"
```
</executor_call>

<parse_result>
Parse JSON output from executor:

```json
{
  "repo": "project-name",
  "model": "codex",
  "cli_display": "codex (gpt-5.2-codex)",
  "prompts": [{
    "file": "/path/to/prompt.md",
    "title": "Prompt Title",
    "execution": {
      "status": "running",
      "pid": 12345,
      "log": "/path/to/log"
    }
  }]
}
```

Extract and report:
- `execution.status`: running, completed, error
- `execution.pid`: process ID for background tasks
- `execution.log`: log file path
</parse_result>

### Step 5: Report Status

<output_format>
Present execution status to user:

**Foreground (completed)**:
```
Execution Complete

Model: {model} ({cli_display})
Prompt: {prompt_file}
Working Directory: {cwd}

{summary from Task or executor output}
```

**Background (started)**:
```
Background Execution Started

Model: {model} ({cli_display})
Prompt: {prompt_file}
Working Directory: {cwd}
PID: {pid}
Log: {log_path}

Monitor with:
  tail -f {log_path}

Check process:
  ps -p {pid}
```

**Worktree mode**:
```
Execution Started in Worktree

Model: {model}
Prompt: {prompt_file}
Worktree: {worktree_path}
Branch: {branch_name}

After completion:
  cd {worktree_path}
  git log --oneline -5
  git diff main...HEAD --stat
```
</output_format>

## Model Reference

| Model | Type | CLI | Description |
|-------|------|-----|-------------|
| `claude` | Task subagent | claude | Claude in current context |
| `codex` | executor.py | codex | OpenAI Codex (gpt-5.2-codex) |
| `codex-high` | executor.py | codex | Codex with high reasoning |
| `codex-xhigh` | executor.py | codex | Codex with max reasoning |
| `gemini` | executor.py | gemini | Gemini 3 Flash |
| `gemini-high` | executor.py | gemini | Gemini 2.5 Pro |
| `gemini-xhigh` | executor.py | gemini | Gemini 3 Pro |
| `zai` | executor.py | zai | Z.AI GLM-4.7 |
| `opencode` | executor.py | opencode | OpenCode with default model (zen) |
| `opencode-zai` | executor.py | opencode | OpenCode with Z.AI GLM-4.7 |
| `opencode-codex` | executor.py | opencode | OpenCode with gpt-5.2-codex |
| `claude-zai` | executor.py | claude | Claude CLI with Z.AI backend |
| `local` | executor.py | lmstudio | Local model via LMStudio |

## Error Handling

<error_prompt_not_found>
If prompt file doesn't exist:
```
Prompt not found: {prompt_file}

Available prompts:
```

Then run `ls ./prompts/*.md` and show available files.
</error_prompt_not_found>

<error_task_failure>
If Task subagent fails:
```
Task failed.

Check prompt content and try again.
Error: {error_message}
```
</error_task_failure>

Other errors:
- Worktree creation fails: Report git error, suggest checking branch status
- Executor not found: Report path issue, check executor location
- Model not recognized: List available models
- Background task fails: Check log file for details

## Examples

**Run with Claude (default)**:
```
/fm:run-prompt prompts/001-setup.md
```

**Run with Codex**:
```
/fm:run-prompt prompts/001-setup.md --model codex
```

**Run in background with worktree**:
```
/fm:run-prompt prompts/001-setup.md --model codex --background --worktree
```

**Run with custom working directory**:
```
/fm:run-prompt prompts/001-setup.md --cwd /path/to/project
```
