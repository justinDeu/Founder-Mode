# Worktree Utilities

Shell functions for worktree operations in founder-mode.

## Detection Functions

### is_worktree

Check if currently in a worktree (vs the main repo).

```bash
is_worktree() {
  local common_dir=$(git rev-parse --git-common-dir 2>/dev/null)
  local git_dir=$(git rev-parse --git-dir 2>/dev/null)
  [ "$common_dir" != "$git_dir" ]
}

# Usage
if is_worktree; then
  echo "In a worktree"
else
  echo "In main repo"
fi
```

### get_common_dir

Get the common directory (shared git data location).

```bash
get_common_dir() {
  git rev-parse --git-common-dir 2>/dev/null | sed 's|/\.bare$||; s|/\.git$||'
}

# Usage
COMMON=$(get_common_dir)
echo "Common directory: $COMMON"
```

### get_worktree_name

Get the name of the current worktree.

```bash
get_worktree_name() {
  basename "$(git rev-parse --show-toplevel 2>/dev/null)"
}

# Usage
NAME=$(get_worktree_name)
echo "Current worktree: $NAME"
```

## Listing Functions

### list_worktrees

List all worktrees for the current repository.

```bash
list_worktrees() {
  git worktree list --porcelain | grep "^worktree " | cut -d' ' -f2-
}

# Usage
for wt in $(list_worktrees); do
  echo "Worktree: $wt"
done
```

### list_worktrees_with_branches

List worktrees with their branch names.

```bash
list_worktrees_with_branches() {
  git worktree list --porcelain | awk '
    /^worktree / { path = substr($0, 10) }
    /^branch / { branch = substr($0, 8); print path "\t" branch }
  '
}

# Usage
list_worktrees_with_branches | while IFS=$'\t' read -r path branch; do
  echo "$path -> $branch"
done
```

## Creation Functions

### create_worktree

Create a worktree with proper path resolution.

```bash
create_worktree() {
  local name="$1"
  local base_branch="${2:-HEAD}"
  local config_dir="${3:-}"

  # Get common directory
  local common_dir=$(get_common_dir)

  # Resolve worktree directory
  local worktree_dir
  if [ -n "$config_dir" ]; then
    # Use configured directory
    case "$config_dir" in
      /*|~*) worktree_dir="$config_dir" ;;  # Absolute
      *)     worktree_dir="$common_dir/$config_dir" ;;  # Relative
    esac
  else
    # Default: flat layout in common directory
    worktree_dir="$common_dir"
  fi

  # Expand tilde
  worktree_dir="${worktree_dir/#\~/$HOME}"

  # Full path
  local path="$worktree_dir/$name"

  # Create parent directory if needed
  mkdir -p "$(dirname "$path")"

  # Check if branch exists
  if git branch --list "$name" | grep -q .; then
    # Branch exists, use it
    git worktree add "$path" "$name"
  else
    # Create new branch
    git worktree add "$path" -b "$name" "$base_branch"
  fi

  echo "$path"
}

# Usage
WORKTREE_PATH=$(create_worktree "gh-123-fix-bug" "main" "./")
cd "$WORKTREE_PATH"
```

## Cleanup Functions

### remove_worktree

Remove a worktree safely.

```bash
remove_worktree() {
  local name_or_path="$1"
  local force="${2:-false}"

  # Resolve path if name given
  local path
  if [ -d "$name_or_path" ]; then
    path="$name_or_path"
  else
    # Search for worktree by name
    path=$(git worktree list --porcelain | grep "^worktree .*$name_or_path$" | cut -d' ' -f2-)
  fi

  if [ -z "$path" ]; then
    echo "Worktree not found: $name_or_path" >&2
    return 1
  fi

  # Remove worktree
  if [ "$force" = "true" ]; then
    git worktree remove --force "$path"
  else
    git worktree remove "$path"
  fi

  # Clean up stale entries
  git worktree prune
}

# Usage
remove_worktree "gh-123-fix-bug"
remove_worktree "/path/to/worktree" true  # Force remove
```

### prune_worktrees

Clean up stale worktree references.

```bash
prune_worktrees() {
  git worktree prune
  echo "Pruned stale worktree references"
}
```

