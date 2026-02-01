#!/usr/bin/env python3
"""Feature Identifier for direction-analyzer.

Analyzes trajectory data to identify and prioritize potential next features,
suggesting what work would be most valuable to pursue.

This transforms development insights into concrete feature suggestions ranked
by impact, effort, and strategic fit.
"""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import hashlib


# Paths to ignore (generated code, vendored dependencies, etc.)
IGNORE_PATHS = {
    'node_modules',
    'vendor',
    '.venv',
    'venv',
    'env',
    'dist',
    'build',
    'target',
    '__pycache__',
    '.git',
    '.tox',
    'migrations',
}

# Patterns suggesting future work
FUTURE_PATTERNS = [
    re.compile(r'future', re.IGNORECASE),
    re.compile(r'v2\b', re.IGNORECASE),
    re.compile(r'next version', re.IGNORECASE),
    re.compile(r'todo.*feature', re.IGNORECASE),
    re.compile(r'not implemented', re.IGNORECASE),
]

# API endpoint patterns (for detecting gaps)
API_PATTERNS = [
    re.compile(r'@?(get|post|put|delete|patch)\s*\(\s*[\'"](/[^\']+)', re.IGNORECASE),
    re.compile(r'app\.(get|post|put|delete|patch)\s*\(\s*[\'"](/[^\']+)'),
    re.compile(r'router\.(get|post|put|delete|patch)\s*\(\s*[\'"](/[^\']+)'),
]


def should_ignore_path(file_path: str) -> bool:
    """Check if a path should be ignored (generated/vendored code).

    Args:
        file_path: File path to check

    Returns:
        True if path should be ignored
    """
    path_lower = file_path.lower()

    # Check if any ignore segment is in the path
    for ignore in IGNORE_PATHS:
        if f'/{ignore}/' in f'/{file_path}/' or file_path.startswith(ignore):
            return True

    return False


def calculate_priority_score(suggestion: dict, trajectory: dict) -> float:
    """Calculate priority score for a suggestion.

    Higher score = higher priority. Considers impact, effort, momentum,
    opportunistic potential, and recent activity.

    Args:
        suggestion: Suggestion dict with impact/effort fields
        trajectory: Trajectory analysis dict

    Returns:
        Priority score (0-10 range typical)
    """
    score = 0.0

    # Impact (0-3)
    impact_scores = {'high': 3, 'medium': 2, 'low': 1}
    score += impact_scores.get(suggestion.get('impact', 'medium'), 2)

    # Effort inverse (0-3) - smaller effort gets higher score
    effort_scores = {'small': 3, 'medium': 2, 'large': 1}
    score += effort_scores.get(suggestion.get('effort', 'medium'), 2)

    # Momentum alignment (0-2)
    if suggestion_aligns_with_momentum(suggestion, trajectory):
        score += 2

    # Opportunistic bonus (0-1.5)
    if suggestion.get('opportunistic'):
        score += 1.5

    # Recency bonus (0-1)
    if suggestion.get('recent_activity'):
        score += 1

    # Severity bonus for debt (0-1)
    if suggestion.get('type') == 'debt':
        severity = suggestion.get('severity', 'low')
        if severity == 'critical':
            score += 1
        elif severity == 'high':
            score += 0.5

    return round(score, 1)


def suggestion_aligns_with_momentum(suggestion: dict, trajectory: dict) -> bool:
    """Check if suggestion aligns with current development momentum.

    Args:
        suggestion: Suggestion dict
        trajectory: Trajectory analysis dict

    Returns:
        True if aligned with momentum
    """
    momentum = trajectory.get('momentum', {})
    trend = momentum.get('trend', 'stable')
    active_streams = trajectory.get('active_streams', [])

    # Get suggestion area
    related_files = suggestion.get('related_files', [])
    if not related_files:
        return False

    # Check if overlaps with active streams
    for stream in active_streams:
        if stream.get('confidence') != 'high':
            continue

        stream_files = stream.get('files_involved', [])
        for stream_file in stream_files:
            for related_file in related_files:
                # Check for path overlap
                if path_overlaps(stream_file, related_file):
                    return True

    # Accelerating momentum = alignment bonus
    if trend == 'accelerating':
        return True

    return False


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


