---
name: fm:direction
description: Analyze codebase trajectory and get actionable development suggestions
argument-hint: [subcommand] [--days N] [--top N] [--type TYPE] [--output FORMAT] [--interactive]
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - AskUserQuestion
---

# Direction

Analyze codebase development trajectory and provide actionable suggestions for next steps. This command orchestrates all direction-analyzer utilities into a unified "smart assistant" experience.

## Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `[subcommand]` | positional | `full` | Command to run: `status`, `suggest`, `generate`, `full` |
| `--days` | option | `30` | Analysis window in days |
| `--top` | option | `10` | Limit suggestions (default: 10) |
| `--type` | option | `all` | Filter: `continuation`, `unblock`, `debt`, `new`, `all` |
| `--output` | option | `summary` | Output format: `summary`, `json`, `prompts` |
| `--interactive` | flag | false | Interactive mode with selection |

## Subcommands

### status

Quick overview of codebase state and momentum. Shows:
- Development velocity trend
- Active work streams
- Stalled work
- Technical debt hotspots

```
/fm:direction status --days 30
```

### suggest

Show prioritized feature suggestions based on trajectory analysis. Ranks by:
- Impact and effort
- Alignment with current momentum
- Opportunistic potential
- Recency of activity

```
/fm:direction suggest --top 10 --type continuation
```

### generate

Generate prompt files from suggestions for immediate execution.

```
/fm:direction generate --top 5
```

### full (default)

Run complete analysis and show everything: status, suggestions, and generated files.

```
/fm:direction full --days 30 --top 10
```

## Execution Flow

### Step 1: Parse Arguments

```
subcommand = first positional argument or "full"
days = --days value or 30
top = --top value or 10
type_filter = --type value or "all"
output_format = --output value or "summary"
interactive = --interactive flag present
```

### Step 2: Validate Repository

```bash
# Check we're in a git repository
git rev-parse --git-dir > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "Error: Not in a git repository"
    exit 1
fi
```

Handle edge cases:
- Empty/new repository: Inform user this feature needs git history
- No commits: Suggest making initial commit first

### Step 3: Locate Scripts

```bash
# Get plugin root
PLUGIN_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$PLUGIN_ROOT" ]; then
    PLUGIN_ROOT=$(git rev-parse --git-common-dir 2>/dev/null | sed 's|/\.bare$||; s|/\.git$||')
fi

# Script paths
GIT_ANALYZER="$PLUGIN_ROOT/direction-analyzer/scripts/git_analyzer.py"
CODE_SCANNER="$PLUGIN_ROOT/direction-analyzer/scripts/code_scanner.py"
TRAJECTORY_DETECTOR="$PLUGIN_ROOT/direction-analyzer/scripts/trajectory_detector.py"
FEATURE_IDENTIFIER="$PLUGIN_ROOT/direction-analyzer/scripts/feature_identifier.py"
PM_FORMATTER="$PLUGIN_ROOT/direction-analyzer/scripts/pm_formatter.py"
```

### Step 4: Run Analysis Based on Subcommand

#### status subcommand

```bash
# Run git analyzer
python3 "$GIT_ANALYZER" --days "$days" --cwd . > /tmp/git_data.json

# Run code scanner
python3 "$CODE_SCANNER" --path . > /tmp/code_data.json

# Run trajectory detector (subset for status)
python3 "$TRAJECTORY_DETECTOR" \
    --git-data /tmp/git_data.json \
    --code-data /tmp/code_data.json \
    --days "$days" \
    --output summary
```

Format output as:

```
Development Status (last {days} days)
================================

Momentum: {Accelerating|Stable|Decelerating} ({velocity_change}% velocity)
  - {commits_this_week} commits from {contributors} contributors
  - Most active: {active_areas}

Active Work Streams:
  1. {stream_name} ({confidence} confidence, {commits} commits)
     - Contributors: {list}
     - Files: {files}

Stalled Work:
  1. {branch_name} ({days_stalled} days, {status})
     - {blocker_hint if any}

Technical Debt Hotspots:
  1. {cluster_path} - {total_markers} markers ({severity} severity)
     - Suggested: {suggested_action}
```

#### suggest subcommand

