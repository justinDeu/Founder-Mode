# Fix OpenCode Log Integration

## Objective

Fix log integration for non-Claude models (specifically OpenCode) that write to internal logs instead of stdout. The current `| tee logfile` pattern breaks because OpenCode writes to `~/.local/share/opencode/log/` instead of stdout, making founder-mode log files empty and progress monitoring impossible.

## Context

@scripts/executor.py - Executes non-Claude CLIs, writes stdout to log file
@agents/readonly-log-watcher.md - Polls log files for progress monitoring

OpenCode writes logs to: `~/.local/share/opencode/log/{timestamp}.log`

The executor directs stdout to the log file, but OpenCode produces minimal stdout output. Its actual execution logs go to its internal location.

## Requirements

1. Detect when OpenCode is the model and identify its log location
2. Either:
   - Stream OpenCode's internal logs to the founder-mode log file
   - OR have the log watcher know to read from OpenCode's location
   - OR find a way to get OpenCode to write to stdout
3. Maintain backward compatibility with models that do write to stdout (codex, gemini, zai)
4. Background mode must work correctly

## Research First

Before implementing, thoroughly research OpenCode's logging capabilities:

### 1. Check OpenCode Documentation

- Fetch https://opencode.ai/docs and look for logging/output configuration
- Search for CLI flags related to output, logging, verbosity
- Look for configuration file options (~/.config/opencode or similar)

### 2. Check OpenCode Source Code

OpenCode is open source. Search the repository for:
- Logging implementation (where does it write logs?)
- CLI argument parsing (any --log, --output, --verbose flags?)
- Configuration options for log destination
- Any hooks or events that could be tapped

```bash
# Clone and search
gh repo clone anomalyco/opencode /tmp/opencode-src
grep -r "log" /tmp/opencode-src/cmd --include="*.go"
grep -r "stdout" /tmp/opencode-src --include="*.go"
```

### 3. Answer These Questions

1. Does OpenCode have a flag to write logs to stdout or a custom location?
   - Check `opencode --help` and `opencode run --help`
   - Check source code for hidden/undocumented flags
2. What is the OpenCode log file naming pattern?
   - Current observation: `~/.local/share/opencode/log/{timestamp}.log`
   - Confirm in source: how is timestamp generated? Is there a session ID?
3. Is there a way to correlate an OpenCode process to its log file?
   - By PID, timestamp, session ID, or other identifier?
4. Does OpenCode support any output hooks or streaming mechanisms?
   - WebSocket, SSE, or other real-time output options?

## Implementation Options

### Option A: Tail OpenCode Logs

Modify executor.py to spawn a background tail process that streams OpenCode's logs to the founder-mode log file:

```python
if model.startswith("opencode"):
    # Find latest log or watch for new one
    # Tail -f that log to our log file
```

Pros: Works without OpenCode changes
Cons: Race condition finding correct log file

### Option B: Model-Specific Log Paths

Add log path awareness to executor.py model config:

```python
MODEL_CONFIG = {
    "opencode": {
        "command": ["opencode", "run"],
        "stdin_mode": "positional",
        "native_log_dir": "~/.local/share/opencode/log/",
    },
}
```

Then update readonly-log-watcher.md to check native_log_dir when specified.

Pros: Clean separation
Cons: Requires watcher to know about model configs

### Option C: Post-Execution Log Copy

After OpenCode completes, copy its log to the founder-mode log:

```python
if model.startswith("opencode"):
    latest_log = find_latest_opencode_log()
    append_to_log(latest_log, log_path)
```

Pros: Simple
Cons: No live progress monitoring

### Option D: OpenCode Stdout Flag

If OpenCode supports `--log-to-stdout` or similar, use it:

```python
"opencode": {
    "command": ["opencode", "--log-to-stdout", "run"],
}
```

Pros: Cleanest solution
Cons: Depends on OpenCode supporting this

## Recommended Approach

Start with Option D (check for stdout flag). If unavailable, implement Option A (tail integration) for live monitoring with Option C as fallback for completion logs.

## Deliverables

1. Update `scripts/executor.py`:
   - Add OpenCode log detection/streaming logic
   - Handle both foreground and background execution modes
   - Add model config for native log locations if needed

2. Update `agents/readonly-log-watcher.md`:
   - Add awareness of alternative log locations
   - Include OpenCode's native log path in monitoring

3. Document the solution in code comments

## Verification

Run these tests:

```bash
# Test OpenCode foreground - check log has content
/founder-mode:run-prompt test-prompt.md --model opencode
cat .founder-mode/logs/*.log | head -50

# Test OpenCode background - verify log monitoring works
/founder-mode:run-prompt test-prompt.md --model opencode --background
tail -f .founder-mode/logs/*.log

# Test other models still work
/founder-mode:run-prompt test-prompt.md --model codex
```

Success criteria:
- [ ] OpenCode execution produces readable log content
- [ ] Background mode shows live progress
- [ ] Log watcher can detect completion/errors
- [ ] Codex, gemini, zai models unaffected
- [ ] No race conditions in log file detection

## Rollback

```bash
git checkout -- scripts/executor.py agents/readonly-log-watcher.md
```
