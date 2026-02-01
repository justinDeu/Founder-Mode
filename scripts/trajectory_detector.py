#!/usr/bin/env python3
"""Trajectory Detector for direction-analyzer.

Synthesizes git history and code pattern data to identify development trajectories:
what work is actively happening, what's stalled, and what patterns suggest next steps.

This is the "brain" that interprets raw data into meaningful patterns.
"""

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


# Import our analyzer modules
import sys
sys.path.insert(0, str(Path(__file__).parent))

try:
    from git_analyzer import (
        get_active_branches,
        get_recent_commits,
        get_velocity_metrics,
        get_work_in_progress,
    )
    from code_scanner import scan_todo_markers, scan_incomplete_implementations
except ImportError:
    # Fallback if run as standalone without proper path setup
    pass


# Branch naming patterns for feature detection
FEATURE_PATTERNS = [
    re.compile(r'^(feature|feat)[/-](.+)', re.IGNORECASE),
    re.compile(r'^(gh|github|issue)[/-]?(\d+)', re.IGNORECASE),
    re.compile(r'^(fix|bugfix)[/-](.+)', re.IGNORECASE),
    re.compile(r'^(refactor|refact)[/-](.+)', re.IGNORECASE),
    re.compile(r'^(wip|draft|tmp)[/-]?(.+)', re.IGNORECASE),
]

# Commit message patterns for WIP detection
WIP_INDICATORS = ['wip', 'work in progress', 'draft', 'temp', 'todo', 'temporary']
BLOCKER_INDICATORS = ['blocked', 'waiting for', 'depends on', 'needs', 'waiting on']
COMPLETION_INDICATORS = ['done', 'complete', 'finish', 'close', 'resolve', 'fix']

# Branches to ignore (bots, dependency updates, etc.)
IGNORE_BRANCHES = {
    'dependabot',
    'renovate',
    'pre-commit-ci',
    'transifex',
    'l10n',
    'i18n',
}


def extract_stream_name_from_branch(branch_name: str) -> Optional[str]:
    """Extract a meaningful stream name from a branch name.

    Args:
        branch_name: Branch name to analyze

    Returns:
        Inferred stream name or None
    """
    # Skip bot branches
    branch_lower = branch_name.lower()
    for ignore in IGNORE_BRANCHES:
        if ignore in branch_lower:
            return None

    for pattern in FEATURE_PATTERNS:
        match = pattern.match(branch_name)
        if match:
            # Return the captured group(s) after the type
            if match.lastindex:
                return '-'.join(match.groups()[1:]).replace('-', ' ').strip()

    # Fallback: use the branch name itself
    return branch_name.replace('-', ' ').replace('_', ' ').title()


def extract_stream_name_from_files(file_paths: list[str]) -> Optional[str]:
    """Infer a stream name from the files being modified.

    Args:
        file_paths: List of file paths

    Returns:
        Inferred stream name or None
    """
    if not file_paths:
        return None

    # Get common directory prefix
    dirs = [Path(f).parent for f in file_paths if f]
    if len(dirs) == 1:
        return str(dirs[0])

    # Find common prefix
    common = Path(dirs[0])
    for d in dirs[1:]:
        try:
            common = Path('/'.join(
                a for a, b in zip(common.parts, Path(d).parts) if a == b
            ))
        except (ValueError, StopIteration):
            return None

    if str(common) != '.':
        return str(common)

    return None


def cluster_files_by_directory(files: list[dict]) -> dict[str, list[str]]:
    """Cluster files by their directory paths.

    Args:
        files: List of file dicts with 'file' key

    Returns:
        Dict mapping directory path to list of files
    """
    clusters: dict[str, list[str]] = {}

    for item in files:
        file_path = item.get('file', '')
        if not file_path:
            continue

        dir_path = str(Path(file_path).parent)
        if dir_path not in clusters:
            clusters[dir_path] = []
        clusters[dir_path].append(file_path)

    return clusters


