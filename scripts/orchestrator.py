#!/usr/bin/env python3
"""Parse orchestrator files and calculate execution waves."""

import argparse
import json
import re
import sys
from pathlib import Path


def parse_dependency_graph(content: str) -> dict[str, list[str]]:
    """Extract dependency graph from orchestrator markdown.

    Looks for patterns like:
        003-01 (state-management)
            |
            v
        003-02 (new-project)

    Returns dict mapping prompt_id -> list of dependency prompt_ids
    """
    deps: dict[str, list[str]] = {}

    # Find the dependency graph section
    graph_match = re.search(
        r"##\s*Dependency Graph\s*```(.*?)```",
        content,
        re.DOTALL | re.IGNORECASE
    )

    if not graph_match:
        return deps

    graph_text = graph_match.group(1)

    # Extract all prompt IDs (pattern: NNN-NN)
    prompt_ids = re.findall(r"\b(\d{3}-\d{2})\b", graph_text)

    # Initialize all prompts with empty deps
    for pid in prompt_ids:
        if pid not in deps:
            deps[pid] = []

    # Parse arrows to find dependencies
    # Look for patterns like "003-01\n    |\n    v\n003-02"
    lines = graph_text.split("\n")
    current_source = None

    for i, line in enumerate(lines):
        # Check if line contains a prompt ID
        match = re.search(r"\b(\d{3}-\d{2})\b", line)
        if match:
            pid = match.group(1)
            if current_source and current_source != pid:
                # This prompt depends on current_source
                if pid not in deps:
                    deps[pid] = []
                if current_source not in deps[pid]:
                    deps[pid].append(current_source)
            current_source = pid
        elif "|" in line or "v" in line.lower():
            # Arrow indicator, keep current_source
            pass
        elif line.strip() == "":
            # Empty line might reset context in some formats
            pass

    return deps


def parse_execution_order(content: str) -> list[dict]:
    """Extract execution order from orchestrator markdown.

    Looks for patterns like:
        ### Wave 1: Foundation
        1. `003-01-state-management.md` - Description
        2. `003-02-new-project.md` - Description

    Returns list of {wave: N, prompts: [ids]}
    """
    waves = []

    # Find wave sections
    wave_pattern = re.compile(
        r"###\s*Wave\s*(\d+)[:\s]*(.*?)\n(.*?)(?=###|\Z)",
        re.DOTALL | re.IGNORECASE
    )

    for match in wave_pattern.finditer(content):
        wave_num = int(match.group(1))
        wave_name = match.group(2).strip()
        wave_content = match.group(3)

        # Extract prompt IDs from this wave
        prompt_ids = re.findall(r"`(\d{3}-\d{2})[^`]*\.md`", wave_content)

        if prompt_ids:
            waves.append({
                "wave": wave_num,
                "name": wave_name,
                "prompts": prompt_ids
            })

    return waves


def parse_state_tracking(content: str) -> dict[str, bool]:
    """Extract completion state from orchestrator.

    Looks for:
        [x] 003-01-state-management.md
        [ ] 003-02-new-project.md

    Returns dict mapping prompt_id -> completed (bool)
    """
    state = {}

    # Match checkbox patterns
    pattern = re.compile(r"\[([xX ])\]\s*`?(\d{3}-\d{2})[^`\n]*\.md`?")

    for match in pattern.finditer(content):
        completed = match.group(1).lower() == "x"
        prompt_id = match.group(2)
        state[prompt_id] = completed

    return state


def calculate_waves(deps: dict[str, list[str]]) -> list[list[str]]:
    """Group prompts into dependency waves.

    Wave N contains prompts whose dependencies are all in waves < N.
    """
    if not deps:
        return []

    waves = []
    remaining = set(deps.keys())
    completed = set()

    while remaining:
        # Find all prompts whose deps are satisfied
        ready = [p for p in remaining if all(d in completed for d in deps[p])]

        if not ready:
            # Circular dependency or missing deps
            raise ValueError(
                f"Cannot resolve dependencies. Remaining: {remaining}, "
                f"Completed: {completed}"
            )

        waves.append(sorted(ready))
        completed.update(ready)
        remaining -= set(ready)

    return waves


def resolve_prompt_path(prompt_id: str, prompts_dir: Path) -> dict | None:
    """Find the prompt file for a given ID.

    Searches for files matching pattern: {prompt_id}-*.md
    """
    # Search in prompts_dir and subdirectories
    patterns = [
        f"{prompt_id}-*.md",
        f"**/{prompt_id}-*.md"
    ]

    for pattern in patterns:
        matches = list(prompts_dir.glob(pattern))
        if matches:
            path = matches[0]
            # Extract title from filename
            name = path.stem
            title_part = name[len(prompt_id):].lstrip("-")
            title = title_part.replace("-", " ").title()

            return {
                "id": prompt_id,
                "path": str(path.absolute()),
                "filename": path.name,
                "title": title or prompt_id
            }

    return None


