---
name: fm:orchestrate
description: Execute multiple prompts with dependency management and parallel execution
argument-hint: <workflow.xml|prompt-list> [--model ?|claude|codex|...] [--pending-only]
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
| `<input>` | positional | required | XML workflow file OR comma-separated prompt paths |
| `--model` | option | `?` | Default model. Use `?` for per-prompt selection. |
| `--pending-only` | flag | false | Skip prompts marked complete in log files |
| `--worktree` | flag | false | Create isolated worktree per prompt |
| `--background` | flag | false | Run non-Claude models in background |

## Execution Flow

### Step 1: Parse Input

Determine input type and extract execution plan.

<detect_input_type>
Check the input argument:
- If it ends with `.xml` and the file exists: treat as XML workflow file (go to Step 1a)
- If it contains commas or ends with `.md`: treat as comma-separated prompt list (go to Step 1b)
- Otherwise: report error and exit
</detect_input_type>

#### Step 1a: Parse XML Workflow

<parse_xml_workflow>
Read the XML workflow file using the Read tool. Claude reads XML natively with no parser needed.

Extract the following from the XML:

1. **Workflow metadata** from `<workflow>` attributes:
   - `id` - workflow identifier
   - `base` - base branch
   - `branch` - target branch

2. **Completion actions** from `<on_complete>` attributes:
   - `create_pr` or `merge_to` (mutually exclusive)
   - `delete_worktree`

3. **Prompt list** from each `<prompt>` element:
   - `id` attribute - prompt identifier
   - `<path>` child - file path to prompt
   - `<after>` children - dependency IDs (zero or more)
   - `<model>` child - model override (optional)

If the file contains multiple `<workflow>` elements, the second positional argument selects which one. If there is only one workflow, no selection is needed.
</parse_xml_workflow>

#### Step 1b: Parse Comma-Separated Prompt List

<parse_prompt_list>
Split input on commas. Each entry is a path to a prompt .md file.

All prompts run in a single wave with no dependencies between them.

Build the execution plan:
- One wave containing all prompts
- No dependency edges
- No workflow metadata (ad-hoc execution)
</parse_prompt_list>

### Step 2: Validate the DAG

<validate_dag>
Before executing, validate the dependency graph:

1. **Unique IDs**: Every `<prompt>` must have a unique `id`. If duplicates exist, report them and exit.

2. **Valid references**: Every `<after>` value must match the `id` of another prompt in the workflow. Report any dangling references.

3. **Files exist**: Every `<path>` must point to an existing file. Check each with:
   ```bash
   test -f "{path}"
   ```
   Report any missing files.

4. **No cycles**: Perform a topological sort. If it fails, a cycle exists. Report the involved prompt IDs and exit.

5. **Single sink**: Identify prompts that no other prompt lists in an `<after>`. There must be exactly one. If zero or more than one, report the issue and exit.

6. **All paths reach sink**: Starting from the sink, walk backward through dependencies. Every prompt must be reachable. Report any unreachable prompts.

If validation fails, display all errors and exit without executing.
</validate_dag>

### Step 3: Compute Waves

<compute_waves>
Group prompts into execution waves using topological layering:

- **Wave 1**: All prompts with zero `<after>` dependencies (source nodes)
- **Wave N**: All prompts whose every dependency appears in waves 1 through N-1

Store the wave assignments for display and execution.
</compute_waves>

### Step 4: Display Execution Plan and Confirm

Show the user what will be executed:

