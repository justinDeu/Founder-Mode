#!/usr/bin/env python3
"""Validate orchestrator YAML workflow configs.

This validator checks YAML structure and DAG constraints.
It does NOT execute workflows or generate execution plans.
"""

import argparse
import sys
from pathlib import Path
from difflib import get_close_matches

# Check for PyYAML
try:
    import yaml
except ImportError:
    print(
        "ERROR: PyYAML is not installed.\n"
        "Install it with: pip install pyyaml\n"
        "Or run: pip install -r requirements.txt",
        file=sys.stderr
    )
    sys.exit(1)


# Schema constants
ALLOWED_WORKFLOW_KEYS = {"base", "branch", "on_complete", "prompts"}
ALLOWED_ON_COMPLETE_KEYS = {"create_pr", "merge_to", "delete_worktree"}
ALLOWED_PROMPT_KEYS = {"path", "after", "model"}
ALLOWED_MODELS = {
    "claude", "codex", "gemini", "zai",
    "opencode", "opencode-zai", "opencode-codex", "claude-zai"
}


class ValidationError:
    """Collect validation errors with context."""

    def __init__(self):
        self.errors = []

    def add(self, message):
        self.errors.append(message)

    def has_errors(self):
        return len(self.errors) > 0

    def print(self):
        if not self.has_errors():
            return

        print("VALIDATION FAILED:", file=sys.stderr)
        for error in self.errors:
            print(f"  - {error}", file=sys.stderr)


def suggest_correction(field, allowed):
    """Suggest correction for unknown field using difflib."""
    matches = get_close_matches(field, allowed, n=1, cutoff=0.6)
    if matches:
        return f" (did you mean '{matches[0]}'?)"
    return ""


def validate_on_complete(on_complete, path, errors):
    """Validate on_complete section."""
    if on_complete is None:
        return

    if not isinstance(on_complete, dict):
        errors.add(f"{path} must be a map, got {type(on_complete).__name__}")
        return

    # Check for unknown keys
    for key in on_complete:
        if key not in ALLOWED_ON_COMPLETE_KEYS:
            allowed_str = ", ".join(sorted(ALLOWED_ON_COMPLETE_KEYS))
            suggestion = suggest_correction(key, ALLOWED_ON_COMPLETE_KEYS)
            errors.add(f"Unknown field '{path}.{key}'{suggestion} (allowed: {allowed_str})")

    # Check mutual exclusivity
    if on_complete.get("create_pr") and on_complete.get("merge_to"):
        errors.add(
            f"Cannot specify both 'create_pr' and 'merge_to' in {path}. "
            "These options are mutually exclusive."
        )

    # Validate types
    if "create_pr" in on_complete and not isinstance(on_complete["create_pr"], bool):
        errors.add(f"{path}.create_pr must be boolean")

    if "merge_to" in on_complete:
        merge_to = on_complete["merge_to"]
        if not isinstance(merge_to, str) or not merge_to.strip():
            errors.add(f"{path}.merge_to must be non-empty string")

    if "delete_worktree" in on_complete and not isinstance(on_complete["delete_worktree"], bool):
        errors.add(f"{path}.delete_worktree must be boolean")


def validate_prompt(prompt_id, prompt, workflow_id, all_prompt_ids, errors):
    """Validate a single prompt configuration."""
    prefix = f"workflows.{workflow_id}.prompts.{prompt_id}"

    # Check for unknown keys
    for key in prompt:
        if key not in ALLOWED_PROMPT_KEYS:
            allowed_str = ", ".join(sorted(ALLOWED_PROMPT_KEYS))
            suggestion = suggest_correction(key, ALLOWED_PROMPT_KEYS)
            errors.add(f"Unknown field '{prefix}.{key}'{suggestion} (allowed: {allowed_str})")

    # Validate required fields
    if "path" not in prompt:
        errors.add(f"{prefix} is missing required field 'path'")
        return

    # Validate path
    path = prompt["path"]
    if not isinstance(path, str) or not path.strip():
        errors.add(f"{prefix}.path must be non-empty string")
    else:
        # Check if file exists (relative to current directory)
        file_path = Path(path)
        if not file_path.exists():
            errors.add(f"Prompt path does not exist: {path}")

    # Validate after
    if "after" in prompt:
        after = prompt["after"]
        if not isinstance(after, list):
            errors.add(f"{prefix}.after must be a list")
        else:
            for dep in after:
                if not isinstance(dep, str):
                    errors.add(f"{prefix}.after must contain only strings")
                elif dep not in all_prompt_ids:
                    errors.add(
                        f"Invalid reference in {prefix}.after: '{dep}' not found "
                        f"in prompts for workflow '{workflow_id}'"
                    )

    # Validate model
    if "model" in prompt:
        model = prompt["model"]
        if not isinstance(model, str):
            errors.add(f"{prefix}.model must be a string")
        elif model not in ALLOWED_MODELS:
            allowed_str = ", ".join(sorted(ALLOWED_MODELS))
            errors.add(
                f"Invalid model '{model}' in {prefix} (allowed: {allowed_str})"
            )


