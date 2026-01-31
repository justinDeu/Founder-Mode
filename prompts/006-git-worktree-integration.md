# Git Worktree Integration

## Objective

Add intelligent git worktree management to founder-mode. Enable automatic creation, navigation, and configuration of worktrees when executing prompts or working on issues. Support configurable worktree locations and naming schemes based on task source (prompt, GitHub issue, Jira ticket).

## Context

Current state: founder-mode has `worktree_dir` in config but no implementation.

```
@CLAUDE.md                     # Config block location
@references/github-utilities.md   # Issue patterns
@references/jira-config.md        # Jira patterns
@commands/run-prompt.md           # Where worktree creation integrates
```

User needs:
- Worktrees in flat layout (sibling directories) OR nested (./worktrees/)
- Naming varies by source: `gh-123-short-name`, `jira-ABC-123-title`, `prompt-001-feature`
- Detection of current context (main repo vs existing worktree)
- Future: environment setup after worktree creation

## Requirements

### Core Worktree Operations

Create `references/worktree-management.md`:

1. **Detection**
   - Use `git rev-parse --git-common-dir` to find the shared git directory
   - Compare to current directory to determine if at common dir or in worktree
   - All relative paths resolve from the common dir, not cwd

2. **Location Check Before Operations**

   Before any worktree operation:

   ```bash
   COMMON_DIR=$(git rev-parse --git-common-dir | sed 's|/\.git$||')
   CURRENT_DIR=$(pwd)
   ```

   If `COMMON_DIR != CURRENT_DIR`, user is in a worktree. Use AskUserQuestion:

   ```
   AskUserQuestion(
     questions: [{
       question: "You're in worktree '{current_worktree_name}'. Create new worktree at {computed_absolute_path}?",
       header: "Worktree Path",
       options: [
         { label: "Yes, create there", description: "Worktree created as sibling at {path}" },
         { label: "Change location", description: "Specify a different path for this worktree" },
         { label: "Cancel", description: "Don't create a worktree" }
       ]
     }]
   )
   ```

   If user chooses "Change location", follow up to get the desired path.

3. **Location Resolution**
   - All configured paths are relative to the git common directory
   - Read `worktree_dir` from founder_mode_config
   - Support absolute paths: `~/.worktrees/project-name/`
   - Support relative paths: `./` (flat siblings) or `./.worktrees/` (nested)
   - Default: `./` (flat layout in common dir)

4. **Creation**
   - Create branch from current HEAD or specified base
   - Run `git worktree add <path> -b <branch-name>`
   - Return the worktree path for subsequent operations

5. **Cleanup**
   - `git worktree remove <path>` when work complete
   - `git worktree prune` to clean stale entries

### Naming Configuration

Extend founder_mode_config with worktree naming rules:

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

**Variable extraction:**
- `{number}`: Issue/PR number, prompt number (e.g., 123, 001)
- `{slug}`: Sanitized short name from title (max 30 chars, lowercase, hyphens)
- `{project}`: Jira project key (e.g., ABC)
- `{date}`: YYYY-MM-DD
- `{branch}`: Base branch name

**Slug generation:**
- Extract first 5 meaningful words from title
- Remove articles, prepositions
- Lowercase, replace spaces with hyphens
- Truncate to 30 chars max

### Integration Points

1. **run-prompt command**

Update `commands/run-prompt.md`:

When `--worktree` flag provided:
1. Determine naming source (prompt file → prompt naming)
2. Generate worktree name using config
3. Create worktree at configured location
4. Change to worktree directory
5. Execute prompt
6. Return to original directory on completion

2. **fix-gh-issue command**

Update `commands/fix-gh-issue.md`:

- Extract issue number and title from gh CLI
- Use `github` naming template
- Auto-create worktree unless `--no-worktree` specified

3. **Jira workflow (future)**

Pattern for `jira` naming when Jira integration complete.

### Worktree Utilities

Create `references/worktree-utilities.md`:

