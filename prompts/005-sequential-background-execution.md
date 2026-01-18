# Sequential Background Execution Mode

## Objective

Enhance the orchestrate command's `--background` mode to support sequential wave execution with per-prompt monitoring and automatic wave chaining.

## Problem Statement

Currently the orchestrate command has two modes:
1. **Foreground**: Tasks run synchronously via Task subagents. Blocking, no progress visibility during execution.
2. **Background parallel**: All prompts in a wave spawn simultaneously with monitors, but the orchestrator itself blocks waiting for completion.

**Missing capability**: When running non-Claude models sequentially (single-prompt waves or due to dependencies), each prompt should:
1. Start in background (non-blocking spawn)
2. Have a monitor for live progress visibility
3. Be polled for completion via result file
4. Auto-chain to next wave on completion

## Context Files to Read

```
commands/orchestrate.md        # Current orchestrate implementation
scripts/executor.py            # Non-Claude model execution
agents/readonly-log-watcher.md # Log monitoring agent
references/state-utilities.md  # State management patterns
```

## Deliverables

### 1. Update orchestrate.md

Modify wave execution behavior for `--background` mode:

```markdown
**4d. Wait for wave completion (revised):**

If background execution:
- Do NOT block on Task agent completion
- Instead, poll result files at regular intervals
- Report progress to user during polling

Polling loop:
```bash
while not all_complete:
    for prompt_id in wave:
        result_file=".founder-mode/logs/${prompt_id}-result.json"
        if [ -f "$result_file" ]; then
            status=$(jq -r '.status' "$result_file")
            if [ "$status" = "success" ] || [ "$status" = "failed" ]; then
                mark_prompt_complete(prompt_id, status)
            fi
        fi
    done

    # Report current status
    show_wave_progress(wave, completed, pending)

    # Wait before next poll
    sleep 10
done
```

This allows the orchestrator to:
- Show live progress updates
- Detect completion from any prompt
- Chain to next wave without blocking
```

### 2. Add Progress Reporting

During polling, report status like:

```
Wave 2 Progress
===============
[✓] 004-01: SUCCESS - Created GitHub integration files
[⏳] 004-02: IN PROGRESS - Running (2m 30s)
[⏸] 004-03: PENDING - Waiting for 004-02

Polling in 10s...
```

### 3. Update Monitor Integration

When spawning monitors for background execution, include:
- Prompt ID for correlation
- Expected result file path
- Timeout handling

```markdown
Task(
  subagent_type: "founder-mode:readonly-log-watcher",
  run_in_background: true,
  model: "haiku",
  prompt: """
Monitor prompt {prompt_id}.
Log file: {log_file}
Result file: .founder-mode/logs/{prompt_id}-result.json
Timeout: {timeout} minutes

Report status changes. Signal completion when result file appears.
"""
)
```

## Instructions

### Step 1: Read Current Implementation

Study orchestrate.md steps 4a-4f to understand current wave execution.

### Step 2: Modify Polling Logic

Replace blocking Task agent wait with result file polling:
- Add polling interval configuration (default 10s)
- Add timeout handling (default 30min per prompt)
- Add progress reporting during polling

### Step 3: Update Monitor Spawning

Ensure monitors are spawned with:
- Correlation to specific prompt
- Knowledge of result file location
- Proper timeout handling

### Step 4: Test Wave Chaining

Verify that:
- Wave N completes via result file detection
- Wave N+1 starts automatically
- Progress is reported throughout

## Verification

- [ ] `--background` mode spawns prompts without blocking
- [ ] Result files are polled for completion
- [ ] Progress is reported during polling
- [ ] Waves chain automatically on completion
- [ ] Timeouts are handled gracefully
- [ ] Monitors correlate with specific prompts

## Rollback

```bash
git checkout -- commands/orchestrate.md
```