def validate_dag(workflow_id, prompts, errors):
    """Validate DAG constraints: single sink, no cycles, all connected."""
    prefix = f"workflows.{workflow_id}.prompts"

    if not prompts:
        errors.add(f"{prefix} cannot be empty")
        return

    prompt_ids = set(prompts.keys())

    # Build dependency graph
    deps = {pid: set(prompts[pid].get("after", [])) for pid in prompts}
    # Filter out any invalid deps (already reported in validate_prompt)
    for pid in deps:
        deps[pid] = {d for d in deps[pid] if d in prompt_ids}

    # Build reverse graph (who depends on me)
    dependents = {pid: set() for pid in prompts}
    for pid, dep_list in deps.items():
        for dep in dep_list:
            dependents[dep].add(pid)

    # Find sinks (nodes with no dependents)
    sinks = {pid for pid in prompts if not dependents[pid]}

    if len(sinks) == 0:
        errors.add(f"No sink found in {prefix}. Every prompt has a dependent (cycle?).")
    elif len(sinks) > 1:
        sinks_str = ", ".join(sorted(sinks))
        errors.add(
            f"Multiple sinks found: {{{sinks_str}}}. "
            f"DAG must converge to single sink."
        )

    # Check for cycles using DFS
    def has_cycle(node, visited, rec_stack):
        visited.add(node)
        rec_stack.add(node)

        for neighbor in deps.get(node, []):
            if neighbor not in visited:
                if has_cycle(neighbor, visited, rec_stack):
                    return True
            elif neighbor in rec_stack:
                return True

        rec_stack.remove(node)
        return False

    visited = set()
    for node in prompts:
        if node not in visited:
            if has_cycle(node, set(), set()):
                errors.add(f"Cycle detected in dependency graph for workflow '{workflow_id}'")
                break

    # Check that all nodes can reach the sink
    if len(sinks) == 1:
        sink = sinks.pop()

        def can_reach_sink(node, visited):
            if node == sink:
                return True
            visited.add(node)

            for dependent in dependents.get(node, []):
                if dependent not in visited:
                    if can_reach_sink(dependent, visited):
                        return True
            return False

        for node in prompts:
            if not can_reach_sink(node, set()):
                errors.add(
                    f"Prompt '{node}' cannot reach the sink '{sink}'. "
                    f"All paths must converge to the sink."
                )


def validate_workflow(workflow_id, workflow, errors):
    """Validate a single workflow."""
    if not isinstance(workflow, dict):
        errors.add(f"workflows.{workflow_id} must be a map")
        return

    # Check for unknown keys
    for key in workflow:
        if key not in ALLOWED_WORKFLOW_KEYS:
            allowed_str = ", ".join(sorted(ALLOWED_WORKFLOW_KEYS))
            suggestion = suggest_correction(key, ALLOWED_WORKFLOW_KEYS)
            errors.add(
                f"Unknown field 'workflows.{workflow_id}.{key}'{suggestion} "
                f"(allowed: {allowed_str})"
            )

    # Validate required fields
    if "base" not in workflow:
        errors.add(f"workflows.{workflow_id} is missing required field 'base'")
    else:
        base = workflow["base"]
        if not isinstance(base, str) or not base.strip():
            errors.add(f"workflows.{workflow_id}.base must be non-empty string")

    if "branch" not in workflow:
        errors.add(f"workflows.{workflow_id} is missing required field 'branch'")
    else:
        branch = workflow["branch"]
        if not isinstance(branch, str) or not branch.strip():
            errors.add(f"workflows.{workflow_id}.branch must be non-empty string")

    # Validate on_complete
    validate_on_complete(
        workflow.get("on_complete"),
        f"workflows.{workflow_id}.on_complete",
        errors
    )

    # Validate prompts
    if "prompts" not in workflow:
        errors.add(f"workflows.{workflow_id} is missing required field 'prompts'")
        return

    prompts = workflow["prompts"]
    if not isinstance(prompts, dict) or not prompts:
        errors.add(f"workflows.{workflow_id}.prompts must be non-empty map")
        return

    # Validate each prompt
    prompt_ids = set(prompts.keys())
    for prompt_id, prompt in prompts.items():
        validate_prompt(prompt_id, prompt, workflow_id, prompt_ids, errors)

    # Validate DAG structure
    validate_dag(workflow_id, prompts, errors)


def validate_config(config):
    """Validate the entire YAML config."""
    errors = ValidationError()

    # Top-level must be 'workflows'
    if not isinstance(config, dict):
        errors.add("Config must be a map with 'workflows' key")
        return errors

    if "workflows" not in config:
        errors.add("Config is missing required key 'workflows'")
        return errors

    workflows = config["workflows"]
    if not isinstance(workflows, dict) or not workflows:
        errors.add("'workflows' must be a non-empty map")
        return errors

    # Check for unknown top-level keys
    for key in config:
        if key != "workflows":
            errors.add(f"Unknown field '{key}' at top level (only 'workflows' allowed)")

    # Validate each workflow
    for workflow_id in workflows:
        validate_workflow(workflow_id, workflows[workflow_id], errors)

    return errors


def main():
    parser = argparse.ArgumentParser(description="Validate orchestrator YAML configs")
    parser.add_argument("config", help="Path to YAML config file")
    args = parser.parse_args()

    config_path = Path(args.config)

    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    # Load YAML
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"ERROR: Failed to parse YAML: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to read file: {e}", file=sys.stderr)
        sys.exit(1)

    if config is None:
        print("ERROR: Config file is empty", file=sys.stderr)
        sys.exit(1)

    # Validate
    errors = validate_config(config)

    if errors.has_errors():
        errors.print()
        sys.exit(1)
    else:
        print("VALID")
        sys.exit(0)


if __name__ == "__main__":
    main()