def detect_active_work_streams(
    git_data: dict,
    code_data: dict,
    days_threshold: int = 7
) -> list[dict]:
    """Identify active development areas.

    Combines branch activity, recent commits, and file changes to infer
    what features/areas are actively being developed.

    Args:
        git_data: Output from git_analyzer
        code_data: Output from code_scanner
        days_threshold: Days considered "recent"

    Returns:
        List of active work stream dicts
    """
    streams = []
    recent_commits = git_data.get('recent_commits', [])
    branches = git_data.get('active_branches', [])

    # Group commits by inferred stream
    commit_streams: dict[str, list[dict]] = {}

    # Process branches for stream names
    for branch in branches:
        branch_name = branch.get('name', '')
        if not branch_name or branch_name.startswith('origin/'):
            continue

        stream_name = extract_stream_name_from_branch(branch_name)
        if not stream_name:
            continue

        last_date_str = branch.get('last_commit_date', '')
        try:
            last_date = datetime.fromisoformat(last_date_str.replace('Z', '+00:00'))
            days_since = (datetime.now(timezone.utc) - last_date).days
        except (ValueError, AttributeError):
            continue

        if days_since <= days_threshold:
            if stream_name not in commit_streams:
                commit_streams[stream_name] = []
            commit_streams[stream_name].append({
                'type': 'branch',
                'name': branch_name,
                'date': last_date_str,
            })

    # Process commits by file patterns
    active_files = git_data.get('velocity', {}).get('most_active_files', [])
    file_clusters = cluster_files_by_directory(active_files)

    for cluster_dir, files in file_clusters.items():
        if cluster_dir in ('.', '', 'scripts'):
            continue

        stream_name = extract_stream_name_from_files(files)
        if stream_name:
            if stream_name not in commit_streams:
                commit_streams[stream_name] = []
            commit_streams[stream_name].extend([
                {'type': 'file', 'file': f} for f in files[:3]
            ])

    # Build stream objects
    for stream_name, items in commit_streams.items():
        # Count commits in this stream
        recent_commits_in_stream = []
        for commit in recent_commits:
            # Check if commit relates to this stream
            for item in items:
                if item.get('type') == 'file' and item.get('file') in str(commit.get('message', '')):
                    recent_commits_in_stream.append(commit)
                    break
                elif item.get('type') == 'branch' and item.get('name') in str(commit.get('message', '')):
                    recent_commits_in_stream.append(commit)
                    break

        # Get contributors
        contributors = list(set(
            c.get('author', '') for c in recent_commits_in_stream if c.get('author')
        ))

        # Get files involved
        files_involved = []
        for item in items:
            if item.get('type') == 'file':
                files_involved.append(item['file'])

        # Count TODOs in this area
        todos = code_data.get('by_category', {}).get('todos', [])
        todos_in_area = []
        for todo in todos:
            file_path = todo.get('file_path', '')
            for f in files_involved:
                if file_path.startswith(str(Path(f).parent)):
                    todos_in_area.append(todo)
                    break

        # Estimate confidence based on signal strength
        confidence = 'low'
        if len(recent_commits_in_stream) >= 5 or len(items) >= 3:
            confidence = 'high'
        elif len(recent_commits_in_stream) >= 2 or len(items) >= 2:
            confidence = 'medium'

        # Estimate completion based on TODO trend
        estimated_completion = None
        if todos_in_area:
            # High TODO count suggests incomplete
            estimated_completion = 'in_progress'

        streams.append({
            'stream_name': stream_name,
            'confidence': confidence,
            'recent_commits': len(recent_commits_in_stream),
            'files_involved': files_involved[:5],  # Limit to top 5
            'contributors': contributors[:5],  # Limit to top 5
            'estimated_completion': estimated_completion,
            'indicator_count': len(items),
        })

    # Sort by activity
    streams.sort(key=lambda s: s['recent_commits'], reverse=True)

    return streams