```bash
# Run full pipeline
python3 "$GIT_ANALYZER" --days "$days" --cwd . > /tmp/git_data.json
python3 "$CODE_SCANNER" --path . > /tmp/code_data.json
python3 "$TRAJECTORY_DETECTOR" \
    --git-data /tmp/git_data.json \
    --code-data /tmp/code_data.json \
    --days "$days" \
    --output json > /tmp/trajectory.json

# Generate suggestions
python3 "$FEATURE_IDENTIFIER" \
    --trajectory /tmp/trajectory.json \
    --top "$top" \
    --type "$type_filter" \
    --output summary
```

Format output as:

```
Top Suggestions
===============

{for each suggestion}

1. [{type}] {title} (priority: {score})
   {description}
   Evidence:
     • {evidence_1}
     • {evidence_2}
   Action: {suggested_action}

   Run: /fm:run-prompt {prompt_file}
```

#### generate subcommand

```bash
# Run full pipeline if not already run
if [ ! -f /tmp/trajectory.json ]; then
    python3 "$GIT_ANALYZER" --days "$days" --cwd . > /tmp/git_data.json
    python3 "$CODE_SCANNER" --path . > /tmp/code_data.json
    python3 "$TRAJECTORY_DETECTOR" \
        --git-data /tmp/git_data.json \
        --code-data /tmp/code_data.json \
        --days "$days" \
        --output json > /tmp/trajectory.json
fi

# Generate suggestions
python3 "$FEATURE_IDENTIFIER" \
    --trajectory /tmp/trajectory.json \
    --top "$top" \
    --type "$type_filter" \
    --output json > /tmp/suggestions.json

# Generate prompts using pm_formatter
python3 "$PM_FORMATTER" \
    --input /tmp/suggestions.json \
    --format prompt \
    --output-dir "prompts/generated"
```

Format output as:

```
Generating prompts for top {count} suggestions...

Created:
  {prompt_file_1}
  {prompt_file_2}
  {prompt_file_3}

Workflow:
  prompts/generated/workflow.yaml

Next Steps:
  1. Run: /fm:run-prompt {first_prompt} --worktree
  2. Or execute all: /fm:orchestrate prompts/generated/workflow.yaml
```

#### full subcommand

Run all three: status, suggest, and generate.

```
Direction Analysis
==================

[Status section from above]

[Suggestions section from above]

[Generated files section from above]

Next Steps:
  1. /fm:run-prompt prompts/generated/001-{first-suggestion}.md --worktree
  2. /fm:orchestrate prompts/generated/workflow.yaml
```

### Step 5: Interactive Mode (if --interactive)

```
Direction Analyzer - Interactive Mode
=====================================

Found {count} suggestions. Select which to generate prompts for:

[x] 1. {title} ({type}, priority: {score})
[ ] 2. {title} ({type}, priority: {score})
[x] 3. {title} ({type}, priority: {score})
...

(Use space to toggle, enter to confirm, q to quit)

Generate prompts for {selected} items? [Y/n]
```

Use AskUserQuestion with multiSelect:

```
AskUserQuestion(
  questions: [{
    question: "Select suggestions to generate prompts for:",
    header: "Suggestions",
    options: [
      {
        label: "{title}",
        description: "{type} | Priority: {score} | {description[:80]}"
      }
      // ... for each suggestion
    ],
    multiSelect: true
  }]
)
```

After selection, generate prompts using pm_formatter with selected items only.

### Step 6: Handle --output Format

#### summary (default)

Human-readable text output as shown in examples above.

#### json

Raw JSON output for programmatic consumption:

```bash
python3 "$FEATURE_IDENTIFIER" \
    --trajectory /tmp/trajectory.json \
    --top "$top" \
    --type "$type_filter" \
    --output json
```

Output is the complete suggestions JSON with all fields.

#### prompts

Shortcut for `generate` subcommand - creates prompt files and shows paths.

### Step 7: Report Results

<status_output>
For `status` subcommand:

```
Development Status Analysis Complete
=====================================

{formatted status output}

Analyzed {commits_count} commits across {days} days
Repository: {repo_name}
Analysis time: {timestamp}
```
</status_output>

<suggest_output>
For `suggest` subcommand:

```
Feature Suggestions Generated
==============================

{formatted suggestions output}

Found {total} suggestions (showing top {displayed})
Run 'generate' to create prompt files
```
</suggest_output>

<generate_output>
For `generate` subcommand:

