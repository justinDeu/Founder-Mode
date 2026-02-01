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

from state import (
    load_state,
    save_state,
    create_state,
    update_iteration,
    extract_next_steps,
    get_state_file,
)
from status import start_agent, complete_agent, fail_agent


# Z.AI Provider Documentation
# ============================
# Z.AI has multiple provider prefixes with different API access levels:
#
# - zai/glm-4.7: Base provider. May have restricted API access, causing
#   silent failures where requests appear to succeed but produce no useful
#   output (empty responses, truncated completions, or no tool calls).
#
# - zai-coding-plan/glm-4.7: Coding-specific endpoint with proper API access.
#   This is the known-working provider for code generation tasks.
#
# When troubleshooting Z.AI issues:
# 1. Check if the provider prefix matches a known-working provider
# 2. Silent failures (no errors but bad output) usually indicate wrong provider
# 3. The zai-coding-plan/ prefix is required for full API functionality
#
# Known providers:
ZAI_KNOWN_WORKING_PROVIDERS = ["zai-coding-plan/glm-4.7"]
ZAI_PROBLEMATIC_PROVIDERS = ["zai/glm-4.7"]


def validate_zai_provider(model_name: str, command: list[str]) -> None:
    """Warn if using a problematic Z.AI provider.

    Checks command arguments for zai provider strings and warns if
    a problematic provider is detected. Does not block execution.
    """
    # Look for provider in command arguments
    for arg in command:
        if "/" not in arg:
            continue
        # Check for problematic providers
        for problematic in ZAI_PROBLEMATIC_PROVIDERS:
            if problematic in arg:
                print(
                    f"Warning: Model '{model_name}' uses provider '{arg}' which may have "
                    f"API access issues causing silent failures.\n"
                    f"Consider using one of: {ZAI_KNOWN_WORKING_PROVIDERS}",
                    file=sys.stderr,
                )
                return
        # Log known-working providers for debugging
        for working in ZAI_KNOWN_WORKING_PROVIDERS:
            if working in arg:
                # Debug log: uncomment if needed for troubleshooting
                # print(f"Debug: Using known-working Z.AI provider: {arg}", file=sys.stderr)
                return


def update_status(
    session_dir: str | None,
    agent_id: str | None,
    action: str,
    **kwargs
) -> None:
    """Update agent status if session tracking is enabled.

    Args:
        session_dir: Path to session directory (None to skip)
        agent_id: Agent identifier
        action: One of 'start', 'complete', 'fail'
        **kwargs: Additional arguments for the status function
    """
    if not session_dir or not agent_id:
        return

    session_path = Path(session_dir)

    try:
        if action == "start":
            start_agent(session_path, agent_id, kwargs.get("pid"))
        elif action == "complete":
            complete_agent(session_path, agent_id, kwargs.get("exit_code", 0))
        elif action == "fail":
            fail_agent(
                session_path,
                agent_id,
                kwargs.get("error", "Unknown error"),
                kwargs.get("exit_code", 1),
            )
    except Exception as e:
        # Don't fail execution due to status tracking errors
        print(f"Warning: Status update failed: {e}", file=sys.stderr)