```bash
# Detect if in worktree
is_worktree() {
  local common_dir=$(git rev-parse --git-common-dir 2>/dev/null)
  local git_dir=$(git rev-parse --git-dir 2>/dev/null)
  [ "$common_dir" != "$git_dir" ]
}

# Get main repo path
get_main_repo() {
  git rev-parse --git-common-dir | sed 's|/\.bare$||; s|/\.git$||'
}

# Get current worktree name
get_worktree_name() {
  basename "$(git rev-parse --show-toplevel)"
}

# List all worktrees
list_worktrees() {
  git worktree list --porcelain | grep "^worktree " | cut -d' ' -f2
}

# Create worktree with naming (must be run from common dir or use absolute path)
create_worktree() {
  local name="$1"
  local base_branch="${2:-HEAD}"
  local common_dir=$(git rev-parse --git-common-dir | sed 's|/\.bare$||; s|/\.git$||')
  local worktree_dir="${3:-$common_dir}"

  local path="${worktree_dir}/${name}"
  git worktree add "$path" -b "$name" "$base_branch"
  echo "$path"
}

# Remove worktree safely
remove_worktree() {
  local name="$1"
  git worktree remove "$name" --force 2>/dev/null || true
  git worktree prune
}
```

### Context Awareness

When founder-mode commands run, determine context:

```
Location Detection:
1. COMMON_DIR = git rev-parse --git-common-dir (strip /.git suffix)
2. CURRENT_DIR = pwd
3. If COMMON_DIR == CURRENT_DIR → at common dir, proceed normally
4. If different → in a worktree, prompt user before creating outside cwd
5. Extract current worktree name from basename of CURRENT_DIR

Context Actions:
- At common dir: Create worktrees using configured relative paths
- In worktree: Compute absolute path, ask user permission, then create
- Always resolve worktree_dir relative to COMMON_DIR, never cwd
```

### Environment Setup Hooks (Future-Ready)

Design the extension point but don't implement:

```xml
<founder_mode_config>
worktree_dir: ./
worktree_naming:
  prompt: prompt-{number}-{slug}
  github: gh-{number}-{slug}
worktree_setup:
  detect: true
  hooks:
    - ./scripts/setup-env.sh
  # OR declarative (future):
  # python_venv: true
  # npm_install: true
  # port_range: 8000-8999
</founder_mode_config>
```

Document the pattern in worktree-management.md:
- Detection of project type (package.json, pyproject.toml, etc.)
- Suggest setup configuration based on detected markers
- Execute user-provided hooks after worktree creation
- Mark as "planned feature" with extension point ready

## Implementation

### Step 1: Create Worktree Reference Docs

File: `references/worktree-management.md`

Content:
- Git worktree fundamentals
- Detection patterns
- Location resolution algorithm
- Creation and cleanup procedures
- Integration with founder-mode commands

### Step 2: Create Worktree Utilities

File: `references/worktree-utilities.md`

Content:
- Shell functions for worktree operations
- Naming template expansion logic
- Context detection functions
- Error handling patterns

### Step 3: Update run-prompt Command

File: `commands/run-prompt.md`

Changes:
- Add worktree creation before prompt execution
- Add worktree cleanup option after completion
- Document `--worktree` flag behavior
- Add `--worktree-keep` to preserve after execution

### Step 4: Update fix-gh-issue Command

File: `commands/fix-gh-issue.md`

Changes:
- Default to worktree creation for issue work
- Use github naming template
- Add `--no-worktree` flag to skip

### Step 5: Document Config Schema

Update `CLAUDE.md` with:
- Full worktree_naming options
- Example configurations for different styles
- Future worktree_setup documentation (marked as planned)

## Output

Create or modify:
- `./references/worktree-management.md` (new)
- `./references/worktree-utilities.md` (new)
- `./commands/run-prompt.md` (update)
- `./commands/fix-gh-issue.md` (update)
- `./CLAUDE.md` (update config documentation)

## Verification

- [ ] `references/worktree-management.md` explains detection, location, creation, cleanup
- [ ] `references/worktree-utilities.md` provides reusable shell functions
- [ ] Naming templates support prompt, github, jira sources
- [ ] `run-prompt.md` documents `--worktree` flag
- [ ] `fix-gh-issue.md` defaults to worktree with `--no-worktree` escape
- [ ] Config documentation shows worktree_naming examples
- [ ] Future environment setup pattern documented (not implemented)
- [ ] Flat layout (`./`) and nested (`./.worktrees/`) both supported
- [ ] Location check prompts user when invoked from within a worktree
