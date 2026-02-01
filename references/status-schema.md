# Status Schema

Schema and utilities for parallel execution status tracking.

## Directory Structure

```
.founder-mode/status/
  sessions/
    {session-id}/
      status.json       # Aggregate status for the session
      001.log           # Agent 1 output
      002.log           # Agent 2 output
      ...
  active-session        # Symlink to current session directory
```

Session IDs use format: `{YYYYMMDD-HHMMSS}-{short-uuid}`

Example: `20260201-143022-abc12345`

## Status Schema

### status.json

```json
{
  "schema_version": "1.0",
  "session_id": "20260201-143022-abc12345",
  "source": "orchestrate",
  "source_file": "prompts/monitor/000-orchestrator.md",
  "started_at": "2026-02-01T14:30:22Z",
  "completed_at": null,
  "status": "running",
  "agents": [...],
  "summary": {...},
  "waves": [...]
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Schema version for compatibility |
| `session_id` | string | Unique session identifier |
| `source` | string | One of: `orchestrate`, `execute-phase`, `run-prompt` |
| `source_file` | string | Path to orchestrator or prompt file |
| `started_at` | string | ISO8601 timestamp |
| `completed_at` | string/null | ISO8601 timestamp or null if running |
| `status` | string | Session status (see transitions below) |
| `agents` | array | List of agent status objects |
| `summary` | object | Aggregated counts |
| `waves` | array | Wave status objects |

### Agent Object

```json
{
  "id": "001",
  "name": "001-status-file-schema",
  "prompt_path": "prompts/monitor/001-status-file-schema.md",
  "status": "running",
  "wave": 1,
  "started_at": "2026-02-01T14:30:25Z",
  "completed_at": null,
  "duration_seconds": null,
  "exit_code": null,
  "pid": 12345,
  "log_file": ".founder-mode/status/sessions/20260201-143022-abc12345/001.log",
  "model": "claude",
  "error": null
}
```

### Summary Object

```json
{
  "total": 5,
  "queued": 2,
  "running": 2,
  "complete": 1,
  "failed": 0,
  "cancelled": 0
}
```

### Wave Object

```json
{
  "wave": 1,
  "status": "running",
  "agents": ["001", "003", "005"]
}
```

## Status Transitions

### Agent Status

```
queued -> running -> complete
queued -> running -> failed
queued -> cancelled
running -> cancelled
```

Valid statuses: `queued`, `running`, `complete`, `failed`, `cancelled`

### Session Status

```
running -> complete   (all agents complete/cancelled, none failed)
running -> failed     (any agent failed)
running -> cancelled  (user cancelled)
```

Valid statuses: `running`, `complete`, `failed`, `cancelled`

### Wave Status

```
pending -> running -> complete
```

Valid statuses: `pending`, `running`, `complete`

## Atomic Update Protocol

Status updates must be atomic to prevent corruption during concurrent writes.

### File Locking

```python
import json
import time
from pathlib import Path

def update_agent_status(session_dir: Path, agent_id: str, updates: dict):
    """Atomically update a single agent's status."""
    lock_file = session_dir / "status.json.lock"

    # Acquire lock (mkdir is atomic)
    while True:
        try:
            lock_file.mkdir()
            break
        except FileExistsError:
            time.sleep(0.05)

    try:
        # Read current state
        status_file = session_dir / "status.json"
        status = json.loads(status_file.read_text())

        # Update agent entry
        for agent in status["agents"]:
            if agent["id"] == agent_id:
                agent.update(updates)
                break

        # Recalculate summary
        status["summary"] = calculate_summary(status["agents"])

        # Atomic write
        tmp_file = status_file.with_suffix(".json.tmp")
        tmp_file.write_text(json.dumps(status, indent=2))
        tmp_file.rename(status_file)
    finally:
        # Release lock
        lock_file.rmdir()


def calculate_summary(agents: list) -> dict:
    """Calculate summary counts from agent list."""
    summary = {
        "total": len(agents),
        "queued": 0,
        "running": 0,
        "complete": 0,
        "failed": 0,
        "cancelled": 0
    }

    for agent in agents:
        status = agent.get("status", "queued")
        if status in summary:
            summary[status] += 1

    return summary
