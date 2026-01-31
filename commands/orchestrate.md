---
name: fm:orchestrate
description: Execute multiple prompts with dependency management and parallel execution
argument-hint: <orchestrator-file|prompt-list> [--model ?|claude|codex|...] [--pending-only]
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Task
  - AskUserQuestion
---

# Orchestrate

Execute multiple prompts respecting dependencies. Prompts within the same wave run in parallel.

## Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `<input>` | positional | required | Orchestrator .md file OR comma-separated prompt IDs |
| `--model` | option | `?` | Default model. Use `?` for per-prompt selection. |
| `--pending-only` | flag | false | Skip prompts marked complete in orchestrator |
| `--worktree` | flag | false | Create isolated worktree per prompt |
| `--background` | flag | false | Run non-Claude models in background |

## Execution Flow

### Step 1: Parse Input

<get_orchestrator_path>
Locate orchestrator.py:
```bash
PLUGIN_ROOT=$(jq -r '.plugins."founder-mode@local"[0].installPath // empty' ~/.claude/plugins/installed_plugins.json 2>/dev/null)
if [ -z "$PLUGIN_ROOT" ]; then
    # Works in normal repos and worktrees
    PLUGIN_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
fi
if [ -z "$PLUGIN_ROOT" ]; then
    # Fallback for bare repo parent setups
    PLUGIN_ROOT=$(git rev-parse --git-common-dir 2>/dev/null | sed 's|/\.bare$||; s|/\.git$||')
fi
ORCHESTRATOR="$PLUGIN_ROOT/scripts/orchestrator.py"
```
</get_orchestrator_path>

<parse_input>
Call orchestrator.py to parse input:

```bash
python3 "$ORCHESTRATOR" "{input}" --prompts-dir ./prompts {--pending-only}
```

This returns JSON:
```json
{
  "orchestrator": "/path/to/file.md",
  "dependencies": {"003-01": [], "003-02": ["003-01"]},
  "waves": [["003-01"], ["003-02", "003-03"]],
  "prompts": {
    "003-01": {
      "id": "003-01",
      "path": "/path/to/003-01-name.md",
      "title": "Name",
      "completed": false,
      "dependencies": []
    }
  }
}
```
</parse_input>

<validate_input>
If no prompts found:
```
No prompts found matching input: {input}

Check that:
- Orchestrator file exists and has valid format
- Prompt IDs match files in ./prompts/
- Use --pending-only only if orchestrator has state tracking
```
Exit without proceeding.
</validate_input>

### Step 2: Display Execution Plan and Confirm

Show the user what will be executed:

```
Execution Plan
==============

Orchestrator: {orchestrator path or "Ad-hoc list"}
Total prompts: {count}
Waves: {wave count}

Wave 1:
  - 003-01: State Management Foundation
  - 003-02: New Project Command (depends on: 003-01)

Wave 2:
  - 003-03: Discuss Phase (depends on: 003-02)
  - 003-04: Plan Phase (depends on: 003-03)

{if --pending-only}
Skipped (already complete): 003-01, 003-02
{/if}
```

<confirm_plan>
Use AskUserQuestion to confirm before proceeding:

Question: "Proceed with this execution plan?"
Options:
- `Proceed` - Continue to model selection and execution
- `Modify` - Let user specify different prompts or options
- `Cancel` - Abort orchestration

If user selects "Modify", ask what they want to change:
- Different prompt list
- Different flags (--pending-only, --background, etc.)
- Different orchestrator file

If user selects "Cancel", exit with:
```
Orchestration cancelled.
```
</confirm_plan>

### Step 3: Model Selection

<model_selection_per_prompt>
If `--model ?` or no model specified, prompt for each prompt's model:

For each prompt, use AskUserQuestion:

Question: "Select model for {prompt_id}: {title}"
Options:
- `claude` - Claude in Task subagent
- `codex` - OpenAI Codex (gpt-5.2-codex)
- `gemini` - Gemini 3 Flash
- `codex-high` - Codex with high reasoning
- `opencode-zai` - OpenCode with Z.AI

Store selections in a mapping: `{prompt_id: model}`
</model_selection_per_prompt>

<model_selection_batch>
If `--model MODEL` specified, use that model for all prompts.

Store: `{prompt_id: MODEL}` for all prompts.
</model_selection_batch>

### Step 4: Execute Waves

For each wave in order:

<execute_wave>
**4a. Report wave start:**
```
Wave {N} Starting
=================
Prompts: {list of prompt IDs in this wave}
```