def gather_evidence(area: str, trajectory: dict) -> list[str]:
    """Gather evidence for a suggestion from trajectory data.

    Args:
        area: Area/directory path
        trajectory: Trajectory analysis dict

    Returns:
        List of evidence strings
    """
    evidence = []

    # Check active streams
    active_streams = trajectory.get('active_streams', [])
    for stream in active_streams:
        files = stream.get('files_involved', [])
        for f in files:
            if area in f or path_overlaps(area, f):
                if stream.get('recent_commits', 0) > 0:
                    evidence.append(
                        f"Active stream '{stream['stream_name']}' with "
                        f"{stream['recent_commits']} recent commits"
                    )
                break

    # Check stalled work
    stalled = trajectory.get('stalled_work', [])
    for item in stalled:
        feature_area = item.get('feature_area', '')
        if area in feature_area or path_overlaps(area, feature_area):
            evidence.append(
                f"Branch '{item['branch_name']}' stalled "
                f"{item['days_stalled']} days"
            )
            break

    # Check debt clusters
    debt = trajectory.get('debt_clusters', [])
    for cluster in debt:
        cluster_path = cluster.get('cluster_path', '')
        if path_overlaps(area, cluster_path):
            markers = cluster.get('total_markers', 0)
            severity = cluster.get('severity', 'unknown')
            evidence.append(
                f"{markers} technical debt markers in {cluster_path} ({severity} severity)"
            )
            break

    return evidence


def identify_continuation_opportunities(trajectory: dict) -> list[dict]:
    """Find partially complete work worth continuing.

    Args:
        trajectory: Trajectory analysis dict

    Returns:
        List of continuation opportunity dicts
    """
    opportunities = []
    active_streams = trajectory.get('active_streams', [])
    stalled = trajectory.get('stalled_work', [])

    # Process active streams
    for stream in active_streams:
        if stream.get('confidence') == 'low':
            continue

        stream_name = stream['stream_name']
        files = stream.get('files_involved', [])
        recent_commits = stream.get('recent_commits', 0)

        # Skip if no files
        if not files:
            continue

        # Estimate progress based on completion and TODOs
        estimated_completion = stream.get('estimated_completion')
        if estimated_completion == 'in_progress':
            progress = 60  # Assume 60% if TODOs present
        elif recent_commits > 5:
            progress = 80
        elif recent_commits > 2:
            progress = 50
        else:
            progress = 30

        # Determine priority
        priority = 'medium'
        if recent_commits > 5:
            priority = 'high'
        elif recent_commits < 2:
            priority = 'low'

        # Gather evidence
        evidence = gather_evidence(files[0], trajectory)
        if not evidence:
            evidence.append(f"{recent_commits} recent commits in this area")

        # Suggest next step
        suggested_step = f"Continue implementing {stream_name} functionality"
        if stream.get('estimated_completion') == 'in_progress':
            suggested_step = f"Complete remaining {stream_name} tasks and address TODOs"

        opportunities.append({
            'id': f"continue-{slugify(stream_name)}",
            'type': 'continuation',
            'title': f"Continue work on {stream_name}",
            'description': (
                f"Active development with {recent_commits} recent commits. "
                f"Estimated {progress}% complete."
            ),
            'evidence': evidence,
            'suggested_action': suggested_step,
            'effort': 'medium' if progress < 70 else 'small',
            'impact': 'high' if priority == 'high' else 'medium',
            'priority_score': 0,  # Calculated later
            'related_files': files,
            'tags': [stream_name, 'active'],
            'recent_activity': recent_commits > 0,
            'progress_percent': progress,
        })

    # Process stalled work that might be worth reviving
    for item in stalled[:5]:  # Limit to top 5
        if item.get('days_stalled', 0) > 30:
            continue  # Too stale

        feature_area = item.get('feature_area', '')
        if not feature_area:
            continue

        days_stalled = item.get('days_stalled', 0)

        evidence = [
            f"Branch '{item['branch_name']}' inactive for {days_stalled} days"
        ]

        if item.get('blocker_hints'):
            evidence.extend(item['blocker_hints'])

        opportunities.append({
            'id': f"revive-{slugify(feature_area)}",
            'type': 'continuation',
            'title': f"Revive stalled work on {feature_area}",
            'description': (
                f"Work paused {days_stalled} days ago. "
                f"May be worth reviving if still relevant."
            ),
            'evidence': evidence,
            'suggested_action': f"Review '{item['branch_name']}' branch and decide whether to continue or close",
            'effort': 'small',
            'impact': 'medium',
            'priority_score': 0,
            'related_files': [],
            'tags': [feature_area, 'stalled'],
            'recent_activity': False,
            'progress_percent': 40,
        })

    return opportunities