def detect_stalled_work(
    git_data: dict,
    code_data: dict,
    stall_threshold_days: int = 14
) -> list[dict]:
    """Identify work that has stopped.

    Finds branches or areas with incomplete work but no recent activity.

    Args:
        git_data: Output from git_analyzer
        code_data: Output from code_scanner
        stall_threshold_days: Days of inactivity to consider "stalled"

    Returns:
        List of stalled work dicts
    """
    stalled = []
    branches = git_data.get('active_branches', [])
    todos = code_data.get('by_category', {}).get('todos', [])
    incomplete = code_data.get('by_category', {}).get('incomplete', [])

    # Check branches for staleness
    for branch in branches:
        branch_name = branch.get('name', '')
        if not branch_name or branch_name.startswith('origin/'):
            continue

        stream_name = extract_stream_name_from_branch(branch_name)
        if not stream_name:
            continue

        last_date_str = branch.get('last_commit_date', '')
        try:
            last_date = datetime.fromisoformat(last_date_str.replace('Z', '+00:00'))
            days_stalled = (datetime.now(timezone.utc) - last_date).days
        except (ValueError, AttributeError):
            continue

        if days_stalled >= stall_threshold_days:
            # Find incomplete markers in this area
            message = branch.get('last_commit_message', '').lower()

            blocker_hints = []
            for indicator in BLOCKER_INDICATORS:
                if indicator in message:
                    blocker_hints.append(f"Message mentions '{indicator}'")

            # Check for WIP indicators in branch name
            if any(wip in branch_name.lower() for wip in WIP_INDICATORS):
                blocker_hints.append("Branch name suggests WIP")

            # Check for TODOs in related files
            # This is approximate since we don't have file->branch mapping
            incomplete_markers = len([t for t in todos if 'stream' not in t])

            stalled.append({
                'branch_name': branch_name,
                'feature_area': stream_name,
                'last_activity_date': last_date_str,
                'days_stalled': days_stalled,
                'incomplete_markers': incomplete_markers,
                'blocker_hints': blocker_hints if blocker_hints else None,
            })

    # Sort by days stalled (most stalled first)
    stalled.sort(key=lambda s: s['days_stalled'], reverse=True)

    return stalled


def detect_debt_clusters(code_data: dict) -> list[dict]:
    """Identify areas with accumulated technical debt.

    Clusters TODOs, FIXMEs, and incomplete implementations by directory
    to identify high-debt areas.

    Args:
        code_data: Output from code_scanner

    Returns:
        List of debt cluster dicts
    """
    todos = code_data.get('by_category', {}).get('todos', [])
    incomplete = code_data.get('by_category', {}).get('incomplete', [])

    # Cluster by directory
    debt_by_dir: dict[str, dict] = {}

    for todo in todos:
        file_path = todo.get('file_path', '')
        if not file_path:
            continue

        dir_path = str(Path(file_path).parent)
        marker_type = todo.get('marker_type', 'OTHER')

        if dir_path not in debt_by_dir:
            debt_by_dir[dir_path] = {
                'todo_count': 0,
                'fixme_count': 0,
                'hack_count': 0,
                'xxx_count': 0,
                'incomplete_count': 0,
            }

        if marker_type == 'TODO':
            debt_by_dir[dir_path]['todo_count'] += 1
        elif marker_type == 'FIXME':
            debt_by_dir[dir_path]['fixme_count'] += 1
        elif marker_type == 'HACK':
            debt_by_dir[dir_path]['hack_count'] += 1
        elif marker_type == 'XXX':
            debt_by_dir[dir_path]['xxx_count'] += 1

    for item in incomplete:
        file_path = item.get('file_path', '')
        if not file_path:
            continue

        dir_path = str(Path(file_path).parent)
        if dir_path not in debt_by_dir:
            debt_by_dir[dir_path] = {
                'todo_count': 0,
                'fixme_count': 0,
                'hack_count': 0,
                'xxx_count': 0,
                'incomplete_count': 0,
            }
        debt_by_dir[dir_path]['incomplete_count'] += 1

    # Convert to list and calculate severity
    clusters = []
    for cluster_path, counts in debt_by_dir.items():
        total_markers = (
            counts['todo_count'] +
            counts['fixme_count'] +
            counts['hack_count'] +
            counts['xxx_count'] +
            counts['incomplete_count']
        )

        if total_markers == 0:
            continue

        # Calculate severity based on density
        severity = 'low'
        if total_markers >= 10 or counts['fixme_count'] >= 5:
            severity = 'critical'
        elif total_markers >= 5 or counts['fixme_count'] >= 3:
            severity = 'high'
        elif total_markers >= 3:
            severity = 'medium'

        # Suggest action based on marker types
        suggested_action = None
        if counts['fixme_count'] > 0:
            suggested_action = 'Address FIXMEs (known bugs)'
        elif counts['hack_count'] > 2:
            suggested_action = 'Refactor HACKs - technical debt accumulation'
        elif counts['incomplete_count'] > 2:
            suggested_action = 'Complete incomplete implementations'
        elif counts['todo_count'] > 5:
            suggested_action = 'Review and prioritize TODOs'

        clusters.append({
            'cluster_path': cluster_path,
            'todo_count': counts['todo_count'],
            'fixme_count': counts['fixme_count'],
            'hack_count': counts['hack_count'],
            'xxx_count': counts['xxx_count'],
            'incomplete_count': counts['incomplete_count'],
            'total_markers': total_markers,
            'severity': severity,
            'suggested_action': suggested_action,
        })

    # Sort by severity and total markers
    severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    clusters.sort(key=lambda c: (severity_order.get(c['severity'], 4), -c['total_markers']))

    return clusters