def parse_orchestrator(file_path: Path, prompts_dir: Path) -> dict:
    """Parse an orchestrator file and return execution plan."""
    content = file_path.read_text()

    # Parse dependency graph
    deps = parse_dependency_graph(content)

    # If no deps found, try to get execution order directly
    if not deps:
        waves_from_doc = parse_execution_order(content)
        if waves_from_doc:
            # Build deps from wave order
            all_prior = []
            for wave_info in waves_from_doc:
                for pid in wave_info["prompts"]:
                    deps[pid] = list(all_prior)
                all_prior.extend(wave_info["prompts"])

    # Calculate waves
    waves = calculate_waves(deps) if deps else []

    # Get completion state
    state = parse_state_tracking(content)

    # Resolve all prompt paths
    prompts = {}
    for prompt_id in deps.keys():
        resolved = resolve_prompt_path(prompt_id, prompts_dir)
        if resolved:
            prompts[prompt_id] = resolved
            prompts[prompt_id]["completed"] = state.get(prompt_id, False)
            prompts[prompt_id]["dependencies"] = deps.get(prompt_id, [])

    return {
        "orchestrator": str(file_path.absolute()),
        "dependencies": deps,
        "waves": waves,
        "prompts": prompts,
        "state": state
    }


def parse_prompt_list(prompt_list: str, prompts_dir: Path) -> dict:
    """Parse a comma-separated prompt list (no dependencies)."""
    ids = [p.strip() for p in prompt_list.split(",") if p.strip()]

    prompts = {}
    for prompt_id in ids:
        resolved = resolve_prompt_path(prompt_id, prompts_dir)
        if resolved:
            prompts[prompt_id] = resolved
            prompts[prompt_id]["completed"] = False
            prompts[prompt_id]["dependencies"] = []

    # All prompts in single wave (no deps)
    waves = [list(prompts.keys())] if prompts else []

    return {
        "orchestrator": None,
        "dependencies": {pid: [] for pid in prompts.keys()},
        "waves": waves,
        "prompts": prompts,
        "state": {}
    }


def is_file_path_input(prompt_input: str) -> bool:
    """Detect if input looks like file paths rather than prompt IDs.

    File paths contain '/' or end with '.md'.
    Prompt IDs follow pattern like '003-01' with no path separators.
    """
    items = [p.strip() for p in prompt_input.split(",") if p.strip()]
    return any("/" in item or item.endswith(".md") for item in items)


def extract_prompt_id_from_path(file_path: str) -> str:
    """Extract prompt ID from a file path.

    Examples:
        gh-9-test-issue.md -> gh-9
        003-01-state-management.md -> 003-01
        some-file.md -> some-file (fallback to stem)
    """
    path = Path(file_path)
    stem = path.stem

    # Try gh-N pattern (github issues)
    gh_match = re.match(r"^(gh-\d+)", stem)
    if gh_match:
        return gh_match.group(1)

    # Try NNN-NN pattern (standard prompts)
    std_match = re.match(r"^(\d{3}-\d{2})", stem)
    if std_match:
        return std_match.group(1)

    # Fallback to full stem
    return stem


def resolve_file_path(file_path: str) -> dict | None:
    """Resolve a file path directly to prompt metadata.

    Unlike resolve_prompt_path which searches by ID, this uses the path as-is.
    """
    path = Path(file_path)
    if not path.exists():
        return None

    prompt_id = extract_prompt_id_from_path(file_path)

    # Extract title from filename
    stem = path.stem
    # Remove the ID prefix to get the title part
    if stem.startswith(prompt_id):
        title_part = stem[len(prompt_id):].lstrip("-")
    else:
        title_part = stem
    title = title_part.replace("-", " ").title() or prompt_id

    return {
        "id": prompt_id,
        "path": str(path.absolute()),
        "filename": path.name,
        "title": title
    }


def parse_file_path_list(prompt_list: str) -> dict:
    """Parse comma-separated file paths (no dependencies).

    Similar to parse_prompt_list but uses paths directly instead of ID resolution.
    """
    paths = [p.strip() for p in prompt_list.split(",") if p.strip()]

    prompts = {}
    for file_path in paths:
        resolved = resolve_file_path(file_path)
        if resolved:
            prompt_id = resolved["id"]
            prompts[prompt_id] = resolved
            prompts[prompt_id]["completed"] = False
            prompts[prompt_id]["dependencies"] = []

    # All prompts in single wave (no deps)
    waves = [list(prompts.keys())] if prompts else []

    return {
        "orchestrator": None,
        "dependencies": {pid: [] for pid in prompts.keys()},
        "waves": waves,
        "prompts": prompts,
        "state": {}
    }


def main():
    parser = argparse.ArgumentParser(description="Parse orchestrator files")
    parser.add_argument("input", help="Orchestrator file path or comma-separated prompt list")
    parser.add_argument("--prompts-dir", default="./prompts",
                        help="Directory containing prompt files")
    parser.add_argument("--pending-only", action="store_true",
                        help="Only include prompts not marked complete")

    args = parser.parse_args()
    prompts_dir = Path(args.prompts_dir)

    input_path = Path(args.input)

    if input_path.exists() and input_path.suffix == ".md":
        # Parse orchestrator file
        result = parse_orchestrator(input_path, prompts_dir)
    elif is_file_path_input(args.input):
        # Input contains file paths - use them directly
        result = parse_file_path_list(args.input)
    else:
        # Treat as comma-separated prompt IDs
        result = parse_prompt_list(args.input, prompts_dir)

    # Filter to pending only if requested
    if args.pending_only:
        pending_ids = {pid for pid, info in result["prompts"].items()
                       if not info.get("completed", False)}
        result["prompts"] = {pid: info for pid, info in result["prompts"].items()
                            if pid in pending_ids}
        result["waves"] = [[pid for pid in wave if pid in pending_ids]
                          for wave in result["waves"]]
        result["waves"] = [w for w in result["waves"] if w]  # Remove empty waves

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