def identify_unblock_actions(trajectory: dict) -> list[dict]:
    """Find ways to unblock stalled work.

    Args:
        trajectory: Trajectory analysis dict

    Returns:
        List of unblock action dicts
    """
    actions = []
    stalled = trajectory.get('stalled_work', [])

    for item in stalled:
        blocker_hints = item.get('blocker_hints', [])
        feature_area = item.get('feature_area', '')
        branch_name = item.get('branch_name', '')

        if not feature_area:
            continue

        # Determine blocker type from hints
        blocker_type = 'technical'
        if any('depends' in h.lower() or 'waiting' in h.lower() for h in blocker_hints):
            blocker_type = 'dependency'
        elif any('needs' in h.lower() for h in blocker_hints):
            blocker_type = 'resource'

        # Suggest action based on blocker type
        if blocker_type == 'dependency':
            suggested = f"Resolve dependencies blocking '{branch_name}'"
            impact = 'high'
        elif blocker_type == 'resource':
            suggested = f"Allocate resources or review requirements for '{branch_name}'"
            impact = 'medium'
        else:
            suggested = f"Investigate and resolve blockers in '{branch_name}'"
            impact = 'medium'

        # Estimate effort
        days_stalled = item.get('days_stalled', 0)
        if days_stalled > 30:
            effort = 'large'
        elif days_stalled > 14:
            effort = 'medium'
        else:
            effort = 'small'

        evidence = [f"Stalled {days_stalled} days"]
        evidence.extend(blocker_hints)

        actions.append({
            'id': f"unblock-{slugify(feature_area)}",
            'type': 'unblock',
            'title': f"Unblock {feature_area}",
            'description': f"'{branch_name}' is blocked and needs attention",
            'evidence': evidence,
            'suggested_action': suggested,
            'effort': effort,
            'impact': impact,
            'priority_score': 0,
            'related_files': [],
            'tags': [feature_area, 'unblock', blocker_type],
            'blocker_type': blocker_type,
            'recent_activity': False,
        })

    return actions


def identify_debt_opportunities(trajectory: dict) -> list[dict]:
    """Find valuable technical debt to address.

    Args:
        trajectory: Trajectory analysis dict

    Returns:
        List of debt opportunity dicts
    """
    opportunities = []
    debt_clusters = trajectory.get('debt_clusters', [])
    active_streams = trajectory.get('active_streams', [])

    for cluster in debt_clusters:
        cluster_path = cluster['cluster_path']
        severity = cluster['severity']

        # Skip low severity
        if severity == 'low':
            continue

        # Determine debt type based on markers
        fixme_count = cluster.get('fixme_count', 0)
        hack_count = cluster.get('hack_count', 0)
        incomplete_count = cluster.get('incomplete_count', 0)
        todo_count = cluster.get('todo_count', 0)

        if incomplete_count > 0:
            debt_type = 'incomplete'
        elif fixme_count > 0:
            debt_type = 'outdated'  # FIXMEs suggest old/broken code
        elif hack_count > 2:
            debt_type = 'complexity'
        else:
            debt_type = 'todo'

        # Check if overlaps with active work (opportunistic)
        opportunistic = False
        for stream in active_streams:
            stream_files = stream.get('files_involved', [])
            for f in stream_files:
                if path_overlaps(f, cluster_path):
                    opportunistic = True
                    break

        # Suggest approach
        if debt_type == 'incomplete':
            approach = f"Complete {incomplete_count} incomplete implementations"
            benefit = 'functionality'
        elif debt_type == 'outdated':
            approach = f"Fix {fixme_count} known issues"
            benefit = 'reliability'
        elif debt_type == 'complexity':
            approach = f"Refactor {hack_count} temporary hacks"
            benefit = 'maintainability'
        else:
            approach = f"Address {todo_count} TODOs"
            benefit = 'maintainability'

        # Estimate effort
        total_markers = cluster.get('total_markers', 0)
        if total_markers >= 10:
            effort = 'large'
        elif total_markers >= 5:
            effort = 'medium'
        else:
            effort = 'small'

        # Determine impact based on severity
        impact = 'low'
        if severity == 'critical':
            impact = 'high'
        elif severity == 'high':
            impact = 'medium'

        # Gather evidence
        evidence = [
            f"{total_markers} technical debt markers",
            f"{fixme_count} FIXMEs, {hack_count} HACKs, {incomplete_count} incomplete"
        ]

        if opportunistic:
            evidence.append("Overlaps with active work - good opportunity")

        opportunities.append({
            'id': f"debt-{slugify(cluster_path)}",
            'type': 'debt',
            'title': f"Address technical debt in {cluster_path}",
            'description': (
                f"{cluster['suggested_action'] or 'Technical debt cleanup'} "
                f"({total_markers} markers)"
            ),
            'evidence': evidence,
            'suggested_action': approach,
            'effort': effort,
            'impact': impact,
            'priority_score': 0,
            'related_files': [cluster_path],
            'tags': ['debt', cluster_path, benefit],
            'debt_type': debt_type,
            'benefit': benefit,
            'opportunistic': opportunistic,
            'severity': severity,
            'recent_activity': opportunistic,
        })

    return opportunities


