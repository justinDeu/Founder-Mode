#!/usr/bin/env python3
"""Minimal executor for non-Claude CLI models with optional verification loop."""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path


MODEL_COMMANDS = {
    "codex": lambda prompt: (["codex", "exec", "--full-auto", "-"], prompt, True),
    "gemini": lambda prompt: (["gemini", "-y", "-p", prompt], None, False),
    "zai": lambda prompt: (["zai", "-p", prompt], None, False),
}

VERIFICATION_PATTERN = re.compile(r"<verification>(.*?)</verification>", re.DOTALL)


def run_cli(model: str, prompt: str, cwd: str, log_path: Path) -> bool:
    """Run the CLI for the given model. Returns True on success."""
    if model not in MODEL_COMMANDS:
        raise ValueError(f"Unknown model: {model}. Supported: {list(MODEL_COMMANDS.keys())}")

    cmd, stdin_data, uses_stdin = MODEL_COMMANDS[model](prompt)

    with open(log_path, "a") as log_file:
        log_file.write(f"\n--- Execution at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        log_file.flush()

        proc = subprocess.run(
            cmd,
            cwd=cwd,
            input=stdin_data if uses_stdin else None,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )

    return proc.returncode == 0


def check_verification(log_path: Path) -> tuple[str, str | None]:
    """Check log for verification markers. Returns (status, reason)."""
    content = log_path.read_text()
    matches = VERIFICATION_PATTERN.findall(content)

    if not matches:
        return "no_marker", None

    last_match = matches[-1].strip()

    if last_match == "VERIFICATION_COMPLETE":
        return "complete", None

    if last_match.startswith("NEEDS_RETRY:"):
        reason = last_match[len("NEEDS_RETRY:"):].strip()
        return "retry", reason

    return "unknown", last_match


def build_retry_prompt(original_prompt: str, log_path: Path, reason: str) -> str:
    """Build prompt with history for retry."""
    history = log_path.read_text()
    return f"""{original_prompt}

--- Previous Attempt ---
{history}

--- Retry Reason ---
{reason}

Please address the issue and try again.
"""


def main():
    parser = argparse.ArgumentParser(description="Execute non-Claude CLI models")
    parser.add_argument("--prompt", required=True, help="Path to prompt file")
    parser.add_argument("--cwd", required=True, help="Working directory for execution")
    parser.add_argument("--model", required=True, help="Model to use (codex, gemini, zai)")
    parser.add_argument("--log", required=True, help="Path to log file")
    parser.add_argument("--loop", action="store_true", help="Enable verification loop")
    parser.add_argument("--max-iterations", type=int, default=3, help="Max loop iterations")
    parser.add_argument("--completion-marker", default="VERIFICATION_COMPLETE",
                        help="Marker indicating successful completion")

    args = parser.parse_args()

    prompt_path = Path(args.prompt)
    log_path = Path(args.log)
    cwd = args.cwd

    if not prompt_path.exists():
        print(json.dumps({"status": "error", "message": f"Prompt file not found: {args.prompt}"}))
        sys.exit(1)

    original_prompt = prompt_path.read_text()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    iterations = 0
    status = "unknown"
    current_prompt = original_prompt

    while iterations < args.max_iterations:
        iterations += 1

        success = run_cli(args.model, current_prompt, cwd, log_path)

        if not success:
            status = "cli_error"
            break

        if not args.loop:
            status = "success"
            break

        verification_status, reason = check_verification(log_path)

        if verification_status == "complete":
            status = "success"
            break

        if verification_status == "retry" and iterations < args.max_iterations:
            current_prompt = build_retry_prompt(original_prompt, log_path, reason)
            status = "retrying"
            continue

        if verification_status == "no_marker":
            status = "no_verification_marker"
            break

        status = f"verification_failed:{verification_status}"
        break

    result = {
        "status": status,
        "iterations": iterations,
        "log_path": str(log_path.absolute()),
    }

    print(json.dumps(result))
    sys.exit(0 if status == "success" else 1)


if __name__ == "__main__":
    main()