```
Execution Plan
==============

Workflow: {id} (or "Ad-hoc list" for comma-separated input)
Base branch: {base}
Target branch: {branch}
Total prompts: {count}
Waves: {wave count}

Wave 1:
  - {id}: {path}
  - {id}: {path}

Wave 2:
  - {id}: {path} (after: {dep1}, {dep2})

On complete: {create_pr / merge_to / none}
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
- Different workflow file

If user selects "Cancel", exit with:
```
Orchestration cancelled.
```
</confirm_plan>

### Step 5: Model Selection

<model_selection_per_prompt>
If `--model ?` or no model specified, prompt for each prompt's model.

For each prompt, check if it has a `<model>` override in the XML. If so, use it. Otherwise, use AskUserQuestion:

Question: "Select model for {prompt_id}: {path}"
Options:
- `claude` - Claude in Task subagent
- `codex` - OpenAI Codex (gpt-5.2-codex)
- `gemini` - Gemini 3 Flash
- `codex-high` - Codex with high reasoning
- `opencode-zai` - OpenCode with Z.AI

Store selections in a mapping: `{prompt_id: model}`
</model_selection_per_prompt>

<model_selection_batch>
If `--model MODEL` specified, use that model for all prompts unless a prompt has a `<model>` override in the XML. XML-level overrides take precedence.

Store: `{prompt_id: MODEL}` for all prompts.
</model_selection_batch>

### Step 6: Execute Waves

For each wave in order:

<execute_wave>
**6a. Report wave start:**
```
Wave {N} Starting
=================
Prompts: {list of prompt IDs in this wave}
```

**6b. Spawn Task agents for all prompts in wave (PARALLEL):**

Route through run-prompt when `--worktree` is specified (ensures worktree creation for all models).
For Claude models without `--worktree`, spawn directly as Task subagents.
For non-Claude models, always spawn Tasks that call run-prompt.

CRITICAL: Spawn ALL tasks for the wave in a SINGLE message with multiple Task tool calls.

<spawn_with_worktree>
**If `--worktree` flag is set (any model):**

All prompts route through run-prompt to leverage its worktree creation logic:

```
# For each prompt in wave, spawn in parallel:
Task(
  subagent_type: "general-purpose",
  run_in_background: true,  # if --background
  prompt: """
Execute prompt via run-prompt: {prompt_id} - {path}

Call:
/fm:run-prompt {prompt_path} --model {model} --worktree {--background}

Write results to .founder-mode/logs/{prompt_id}-result.json:
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
</spawn_with_worktree>

<spawn_without_worktree>
**If no `--worktree` flag:**

For Claude models, spawn directly as Task subagents.
For non-Claude models, spawn Tasks that call run-prompt.

```
# For each prompt in wave, spawn in parallel:
Task(
  subagent_type: "general-purpose",
  run_in_background: true,  # if --background
  prompt: """
Execute prompt: {prompt_id} - {path}

<task>
{Read prompt file content}
</task>

Working directory: {cwd}
Model: {selected_model}

If non-Claude model, call:
/fm:run-prompt {prompt_path} --model {model} {--background}

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
</spawn_without_worktree>

**6c. If --background with non-Claude, spawn monitors:**

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

**6d. Wait for wave completion:**

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

**6e. Report wave results:**
```
Wave {N} Complete
=================
| Prompt | Status | Summary |
|--------|--------|---------|
| {id} | SUCCESS | {summary from result file} |
| {id} | SUCCESS | {summary from result file} |

Proceeding to Wave {N+1}...
```

**6f. Handle failures:**

If any prompt in wave fails:
```
Wave {N} had failures:
- {id}: FAILED - {error summary}

Options:
1. Retry failed prompts
2. Skip and continue to next wave
3. Abort orchestration
```

Use AskUserQuestion to let user decide.
</execute_wave>

### Step 7: Process on_complete Actions

<on_complete_actions>
After all waves finish successfully, process the `<on_complete>` element:

**If `create_pr="true"`:**
Create a pull request from `branch` to `base` using gh CLI.

**If `merge_to` is set:**
Merge the working branch into the specified branch.

**If `delete_worktree="true"`:**
Remove the worktree after completion actions finish.

Skip on_complete processing if any prompts failed.
</on_complete_actions>

### Step 8: Final Report

After all waves complete:

```
Orchestration Complete
======================

Workflow: {id}
Total prompts: {N}
Successful: {N}
Failed: {N}
Skipped: {N}

Results by wave:
| Wave | Prompts | Status |
|------|---------|--------|
| 1 | {ids} | Complete |
| 2 | {ids} | Complete |

On complete: {action taken or "none"}

Logs: .founder-mode/logs/
```

## Examples

**Run XML workflow:**
```
/fm:orchestrate prompts/monitor/workflow.xml
```

**Run specific workflow from multi-workflow file:**
```
/fm:orchestrate prompts/workflows.xml direction-analyzer
```

**Run specific prompts (no deps, all parallel):**
```
/fm:orchestrate prompts/001-setup.md,prompts/002-core.md,prompts/003-tests.md --model codex
```

**Run with worktrees and background:**
```
/fm:orchestrate prompts/monitor/workflow.xml --model codex --background --worktree
```

## Error Handling

<error_file_not_found>
If workflow file not found:
```
Workflow file not found: {path}

Check that the file exists and is a valid .xml workflow file.
See references/workflow-xml-schema.md for the XML format.
```
</error_file_not_found>

<error_invalid_xml>
If XML is malformed or missing required elements:
```
Invalid workflow XML: {error}

Required structure:
  <workflow id="..." base="..." branch="...">
    <prompt id="...">
      <path>...</path>
    </prompt>
  </workflow>

See references/workflow-xml-schema.md for full schema.
```
</error_invalid_xml>

<error_dag_validation>
If DAG validation fails:
```
Workflow DAG validation failed:

{list of specific errors, e.g.:
- Prompt "foo" references unknown dependency "bar"
- Cycle detected: a -> b -> c -> a
- Multiple sink nodes: "x", "y" (expected exactly one)
- Prompt "z" is unreachable from any source
}

Fix the workflow XML and retry.
```
</error_dag_validation>

<error_circular_deps>
If circular dependency detected:
```
Circular dependency detected.

Cannot resolve execution order for: {prompt IDs}

Check <after> elements in the workflow XML.
```
</error_circular_deps>