```
Prompt Files Generated
======================

{file list}

Workflow created: {workflow_path}

Execute with:
  /fm:run-prompt {first_prompt} --worktree
  /fm:orchestrate {workflow_path}
```
</generate_output>

<full_output>
For `full` subcommand (default):

```
Direction Analysis Complete
============================

[All three sections combined]

Next Actions:
  1. /fm:run-prompt {first_prompt} --worktree
  2. /fm:orchestrate {workflow_path}
  3. /fm:direction --interactive  # to select different suggestions
```
</full_output>

## Error Handling

<error_not_git_repo>
```
Error: Not in a git repository

The direction analyzer requires git history to analyze development patterns.
Initialize a git repository first:

  git init
  git add .
  git commit -m "Initial commit"

Then run /fm:direction again.
```
</error_not_git_repo>

<error_no_commits>
```
Error: Repository has no commits

The direction analyzer needs commit history to identify patterns.
Make your first commit:

  git commit -m "Initial commit"

Then run /fm:direction again.
```
</error_no_commits>

<error_no_suggestions>
```
Analysis Complete - No Suggestions Found
=========================================

Good news! Your codebase appears clean:
  - No stalled work detected
  - No critical technical debt
  - No obvious continuation opportunities

This could mean:
  - New project with little history
  - Well-maintained codebase
  - Very short analysis window ({days} days)

Try:
  /fm:direction --days 90  # analyze longer window
```
</error_no_suggestions>

<error_script_missing>
```
Error: Direction analyzer scripts not found

Expected location: {PLUGIN_ROOT}/direction-analyzer/scripts/

Check founder-mode installation:
  Claude Code → Settings → Plugins → founder-mode

Reinstall if needed.
```
</error_script_missing>

<error_analysis_failed>
```
Analysis Failed
===============

Script: {script_name}
Error: {error_message}

Check:
  1. Python 3 is installed: python3 --version
  2. Git is available: git --version
  3. Repository is accessible

Run with verbose output for debugging.
```
</error_analysis_failed>

## Examples

**Quick status check:**
```
/fm:direction status
```

**Get top 5 suggestions for continuing work:**
```
/fm:direction suggest --top 5 --type continuation
```

**Generate prompt files for top 3 suggestions:**
```
/fm:direction generate --top 3
```

**Interactive mode:**
```
/fm:direction --interactive
```

**Full analysis with custom window:**
```
/fm:direction full --days 60 --top 15
```

**JSON output for scripting:**
```
/fm:direction suggest --output json > suggestions.json
```

**Focus on unblocking stalled work:**
```
/fm:direction suggest --type unblock --top 10
```

## Integration with Scripts

The command orchestrates these utilities:

<git_analyzer>
```python
from scripts.git_analyzer import analyze_repository

git_data = analyze_repository(days=args.days, cwd=".")
```

Returns:
- recent_commits
- active_branches
- velocity metrics
- work_in_progress
</git_analyzer>

<code_scanner>
```python
from scripts.code_scanner import generate_report

code_data = generate_report(path=".")
```

Returns:
- by_category (todos, incomplete, etc.)
- by_file
- summary
</code_scanner>

<trajectory_detector>
```python
from scripts.trajectory_detector import detect_trajectories

trajectory = detect_trajectories(git_data, code_data, days=args.days)
```

Returns:
- momentum (trend, velocity_change, etc.)
- active_streams
- stalled_work
- debt_clusters
</trajectory_detector>

<feature_identifier>
```python
from scripts.feature_identifier import generate_suggestions

suggestions = generate_suggestions(trajectory)
```

Returns:
- top_suggestions
- by_type
- summary stats
</feature_identifier>

<pm_formatter>
```python
from scripts.pm_formatter import generate_prompt_file, generate_workflow

for suggestion in suggestions['top_suggestions']:
    prompt_path = generate_prompt_file(suggestion)
    print(f"Created: {prompt_path}")

workflow_path = generate_workflow(suggestions['top_suggestions'], "prompts/generated/workflow.yaml")
```

Creates:
- Individual prompt files
- workflow.yaml for orchestration
</pm_formatter>

## Output Formatting