**4b. Spawn Task agents for all prompts in wave (PARALLEL):**

For Claude models, spawn directly as Task subagents.
For non-Claude models, spawn Tasks that call run-prompt.

CRITICAL: Spawn ALL tasks for the wave in a SINGLE message with multiple Task tool calls.

```
# For each prompt in wave, spawn in parallel:
Task(
  subagent_type: "general-purpose",
  run_in_background: true,  # if --background
  prompt: """
Execute prompt: {prompt_id} - {title}

<task>
{Read prompt file content}
</task>

Working directory: {cwd}
Model: {selected_model}

If non-Claude model, call:
/fm:run-prompt {prompt_path} --model {model} {--background} {--worktree}

Execute completely. Write results to .founder-mode/logs/{prompt_id}-result.json:
{
  "prompt_id": "{prompt_id}",
  "status": "success|failed",
  "summary": "what was accomplished",
  "files_changed": ["list", "of", "files"],
  "errors": []
}
"""
)
```

**4c. If --background with non-Claude, spawn monitors:**

For each background execution, spawn a readonly-log-watcher:

```
Task(
  subagent_type: "founder-mode:readonly-log-watcher",
  run_in_background: true,
  model: "haiku",
  prompt: """
Monitor execution of prompt {prompt_id}.
Log file: .founder-mode/logs/{log_file}
Timeout: 30 minutes

Report status changes. Final report when complete or timeout.
"""
)
```

**4d. Wait for wave completion:**

If foreground execution: Tasks complete synchronously, proceed to next wave.

If background execution: Poll result files until all prompts in wave complete.

```bash
# Check for completion
for prompt_id in wave:
    result_file=".founder-mode/logs/${prompt_id}-result.json"
    if [ -f "$result_file" ]; then
        status=$(jq -r '.status' "$result_file")
        # Track completion
    fi
done
```

**4e. Report wave results:**
```
Wave {N} Complete
=================
| Prompt | Status | Summary |
|--------|--------|---------|
| 003-01 | SUCCESS | Created templates and utilities |
| 003-02 | SUCCESS | Implemented new-project command |

Proceeding to Wave {N+1}...
```

**4f. Handle failures:**

If any prompt in wave fails:
```
Wave {N} had failures:
- 003-02: FAILED - {error summary}

Options:
1. Retry failed prompts
2. Skip and continue to next wave
3. Abort orchestration
```

Use AskUserQuestion to let user decide.
</execute_wave>

### Step 5: Final Report

After all waves complete:

```
Orchestration Complete
======================

Total prompts: {N}
Successful: {N}
Failed: {N}
Skipped: {N}

Results by wave:
| Wave | Prompts | Status |
|------|---------|--------|
| 1 | 003-01, 003-02 | Complete |
| 2 | 003-03, 003-04 | Complete |

{if orchestrator file}
Updated state in: {orchestrator path}
{/if}

Logs: .founder-mode/logs/
```

### Step 6: Update Orchestrator State (if applicable)

If input was an orchestrator file with state tracking, update completion checkboxes:

Read the orchestrator file, find state tracking section, update:
```
[x] 003-01-state-management.md
[x] 003-02-new-project.md
[ ] 003-03-discuss-phase.md  <- still pending if failed
```

Write updated file.

## Examples

**Run orchestrator file:**
```
/fm:orchestrate prompts/phase-completion/000-orchestrator.md
```

**Run specific prompts (no deps, all parallel):**
```
/fm:orchestrate 003-01,003-02,003-03 --model codex
```

**Run pending prompts only:**
```
/fm:orchestrate prompts/phase-completion/000-orchestrator.md --pending-only
```

**Run in background with worktrees:**
```
/fm:orchestrate 003-01,003-02 --model codex --background --worktree
```

## Error Handling

<error_orchestrator_not_found>
If orchestrator.py not found:
```
Orchestrator script not found.

Expected: {expected_path}

Ensure founder-mode is properly installed.
```
</error_orchestrator_not_found>

<error_parse_failed>
If parsing fails:
```
Failed to parse input: {error}

For orchestrator files, ensure:
- File has "## Dependency Graph" section
- Prompt IDs follow NNN-NN pattern
- Execution order is defined

For prompt lists:
- Use comma-separated IDs: 003-01,003-02,003-03
- IDs must match files in ./prompts/
```
</error_parse_failed>

<error_circular_deps>
If circular dependency detected:
```
Circular dependency detected.

Cannot resolve execution order for: {prompt IDs}

Check dependency graph in orchestrator file.
```
</error_circular_deps>