# Model configuration structure:
# - command: base command list (prompt will be appended for positional mode)
# - stdin_mode: "stdin" (pipe prompt to stdin) or "positional" (append prompt to command)
# - env: environment variables to set (merged with current env)
# - env_from: map of {TARGET_VAR: SOURCE_VAR} to read from current env and set as TARGET_VAR
#   e.g., {"ANTHROPIC_AUTH_TOKEN": "ZAI_API_KEY"} reads ZAI_API_KEY and sets ANTHROPIC_AUTH_TOKEN
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
    # OpenCode writes logs to stderr by default. Use --print-logs to enable log output.
    # The executor redirects stderr to stdout via stderr=subprocess.STDOUT.
    "opencode": {
        "command": ["opencode", "--print-logs", "run"],
        "stdin_mode": "positional",
        "env": {},
    },
    "opencode-zai": {
        "command": ["opencode", "--print-logs", "--model", "zai-coding-plan/glm-4.7", "run"],
        "stdin_mode": "positional",
        "env": {},
    },
    "opencode-codex": {
        "command": ["opencode", "--print-logs", "--model", "openai/gpt-5.2-codex", "run"],
        "stdin_mode": "positional",
        "env": {},
    },
    # Claude with Z.AI backend
    # Requires ZAI_API_KEY environment variable to be set
    "claude-zai": {
        "command": ["claude", "-p"],
        "stdin_mode": "positional",
        "env": {
            "ANTHROPIC_BASE_URL": "https://api.z.ai/api/anthropic",
        },
        "env_from": {
            "ANTHROPIC_AUTH_TOKEN": "ZAI_API_KEY",
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
    env_vars = dict(config.get("env", {}))  # Copy to allow mutation

    # Resolve env_from: maps target env var -> source env var name
    # e.g., {"ANTHROPIC_AUTH_TOKEN": "ZAI_API_KEY"} reads ZAI_API_KEY and sets ANTHROPIC_AUTH_TOKEN
    if "env_from" in config:
        for target_var, source_var in config["env_from"].items():
            value = os.environ.get(source_var)
            if value:
                env_vars[target_var] = value
            else:
                print(f"Warning: {source_var} not set, {target_var} will not be configured",
                      file=sys.stderr)

    # Validate Z.AI providers and warn about potential issues
    validate_zai_provider(model, cmd)

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

# Two-stage verification markers
STAGE1_COMPLETE = "SPEC_COMPLIANCE_VERIFIED"
STAGE2_COMPLETE = "QUALITY_VERIFIED"

# Combined pattern for two-stage mode
TWO_STAGE_PATTERN = re.compile(
    r"<verification>(SPEC_COMPLIANCE_VERIFIED|QUALITY_VERIFIED|VERIFICATION_COMPLETE|NEEDS_RETRY:.*?)</verification>",
    re.DOTALL
)


def get_iteration_log_path(base_dir: Path, prompt_id: str, iteration: int, timestamp: str) -> Path:
    """Generate log path for a specific iteration."""
    return base_dir / f"{prompt_id}-iter{iteration}-{timestamp}.log"


def get_loop_log_path(base_dir: Path, prompt_id: str, timestamp: str) -> Path:
    """Generate aggregate loop log path."""
    return base_dir / f"{prompt_id}-loop-{timestamp}.log"


def run_cli(
    model: str,
    prompt: str,
    cwd: str,
    log_path: Path,
    session_dir: str | None = None,
    agent_id: str | None = None,
) -> bool:
    """Run the CLI for the given model (blocking). Returns True on success."""
    # Ensure log directory exists
    log_path.parent.mkdir(parents=True, exist_ok=True)

    cmd, stdin_data, uses_stdin, env_vars = get_model_command(model, prompt)

    # Merge environment variables with current environment
    env = None
    if env_vars:
        env = os.environ.copy()
        env.update(env_vars)

    # Mark agent as running
    update_status(session_dir, agent_id, "start")

    try:
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

        success = proc.returncode == 0

        # Update status based on result
        if success:
            update_status(session_dir, agent_id, "complete", exit_code=0)
        else:
            update_status(
                session_dir,
                agent_id,
                "fail",
                error=f"Exit code {proc.returncode}",
                exit_code=proc.returncode,
            )

        return success

    except Exception as e:
        update_status(session_dir, agent_id, "fail", error=str(e), exit_code=1)
        raise


def run_cli_background(
    model: str,
    prompt: str,
    cwd: str,
    log_path: Path,
    session_dir: str | None = None,
    agent_id: str | None = None,
) -> int:
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

    # Mark agent as running with PID
    update_status(session_dir, agent_id, "start", pid=proc.pid)

    # Note: log_file intentionally not closed - subprocess owns it now
    # Note: Background processes can't update status on completion - monitor will detect via PID
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


def check_two_stage_verification(log_path: Path) -> tuple[str, str | None]:
    """Check log for two-stage verification markers.

    Returns (stage, reason) where stage is:
    - "stage1_complete": Spec compliance passed, ready for quality check
    - "stage2_complete": Both stages passed
    - "stage1_retry": Stage 1 needs retry
    - "stage2_retry": Stage 2 needs retry
    - "no_marker": No verification marker found
    """
    content = log_path.read_text()
    matches = TWO_STAGE_PATTERN.findall(content)

    if not matches:
        return "no_marker", None

    last_match = matches[-1].strip()

    if last_match == STAGE2_COMPLETE:
        return "stage2_complete", None
    if last_match == STAGE1_COMPLETE:
        return "stage1_complete", None
    if last_match.startswith("NEEDS_RETRY:"):
        reason = last_match[len("NEEDS_RETRY:"):].strip()
        # Determine which stage failed based on context
        if STAGE1_COMPLETE in content:
            return "stage2_retry", reason
        return "stage1_retry", reason

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
    parser.add_argument("--log", default=None, help="Path to log file (auto-generated if not provided)")
    parser.add_argument("--background", action="store_true", help="Run in background (non-blocking)")
    parser.add_argument("--loop", action="store_true", help="Enable verification loop")
    parser.add_argument("--max-iterations", type=int, default=3, help="Max loop iterations")
    parser.add_argument("--completion-marker", default="VERIFICATION_COMPLETE",
                        help="Marker indicating successful completion")
    parser.add_argument("--two-stage", action="store_true",
                        help="Enable two-stage verification (spec compliance + quality)")
    parser.add_argument("--session-dir", default=None,
                        help="Session directory for status updates")
    parser.add_argument("--agent-id", default=None,
                        help="Agent ID within the session")

    args = parser.parse_args()

    prompt_path = Path(args.prompt)
    cwd = args.cwd
    prompt_id = prompt_path.stem

    # Generate timestamp once at start for consistent log naming
    execution_timestamp = time.strftime('%Y%m%d-%H%M%S')
    log_dir = Path(cwd) / ".founder-mode" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Determine log path for non-loop mode or explicit --log
    if args.log:
        log_path = Path(args.log)
    else:
        log_path = log_dir / f"{prompt_id}_{execution_timestamp}.log"

    if not prompt_path.exists():
        print(json.dumps({"status": "error", "message": f"Prompt file not found: {args.prompt}"}))
        sys.exit(1)

    original_prompt = prompt_path.read_text()

    # Background execution: spawn and return immediately
    if args.background:
        pid = run_cli_background(
            args.model, original_prompt, cwd, log_path,
            args.session_dir, args.agent_id
        )
        result = {
            "status": "running",
            "pid": pid,
            "log_path": str(log_path.absolute()),
            "model": args.model,
        }
        if args.session_dir and args.agent_id:
            result["session_dir"] = args.session_dir
            result["agent_id"] = args.agent_id
        print(json.dumps(result))
        sys.exit(0)

    # Initialize loop logging if enabled
    loop_log_path = None
    iteration_logs = []

    if args.loop:
        loop_log_path = get_loop_log_path(log_dir, prompt_id, execution_timestamp)
        with open(loop_log_path, "w") as f:
            f.write(f"=== Loop started at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            f.write(f"Prompt: {prompt_id}\n")
            f.write(f"Model: {args.model}\n")
            f.write(f"Max iterations: {args.max_iterations}\n\n")

    # Initialize state for persistence (loop mode only)
    state = None
    if args.loop:
        existing_state = load_state(cwd, prompt_id)
        if existing_state and existing_state.get("status") == "running":
            state = existing_state
            print(f"Resuming from iteration {state['iteration']}", file=sys.stderr)
        else:
            state = create_state(
                prompt_id, args.model, args.max_iterations,
                str(loop_log_path.absolute()), cwd
            )
        state["status"] = "running"
        save_state(state)

    # Foreground execution with optional verification loop
    iterations = state["iteration"] if state else 0
    status = "unknown"
    current_prompt = original_prompt
    stage = "spec"  # For two-stage mode: "spec" or "quality"
    stages_completed = []  # Track completed stages for result JSON

    # Two-stage verification mode
    if args.two_stage and args.loop:
        while iterations < args.max_iterations:
            iterations += 1

            # Determine log path for this iteration
            iteration_log_path = get_iteration_log_path(log_dir, prompt_id, iterations, execution_timestamp)
            iteration_logs.append(str(iteration_log_path.absolute()))

            if stage == "spec":
                # Stage 1: Spec compliance
                stage_prompt = current_prompt + """

## Verification Stage 1: Spec Compliance

After completing the work, verify SPEC COMPLIANCE:
- Does the output match the requirements?
- Are all specified features implemented?
- Do the tests pass?

If spec compliance is verified, output:
<verification>SPEC_COMPLIANCE_VERIFIED</verification>

If not, output:
<verification>NEEDS_RETRY: [reason]</verification>
"""
            else:
                # Stage 2: Quality check
                stage_prompt = current_prompt + """

## Verification Stage 2: Code Quality

Spec compliance is verified. Now check CODE QUALITY:
- Is the code well-organized?
- Is error handling complete?
- Are there any obvious improvements?

If quality is acceptable, output:
<verification>QUALITY_VERIFIED</verification>

If not, output:
<verification>NEEDS_RETRY: [reason]</verification>
"""

            success = run_cli(
                args.model, stage_prompt, cwd, iteration_log_path,
                args.session_dir, args.agent_id
            )

            # Append summary to loop log
            with open(loop_log_path, "a") as f:
                f.write(f"--- Iteration {iterations} (Stage: {stage}) ---\n")
                f.write(f"Log: {iteration_log_path}\n")
                f.write(f"Status: {'success' if success else 'cli_error'}\n\n")

            if not success:
                if state:
                    update_iteration(state, 1, False, "CLI returned non-zero exit code")
                    save_state(state)
                status = "cli_error"
                break

            verification_status, reason = check_two_stage_verification(iteration_log_path)

            # Update loop log with verification result
            with open(loop_log_path, "a") as f:
                f.write(f"Verification: {verification_status}\n")
                if reason:
                    f.write(f"Reason: {reason}\n")
                f.write("\n")

            # Update state with iteration results
            if state:
                marker_found = verification_status in ("stage1_complete", "stage2_complete")
                update_iteration(state, 0, marker_found, reason)

                log_content = iteration_log_path.read_text()
                next_steps = extract_next_steps(log_content)
                if next_steps:
                    state["suggested_next_steps"] = next_steps

                save_state(state)

            if verification_status == "stage2_complete":
                stages_completed = ["spec", "quality"]
                status = "success"
                break
            if verification_status == "stage1_complete":
                stages_completed = ["spec"]
                stage = "quality"  # Proceed to stage 2
                continue
            if verification_status in ("stage1_retry", "stage2_retry"):
                current_prompt = build_retry_prompt(original_prompt, iteration_log_path, reason)
                continue
            if verification_status == "no_marker":
                status = "no_verification_marker"
                break

            status = f"verification_failed:{verification_status}"
            break

    # Standard verification loop (non-two-stage)
    elif args.loop:
        while iterations < args.max_iterations:
            iterations += 1

            # Determine log path for this iteration
            iteration_log_path = get_iteration_log_path(log_dir, prompt_id, iterations, execution_timestamp)
            iteration_logs.append(str(iteration_log_path.absolute()))

            success = run_cli(
                args.model, current_prompt, cwd, iteration_log_path,
                args.session_dir, args.agent_id
            )

            # Append summary to loop log
            with open(loop_log_path, "a") as f:
                f.write(f"--- Iteration {iterations} ---\n")
                f.write(f"Log: {iteration_log_path}\n")
                f.write(f"Status: {'success' if success else 'cli_error'}\n\n")

            if not success:
                # Update state on CLI error
                if state:
                    update_iteration(state, 1, False, "CLI returned non-zero exit code")
                    save_state(state)
                status = "cli_error"
                break

            verification_status, reason = check_verification(iteration_log_path)

            # Update loop log with verification result
            with open(loop_log_path, "a") as f:
                f.write(f"Verification: {verification_status}\n")
                if reason:
                    f.write(f"Reason: {reason}\n")
                f.write("\n")

            # Update state with iteration results
            if state:
                marker_found = verification_status == "complete"
                update_iteration(state, 0, marker_found, reason)

                # Extract next steps from iteration log
                log_content = iteration_log_path.read_text()
                next_steps = extract_next_steps(log_content)
                if next_steps:
                    state["suggested_next_steps"] = next_steps

                save_state(state)

            if verification_status == "complete":
                status = "success"
                break

            if verification_status == "retry" and iterations < args.max_iterations:
                current_prompt = build_retry_prompt(original_prompt, iteration_log_path, reason)
                status = "retrying"
                continue

            if verification_status == "no_marker":
                status = "no_verification_marker"
                break

            status = f"verification_failed:{verification_status}"
            break

    # Non-loop mode: single execution
    else:
        iteration_log_path = log_path
        success = run_cli(
            args.model, current_prompt, cwd, iteration_log_path,
            args.session_dir, args.agent_id
        )
        iterations = 1
        status = "success" if success else "cli_error"

    # Finalize loop log
    if args.loop:
        with open(loop_log_path, "a") as f:
            f.write(f"=== Loop finished at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            f.write(f"Final status: {status}\n")
            f.write(f"Total iterations: {iterations}\n")

    # Update final state
    if state:
        state["status"] = status
        save_state(state)

    # Build result JSON
    result = {
        "status": status,
        "iterations": iterations,
    }

    if args.loop:
        result["loop_log"] = str(loop_log_path.absolute())
        result["iteration_logs"] = iteration_logs
        result["log_path"] = str(loop_log_path.absolute())  # Primary log is the loop log
        result["state_file"] = str(get_state_file(cwd, prompt_id).absolute())
    else:
        result["log_path"] = str(log_path.absolute())

    # Add two-stage information if enabled
    if args.two_stage:
        result["two_stage"] = True
        result["stages_completed"] = stages_completed

    print(json.dumps(result))
    sys.exit(0 if status == "success" else 1)


if __name__ == "__main__":
    main()
