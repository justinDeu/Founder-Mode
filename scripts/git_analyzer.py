#!/usr/bin/env python3
"""Git history analyzer for development velocity metrics.

Analyzes git history to extract development velocity metrics, active branches,
recent commit patterns, and contributor activity. Provides the foundation for
understanding "where the codebase is going" by extracting quantifiable signals.
"""

import argparse
import json
import subprocess
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


# Git log format: full_hash|short_hash|author|date|subject
GIT_LOG_FORMAT = "%H|%h|%an|%aI|%s"


def run_git_command(
    args: list[str],
    cwd: Optional[str] = None,
    check: bool = True
) -> subprocess.CompletedProcess:
    """Run a git command with proper error handling.

    Args:
        args: Git command arguments (without 'git' prefix)
        cwd: Working directory for the command
        check: Whether to raise on non-zero exit

    Returns:
        CompletedProcess result

    Raises:
        subprocess.CalledProcessError: If check=True and command fails
    """
    cmd = ["git"] + args
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check
    )


def get_repo_root(cwd: Optional[str] = None) -> str:
    """Get the repository root directory.

    Works with both standard and bare repositories.

    Args:
        cwd: Working directory (defaults to current)

    Returns:
        Path to repository root
    """
    result = run_git_command(["rev-parse", "--show-toplevel"], cwd=cwd, check=False)
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()

    # Try git-dir for bare repos
    result = run_git_command(["rev-parse", "--git-dir"], cwd=cwd)
    git_dir = result.stdout.strip()
    if git_dir == ".":
        return str(Path(cwd or ".").resolve())
    return str(Path(git_dir).parent.resolve())


def get_default_branch(cwd: Optional[str] = None) -> str:
    """Detect the default branch (main or master).

    Args:
        cwd: Working directory

    Returns:
        Name of default branch
    """
    # Check for origin/main first
    result = run_git_command(
        ["rev-parse", "--verify", "--quiet", "origin/main"],
        cwd=cwd,
        check=False
    )
    if result.returncode == 0:
        return "main"

    # Check for origin/master
    result = run_git_command(
        ["rev-parse", "--verify", "--quiet", "origin/master"],
        cwd=cwd,
        check=False
    )
    if result.returncode == 0:
        return "master"

    # Check local main
    result = run_git_command(
        ["rev-parse", "--verify", "--quiet", "main"],
        cwd=cwd,
        check=False
    )
    if result.returncode == 0:
        return "main"

    # Fall back to master
    return "master"


def parse_commit_line(line: str) -> Optional[dict]:
    """Parse a single commit line from git log output.

    Args:
        line: Pipe-delimited commit line

    Returns:
        Parsed commit dict or None if invalid
    """
    parts = line.strip().split("|", 4)
    if len(parts) < 5:
        return None

    full_hash, short_hash, author, date, subject = parts
    return {
        "hash": short_hash,
        "full_hash": full_hash,
        "author": author,
        "date": date,
        "message": subject,
    }


def get_recent_commits(days: int = 30, cwd: Optional[str] = None) -> list[dict]:
    """Return commits from the last N days.

    Args:
        days: Number of days to look back
        cwd: Working directory

    Returns:
        List of commit dicts with hash, author, date, message, files_changed,
        insertions, and deletions
    """
    since_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # Get basic commit info
    result = run_git_command(
        ["log", f"--since={since_date}", f"--format={GIT_LOG_FORMAT}"],
        cwd=cwd,
        check=False
    )

    if result.returncode != 0 or not result.stdout.strip():
        return []

    commits = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        commit = parse_commit_line(line)
        if commit:
            commits.append(commit)

    # Get stats for each commit (batch for efficiency)
    if commits:
        result = run_git_command(
            ["log", f"--since={since_date}", "--format=%H", "--numstat"],
            cwd=cwd,
            check=False
        )

        if result.returncode == 0:
            stats = parse_numstat_output(result.stdout)
            for commit in commits:
                commit_stats = stats.get(commit["full_hash"], {})
                commit["files_changed"] = commit_stats.get("files_changed", 0)
                commit["insertions"] = commit_stats.get("insertions", 0)
                commit["deletions"] = commit_stats.get("deletions", 0)
                # Remove full_hash from output
                del commit["full_hash"]

    return commits


def parse_numstat_output(output: str) -> dict[str, dict]:
    """Parse git log --numstat output into per-commit stats.

    Args:
        output: Raw numstat output

    Returns:
        Dict mapping commit hash to stats dict
    """
    stats = {}
    current_hash = None
    current_stats = {"files_changed": 0, "insertions": 0, "deletions": 0}

    for line in output.split("\n"):
        line = line.strip()
        if not line:
            continue

        # Check if this is a commit hash (40 hex chars)
        if len(line) == 40 and all(c in "0123456789abcdef" for c in line):
            if current_hash:
                stats[current_hash] = current_stats
            current_hash = line
            current_stats = {"files_changed": 0, "insertions": 0, "deletions": 0}
        elif current_hash and "\t" in line:
            # This is a numstat line: insertions\tdeletions\tfilename
            parts = line.split("\t")
            if len(parts) >= 2:
                try:
                    ins = int(parts[0]) if parts[0] != "-" else 0
                    dels = int(parts[1]) if parts[1] != "-" else 0
                    current_stats["files_changed"] += 1
                    current_stats["insertions"] += ins
                    current_stats["deletions"] += dels
                except ValueError:
                    pass

    if current_hash:
        stats[current_hash] = current_stats

    return stats