<format_status>
```python
def format_status_output(trajectory: dict, days: int) -> str:
    lines = []
    lines.append(f"Development Status (last {days} days)")
    lines.append("=" * 40)
    lines.append("")

    # Momentum
    m = trajectory['momentum']
    trend_symbol = {"accelerating": "+", "stable": "=", "decelerating": "-"}
    lines.append(f"Momentum: {m['trend'].capitalize()} ({trend_symbol[m['trend']]}{abs(m['velocity_change_percent']):.0f}% velocity)")
    lines.append(f"  - {m['commits_this_week']} commits from {m['contributors_this_week']} contributors")

    if m['hottest_areas']:
        lines.append(f"  - Most active: {', '.join([a['file'] for a in m['hottest_areas'][:3]])}")

    lines.append("")

    # Active streams
    active = trajectory['active_streams']
    if active:
        lines.append("Active Work Streams:")
        for i, stream in enumerate(active[:5], 1):
            conf = stream['confidence']
            lines.append(f"  {i}. {stream['stream_name']} ({conf} confidence, {stream['recent_commits']} commits)")
            if stream['contributors']:
                lines.append(f"     - Contributors: {', '.join(stream['contributors'])}")
            if stream['files_involved']:
                lines.append(f"     - Files: {', '.join(stream['files_involved'][:3])}")

        lines.append("")

    # Stalled work
    stalled = trajectory['stalled_work']
    if stalled:
        lines.append("Stalled Work:")
        for i, item in enumerate(stalled[:3], 1):
            lines.append(f"  {i}. {item['feature_area']} ({item['days_stalled']} days)")
            if item.get('blocker_hints'):
                lines.append(f"     - {item['blocker_hints'][0]}")

        lines.append("")

    # Debt clusters
    debt = trajectory['debt_clusters']
    if debt:
        lines.append("Technical Debt Hotspots:")
        for i, cluster in enumerate(debt[:3], 1):
            sev = cluster['severity']
            lines.append(f"  {i}. {cluster['cluster_path']} - {cluster['total_markers']} markers ({sev} severity)")
            if cluster.get('suggested_action'):
                lines.append(f"     - {cluster['suggested_action']}")

    return "\n".join(lines)
```
</format_status>

<format_suggestions>
```python
def format_suggestions_output(suggestions: dict, top_n: int) -> str:
    lines = []
    lines.append("Top Suggestions")
    lines.append("=" * 40)
    lines.append("")

    for i, sugg in enumerate(suggestions['top_suggestions'][:top_n], 1):
        stype = sugg['type']
        title = sugg['title']
        score = sugg['priority_score']
        desc = sugg['description']
        action = sugg['suggested_action']

        lines.append(f"{i}. [{stype}] {title} (priority: {score})")
        lines.append(f"   {desc}")

        if sugg.get('evidence'):
            lines.append("   Evidence:")
            for ev in sugg['evidence'][:2]:
                lines.append(f"     • {ev}")

        lines.append(f"   Action: {action}")
        lines.append(f"   Run: /fm:run-prompt prompts/generated/{slugify(title)}.md")
        lines.append("")

    # Summary
    summary = suggestions['summary']
    lines.append(f"Total: {summary['total_suggestions']} suggestions")
    lines.append(f"High priority: {summary['high_priority']}")
    lines.append(f"Quick wins: {summary['quick_wins']}")

    return "\n".join(lines)
```
</format_suggestions>

<format_generate>
```python
def format_generate_output(created_files: list[str], workflow_path: str) -> str:
    lines = []
    lines.append(f"Generating prompts for {len(created_files)} suggestions...")
    lines.append("")
    lines.append("Created:")
    for path in created_files:
        lines.append(f"  {path}")

    lines.append("")
    lines.append(f"Workflow:")
    lines.append(f"  {workflow_path}")
    lines.append("")
    lines.append("Run with:")
    if created_files:
        lines.append(f"  1. /fm:run-prompt {created_files[0]} --worktree")
    lines.append(f"  2. /fm:orchestrate {workflow_path}")

    return "\n".join(lines)
```
</format_generate>

## Anti-Patterns

Avoid:
- Overwhelming output with too many suggestions (use --top)
- Jargon without explanation
- Actions that don't have clear next steps
- Generating prompts for low-priority suggestions
- Running analysis on extremely short windows (<7 days)

Instead:
- Default to sensible limits (10 suggestions, 30 days)
- Explain technical terms in context
- Always provide actionable next steps
- Prioritize by impact and effort
- Use appropriate windows for meaningful patterns
