#!/usr/bin/env python3
"""Terminal table renderer for parallel execution monitoring."""

import os
import sys
from datetime import datetime, timezone
from typing import Optional


class Colors:
    """ANSI escape codes for terminal formatting."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground colors
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Cursor control
    CLEAR_LINE = "\033[2K"
    MOVE_UP = "\033[A"
    HIDE_CURSOR = "\033[?25l"
    SHOW_CURSOR = "\033[?25h"

    @classmethod
    def supports_color(cls) -> bool:
        """Check if terminal supports color output."""
        if os.environ.get("NO_COLOR"):
            return False
        if os.environ.get("FORCE_COLOR"):
            return True
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


# Status icons and colors
STATUS_DISPLAY = {
    "queued": ("○", Colors.DIM, "Queue"),
    "running": ("●", Colors.YELLOW, "Run"),
    "complete": ("✓", Colors.GREEN, "Done"),
    "failed": ("✗", Colors.RED, "Fail"),
    "cancelled": ("⊘", Colors.DIM, "Skip"),
}


def format_status(status: str, use_color: bool = True) -> str:
    """Format agent status with icon and color."""
    icon, color, label = STATUS_DISPLAY.get(status, ("?", "", status[:5]))
    if use_color and Colors.supports_color():
        return f"{color}{icon} {label}{Colors.RESET}"
    return f"{icon} {label}"


def format_duration(seconds: Optional[float]) -> str:
    """Format duration in human-readable form."""
    if seconds is None:
        return "-"
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes < 60:
        return f"{minutes}m {secs:02d}s"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins:02d}m"


def format_elapsed(started_at: Optional[str]) -> str:
    """Format elapsed time from ISO timestamp."""
    if not started_at:
        return "-"
    try:
        # Handle both Z suffix and +00:00 format
        ts = started_at.replace("Z", "+00:00")
        start = datetime.fromisoformat(ts)
        # Make now timezone-aware if start is
        if start.tzinfo:
            now = datetime.now(timezone.utc)
        else:
            now = datetime.now()
        elapsed = (now - start).total_seconds()
        return format_duration(elapsed)
    except (ValueError, TypeError):
        return "-"


def truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis if too long."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def render_table(
    status: dict, use_color: bool = True, show_logs: bool = True
) -> list[str]:
    """Render status as a formatted table.

    Args:
        status: Session status dictionary
        use_color: Whether to use ANSI colors
        show_logs: Whether to show log tail commands

    Returns:
        List of lines to print
    """
    lines = []
    summary = status.get("summary", {})
    complete = summary.get("complete", 0) + summary.get("cancelled", 0)
    total = summary.get("total", 0)

    # Header
    title = "Parallel Execution Monitor"
    progress = f"[{complete}/{total} complete]"

    if use_color and Colors.supports_color():
        header = f"{Colors.BOLD}{title}{Colors.RESET}"
    else:
        header = title

    lines.append(f"┌{'─' * 77}┐")
    lines.append(f"│ {header:<50} {progress:>24} │")
    lines.append(f"├─────┬{'─' * 22}┬{'─' * 10}┬{'─' * 9}┬{'─' * 27}┤")
    lines.append(
        f"│ {'#':<3} │ {'Task':<20} │ {'Status':<8} │ {'Time':<7} │ {'Log':<25} │"
    )
    lines.append(f"├─────┼{'─' * 22}┼{'─' * 10}┼{'─' * 9}┼{'─' * 27}┤")

    # Agent rows
    for i, agent in enumerate(status.get("agents", []), 1):
        name = truncate(agent.get("name", agent.get("id", "?")), 20)
        status_str = format_status(agent.get("status", "queued"), use_color)

        # Duration: use completed duration or elapsed time
        if agent.get("duration_seconds"):
            time_str = format_duration(agent["duration_seconds"])
        elif agent.get("started_at"):
            time_str = format_elapsed(agent["started_at"])
        else:
            time_str = "-"

        # Log command (only for running agents)
        if show_logs and agent.get("status") == "running" and agent.get("log_file"):
            log_str = truncate(f"tail -f {agent['log_file']}", 25)
        else:
            log_str = ""

        # Calculate display width accounting for ANSI codes
        # status_str contains color codes, so we need to pad differently
        if use_color and Colors.supports_color():
            # ANSI codes add ~9 chars that don't display
            status_padding = 17  # 8 visible + 9 for codes
        else:
            status_padding = 8

        lines.append(
            f"│ {i:<3} │ {name:<20} │ {status_str:<{status_padding}} │ {time_str:<7} │ {log_str:<25} │"
        )

    lines.append(f"└─────┴{'─' * 22}┴{'─' * 10}┴{'─' * 9}┴{'─' * 27}┘")

    # Footer with session info
    source = status.get("source_file", "")
    if source:
        lines.append(f"Source: {truncate(source, 70)}")

    session_status = status.get("status", "running")
    if session_status == "failed":
        failed_agents = [
            a for a in status.get("agents", []) if a.get("status") == "failed"
        ]
        if failed_agents:
            names = ", ".join(a.get("name", a.get("id")) for a in failed_agents)
            if use_color and Colors.supports_color():
                lines.append(f"{Colors.RED}Failed: {names}{Colors.RESET}")
            else:
                lines.append(f"Failed: {names}")

    return lines


class LiveDisplay:
    """Manages in-place terminal updates."""

    def __init__(self):
        self.last_line_count = 0
        self.use_color = Colors.supports_color()

    def clear_previous(self):
        """Clear previously rendered lines."""
        if self.last_line_count > 0:
            # Move up and clear each line
            for _ in range(self.last_line_count):
                sys.stdout.write(Colors.MOVE_UP + Colors.CLEAR_LINE)
            sys.stdout.flush()

    def render(self, status: dict, show_logs: bool = True):
        """Render status, clearing previous output first."""
        self.clear_previous()
        lines = render_table(status, self.use_color, show_logs)
        for line in lines:
            print(line)
        self.last_line_count = len(lines)

    def __enter__(self):
        if self.use_color:
            sys.stdout.write(Colors.HIDE_CURSOR)
            sys.stdout.flush()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.use_color:
            sys.stdout.write(Colors.SHOW_CURSOR)
            sys.stdout.flush()
        return False


def print_status(status: dict, use_color: Optional[bool] = None):
    """Print status table once (no live updates)."""
    if use_color is None:
        use_color = Colors.supports_color()
    lines = render_table(status, use_color)
    for line in lines:
        print(line)


def format_summary_line(status: dict, use_color: bool = True) -> str:
    """Format a single-line summary of session status.

    Example: "Running: 2/5 complete, 2 running, 1 queued"
    """
    summary = status.get("summary", {})
    session_status = status.get("status", "running")

    parts = []
    if summary.get("complete", 0) > 0:
        parts.append(f"{summary['complete']} complete")
    if summary.get("running", 0) > 0:
        parts.append(f"{summary['running']} running")
    if summary.get("queued", 0) > 0:
        parts.append(f"{summary['queued']} queued")
    if summary.get("failed", 0) > 0:
        parts.append(f"{summary['failed']} failed")

    status_label = session_status.capitalize()
    if use_color and Colors.supports_color():
        if session_status == "complete":
            status_label = f"{Colors.GREEN}{status_label}{Colors.RESET}"
        elif session_status == "failed":
            status_label = f"{Colors.RED}{status_label}{Colors.RESET}"
        elif session_status == "running":
            status_label = f"{Colors.YELLOW}{status_label}{Colors.RESET}"

    return f"{status_label}: {', '.join(parts)}"


if __name__ == "__main__":
    # Demo with sample data
    sample_status = {
        "session_id": "20260201-143022-abc12345",
        "source": "orchestrate",
        "source_file": "prompts/monitor/000-orchestrator.md",
        "status": "running",
        "agents": [
            {
                "id": "001",
                "name": "001-auth-login",
                "status": "complete",
                "duration_seconds": 154,
            },
            {
                "id": "002",
                "name": "002-auth-signup",
                "status": "complete",
                "duration_seconds": 192,
            },
            {
                "id": "003",
                "name": "003-dashboard-layout",
                "status": "running",
                "started_at": "2026-02-01T14:33:00+00:00",
                "log_file": "/tmp/fm/003.log",
            },
            {
                "id": "004",
                "name": "004-api-endpoints",
                "status": "running",
                "started_at": "2026-02-01T14:33:05+00:00",
                "log_file": "/tmp/fm/004.log",
            },
            {"id": "005", "name": "005-database-schema", "status": "queued"},
        ],
        "summary": {
            "total": 5,
            "queued": 1,
            "running": 2,
            "complete": 2,
            "failed": 0,
            "cancelled": 0,
        },
    }

    print("Single print:")
    print_status(sample_status)
    print()
    print("Summary line:")
    print(format_summary_line(sample_status))
