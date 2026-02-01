---
name: fm:orchestrate
description: Execute workflow configs with strict adherence to defined plans
argument-hint: <workflow.yaml> <workflow-id> [--model ?|claude|codex|...] [--background]
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Task
  - AskUserQuestion
---

# Orchestrate

Execute workflow configs with STRICT adherence to the defined plan.

## CRITICAL: EXECUTION RULES

<strict_execution_rules>
**THE PLAN IS LAW. THERE ARE NO EXCEPTIONS.**

1. **ZERO DEVIATION**: Execute prompts EXACTLY as defined in the YAML.
   - Do not skip prompts
   - Do not reorder prompts
   - Do not add prompts
   - Do not modify prompt parameters

2. **FAIL FAST**: If ANY step fails, STOP the workflow IMMEDIATELY.
   - Do not attempt to recover
   - Do not continue with other prompts
   - Do not try alternative approaches
   - Report failure and halt

3. **NO IMPROVISATION**: The orchestrator does not make decisions.
   - Prompts make decisions
   - Orchestrator only coordinates
   - If unclear, STOP and ask user

4. **ATOMIC WORKFLOWS**: A workflow either completes fully or fails entirely.
   - Partial completion is failure
   - All-or-nothing execution
</strict_execution_rules>

## Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `<workflow.yaml>` | positional | required | Path to YAML workflow config |
| `<workflow-id>` | positional | required | Which workflow to execute from config |
| `--model` | option | `?` | Default model. Use `?` for per-prompt selection. |
| `--background` | flag | false | Run non-Claude models in background |

## Execution Flow

### Step 1: Validate Config

<validate_config>
```bash
# Locate orchestrator.py
PLUGIN_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$PLUGIN_ROOT" ]; then
    PLUGIN_ROOT=$(git rev-parse --git-common-dir 2>/dev/null | sed 's|/\.bare$||; s|/\.git$||')
fi
ORCHESTRATOR="$PLUGIN_ROOT/scripts/orchestrator.py"

# Validate config
python3 "$ORCHESTRATOR" {workflow.yaml}
```

If exit code != 0: STOP. Display errors. Do not proceed.
</validate_config>

### Step 2: Load YAML and Select Workflow

<load_workflow>
```yaml
# Read the YAML file directly
import yaml

with open("{workflow.yaml}") as f:
    config = yaml.safe_load(f)

workflow = config["workflows"]["{workflow-id}"]

# Extract workflow details
base = workflow["base"]           # git branch to start from
branch = workflow["branch"]       # working branch name
on_complete = workflow.get("on_complete", {})
prompts = workflow["prompts"]
```
</load_workflow>

### Step 3: Compute Waves via Topological Sort

<compute_waves>
Waves are computed by analyzing the `after` dependencies:

```
Wave 1: All prompts with no 'after' dependencies (entry points)
Wave N: All prompts whose 'after' deps are satisfied by waves 1..N-1
Final wave: Contains the sink prompt
```

Algorithm:
```
prompts_without_deps = [p for p in prompts if not prompts[p].get('after')]
waves = [prompts_without_deps]

remaining = set(prompts) - set(prompts_without_deps)
completed = set(prompts_without_deps)

while remaining:
    ready = [p for p in remaining if all(d in completed for d in prompts[p].get('after', []))]
    if not ready:
        raise ValueError("Cannot resolve waves")
    waves.append(ready)
    completed.update(ready)
    remaining -= set(ready)
```

Example output:
```
Wave 1: [setup, db-schema]
Wave 2: [backend-auth]
Wave 3: [frontend-auth]
Wave 4: [auth-tests] (sink)
```
</compute_waves>

### Step 4: Create Base Worktree

<create_base_worktree>
```bash
# Compute worktree location
COMMON_DIR=$(git rev-parse --git-common-dir | sed 's|/\.git$||')
WORKTREE_PATH="$COMMON_DIR/{branch}"

# Create worktree
git worktree add "$WORKTREE_PATH" -b {branch} {base}
```

If fails: STOP workflow. Report git error.
</create_base_worktree>

### Step 5: Execute Waves

<execute_waves>
For each wave in order:

