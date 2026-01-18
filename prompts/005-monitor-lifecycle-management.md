# 005: Monitor Lifecycle Management

<objective>
Add lifecycle management for background monitoring agents to prevent stale monitors from running when orchestration is restarted.

When orchestration fails and the user restarts with a different strategy, old monitoring agents continue watching dead processes. They eventually timeout with stale failure reports while new execution succeeds. This creates noise and confusion.

The goal: monitors check for cancellation signals and exit cleanly when their orchestration run is superseded.
</objective>

<context>
@commands/orchestrate.md - Spawns readonly-log-watcher agents in step 4c
@agents/readonly-log-watcher.md - Monitors log files, polls every 15-30 seconds
@references/state-utilities.md - Patterns for atomic state updates and file locking

Current flow:
1. Orchestrator spawns background execution for prompt (e.g., codex)
2. Orchestrator spawns readonly-log-watcher to monitor that execution
3. If orchestration fails and user restarts, old watchers keep running
4. Old watchers eventually timeout and report stale failures

Log files live in: `.founder-mode/logs/`
</context>

<requirements>
1. **Orchestration Run ID**: Generate a unique run ID when orchestration starts
2. **Run State File**: Create `.founder-mode/logs/orchestration-run.json` with current run ID
3. **Monitor Registration**: When spawning monitors, pass the run ID they belong to
4. **Cancellation Check**: Monitors check if their run ID matches current before each poll
5. **Clean Exit**: Monitors exit with "CANCELLED - orchestration restarted" status when superseded
</requirements>

<implementation>
**In orchestrate.md:**

After Step 1 (Parse Input), add run ID generation:
```bash
RUN_ID=$(date +%Y%m%d-%H%M%S)-$$
echo '{"run_id": "'$RUN_ID'", "started": "'$(date -Iseconds)'"}' > .founder-mode/logs/orchestration-run.json
```

In Step 4c (spawn monitors), pass run ID to watcher:
```
Task(
  ...
  prompt: """
  ...
  Run ID: {RUN_ID}
  ...
  """
)
```

**In readonly-log-watcher.md:**

Add cancellation check to monitoring workflow:

Before each poll cycle:
1. Read `.founder-mode/logs/orchestration-run.json`
2. Compare `run_id` to the run ID passed at spawn time
3. If mismatch: exit with status CANCELLED

Add a new section "## Cancellation Detection" documenting this behavior.

**State File Format:**
```json
{
  "run_id": "20260118-173000-12345",
  "started": "2026-01-18T17:30:00+00:00",
  "prompts": ["003-01", "003-02"],
  "monitors": [
    {"prompt_id": "003-01", "log_file": "codex-003-01-xxx.log"},
    {"prompt_id": "003-02", "log_file": "codex-003-02-xxx.log"}
  ]
}
```
</implementation>

<output>
Modify:
- ./commands/orchestrate.md - Add run ID generation, state file creation, pass run ID to monitors
- ./agents/readonly-log-watcher.md - Add cancellation detection before each poll

Create:
- None (state file created at runtime)
</output>

<verification>
Before declaring complete:
- [ ] orchestrate.md generates unique run ID at start
- [ ] orchestrate.md creates/overwrites orchestration-run.json
- [ ] orchestrate.md passes run ID when spawning monitors
- [ ] readonly-log-watcher.md reads orchestration-run.json before each poll
- [ ] readonly-log-watcher.md exits with CANCELLED status when run ID mismatches
- [ ] Both files remain valid markdown with proper structure
</verification>