```

### Write Protocol

1. Acquire lock via mkdir (atomic operation)
2. Read current status.json
3. Update only the relevant agent entry
4. Recalculate summary counts
5. Write to .tmp file
6. Atomic rename .tmp to status.json
7. Release lock via rmdir

## Session Lifecycle

### Create Session

```python
from datetime import datetime
from pathlib import Path
from uuid import uuid4

def create_session(
    cwd: str,
    source: str,
    source_file: str,
    agents: list[dict],
    waves: list[dict] = None
) -> Path:
    """Create a new execution session."""
    session_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
    base_dir = Path(cwd) / ".founder-mode" / "status"
    session_dir = base_dir / "sessions" / session_id
    session_dir.mkdir(parents=True)

    # Initialize agent entries
    for agent in agents:
        agent.setdefault("status", "queued")
        agent.setdefault("started_at", None)
        agent.setdefault("completed_at", None)
        agent.setdefault("duration_seconds", None)
        agent.setdefault("exit_code", None)
        agent.setdefault("pid", None)
        agent.setdefault("error", None)
        agent["log_file"] = str(session_dir / f"{agent['id']}.log")

    status = {
        "schema_version": "1.0",
        "session_id": session_id,
        "source": source,
        "source_file": source_file,
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "status": "running",
        "agents": agents,
        "summary": calculate_summary(agents),
        "waves": waves or []
    }

    (session_dir / "status.json").write_text(json.dumps(status, indent=2))

    # Update active-session symlink
    active_link = base_dir / "active-session"
    active_link.unlink(missing_ok=True)
    active_link.symlink_to(session_dir)

    return session_dir
```

### Complete Session

```python
def complete_session(session_dir: Path):
    """Mark session as complete and calculate final status."""
    status_file = session_dir / "status.json"
    status = json.loads(status_file.read_text())

    # Determine final status
    if any(a["status"] == "failed" for a in status["agents"]):
        status["status"] = "failed"
    elif all(a["status"] in ("complete", "cancelled") for a in status["agents"]):
        status["status"] = "complete"

    status["completed_at"] = datetime.now().isoformat()

    # Atomic write
    tmp_file = status_file.with_suffix(".json.tmp")
    tmp_file.write_text(json.dumps(status, indent=2))
    tmp_file.rename(status_file)
```

### Start Agent

```python
def start_agent(session_dir: Path, agent_id: str, pid: int = None):
    """Mark an agent as running."""
    update_agent_status(session_dir, agent_id, {
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "pid": pid
    })
```

### Complete Agent

```python
def complete_agent(session_dir: Path, agent_id: str, exit_code: int = 0):
    """Mark an agent as complete."""
    # Read to get started_at for duration calculation
    status = json.loads((session_dir / "status.json").read_text())
    agent = next((a for a in status["agents"] if a["id"] == agent_id), None)

    duration = None
    if agent and agent.get("started_at"):
        started = datetime.fromisoformat(agent["started_at"])
        duration = (datetime.now() - started).total_seconds()

    update_agent_status(session_dir, agent_id, {
        "status": "complete",
        "completed_at": datetime.now().isoformat(),
        "duration_seconds": duration,
        "exit_code": exit_code,
        "pid": None
    })
```

### Fail Agent

```python
def fail_agent(session_dir: Path, agent_id: str, error: str, exit_code: int = 1):
    """Mark an agent as failed."""
    status = json.loads((session_dir / "status.json").read_text())
    agent = next((a for a in status["agents"] if a["id"] == agent_id), None)

    duration = None
    if agent and agent.get("started_at"):
        started = datetime.fromisoformat(agent["started_at"])
        duration = (datetime.now() - started).total_seconds()

    update_agent_status(session_dir, agent_id, {
        "status": "failed",
        "completed_at": datetime.now().isoformat(),
        "duration_seconds": duration,
        "exit_code": exit_code,
        "pid": None,
        "error": error
    })