**5a. Report wave start:**
```
═══════════════════════════════════════════════════════════════
WAVE {N}/{TOTAL} STARTING
Workflow: {workflow-id}
Branch: {branch}
Prompts: {prompt-ids}
Parallel: {yes/no}
═══════════════════════════════════════════════════════════════
```

**5b. If wave has multiple prompts (parallel execution):**

For each prompt in wave:
```bash
# Create temp worktree
git worktree add "$COMMON_DIR/{workflow-id}--{prompt-id}" {branch}
```

Spawn Task agents for ALL prompts in wave **simultaneously**:
```
# For each prompt in wave, spawn in parallel:
Task(
  subagent_type: "general-purpose",
  run_in_background: {--background flag},
  prompt: """
Execute prompt: {prompt-id} - {title}

Working directory: {worktree-path}/{workflow-id}--{prompt-id}
Model: {model from prompt or workflow default}

Read the prompt file at: {prompt.path}
Execute completely.

Working in isolated worktree. Do NOT modify other worktrees.

On completion, write result to .founder-mode/logs/{prompt-id}-result.json:
{
  "prompt_id": "{prompt-id}",
  "status": "success|failed",
  "summary": "what was accomplished",
  "files_changed": ["list", "of", "files"],
  "errors": []
}
"""
)
```

**5c. If wave has single prompt:**

Execute directly in base worktree:
```
Task(
  subagent_type: "general-purpose",
  run_in_background: {--background flag},
  prompt: """
Execute prompt: {prompt-id} - {title}

Working directory: {worktree-path}
Model: {model from prompt or workflow default}

Read the prompt file at: {prompt.path}
Execute completely.

On completion, write result to .founder-mode/logs/{prompt-id}-result.json:
{
  "prompt_id": "{prompt-id}",
  "status": "success|failed",
  "summary": "what was accomplished",
  "files_changed": ["list", "of", "files"],
  "errors": []
}
"""
)
```

**5d. Monitor execution:**

While prompts are running, report status every 30 seconds:
```
[{timestamp}] MONITOR: {workflow-id}
  Wave: {N}/{total}
  Active: {prompt-ids currently running}
  Complete: {prompt-ids finished this wave}
  Elapsed: {time since wave start}
```

On prompt completion:
```
[{timestamp}] PROMPT COMPLETE: {prompt-id}
  Duration: {time}
  Files changed: {count}
  Status: SUCCESS
```

On prompt failure:
```
[{timestamp}] PROMPT FAILED: {prompt-id}
  Duration: {time}
  Error: {error message}

  !!! WORKFLOW HALTED !!!
```

**5e. Check results:**

If ALL prompts succeed: proceed to merge step.

If ANY prompt fails:
```
═══════════════════════════════════════════════════════════════
WORKFLOW FAILED
═══════════════════════════════════════════════════════════════
Workflow: {workflow-id}
Branch: {branch}
Failed at: Wave {N}, Prompt {prompt-id}
Error: {error message from result.json}

Temp worktrees preserved for debugging:
  - {workflow-id}--{prompt-id}
  - {workflow-id}--{other-prompts}

STOPPING. No further prompts will execute.
═══════════════════════════════════════════════════════════════
```

STOP IMMEDIATELY. Do not continue. Preserve state.
</execute_waves>

### Step 6: Merge Parallel Work

<merge_parallel_work>
After parallel wave completes successfully:

**6a. For each temp worktree in the wave:**

```bash
cd "$WORKTREE_PATH"  # Base worktree
git merge {workflow-id}--{prompt-id} --no-edit
```

**6b. If merge conflict occurs:**

STOP execution. Report conflict:
```
═══════════════════════════════════════════════════════════════
MERGE CONFLICT
═══════════════════════════════════════════════════════════════
Wave {N} has merge conflicts:
  - {workflow-id}--{prompt-a}: conflicts with {workflow-id}--{prompt-b}
  - Files: {list of conflicting files}

Temp worktrees preserved for manual resolution.
═══════════════════════════════════════════════════════════════
```

Use AskUserQuestion:
```
Question: "How should merge conflicts be resolved?"
Options:
- "Resolve manually" - Preserve worktrees, exit for manual resolution
- "Attempt auto-resolve" - Claude analyzes and resolves conflicts
- "Abort workflow" - Cleanup and exit
```

