---
name: fm:orchestrate
description: Execute multiple prompts with dependency management and parallel execution
argument-hint: <workflow.xml|prompt-list> [workflow-id] [--model ?|claude|codex|agent-team|...] [--pending-only]
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Task
  - AskUserQuestion
  - TeamCreate
  - SendMessage
  - TaskCreate
  - TaskUpdate
  - TaskList
  - TaskGet
---

# Orchestrate

Execute multiple prompts respecting dependencies. Prompts within the same wave run in parallel.

## Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `<input>` | positional | required | XML workflow file OR comma-separated prompt paths |
| `[workflow-id]` | positional | (auto) | Selects which workflow to run when XML file contains multiple `<workflow>` elements. Optional if file has only one. |
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

### Step 3: Compute Execution Schedule

<compute_schedule>
Build a dependency-aware schedule. Waves are used for display and planning, but execution is dependency-triggered: a prompt starts as soon as all its dependencies complete, not when an entire wave finishes.

**Wave assignment (for display):**

- **Wave 1**: All prompts with zero `<after>` dependencies (source nodes)
- **Wave N**: All prompts whose every dependency appears in waves 1 through N-1

**Execution rule:**

A prompt becomes **ready** the moment every prompt in its `<after>` list has completed. Do not wait for an entire wave to finish before starting the next prompt. A single long-running task in wave 1 should not block wave 2 tasks that do not depend on it.

For agent-team mode this is critical: the team lead should continuously check for newly unblocked prompts and assign them to idle teammates rather than waiting for a full wave boundary.

Store the wave assignments for display and the raw dependency edges for execution.
</compute_schedule>

### Step 4: Display Execution Plan and Confirm

Show the user what will be executed:

