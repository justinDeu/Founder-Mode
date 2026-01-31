# Worktree Management

Git worktree fundamentals and founder-mode integration patterns.

## Git Worktree Basics

Git worktrees allow multiple working directories attached to a single repository. Each worktree:
- Has its own working directory and index
- Shares the same `.git` repository data
- Can have different branches checked out simultaneously
- Enables parallel development without stashing or committing

## Key Concepts

### Common Directory

The **common directory** is where all worktrees share their git data:

```bash
# Get common directory (strip /.git suffix for repo root)
COMMON_DIR=$(git rev-parse --git-common-dir | sed 's|/\.git$||')
```

This is the anchor point for all worktree operations. Configured paths resolve relative to this location, not the current working directory.

### Detection

Determine if currently in a worktree vs the main repo:

```bash
COMMON_DIR=$(git rev-parse --git-common-dir | sed 's|/\.git$||')
CURRENT_DIR=$(pwd)

if [ "$COMMON_DIR" = "$CURRENT_DIR" ]; then
  echo "At common directory"
else
  echo "In worktree: $(basename $CURRENT_DIR)"
fi
```

## Location Resolution

### Path Types

| Type | Example | Resolution |
|------|---------|------------|
| Absolute | `~/.worktrees/project/` | Used as-is |
| Relative | `./` | Resolved from common directory |
| Nested | `./.worktrees/` | Subdirectory of common directory |

### Configuration

Set `worktree_dir` in founder_mode_config:

```xml
<founder_mode_config>
worktree_dir: ./
</founder_mode_config>
```

**Examples:**
- `./` - Worktrees as siblings in common directory (flat layout)
- `./.worktrees/` - Worktrees in subdirectory (nested layout)
- `~/.worktrees/myproject/` - Absolute path (machine-specific)

### Resolution Algorithm

```
1. Read worktree_dir from config (default: ./)
2. Get COMMON_DIR from git rev-parse --git-common-dir
3. If worktree_dir is absolute: use as-is
4. If worktree_dir is relative: resolve from COMMON_DIR
5. Compute full path: {resolved_worktree_dir}/{worktree_name}
```

## Location Check Before Operations

When a founder-mode command needs to create a worktree, check the current location first.

### At Common Directory

If `CURRENT_DIR == COMMON_DIR`, proceed normally using configured relative paths.

### In a Worktree

If `CURRENT_DIR != COMMON_DIR`, the user is in an existing worktree. Before creating a new worktree:

1. Compute the absolute path where the worktree will be created
2. Inform the user that the path is outside the current directory
3. Ask for confirmation using AskUserQuestion:

```
AskUserQuestion(
  questions: [{
    question: "You're in worktree '{current_name}'. Create new worktree at {absolute_path}?",
    header: "Worktree Path",
    options: [
      { label: "Yes, create there", description: "New worktree at {path}" },
      { label: "Change location", description: "Specify a different path" },
      { label: "Cancel", description: "Don't create a worktree" }
    ]
  }]
)
```

If user chooses "Change location", prompt for a custom path.

## Naming Configuration

Configure naming templates per source type:

```xml
<founder_mode_config>
worktree_dir: ./
worktree_naming:
  prompt: prompt-{number}-{slug}
  github: gh-{number}-{slug}
  jira: {project}-{number}-{slug}
  default: wt-{slug}
</founder_mode_config>
```

### Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{number}` | Issue/prompt number | `123`, `001` |
| `{slug}` | Sanitized title | `fix-login-redirect` |
| `{project}` | Jira project key | `PROJ` |
| `{date}` | Current date | `2024-01-15` |
| `{branch}` | Base branch name | `main` |

### Slug Generation

1. Extract title from source (issue title, prompt name, etc.)
2. Take first 5 meaningful words (skip articles/prepositions)
3. Lowercase, replace spaces with hyphens
4. Truncate to 30 characters max
5. Remove trailing hyphens

**Example:**
- Input: "Fix the authentication redirect loop in OAuth flow"
- Output: `fix-authentication-redirect-loop-oauth`

## Creation

### Basic Creation

```bash
# From common directory
git worktree add ./gh-123-fix-bug -b gh-123-fix-bug main

# Creates:
# - New directory: ./gh-123-fix-bug
# - New branch: gh-123-fix-bug (based on main)
```

### From Within a Worktree

```bash
# Compute path relative to common directory
COMMON_DIR=$(git rev-parse --git-common-dir | sed 's|/\.git$||')
WORKTREE_PATH="$COMMON_DIR/gh-456-new-feature"

git worktree add "$WORKTREE_PATH" -b gh-456-new-feature main
```

### Branch Handling

- If branch doesn't exist: Create with `-b` flag
- If branch exists: Use without `-b` flag
- Check first: `git branch --list "$BRANCH_NAME"`

## Cleanup

### Remove Worktree

```bash
# Remove worktree (keeps branch)
git worktree remove ./gh-123-fix-bug

# Force remove if uncommitted changes
git worktree remove --force ./gh-123-fix-bug
```

### Prune Stale Entries

```bash
# Clean up references to deleted worktrees
git worktree prune
```

### List Worktrees

```bash
# Human-readable
git worktree list

# Machine-parseable
git worktree list --porcelain
```

## Integration with Commands

### run-prompt

When `--worktree` flag is provided:

1. Determine source type (prompt file)
2. Read naming template from config
3. Generate worktree name
4. Check current location, ask permission if needed
5. Create worktree
6. Execute prompt in worktree
7. Return to original directory

### fix-gh-issue

When fixing a GitHub issue:

1. Fetch issue number and title
2. Use `github` naming template
3. Create worktree (default behavior)
4. Fix issue in worktree
5. Create PR from worktree branch
6. Optionally clean up worktree

Use `--no-worktree` flag to skip worktree creation.

## Environment Setup (Planned)

Future feature: automatic environment setup after worktree creation.

### Extension Point

```xml
<founder_mode_config>
worktree_setup:
  detect: true
  hooks:
    - ./scripts/setup-env.sh
</founder_mode_config>
```

### Project Type Detection

| Marker | Project Type | Setup Actions |
|--------|--------------|---------------|
| `package.json` | Node.js | `npm install` |
| `pyproject.toml` | Python | Create venv, `pip install` |
| `go.mod` | Go | `go mod download` |
| `Cargo.toml` | Rust | `cargo build` |
| `.devcontainer/` | Dev Container | Container setup |

### Hook Execution

After worktree creation:
1. Detect project type from markers
2. Suggest setup configuration if not configured
3. Execute configured hooks
4. Report setup status

This feature is planned but not yet implemented.