def analyze_momentum(git_data: dict, window_days: int = 30) -> dict:
    """Calculate development momentum.

    Analyzes commit velocity trends to determine if development is
    accelerating, stable, or decelerating.

    Args:
        git_data: Output from git_analyzer
        window_days: Analysis window in days

    Returns:
        Momentum analysis dict
    """
    commits = git_data.get('recent_commits', [])
    velocity = git_data.get('velocity', {})

    # Split into two halves for comparison
    half_window = window_days // 2
    now = datetime.now(timezone.utc)

    commits_first_half = []
    commits_second_half = []

    for commit in commits:
        try:
            commit_date = datetime.fromisoformat(commit['date'].replace('Z', '+00:00'))
            days_ago = (now - commit_date).days

            if days_ago <= half_window:
                commits_second_half.append(commit)
            elif days_ago <= window_days:
                commits_first_half.append(commit)
        except (ValueError, KeyError):
            continue

    # Calculate metrics
    commits_this_week = len(commits_second_half)
    commits_last_week = len(commits_first_half)

    # Get contributors
    contributors_this_week = set(c.get('author', '') for c in commits_second_half if c.get('author'))
    contributors_last_week = set(c.get('author', '') for c in commits_first_half if c.get('author'))

    # Calculate velocity change
    if commits_last_week > 0:
        velocity_change = ((commits_this_week - commits_last_week) / commits_last_week) * 100
    elif commits_this_week > 0:
        velocity_change = 100.0  # Started from zero
    else:
        velocity_change = 0.0

    # Determine trend
    if velocity_change > 15:
        trend = 'accelerating'
    elif velocity_change < -15:
        trend = 'decelerating'
    else:
        trend = 'stable'

    # Hottest areas (most recently changed files)
    recent_files = velocity.get('most_active_files', [])[:5]

    # Coldest areas (files with TODOs but no recent changes)
    # This is approximate since we don't have last-change-date per file
    coldest_areas = []
    todos = git_data.get('code_data', {}).get('by_category', {}).get('todos', [])
    if todos:
        # Group TODOs by file
        todo_files = Counter(t.get('file_path', '') for t in todos)
        coldest_areas = [
            {'file': f, 'todo_count': c}
            for f, c in todo_files.most_common(5)
        ]

    # Generate summary
    summary_parts = []
    if trend == 'accelerating':
        summary_parts.append("Development is accelerating")
    elif trend == 'decelerating':
        summary_parts.append("Development is slowing down")
    else:
        summary_parts.append("Development velocity is stable")

    if len(contributors_this_week) > len(contributors_last_week):
        new_count = len(contributors_this_week) - len(contributors_last_week)
        summary_parts.append(f" with {new_count} new contributors")

    summary = ''.join(summary_parts) + '.'

    return {
        'trend': trend,
        'velocity_change_percent': round(velocity_change, 1),
        'commits_this_week': commits_this_week,
        'commits_last_week': commits_last_week,
        'contributors_this_week': len(contributors_this_week),
        'contributors_last_week': len(contributors_last_week),
        'hottest_areas': recent_files,
        'coldest_areas': coldest_areas,
        'summary': summary,
    }


def path_overlaps(path1: str, path2: str) -> bool:
    """Check if two paths overlap (one is prefix of the other).

    Args:
        path1: First path
        path2: Second path

    Returns:
        True if paths overlap
    """
    p1 = Path(path1)
    p2 = Path(path2)

    # Check if one is a prefix of the other
    try:
        p2.relative_to(p1)
        return True
    except ValueError:
        pass

    try:
        p1.relative_to(p2)
        return True
    except ValueError:
        pass

    return False