## Naming Functions

### generate_slug

Generate a URL-safe slug from a title.

```bash
generate_slug() {
  local title="$1"
  local max_length="${2:-30}"

  # Words to remove
  local stop_words="a an the in on at to for of and or but is are was were be been being"

  echo "$title" |
    # Lowercase
    tr '[:upper:]' '[:lower:]' |
    # Replace non-alphanumeric with spaces
    sed 's/[^a-z0-9]/ /g' |
    # Remove stop words
    tr ' ' '\n' |
    grep -vE "^($(echo $stop_words | tr ' ' '|'))$" |
    head -5 |
    tr '\n' '-' |
    # Clean up
    sed 's/--*/-/g' |
    sed 's/^-//' |
    sed 's/-$//' |
    # Truncate
    cut -c1-$max_length |
    sed 's/-$//'
}

# Usage
SLUG=$(generate_slug "Fix the authentication redirect loop in OAuth flow")
echo "$SLUG"  # fix-authentication-redirect-loop-oauth
```

### expand_naming_template

Expand a naming template with variables.

```bash
expand_naming_template() {
  local template="$1"
  local number="$2"
  local slug="$3"
  local project="${4:-}"
  local date="${5:-$(date +%Y-%m-%d)}"
  local branch="${6:-main}"

  echo "$template" |
    sed "s/{number}/$number/g" |
    sed "s/{slug}/$slug/g" |
    sed "s/{project}/$project/g" |
    sed "s/{date}/$date/g" |
    sed "s/{branch}/$branch/g"
}

# Usage
NAME=$(expand_naming_template "gh-{number}-{slug}" "123" "fix-login-bug")
echo "$NAME"  # gh-123-fix-login-bug
```

### generate_worktree_name

Generate a worktree name based on source type and config.

```bash
generate_worktree_name() {
  local source_type="$1"  # prompt, github, jira, default
  local number="$2"
  local title="$3"
  local project="${4:-}"

  # Default templates (override with config)
  local template
  case "$source_type" in
    prompt)  template="prompt-{number}-{slug}" ;;
    github)  template="gh-{number}-{slug}" ;;
    jira)    template="{project}-{number}-{slug}" ;;
    *)       template="wt-{slug}" ;;
  esac

  local slug=$(generate_slug "$title")
  expand_naming_template "$template" "$number" "$slug" "$project"
}

# Usage
NAME=$(generate_worktree_name "github" "123" "Fix login redirect bug")
echo "$NAME"  # gh-123-fix-login-redirect-bug
```

## Context Functions

### check_worktree_context

Check location and prepare for worktree creation.

```bash
check_worktree_context() {
  local worktree_name="$1"
  local config_dir="${2:-./}"

  local common_dir=$(get_common_dir)
  local current_dir=$(pwd)

  # Resolve target path
  local target_dir
  case "$config_dir" in
    /*|~*) target_dir="${config_dir/#\~/$HOME}" ;;
    *)     target_dir="$common_dir/$config_dir" ;;
  esac
  local target_path="$target_dir/$worktree_name"

  # Check if at common directory
  if [ "$common_dir" = "$current_dir" ]; then
    echo "at_common_dir"
    echo "$target_path"
  else
    echo "in_worktree"
    echo "$(basename "$current_dir")"
    echo "$target_path"
  fi
}

# Usage
read -r status current_name target_path < <(check_worktree_context "gh-123-fix" "./")
if [ "$status" = "in_worktree" ]; then
  echo "In worktree '$current_name', will create at $target_path"
fi
```

## Error Handling

### worktree_exists

Check if a worktree already exists.

```bash
worktree_exists() {
  local name_or_path="$1"

  if [ -d "$name_or_path" ]; then
    return 0
  fi

  git worktree list --porcelain | grep -q "^worktree .*$name_or_path$"
}

# Usage
if worktree_exists "gh-123-fix"; then
  echo "Worktree already exists"
fi
```

### branch_exists

Check if a branch already exists.

```bash
branch_exists() {
  local branch="$1"
  git branch --list "$branch" | grep -q .
}

# Usage
if branch_exists "gh-123-fix"; then
  echo "Branch exists, will use existing"
fi
```