def identify_new_features(trajectory: dict, codebase_context: dict = None) -> list[dict]:
    """Infer potential new features from gaps.

    Args:
        trajectory: Trajectory analysis dict
        codebase_context: Optional additional context

    Returns:
        List of new feature dicts
    """
    features = []

    # Look for TODO/FIXME comments that mention features
    debt_clusters = trajectory.get('debt_clusters', [])

    for cluster in debt_clusters:
        cluster_path = cluster['cluster_path']
        todo_count = cluster.get('todo_count', 0)

        if todo_count == 0:
            continue

        # Check if in active area (suggests planned features)
        active_streams = trajectory.get('active_streams', [])
        in_active_area = False

        for stream in active_streams:
            stream_files = stream.get('files_involved', [])
            for f in stream_files:
                if path_overlaps(f, cluster_path):
                    in_active_area = True
                    break

        if in_active_area and todo_count > 3:
            # Suggest feature planning
            feature_name = Path(cluster_path).name

            features.append({
                'id': f"feature-{slugify(feature_name)}-enhancements",
                'type': 'new',
                'title': f"Plan {feature_name} enhancements",
                'description': (
                    f"Multiple TODOs in {cluster_path} suggest planned improvements"
                ),
                'evidence': [
                    f"{todo_count} TODOs in active area",
                    f"Area: {cluster_path}"
                ],
                'suggested_action': f"Review TODOs in {cluster_path} and create feature roadmap",
                'effort': 'medium',
                'impact': 'medium',
                'priority_score': 0,
                'related_files': [cluster_path],
                'tags': [feature_name, 'planning'],
                'complexity': 'unknown',
            })

    return features


def prioritize_suggestions(all_suggestions: list[dict], trajectory: dict) -> list[dict]:
    """Rank all suggestions by value.

    Args:
        all_suggestions: List of suggestion dicts
        trajectory: Trajectory analysis dict

    Returns:
        Sorted list with priority_score added
    """
    # Calculate scores
    for suggestion in all_suggestions:
        score = calculate_priority_score(suggestion, trajectory)
        suggestion['priority_score'] = score

    # Sort by score (descending)
    suggestions_sorted = sorted(
        all_suggestions,
        key=lambda s: s['priority_score'],
        reverse=True
    )

    return suggestions_sorted


def slugify(text: str) -> str:
    """Convert text to URL-safe slug.

    Args:
        text: Text to slugify

    Returns:
        Slug string
    """
    # Convert to lowercase and replace spaces/non-alphanumeric with hyphens
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', text.lower()).strip('-')
    # Limit length
    return slug[:50]