def generate_insights(
    active: list[dict],
    stalled: list[dict],
    debt: list[dict],
    momentum: dict
) -> list[str]:
    """Generate actionable insights from analysis results.

    Combines patterns from different detectors to create meaningful,
    actionable recommendations.

    Args:
        active: Active work streams from detect_active_work_streams
        stalled: Stalled work from detect_stalled_work
        debt: Debt clusters from detect_debt_clusters
        momentum: Momentum analysis from analyze_momentum

    Returns:
        List of insight strings
    """
    insights = []

    # High activity + high debt = opportunity
    for stream in active:
        if stream['confidence'] != 'high':
            continue

        stream_files = stream.get('files_involved', [])
        for cluster in debt:
            if cluster['severity'] not in ('high', 'critical'):
                continue

            # Check for overlap
            for file_path in stream_files:
                if path_overlaps(file_path, cluster['cluster_path']):
                    insights.append(
                        f"Active work in '{stream['stream_name']}' overlaps with "
                        f"tech debt in {cluster['cluster_path']} - good time to address"
                    )
                    break

    # Stalled work with blockers
    for item in stalled[:5]:  # Limit to top 5
        if item.get('blocker_hints'):
            hint = item['blocker_hints'][0]
            insights.append(
                f"'{item['branch_name']}' stalled {item['days_stalled']} days: {hint}"
            )
        elif item['days_stalled'] > 30:
            insights.append(
                f"'{item['branch_name']}' has been inactive for {item['days_stalled']} days - "
                f"consider cleanup or review"
            )

    # Momentum changes
    if momentum['trend'] == 'decelerating' and momentum['velocity_change_percent'] < -20:
        insights.append(
            f"Development velocity dropped {abs(momentum['velocity_change_percent'])}% - "
            "check for blockers or burnout"
        )
    elif momentum['trend'] == 'accelerating' and momentum['contributors_this_week'] > 3:
        insights.append(
            f"Strong momentum with {momentum['contributors_this_week']} active contributors - "
            "ensure code review bandwidth"
        )

    # Critical debt clusters
    for cluster in debt:
        if cluster['severity'] == 'critical':
            insights.append(
                f"CRITICAL: {cluster['cluster_path']} has {cluster['total_markers']} "
                f"markers - {cluster['suggested_action'] or 'immediate attention needed'}"
            )

    # High confidence work streams with many TODOs
    for stream in active:
        if stream['confidence'] == 'high' and stream.get('estimated_completion') == 'in_progress':
            insights.append(
                f"'{stream['stream_name']}' is active with incomplete markers - "
                f"track completion to avoid scope creep"
            )

    # Remove duplicates while preserving order
    seen = set()
    unique_insights = []
    for insight in insights:
        if insight not in seen:
            seen.add(insight)
            unique_insights.append(insight)

    return unique_insights


def detect_trajectories(
    git_data: dict,
    code_data: dict,
    days: int = 30
) -> dict:
    """Run full trajectory detection.

    Combines all detection functions into a comprehensive analysis.

    Args:
        git_data: Output from git_analyzer
        code_data: Output from code_scanner
        days: Analysis window

    Returns:
        Complete trajectory analysis dict
    """
    # Inject code_data into git_data for momentum analysis
    git_data_with_code = {**git_data, 'code_data': code_data}

    return {
        'analysis_timestamp': datetime.now(timezone.utc).isoformat(),
        'repository': git_data.get('repository', 'unknown'),
        'momentum': analyze_momentum(git_data_with_code, days),
        'active_streams': detect_active_work_streams(git_data_with_code, code_data),
        'stalled_work': detect_stalled_work(git_data_with_code, code_data),
        'debt_clusters': detect_debt_clusters(code_data),
    }


def format_insights_only(trajectory: dict) -> str:
    """Format trajectory showing only insights.

    Args:
        trajectory: Trajectory analysis dict

    Returns:
        Formatted insights string
    """
    # Generate insights
    insights = generate_insights(
        trajectory.get('active_streams', []),
        trajectory.get('stalled_work', []),
        trajectory.get('debt_clusters', []),
        trajectory.get('momentum', {})
    )

    if not insights:
        return "No significant insights detected."

    lines = ["Development Trajectory Insights", "=" * 50, ""]
    for i, insight in enumerate(insights, 1):
        lines.append(f"{i}. {insight}")

    return "\n".join(lines)


