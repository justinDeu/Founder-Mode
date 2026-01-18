#!/usr/bin/env python3
"""Minimal executor for non-Claude CLI models with optional verification loop."""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


# Model configuration structure:
# - command: base command list (prompt will be appended for positional mode)
# - stdin_mode: "stdin" (pipe prompt to stdin) or "positional" (append prompt to command)
# - env: environment variables to set (merged with current env)
MODEL_CONFIG = {
    # Existing models
    "codex": {
        "command": ["codex", "exec", "--full-auto", "-"],
        "stdin_mode": "stdin",
        "env": {},
    },
    "gemini": {
        "command": ["gemini", "-y", "-p"],
        "stdin_mode": "positional",
        "env": {},
    },
    "zai": {
        "command": ["zai", "-p"],
        "stdin_mode": "positional",
        "env": {},
    },
    # OpenCode variants
    "opencode": {
        "command": ["opencode", "run"],
        "stdin_mode": "positional",
        "env": {},
    },
    "opencode-zai": {
        "command": ["opencode", "--model", "zai/glm-4.7", "run"],
        "stdin_mode": "positional",
        "env": {},
    },
    "opencode-codex": {
        "command": ["opencode", "--model", "openai/gpt-5.2-codex", "run"],
        "stdin_mode": "positional",
        "env": {},
    },
    # Claude with Z.AI backend
    "claude-zai": {
        "command": ["claude", "-p"],
        "stdin_mode": "positional",
        "env": {
            "ANTHROPIC_BASE_URL": "https://api.z.ai/api/anthropic",
            # ANTHROPIC_AUTH_TOKEN must be set in user's environment
        },
        "extra_args": ["--dangerously-skip-permissions"],
    },
}


def get_model_command(model: str, prompt: str) -> tuple[list[str], str | None, bool, dict]:
    """Build command for model. Returns (cmd, stdin_data, uses_stdin, env_vars)."""
    if model not in MODEL_CONFIG:
        raise ValueError(f"Unknown model: {model}. Supported: {list(MODEL_CONFIG.keys())}")

    config = MODEL_CONFIG[model]
    cmd = list(config["command"])  # Copy to avoid mutation
    uses_stdin = config["stdin_mode"] == "stdin"
    env_vars = config.get("env", {})

    # Add extra args if present
    if "extra_args" in config:
        cmd.extend(config["extra_args"])

    if uses_stdin:
        stdin_data = prompt
    else:
        cmd.append(prompt)
        stdin_data = None

    return cmd, stdin_data, uses_stdin, env_vars

VERIFICATION_PATTERN = re.compile(r"<verification>(.*?)</verification>", re.DOTALL)


def run_cli(model: str, prompt: str, cwd: str, log_path: Path) -> bool:
    """Run the CLI for the given model (blocking). Returns True on success."""
    cmd, stdin_data, uses_stdin, env_vars = get_model_command(model, prompt)

    # Merge environment variables with current environment
    env = None
    if env_vars:
        env = os.environ.copy()
        env.update(env_vars)

    with open(log_path, "a") as log_file:
        log_file.write(f"\n--- Execution at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        log_file.write(f"--- Model: {model} | Command: {' '.join(cmd[:3])}... ---\n")
        log_file.flush()

        proc = subprocess.run(
            cmd,
            cwd=cwd,
            input=stdin_data if uses_stdin else None,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )

    return proc.returncode == 0


def run_cli_background(model: str, prompt: str, cwd: str, log_path: Path) -> int:
    """Run the CLI for the given model in background. Returns PID."""
    cmd, stdin_data, uses_stdin, env_vars = get_model_command(model, prompt)

    # Merge environment variables with current environment
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)

    # Ensure log directory exists
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Open log file for the subprocess
    log_file = open(log_path, "a")
    log_file.write(f"\n--- Background execution at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
    log_file.write(f"--- Model: {model} | Command: {' '.join(cmd[:3])}... ---\n")
    log_file.flush()

    # Spawn background process with session isolation
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdin=subprocess.PIPE if uses_stdin else None,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        start_new_session=True,  # Isolate from terminal
    )

    # Write stdin data if needed, then close
    if uses_stdin and stdin_data:
        proc.stdin.write(stdin_data)
        proc.stdin.close()

    # Note: log_file intentionally not closed - subprocess owns it now
    return proc.pid


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
    parser.add_argument("--model", required=True,
                        help="Model to use: codex, gemini, zai, opencode, opencode-zai, opencode-codex, claude-zai")
    parser.add_argument("--log", required=True, help="Path to log file")
    parser.add_argument("--background", action="store_true", help="Run in background (non-blocking)")
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

    # Background execution: spawn and return immediately
    if args.background:
        pid = run_cli_background(args.model, original_prompt, cwd, log_path)
        result = {
            "status": "running",
            "pid": pid,
            "log_path": str(log_path.absolute()),
            "model": args.model,
        }
        print(json.dumps(result))
        sys.exit(0)

    # Foreground execution with optional verification loop
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