def generate_suggestions(trajectory: dict) -> dict:
    """Generate all feature suggestions from trajectory.

    Args:
        trajectory: Trajectory analysis dict

    Returns:
        Complete suggestions dict
    """
    # Get all suggestions
    continuations = identify_continuation_opportunities(trajectory)
    unblocks = identify_unblock_actions(trajectory)
    debts = identify_debt_opportunities(trajectory)
    new_features = identify_new_features(trajectory)

    # Combine and prioritize
    all_suggestions = continuations + unblocks + debts + new_features
    prioritized = prioritize_suggestions(all_suggestions, trajectory)

    # Count by type
    high_priority = sum(1 for s in prioritized if s.get('priority_score', 0) >= 7)
    quick_wins = sum(
        1 for s in prioritized
        if s.get('effort') == 'small' and s.get('priority_score', 0) >= 5
    )

    return {
        'analysis_timestamp': datetime.now(timezone.utc).isoformat(),
        'repository': trajectory.get('repository', 'unknown'),
        'top_suggestions': prioritized[:10],
        'by_type': {
            'continuation': continuations,
            'unblock': unblocks,
            'debt': debts,
            'new': new_features,
        },
        'all_suggestions': prioritized,
        'summary': {
            'total_suggestions': len(prioritized),
            'high_priority': high_priority,
            'quick_wins': quick_wins,
        }
    }


def format_summary(suggestions: dict) -> str:
    """Format suggestions as human-readable summary.

    Args:
        suggestions: Suggestions dict from generate_suggestions

    Returns:
        Formatted summary string
    """
    lines = [
        "Feature Suggestions",
        "=" * 50,
        f"Repository: {suggestions['repository']}",
        f"Analysis Time: {suggestions['analysis_timestamp']}",
        "",
    ]

    summary = suggestions['summary']
    lines.append("=== Summary ===")
    lines.append(f"  Total Suggestions: {summary['total_suggestions']}")
    lines.append(f"  High Priority: {summary['high_priority']}")
    lines.append(f"  Quick Wins: {summary['quick_wins']}")
    lines.append("")

    # Top suggestions
    top = suggestions['top_suggestions']
    lines.append(f"=== Top {len(top)} Suggestions ===")

    for i, suggestion in enumerate(top, 1):
        score = suggestion['priority_score']
        title = suggestion['title']
        effort = suggestion['effort'].upper()
        impact = suggestion['impact'].upper()
        stype = suggestion['type'].upper()

        lines.append(f"\n{i}. [{stype}] {title} (Score: {score})")
        lines.append(f"   Effort: {effort} | Impact: {impact}")
        lines.append(f"   {suggestion['description']}")

        if suggestion.get('evidence'):
            lines.append("   Evidence:")
            for evidence in suggestion['evidence'][:3]:
                lines.append(f"     • {evidence}")

        lines.append(f"   Action: {suggestion['suggested_action']}")

    return "\n".join(lines)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Identify and prioritize feature suggestions from trajectory analysis"
    )
    parser.add_argument(
        "--trajectory",
        type=str,
        help="Path to trajectory_detector.json output"
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Limit to top N suggestions (default: 10)"
    )
    parser.add_argument(
        "--type",
        type=str,
        choices=['continuation', 'unblock', 'debt', 'new', 'all'],
        default='all',
        help="Filter by suggestion type (default: all)"
    )
    parser.add_argument(
        "--output",
        choices=["json", "summary"],
        default="summary",
        help="Output format (default: summary)"
    )

    args = parser.parse_args()

    try:
        # Load trajectory data
        if args.trajectory:
            with open(args.trajectory) as f:
                trajectory = json.load(f)
        else:
            # Run trajectory detector if no file provided
            import sys
            sys.path.insert(0, str(Path(__file__).parent))

            from trajectory_detector import detect_trajectories
            from git_analyzer import analyze_repository
            from code_scanner import generate_report

            git_data = analyze_repository()
            code_data = generate_report()
            trajectory = detect_trajectories(git_data, code_data)

        # Generate suggestions
        suggestions = generate_suggestions(trajectory)

        # Filter by type if requested
        if args.type != 'all':
            filtered = suggestions['by_type'][args.type]
            suggestions['top_suggestions'] = filtered[:args.top]
            suggestions['all_suggestions'] = filtered
            suggestions['summary']['total_suggestions'] = len(filtered)

        # Apply --top limit
        if args.top < len(suggestions['top_suggestions']):
            suggestions['top_suggestions'] = suggestions['top_suggestions'][:args.top]

        # Output
        if args.output == "json":
            # Remove circular references if any
            output = json.loads(json.dumps(suggestions))
            print(json.dumps(output, indent=2))
        else:
            print(format_summary(suggestions))

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