def format_summary(trajectory: dict) -> str:
    """Format trajectory as human-readable summary.

    Args:
        trajectory: Trajectory analysis dict

    Returns:
        Formatted summary string
    """
    lines = [
        "Development Trajectory Analysis",
        "=" * 50,
        f"Repository: {trajectory['repository']}",
        f"Analysis Time: {trajectory['analysis_timestamp']}",
        "",
    ]

    # Momentum section
    m = trajectory['momentum']
    lines.append("=== Momentum ===")
    lines.append(f"  Trend: {m['trend'].upper()}")
    lines.append(f"  Velocity Change: {m['velocity_change_percent']:+.1f}%")
    lines.append(f"  Commits (recent/previous): {m['commits_this_week']}/{m['commits_last_week']}")
    lines.append(f"  Contributors (recent/previous): {m['contributors_this_week']}/{m['contributors_last_week']}")
    lines.append(f"  {m['summary']}")
    lines.append("")

    # Active streams section
    active = trajectory['active_streams']
    lines.append(f"=== Active Work Streams ({len(active)}) ===")
    for stream in active[:5]:
        conf = stream['confidence'].upper()
        lines.append(f"  [{conf}] {stream['stream_name']}")
        lines.append(f"      Commits: {stream['recent_commits']}, Contributors: {len(stream['contributors'])}")
        if stream.get('files_involved'):
            lines.append(f"      Files: {', '.join(stream['files_involved'][:3])}")
    lines.append("")

    # Stalled work section
    stalled = trajectory['stalled_work']
    if stalled:
        lines.append(f"=== Stalled Work ({len(stalled)}) ===")
        for item in stalled[:5]:
            lines.append(
                f"  {item['branch_name']} - {item['days_stalled']} days inactive"
            )
            if item.get('blocker_hints'):
                lines.append(f"      Hint: {item['blocker_hints'][0]}")
        lines.append("")

    # Debt clusters section
    debt = trajectory['debt_clusters']
    if debt:
        lines.append(f"=== Technical Debt Clusters ({len(debt)}) ===")
        for cluster in debt[:5]:
            sev = cluster['severity'].upper()
            lines.append(
                f"  [{sev}] {cluster['cluster_path']}: "
                f"{cluster['total_markers']} markers"
            )
            if cluster.get('suggested_action'):
                lines.append(f"      Suggest: {cluster['suggested_action']}")
        lines.append("")

    # Insights section
    lines.append("=== Key Insights ===")
    insights = generate_insights(
        trajectory['active_streams'],
        trajectory['stalled_work'],
        trajectory['debt_clusters'],
        trajectory['momentum']
    )
    if insights:
        for insight in insights[:10]:
            lines.append(f"  • {insight}")
    else:
        lines.append("  No specific insights at this time.")

    return "\n".join(lines)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Detect development trajectories from git and code patterns"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Analysis window in days (default: 30)"
    )
    parser.add_argument(
        "--output",
        choices=["json", "summary", "insights"],
        default="summary",
        help="Output format (default: summary)"
    )
    parser.add_argument(
        "--git-data",
        type=str,
        help="Path to git_analyzer.json output (optional)"
    )
    parser.add_argument(
        "--code-data",
        type=str,
        help="Path to code_scanner.json output (optional)"
    )
    parser.add_argument(
        "--cwd",
        type=str,
        default=None,
        help="Working directory (default: current)"
    )

    args = parser.parse_args()

    try:
        # Load or generate git data
        if args.git_data:
            with open(args.git_data) as f:
                git_data = json.load(f)
        else:
            from git_analyzer import analyze_repository
            git_data = analyze_repository(days=args.days, cwd=args.cwd)

        # Load or generate code data
        if args.code_data:
            with open(args.code_data) as f:
                code_data = json.load(f)
        else:
            from code_scanner import generate_report
            code_data = generate_report(path=args.cwd or ".")

        # Run trajectory detection
        trajectory = detect_trajectories(git_data, code_data, args.days)

        # Output
        if args.output == "json":
            print(json.dumps(trajectory, indent=2))
        elif args.output == "insights":
            print(format_insights_only(trajectory))
        else:
            print(format_summary(trajectory))

    except FileNotFoundError as e:
        print(f"File not found: {e}", file=__import__("sys").stderr)
        raise SystemExit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=__import__("sys").stderr)
        raise SystemExit(1)
    except Exception as e:
        print(f"Analysis failed: {e}", file=__import__("sys").stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