def get_active_branches(cwd: Optional[str] = None) -> list[dict]:
    """Return branches with recent activity.

    Args:
        cwd: Working directory

    Returns:
        List of branch dicts with name, last_commit_date, last_commit_message,
        ahead_behind_main, and is_current
    """
    # Get current branch
    result = run_git_command(["branch", "--show-current"], cwd=cwd, check=False)
    current_branch = result.stdout.strip() if result.returncode == 0 else ""

    # Get all branches with their last commit info
    result = run_git_command(
        ["branch", "-a", "--format=%(refname:short)|%(committerdate:iso8601)|%(subject)"],
        cwd=cwd,
        check=False
    )

    if result.returncode != 0 or not result.stdout.strip():
        return []

    default_branch = get_default_branch(cwd)
    branches = []

    for line in result.stdout.strip().split("\n"):
        if not line:
            continue

        parts = line.split("|", 2)
        if len(parts) < 3:
            continue

        name, date_str, message = parts

        # Skip remote tracking branches that duplicate local ones
        if name.startswith("origin/") and name[7:] in [b["name"] for b in branches]:
            continue

        # Get ahead/behind count relative to default branch
        ahead_behind = (0, 0)
        if name != default_branch and not name.startswith("origin/"):
            result = run_git_command(
                ["rev-list", "--left-right", "--count", f"{default_branch}...{name}"],
                cwd=cwd,
                check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                try:
                    behind, ahead = result.stdout.strip().split("\t")
                    ahead_behind = (int(ahead), int(behind))
                except ValueError:
                    pass

        branches.append({
            "name": name,
            "last_commit_date": date_str.strip(),
            "last_commit_message": message.strip(),
            "ahead_behind_main": ahead_behind,
            "is_current": name == current_branch,
        })

    # Sort by date (most recent first)
    branches.sort(key=lambda b: b["last_commit_date"], reverse=True)

    return branches


def get_velocity_metrics(days: int = 30, cwd: Optional[str] = None) -> dict:
    """Calculate development velocity metrics.

    Args:
        days: Number of days to analyze
        cwd: Working directory

    Returns:
        Dict with commits_per_day, lines_changed_per_day, active_contributors,
        most_active_files, commit_frequency_by_hour, commit_frequency_by_day
    """
    commits = get_recent_commits(days=days, cwd=cwd)

    if not commits:
        return {
            "commits_per_day": 0.0,
            "lines_changed_per_day": 0.0,
            "active_contributors": 0,
            "most_active_files": [],
            "commit_frequency_by_hour": {},
            "commit_frequency_by_day": {},
        }

    # Calculate basic metrics
    total_commits = len(commits)
    total_insertions = sum(c.get("insertions", 0) for c in commits)
    total_deletions = sum(c.get("deletions", 0) for c in commits)
    total_lines = total_insertions + total_deletions

    # Unique contributors
    contributors = set(c["author"] for c in commits)

    # Commit frequency by hour and day
    hour_counts: Counter = Counter()
    day_counts: Counter = Counter()

    for commit in commits:
        try:
            dt = datetime.fromisoformat(commit["date"].replace("Z", "+00:00"))
            hour_counts[dt.hour] += 1
            day_counts[dt.strftime("%A")] += 1
        except (ValueError, KeyError):
            pass

    # Most active files
    since_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    result = run_git_command(
        ["log", f"--since={since_date}", "--format=", "--name-only"],
        cwd=cwd,
        check=False
    )

    file_counts: Counter = Counter()
    if result.returncode == 0 and result.stdout.strip():
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                file_counts[line.strip()] += 1

    most_active = [
        {"file": f, "changes": c}
        for f, c in file_counts.most_common(10)
    ]

    return {
        "commits_per_day": round(total_commits / days, 2),
        "lines_changed_per_day": round(total_lines / days, 2),
        "active_contributors": len(contributors),
        "most_active_files": most_active,
        "commit_frequency_by_hour": dict(hour_counts),
        "commit_frequency_by_day": dict(day_counts),
    }


def get_work_in_progress(cwd: Optional[str] = None) -> list[dict]:
    """Identify work-in-progress indicators.

    Args:
        cwd: Working directory

    Returns:
        List of WIP indicators including branches with wip/draft/temp names,
        recent stashes, and uncommitted changes summary
    """
    wip_items = []

    # Check for WIP branches
    wip_keywords = ["wip", "draft", "temp", "tmp", "test", "experiment"]
    result = run_git_command(
        ["branch", "--format=%(refname:short)"],
        cwd=cwd,
        check=False
    )

    if result.returncode == 0 and result.stdout.strip():
        for branch in result.stdout.strip().split("\n"):
            branch_lower = branch.lower()
            for keyword in wip_keywords:
                if keyword in branch_lower:
                    wip_items.append({
                        "type": "branch",
                        "name": branch,
                        "indicator": keyword,
                    })
                    break

    # Check for stashes
    result = run_git_command(["stash", "list"], cwd=cwd, check=False)
    if result.returncode == 0 and result.stdout.strip():
        stashes = result.stdout.strip().split("\n")
        for stash in stashes[:5]:  # Limit to 5 most recent
            wip_items.append({
                "type": "stash",
                "name": stash.split(":")[0] if ":" in stash else stash,
                "message": stash.split(":", 2)[-1].strip() if ":" in stash else "",
            })

    # Check for uncommitted changes
    result = run_git_command(["status", "--porcelain"], cwd=cwd, check=False)
    if result.returncode == 0 and result.stdout.strip():
        changes = result.stdout.strip().split("\n")
        staged = sum(1 for c in changes if c and c[0] in "MADRCU")
        unstaged = sum(1 for c in changes if c and len(c) > 1 and c[1] in "MADRCU")
        untracked = sum(1 for c in changes if c and c.startswith("??"))

        if staged or unstaged or untracked:
            wip_items.append({
                "type": "uncommitted",
                "staged_files": staged,
                "unstaged_files": unstaged,
                "untracked_files": untracked,
            })

    return wip_items


def analyze_repository(days: int = 30, cwd: Optional[str] = None) -> dict:
    """Run full repository analysis.

    Args:
        days: Analysis window in days
        cwd: Working directory

    Returns:
        Complete analysis dict with all metrics
    """
    repo_root = get_repo_root(cwd)

    return {
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        "repository": repo_root,
        "velocity": get_velocity_metrics(days=days, cwd=cwd),
        "recent_commits": get_recent_commits(days=days, cwd=cwd),
        "active_branches": get_active_branches(cwd=cwd),
        "work_in_progress": get_work_in_progress(cwd=cwd),
    }


def format_summary(analysis: dict) -> str:
    """Format analysis as human-readable summary.

    Args:
        analysis: Analysis dict from analyze_repository

    Returns:
        Formatted string summary
    """
    lines = []
    lines.append(f"Repository: {analysis['repository']}")
    lines.append(f"Analysis Time: {analysis['analysis_timestamp']}")
    lines.append("")

    # Velocity section
    v = analysis["velocity"]
    lines.append("=== Velocity Metrics ===")
    lines.append(f"  Commits per day: {v['commits_per_day']}")
    lines.append(f"  Lines changed per day: {v['lines_changed_per_day']}")
    lines.append(f"  Active contributors: {v['active_contributors']}")
    lines.append("")

    if v["most_active_files"]:
        lines.append("  Most active files:")
        for f in v["most_active_files"][:5]:
            lines.append(f"    - {f['file']} ({f['changes']} changes)")
        lines.append("")

    # Recent commits section
    commits = analysis["recent_commits"]
    lines.append(f"=== Recent Commits ({len(commits)} total) ===")
    for c in commits[:10]:
        lines.append(f"  {c['hash']} - {c['author']}: {c['message'][:60]}")
    if len(commits) > 10:
        lines.append(f"  ... and {len(commits) - 10} more")
    lines.append("")

    # Branches section
    branches = analysis["active_branches"]
    lines.append(f"=== Active Branches ({len(branches)} total) ===")
    for b in branches[:10]:
        current = "*" if b["is_current"] else " "
        ahead, behind = b["ahead_behind_main"]
        ahead_behind_str = f"+{ahead}/-{behind}" if ahead or behind else ""
        lines.append(f"  {current} {b['name']} {ahead_behind_str}")
    lines.append("")

    # WIP section
    wip = analysis["work_in_progress"]
    if wip:
        lines.append("=== Work In Progress ===")
        for item in wip:
            if item["type"] == "branch":
                lines.append(f"  Branch: {item['name']} (contains '{item['indicator']}')")
            elif item["type"] == "stash":
                lines.append(f"  Stash: {item['name']} - {item['message']}")
            elif item["type"] == "uncommitted":
                lines.append(
                    f"  Uncommitted: {item['staged_files']} staged, "
                    f"{item['unstaged_files']} unstaged, "
                    f"{item['untracked_files']} untracked"
                )
        lines.append("")

    return "\n".join(lines)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze git history for development velocity metrics"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Analysis window in days (default: 30)"
    )
    parser.add_argument(
        "--output",
        choices=["json", "summary"],
        default="json",
        help="Output format (default: json)"
    )
    parser.add_argument(
        "--cwd",
        type=str,
        default=None,
        help="Working directory (default: current)"
    )

    args = parser.parse_args()

    try:
        analysis = analyze_repository(days=args.days, cwd=args.cwd)

        if args.output == "json":
            print(json.dumps(analysis, indent=2))
        else:
            print(format_summary(analysis))

    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {e.stderr}", file=__import__("sys").stderr)
        raise SystemExit(1)
    except Exception as e:
        print(f"Analysis failed: {e}", file=__import__("sys").stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