If user chooses auto-resolve:
1. Read conflicting files from both worktrees
2. Understand intent from BOTH prompts
3. Resolve conflicts by merging changes intelligently
4. Test the resolution if possible
5. Commit with message: "merge: resolve conflict between {prompt-a} and {prompt-b}"
6. If auto-resolve fails: STOP, preserve state for manual intervention

**6c. After successful merge:**

Delete temp worktree:
```bash
git worktree remove "$COMMON_DIR/{workflow-id}--{prompt-id}"
```

**6d. Proceed to next wave ONLY if ALL merges succeeded**
</merge_parallel_work>

### Step 7: Sink Reached - On Complete

<on_complete>
When sink prompt completes successfully:

**7a. Report completion:**
```
═══════════════════════════════════════════════════════════════
WORKFLOW COMPLETE
═══════════════════════════════════════════════════════════════
Workflow: {workflow-id}
Branch: {branch}
Prompts executed: {count}
Waves: {total}
═══════════════════════════════════════════════════════════════
```

**7b. Execute on_complete actions:**

If `create_pr: true`:
```bash
git push -u origin {branch}
gh pr create \
  --title "{workflow-id}" \
  --body "Workflow execution complete

Prompts: {list}
Branch: {branch}
"
```

If `merge_to: {branch}`:
```bash
git checkout {merge_to}
git merge {branch} --no-edit
```

If `delete_worktree: true`:
```bash
git worktree remove "$WORKTREE_PATH"
```

**7c. Report final status:**
```
Final status: SUCCESS
{if PR created}PR: {pr_url}{/if}
{if merged}Merged to: {branch}{/if}
```
</on_complete>

## Backward Compatibility: Comma-Separated Mode

<comma_mode>
For simple parallel execution without workflow config:

```
/fm:orchestrate prompts/001.md,prompts/002.md,prompts/003.md
```

This mode:
- No validation needed
- All prompts run in parallel (single wave)
- Each gets auto-generated worktree named after prompt filename
- No merging (independent work)
- No on_complete actions
</comma_mode>

## Examples

**Execute workflow with YAML config:**
```
/fm:orchestrate workflows/auth-feature.yaml auth-feature
```

**Execute with per-prompt model selection:**
```
/fm:orchestrate workflows/auth-feature.yaml auth-feature --model ?
```

**Execute in background:**
```
/fm:orchestrate workflows/auth-feature.yaml auth-feature --background
```

**Simple parallel execution (no config):**
```
/fm:orchestrate prompts/001.md,prompts/002.md,prompts/003.md --model codex
```

## Error Handling

<error_handling>
**All errors halt the workflow. No exceptions.**

| Error | Action |
|-------|--------|
| Config validation fails | Do not start. Show errors. |
| Worktree creation fails | Stop. Report git error. |
| Prompt execution fails | Stop. Preserve state. Report. |
| Merge conflict | Stop. Ask user for resolution strategy. |
| Merge fails | Stop. Preserve worktrees. |
| Git push fails | Stop. Branch preserved locally. |
| PR creation fails | Warn but workflow considered complete (code exists). |

On any error, preserve state for debugging:
- Keep temp worktrees
- Keep partial branches
- Log all output to .founder-mode/logs/
</error_handling>

## Monitoring

<monitoring>
The orchestrator MUST maintain visibility throughout execution:

**Continuous status (every 30 seconds during prompt execution):**
```
[{timestamp}] MONITOR: {workflow-id}
  Wave: {current-wave}/{total-waves}
  Active: {prompt-ids currently running}
  Complete: {prompt-ids finished this wave}
  Elapsed: {time since wave start}
```

**On prompt completion:**
```
[{timestamp}] PROMPT COMPLETE: {prompt-id}
  Duration: {time}
  Files changed: {count}
  Status: SUCCESS
```

**On prompt failure:**
```
[{timestamp}] PROMPT FAILED: {prompt-id}
  Duration: {time}
  Error: {error message}

  !!! WORKFLOW HALTED !!!
```
</monitoring>
