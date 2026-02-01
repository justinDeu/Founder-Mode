#!/usr/bin/env python3
"""Status management for parallel execution monitoring.

Handles session creation, agent status updates, and lifecycle management.
Status is stored in .founder-mode/status/sessions/{session-id}/status.json.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4


def get_status_dir(cwd: str) -> Path:
    """Get/create the status directory for a project."""
    status_dir = Path(cwd) / ".founder-mode" / "status" / "sessions"
    status_dir.mkdir(parents=True, exist_ok=True)
    return status_dir


def get_active_session(cwd: str) -> Optional[Path]:
    """Get the active session directory, if any."""
    active_link = Path(cwd) / ".founder-mode" / "status" / "active-session"
    if active_link.exists() and active_link.is_symlink():
        return active_link.resolve()
    return None


class StatusLock:
    """Context manager for status file locking.

    Uses mkdir for atomic lock acquisition (works across platforms).
    """

    def __init__(self, session_dir: Path, timeout: float = 5.0):
        self.lock_dir = session_dir / "status.json.lock"
        self.timeout = timeout
        self.acquired = False

    def __enter__(self):
        start = time.monotonic()
        while True:
            try:
                self.lock_dir.mkdir()
                self.acquired = True
                return self
            except FileExistsError:
                if time.monotonic() - start > self.timeout:
                    raise TimeoutError(f"Could not acquire lock after {self.timeout}s")
                time.sleep(0.05)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.acquired:
            try:
                self.lock_dir.rmdir()
            except OSError:
                pass  # Already removed or never created
        return False


def calculate_summary(agents: list[dict]) -> dict:
    """Calculate summary counts from agent statuses."""
    summary = {
        "total": len(agents),
        "queued": 0,
        "running": 0,
        "complete": 0,
        "failed": 0,
        "cancelled": 0,
    }
    for agent in agents:
        status = agent.get("status", "queued")
        if status in summary:
            summary[status] += 1
    return summary


def create_session(
    cwd: str,
    source: str,
    source_file: str,
    agents: list[dict],
    waves: Optional[list[dict]] = None,
) -> Path:
    """Create a new execution session.

    Args:
        cwd: Project working directory
        source: Source type (orchestrate, execute-phase, run-prompt)
        source_file: Path to orchestrator or prompt file
        agents: List of agent definitions with id, name, prompt_path, wave, model
        waves: Optional wave definitions

    Returns:
        Path to the session directory
    """
    # Generate session ID
    session_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
    session_dir = get_status_dir(cwd) / session_id
    session_dir.mkdir(parents=True)

    # Initialize agents with default status
    for agent in agents:
        agent.setdefault("status", "queued")
        agent.setdefault("started_at", None)
        agent.setdefault("completed_at", None)
        agent.setdefault("duration_seconds", None)
        agent.setdefault("exit_code", None)
        agent.setdefault("pid", None)
        agent.setdefault("error", None)
        agent["log_file"] = str(session_dir / f"{agent['id']}.log")

    # Build status structure
    status = {
        "schema_version": "1.0",
        "session_id": session_id,
        "source": source,
        "source_file": source_file,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "status": "running",
        "agents": agents,
        "summary": calculate_summary(agents),
        "waves": waves or [],
    }

    # Write status file
    (session_dir / "status.json").write_text(json.dumps(status, indent=2))

    # Update active-session symlink
    active_link = Path(cwd) / ".founder-mode" / "status" / "active-session"
    active_link.parent.mkdir(parents=True, exist_ok=True)
    if active_link.is_symlink() or active_link.exists():
        active_link.unlink()
    active_link.symlink_to(session_dir)

    return session_dir


def update_agent_status(session_dir: Path, agent_id: str, updates: dict) -> dict:
    """Atomically update a single agent's status.

    Args:
        session_dir: Path to session directory
        agent_id: ID of the agent to update
        updates: Dictionary of fields to update

    Returns:
        Updated status dictionary
    """
    status_file = session_dir / "status.json"

    with StatusLock(session_dir):
        status = json.loads(status_file.read_text())

        # Find and update agent
        for agent in status["agents"]:
            if agent["id"] == agent_id:
                agent.update(updates)

                # Calculate duration if completing
                if updates.get("status") in ("complete", "failed", "cancelled"):
                    if agent.get("started_at") and not agent.get("duration_seconds"):
                        start = datetime.fromisoformat(
                            agent["started_at"].replace("Z", "+00:00")
                        )
                        end = datetime.now(timezone.utc)
                        agent["duration_seconds"] = (end - start).total_seconds()
                        agent["completed_at"] = end.isoformat()
                break

        # Recalculate summary
        status["summary"] = calculate_summary(status["agents"])

        # Check if session is complete
        if all(
            a["status"] in ("complete", "failed", "cancelled") for a in status["agents"]
        ):
            if any(a["status"] == "failed" for a in status["agents"]):
                status["status"] = "failed"
            else:
                status["status"] = "complete"
            status["completed_at"] = datetime.now(timezone.utc).isoformat()

        # Atomic write
        tmp_file = status_file.with_suffix(".json.tmp")
        tmp_file.write_text(json.dumps(status, indent=2))
        tmp_file.rename(status_file)

        return status


def start_agent(session_dir: Path, agent_id: str, pid: Optional[int] = None) -> dict:
    """Mark an agent as running.

    Args:
        session_dir: Path to session directory
        agent_id: ID of the agent to start
        pid: Optional process ID for background execution

    Returns:
        Updated status dictionary
    """
    return update_agent_status(
        session_dir,
        agent_id,
        {
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "pid": pid,
        },
    )


def complete_agent(session_dir: Path, agent_id: str, exit_code: int = 0) -> dict:
    """Mark an agent as complete.

    Args:
        session_dir: Path to session directory
        agent_id: ID of the agent
        exit_code: Exit code (0 for success)

    Returns:
        Updated status dictionary
    """
    return update_agent_status(
        session_dir,
        agent_id,
        {"status": "complete" if exit_code == 0 else "failed", "exit_code": exit_code},
    )


def fail_agent(
    session_dir: Path, agent_id: str, error: str, exit_code: int = 1
) -> dict:
    """Mark an agent as failed with error message.

    Args:
        session_dir: Path to session directory
        agent_id: ID of the agent
        error: Error message
        exit_code: Exit code

    Returns:
        Updated status dictionary
    """
    return update_agent_status(
        session_dir, agent_id, {"status": "failed", "exit_code": exit_code, "error": error}
    )


def load_session_status(session_dir: Path) -> dict:
    """Load current session status.

    Args:
        session_dir: Path to session directory

    Returns:
        Status dictionary
    """
    status_file = session_dir / "status.json"
    return json.loads(status_file.read_text())


def get_running_agents(session_dir: Path) -> list[dict]:
    """Get list of currently running agents.

    Args:
        session_dir: Path to session directory

    Returns:
        List of agent dictionaries with status="running"
    """
    status = load_session_status(session_dir)
    return [a for a in status["agents"] if a["status"] == "running"]


def get_pending_agents(session_dir: Path) -> list[dict]:
    """Get list of queued agents.

    Args:
        session_dir: Path to session directory

    Returns:
        List of agent dictionaries with status="queued"
    """
    status = load_session_status(session_dir)
    return [a for a in status["agents"] if a["status"] == "queued"]


def is_session_complete(session_dir: Path) -> bool:
    """Check if session has completed (success or failure).

    Args:
        session_dir: Path to session directory

    Returns:
        True if session is complete, failed, or cancelled
    """
    status = load_session_status(session_dir)
    return status["status"] in ("complete", "failed", "cancelled")


def cancel_session(session_dir: Path) -> dict:
    """Cancel all pending/running agents and mark session cancelled.

    Args:
        session_dir: Path to session directory

    Returns:
        Updated status dictionary
    """
    status_file = session_dir / "status.json"

    with StatusLock(session_dir):
        status = json.loads(status_file.read_text())

        for agent in status["agents"]:
            if agent["status"] in ("queued", "running"):
                agent["status"] = "cancelled"
                if not agent.get("completed_at"):
                    agent["completed_at"] = datetime.now(timezone.utc).isoformat()

        status["status"] = "cancelled"
        status["completed_at"] = datetime.now(timezone.utc).isoformat()
        status["summary"] = calculate_summary(status["agents"])

        tmp_file = status_file.with_suffix(".json.tmp")
        tmp_file.write_text(json.dumps(status, indent=2))
        tmp_file.rename(status_file)

        return status


def cleanup_old_sessions(cwd: str, keep_days: int = 7) -> int:
    """Remove sessions older than keep_days.

    Args:
        cwd: Project working directory
        keep_days: Number of days to keep sessions

    Returns:
        Count of sessions removed
    """
    import shutil

    status_dir = get_status_dir(cwd)
    cutoff = datetime.now(timezone.utc).timestamp() - (keep_days * 86400)
    removed = 0

    for session_dir in status_dir.iterdir():
        if not session_dir.is_dir():
            continue
        status_file = session_dir / "status.json"
        if not status_file.exists():
            continue

        try:
            status = json.loads(status_file.read_text())
            started = datetime.fromisoformat(status["started_at"].replace("Z", "+00:00"))
            if started.timestamp() < cutoff:
                shutil.rmtree(session_dir)
                removed += 1
        except (json.JSONDecodeError, KeyError, OSError):
            continue

    return removed
