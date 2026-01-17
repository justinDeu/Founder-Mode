---
name: founder-mode:run-prompt
description: Execute a prompt with Claude or other AI models
argument-hint: <prompt-file> [--model claude|codex|gemini] [--background] [--worktree]
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Task
  - AskUserQuestion
---

# Run Prompt

Execute a prompt file using Claude (Task subagent) or external AI models via executor.py.

## Arguments

Parse `$ARGUMENTS` for:

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `<prompt-file>` | positional | required | Path to prompt .md file |
| `--model` | option | `claude` | Model to use: `claude`, `codex`, `codex-high`, `gemini`, `gemini-high`, etc. |
| `--background` | flag | false | Run in background (Task with `run_in_background` or executor background mode) |
| `--worktree` | flag | false | Create isolated git worktree before execution |
| `--cwd` | option | repo root | Working directory for execution |
| `--log` | option | auto | Log file path (non-Claude models only) |

## Execution Flow

<mode_detection>
Determine execution mode based on `--model`:

**Claude models** (default): `claude`
- Execute via Task subagent
- Prompt content injected directly into Task prompt

**Non-Claude models**: `codex`, `codex-high`, `codex-xhigh`, `gemini`, `gemini-high`, `gemini-xhigh`, `zai`, `local`, etc.
- Execute via executor.py script
- Parse JSON result and report status
</mode_detection>

### Step 1: Parse Arguments

```
prompt_file = first positional argument (required)
model = --model value or "claude"
background = --background flag present
worktree = --worktree flag present
cwd = --cwd value or current repo root
log = --log value or auto-generated
```

Validate prompt file exists:
```bash
test -f "$prompt_file" && echo "exists" || echo "missing"
```

### Step 2: Worktree Creation (if --worktree)

Create isolated git worktree for execution. This happens in the skill layer, not executor.

```bash
# Get repo root
REPO_ROOT=$(git rev-parse --show-toplevel)
REPO_NAME=$(basename "$REPO_ROOT")

# Extract prompt identifier from filename
PROMPT_SLUG=$(basename "$prompt_file" .md)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Create worktree directory
WORKTREES_DIR="${REPO_ROOT}/.worktrees"
mkdir -p "$WORKTREES_DIR"

# Branch and worktree names
BRANCH_NAME="prompt/${PROMPT_SLUG}"
WORKTREE_PATH="${WORKTREES_DIR}/${REPO_NAME}-${PROMPT_SLUG}-${TIMESTAMP}"

# Check if branch exists
if git branch --list "$BRANCH_NAME" | grep -q .; then
    # Branch exists - create worktree from it
    git worktree add "$WORKTREE_PATH" "$BRANCH_NAME"
else
    # Create new branch from main
    git worktree add -b "$BRANCH_NAME" "$WORKTREE_PATH" main
fi

# Copy prompt as TASK.md
cp "$prompt_file" "$WORKTREE_PATH/TASK.md"
```

Update `cwd` to `$WORKTREE_PATH` for subsequent execution.

### Step 3a: Claude Execution (default)

Read prompt content and spawn Task subagent.

```
1. Read prompt file content
2. Build Task prompt with injected content
3. Spawn Task subagent
```

<claude_foreground>
For foreground execution (default):

```
Task(
  prompt: """
Execute the following task:

<task>
{prompt_content}
</task>

<working_directory>
{cwd}
</working_directory>

Execute the task completely. When finished, provide a summary of what was accomplished.
""",
  subagent_type: "general-purpose"
)
```
</claude_foreground>

<claude_background>
For background execution (`--background`):

Use Task with `run_in_background: true` and include internal verification instructions.

```
Task(
  prompt: """
Execute the following task in the background:

<task>
{prompt_content}
</task>

<working_directory>
{cwd}
</working_directory>

<verification_instructions>
After completing the task:
1. Verify all changes compile/build successfully
2. Run any relevant tests
3. Create a completion summary file at {cwd}/COMPLETION.md with:
   - What was accomplished
   - Files modified
   - Any issues encountered
   - Verification results (build/test status)
</verification_instructions>

Execute the task completely. Write COMPLETION.md when done.
""",
  subagent_type: "general-purpose",
  run_in_background: true
)
```

Report to user:
```
Background task started.

Working directory: {cwd}
Completion file: {cwd}/COMPLETION.md

Check progress with: cat {cwd}/COMPLETION.md
```
</claude_background>

### Step 3b: Non-Claude Execution

Call executor.py for non-Claude models.

<executor_path>
Locate executor.py (adjust path based on your setup):
```bash
EXECUTOR="/home/thor/fun/founder-mode/daplug/skills/prompt-executor/scripts/executor.py"
```
</executor_path>

<executor_call>
Build and execute command:

```bash
python3 "$EXECUTOR" \
  --prompt "$prompt_file" \
  --cwd "$cwd" \
  --model "$model" \
  --run
```

If `--log` specified:
```bash
python3 "$EXECUTOR" \
  --prompt "$prompt_file" \
  --cwd "$cwd" \
  --model "$model" \
  --run 2>&1 | tee "$log"
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

### Step 4: Report Status

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

| Model | Type | Description |
|-------|------|-------------|
| `claude` | Task subagent | Claude in current context |
| `codex` | executor.py | OpenAI Codex (gpt-5.2-codex) |
| `codex-high` | executor.py | Codex with high reasoning |
| `codex-xhigh` | executor.py | Codex with max reasoning |
| `gemini` | executor.py | Gemini 3 Flash |
| `gemini-high` | executor.py | Gemini 2.5 Pro |
| `gemini-xhigh` | executor.py | Gemini 3 Pro |
| `zai` | executor.py | Z.AI GLM-4.7 |
| `local` | executor.py | Local model via LMStudio |

## Error Handling

- Prompt file not found: Report error, list available prompts in directory
- Worktree creation fails: Report git error, suggest checking branch status
- Executor not found: Report path issue, check executor location
- Model not recognized: List available models
- Background task fails: Check log file for details

## Examples

**Run with Claude (default)**:
```
/founder-mode:run-prompt prompts/001-setup.md
```

**Run with Codex**:
```
/founder-mode:run-prompt prompts/001-setup.md --model codex
```

**Run in background with worktree**:
```
/founder-mode:run-prompt prompts/001-setup.md --model codex --background --worktree
```

**Run with custom working directory**:
```
/founder-mode:run-prompt prompts/001-setup.md --cwd /path/to/project
```