```

## Example Files

### Running Session (2 complete, 2 running, 1 queued)

```json
{
  "schema_version": "1.0",
  "session_id": "20260201-143022-abc12345",
  "source": "orchestrate",
  "source_file": "prompts/monitor/000-orchestrator.md",
  "started_at": "2026-02-01T14:30:22Z",
  "completed_at": null,
  "status": "running",
  "agents": [
    {"id": "001", "name": "status-schema", "status": "complete", "duration_seconds": 154},
    {"id": "003", "name": "table-renderer", "status": "complete", "duration_seconds": 192},
    {"id": "002", "name": "status-writer", "status": "running", "started_at": "2026-02-01T14:33:00Z"},
    {"id": "004", "name": "executor-integration", "status": "running", "started_at": "2026-02-01T14:33:05Z"},
    {"id": "005", "name": "log-utilities", "status": "queued"}
  ],
  "summary": {"total": 5, "queued": 1, "running": 2, "complete": 2, "failed": 0, "cancelled": 0},
  "waves": [
    {"wave": 1, "status": "complete", "agents": ["001", "003"]},
    {"wave": 2, "status": "running", "agents": ["002", "004", "005"]}
  ]
}
```

### Completed Session

```json
{
  "schema_version": "1.0",
  "session_id": "20260201-143022-abc12345",
  "source": "orchestrate",
  "source_file": "prompts/monitor/000-orchestrator.md",
  "started_at": "2026-02-01T14:30:22Z",
  "completed_at": "2026-02-01T14:45:18Z",
  "status": "complete",
  "agents": [
    {"id": "001", "status": "complete", "duration_seconds": 154},
    {"id": "002", "status": "complete", "duration_seconds": 201},
    {"id": "003", "status": "complete", "duration_seconds": 192},
    {"id": "004", "status": "complete", "duration_seconds": 245},
    {"id": "005", "status": "complete", "duration_seconds": 178}
  ],
  "summary": {"total": 5, "queued": 0, "running": 0, "complete": 5, "failed": 0, "cancelled": 0},
  "waves": [
    {"wave": 1, "status": "complete", "agents": ["001", "003"]},
    {"wave": 2, "status": "complete", "agents": ["002", "004", "005"]}
  ]
}
```

### Failed Session

```json
{
  "schema_version": "1.0",
  "session_id": "20260201-143022-abc12345",
  "source": "orchestrate",
  "source_file": "prompts/monitor/000-orchestrator.md",
  "started_at": "2026-02-01T14:30:22Z",
  "completed_at": "2026-02-01T14:38:45Z",
  "status": "failed",
  "agents": [
    {"id": "001", "status": "complete", "duration_seconds": 154},
    {"id": "002", "status": "failed", "error": "Exit code 1: Missing required input", "exit_code": 1},
    {"id": "003", "status": "cancelled"},
    {"id": "004", "status": "cancelled"},
    {"id": "005", "status": "cancelled"}
  ],
  "summary": {"total": 5, "queued": 0, "running": 0, "complete": 1, "failed": 1, "cancelled": 3},
  "waves": [
    {"wave": 1, "status": "complete", "agents": ["001"]},
    {"wave": 2, "status": "complete", "agents": ["002", "003", "004", "005"]}
  ]
}
```

### Cancelled Session

```json
{
  "schema_version": "1.0",
  "session_id": "20260201-143022-abc12345",
  "source": "run-prompt",
  "source_file": "prompts/feature.md",
  "started_at": "2026-02-01T14:30:22Z",
  "completed_at": "2026-02-01T14:32:10Z",
  "status": "cancelled",
  "agents": [
    {"id": "001", "status": "cancelled", "started_at": "2026-02-01T14:30:25Z"}
  ],
  "summary": {"total": 1, "queued": 0, "running": 0, "complete": 0, "failed": 0, "cancelled": 1},
  "waves": []
}
```

## Reading Status

### Get Active Session

```python
def get_active_session(cwd: str) -> Path | None:
    """Get the active session directory."""
    active_link = Path(cwd) / ".founder-mode" / "status" / "active-session"
    if active_link.exists():
        return active_link.resolve()
    return None
```

### Load Session Status

```python
def load_session_status(session_dir: Path) -> dict:
    """Load status.json from a session directory."""
    status_file = session_dir / "status.json"
    if status_file.exists():
        return json.loads(status_file.read_text())
    return {}
```

### Check Session Complete

```python
def is_session_complete(session_dir: Path) -> bool:
    """Check if session has finished (complete, failed, or cancelled)."""
    status = load_session_status(session_dir)
    return status.get("status") in ("complete", "failed", "cancelled")
```