```
Execution Plan
==============

Workflow: {id} (or "Ad-hoc list" for comma-separated input)
Base: {base} -> {branch}
Prompts: {count} across {wave count} waves
On complete: {create_pr / merge_to / none}

| Wave | ID | Prompt | Dependencies | Model |
|------|----|--------|--------------|-------|
| 1 | {id} | {path} | - | claude |
| 1 | {id} | {path} | - | claude |
| 2 | {id} | {path} | {dep1} | codex |
| 2 | {id} | {path} | {dep1}, {dep2} | claude |
| 3* | {id} | {path} | {dep1}, {dep2} | claude |

* = sink node
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

<model_selection_mode>
First determine the execution mode. If `--model ?` or no model specified, ask:

Question: "How should this workflow execute?"
Options:
- `agent-team` - Spawn a Claude Code agent team with shared task list and worktree-per-agent. Team lead coordinates, teammates pick up tasks as dependencies clear. Best for complex workflows.
- `claude` - Claude Task subagents (one per prompt, parallel within waves)
- `codex` - OpenAI Codex via codex CLI
- `gemini` - Gemini 3 Flash via gemini CLI

If `agent-team` is selected, skip per-prompt model selection. The team lead assigns work to teammates who each get their own worktree. Per-prompt `<model>` overrides in the XML are ignored in this mode.
</model_selection_mode>

<model_selection_per_prompt>
For non-agent-team modes with `--model ?`: prompt for each prompt's model.

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
If `--model MODEL` specified (not `?`), use that model for all prompts unless a prompt has a `<model>` override in the XML. XML-level overrides take precedence.

If `--model agent-team`, go directly to agent-team execution (Step 6, agent-team path).

Store: `{prompt_id: MODEL}` for all prompts.
</model_selection_batch>

### Step 6: Execute Prompts

Execution depends on the selected mode: **agent-team** or **task-based** (claude, codex, gemini, etc.).

<execute_agent_team>
#### 6A: Agent-Team Execution

Use Claude Code's TeamCreate to spawn a coordinated team. The team lead (you) manages the task list and assigns work as dependencies clear. Each teammate gets its own worktree automatically.

**6A-1. Create the team:**

```
TeamCreate(
  team_name: "orchestrate-{workflow_id}",
  description: "Executing workflow: {workflow_id}"
)
```

**6A-2. Create tasks from prompts:**

For each prompt in the workflow, create a task. Include dependency info so the team lead knows when to assign:

```
TaskCreate(
  title: "[{prompt_id}] {path}",
  description: """
Prompt: {prompt_id}
Path: {path}
Dependencies: {comma-separated after IDs, or "none"}
Wave: {wave_number}

Execute the prompt file at {path} completely.
""",
  team_name: "orchestrate-{workflow_id}"
)
```

**6A-3. Spawn teammates:**

Spawn teammates for the initial wave of ready prompts (those with no dependencies). Use the Agent tool with `team_name` and `name` parameters. Each teammate gets `isolation: "worktree"`.

```
# For each ready prompt, spawn a teammate:
Agent(
  subagent_type: "general-purpose",
  team_name: "orchestrate-{workflow_id}",
  name: "{prompt_id}",
  isolation: "worktree",
  prompt: """
You are a teammate executing prompt [{prompt_id}].

Read and execute the prompt at: {path}

When done, mark your task complete via TaskUpdate and send a message
to the team lead summarizing what you accomplished.
"""
)
```

**6A-4. Continuous scheduling:**

As teammates complete and go idle, check which prompts are now unblocked (all `<after>` dependencies completed). Assign newly ready prompts immediately. Do not wait for an entire wave to finish.

Loop:
1. Receive teammate completion message
2. Mark their task done
3. Check all remaining prompts: are any newly unblocked?
4. For each newly ready prompt, either assign to an idle teammate or spawn a new one
5. Repeat until all prompts are complete or a failure requires user input

**6A-5. Handle failures:**

If a teammate reports failure, use AskUserQuestion:
- Retry the failed prompt with a new teammate
- Skip it and continue (mark dependents as blocked)
- Abort the workflow

**6A-6. Shutdown:**

When all prompts are complete, send shutdown messages to all teammates:

```
SendMessage(
  to: "{teammate_name}",
  message: { type: "shutdown_request" }
)
```
</execute_agent_team>

<execute_task_based>
#### 6B: Task-Based Execution (claude, codex, gemini, etc.)

Spawn Task subagents per prompt. Uses dependency-triggered scheduling: start each prompt as soon as its dependencies complete, not when an entire wave finishes.

**6B-1. Start all ready prompts:**

Identify every prompt with zero unmet dependencies. Spawn all of them in a SINGLE message with multiple Task tool calls.

Route through run-prompt when `--worktree` is specified or when using non-Claude models:

```
# For each ready prompt, spawn in parallel:
Task(
  subagent_type: "general-purpose",
  run_in_background: true,
  prompt: """
Execute prompt: {prompt_id} - {path}

Call:
/fm:run-prompt {prompt_path} --model {model} {--worktree} {--background}

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

For Claude models without `--worktree`, spawn directly with the prompt content inlined instead of calling run-prompt.

**6B-2. Monitor and schedule:**

As tasks complete, check which prompts are now unblocked. Spawn newly ready prompts immediately in the next message. Do not wait for all running tasks to finish.

Track completion via result files:
```bash
test -f ".founder-mode/logs/${prompt_id}-result.json"
```

**6B-3. If --background with non-Claude, spawn monitors:**

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

**6B-4. Report progress:**

After each batch of completions:
```
Progress: {completed}/{total} prompts
  [{id}] DONE - {summary}
  [{id}] DONE - {summary}
  [{id}] RUNNING...
  [{id}] READY (deps met, starting now)
  [{id}] BLOCKED (waiting on: {dep1}, {dep2})
```

**6B-5. Handle failures:**

If any prompt fails:
```
[{id}] FAILED - {error summary}

Blocked by this failure: {list of downstream prompt IDs}
```

Use AskUserQuestion:
- Retry the failed prompt
- Skip and unblock dependents
- Abort orchestration
</execute_task_based>

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

**Run XML workflow (interactive model selection):**
```
/fm:orchestrate prompts/monitor/workflow.xml
```

**Run specific workflow from multi-workflow file:**
```
/fm:orchestrate prompts/workflows.xml direction-analyzer
```

**Run with agent team (coordinated parallel agents with worktrees):**
```
/fm:orchestrate prompts/monitor/workflow.xml --model agent-team
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
