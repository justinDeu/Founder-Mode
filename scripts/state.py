#!/usr/bin/env python3
"""State management for founder-mode verification loops.

Handles persistent state for resumable execution loops. State is stored
project-locally in .founder-mode/state/{prompt_id}.json.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def get_state_dir(cwd: str) -> Path:
    """Get/create the state directory for a project.

    Args:
        cwd: Project working directory

    Returns:
        Path to .founder-mode/state/ directory (created if missing)
    """
    state_dir = Path(cwd) / ".founder-mode" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def get_state_file(cwd: str, prompt_id: str) -> Path:
    """Get state file path for a prompt.

    Args:
        cwd: Project working directory
        prompt_id: Identifier for the prompt (usually prompt filename stem)

    Returns:
        Path to the state JSON file
    """
    return get_state_dir(cwd) / f"{prompt_id}.json"


def load_state(cwd: str, prompt_id: str) -> Optional[dict]:
    """Load existing state, return None if not found.

    Args:
        cwd: Project working directory
        prompt_id: Identifier for the prompt

    Returns:
        State dictionary or None if file doesn't exist
    """
    state_file = get_state_file(cwd, prompt_id)
    if not state_file.exists():
        return None

    try:
        with open(state_file) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_state(state: dict) -> None:
    """Save state to file, updating last_updated timestamp.

    Args:
        state: State dictionary (must contain 'cwd' and 'prompt_id')
    """
    state["last_updated_at"] = datetime.now(timezone.utc).isoformat()
    state_file = get_state_file(state["cwd"], state["prompt_id"])

    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


def create_state(
    prompt_id: str,
    model: str,
    max_iterations: int,
    log_path: str,
    cwd: str
) -> dict:
    """Create new state structure.

    Args:
        prompt_id: Identifier for the prompt
        model: Model name being used
        max_iterations: Maximum loop iterations allowed
        log_path: Path to the execution log file
        cwd: Project working directory

    Returns:
        New state dictionary
    """
    now = datetime.now(timezone.utc).isoformat()
    return {
        "prompt_id": prompt_id,
        "model": model,
        "status": "created",
        "iteration": 0,
        "max_iterations": max_iterations,
        "log_path": log_path,
        "cwd": cwd,
        "started_at": now,
        "last_updated_at": now,
        "history": [],
        "suggested_next_steps": [],
    }


def update_iteration(
    state: dict,
    exit_code: int,
    marker_found: bool,
    retry_reason: Optional[str] = None
) -> None:
    """Record completed iteration in history.

    Args:
        state: State dictionary to update (modified in place)
        exit_code: Process exit code from the iteration
        marker_found: Whether verification marker was found
        retry_reason: Reason for retry if applicable
    """
    state["iteration"] += 1

    history_entry = {
        "iteration": state["iteration"],
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "exit_code": exit_code,
        "marker_found": marker_found,
    }

    if retry_reason:
        history_entry["retry_reason"] = retry_reason

    state["history"].append(history_entry)


# Patterns for extracting next steps from log content
NEXT_STEPS_PATTERNS = [
    r"next\s+steps?:",
    r"suggested\s+(?:next\s+)?steps?:",
    r"todo:",
    r"remaining\s+(?:work|tasks?):",
]
NEXT_STEPS_HEADER_RE = re.compile(
    r"^\s*(?:" + "|".join(NEXT_STEPS_PATTERNS) + r")\s*(.*)$",
    re.IGNORECASE | re.MULTILINE
)
ITEM_RE = re.compile(r"^\s*(?:\d+[.)]|[-*]|•)\s*(.+)$")


def extract_next_steps(log_content: str) -> list[str]:
    """Extract suggested next steps from log content.

    Looks for headers like "Next steps:", "TODO:", etc.
    and extracts bulleted/numbered items following them.

    Args:
        log_content: Full log file content

    Returns:
        List of extracted step strings (max 10)
    """
    steps = []
    lines = log_content.split('\n')
    in_steps_section = False

    for line in lines:
        # Check for header
        header_match = NEXT_STEPS_HEADER_RE.match(line)
        if header_match:
            in_steps_section = True
            # Check for inline content after header
            inline = header_match.group(1).strip()
            if inline:
                steps.append(inline)
            continue

        if in_steps_section:
            # Check for list item
            item_match = ITEM_RE.match(line)
            if item_match:
                steps.append(item_match.group(1).strip())
            elif line.strip() == "":
                # Empty line ends section
                in_steps_section = False
            elif not line.startswith(" ") and not line.startswith("\t"):
                # Non-indented non-item ends section
                in_steps_section = False

    return steps[:10]  # Limit to 10 items
