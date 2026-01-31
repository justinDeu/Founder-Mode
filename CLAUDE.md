# founder-mode

AI-assisted development workflows for Claude Code.

## Overview

founder-mode provides structured workflows for software development using AI assistance. It enables:

- Prompt execution with isolated worktrees
- Parallel task management across multiple agents
- Structured project planning and execution
- Context preservation between sessions

## Configuration

Configure founder-mode using the `<founder_mode_config>` block in your project's CLAUDE.md or user's `~/.claude/CLAUDE.md`:

```xml
<founder_mode_config>
worktree_dir: ./
logs_dir: .founder-mode/logs/
prompts_dir: ./prompts/
worktree_naming:
  prompt: prompt-{number}-{slug}
  github: gh-{number}-{slug}
  jira: {project}-{number}-{slug}
  default: wt-{slug}
</founder_mode_config>
```

**Settings:**
- `worktree_dir` - Where to create isolated worktrees, relative to git common directory (default: `./`)
- `logs_dir` - Where to store execution logs (default: `.founder-mode/logs/`)
- `prompts_dir` - Where prompts live (default: `./prompts/`)
- `worktree_naming` - Naming templates per source type (see below)

Priority: project CLAUDE.md > user ~/.claude/CLAUDE.md

### Worktree Configuration

**worktree_dir** specifies where worktrees are created. Paths resolve relative to the git common directory (the shared `.git` location), not the current working directory.

| Value | Layout | Example Result |
|-------|--------|----------------|
| `./` | Flat siblings | `/project/gh-123-fix-bug` |
| `./.worktrees/` | Nested subdirectory | `/project/.worktrees/gh-123-fix-bug` |
| `~/.worktrees/myproject/` | Absolute path | `~/.worktrees/myproject/gh-123-fix-bug` |

**worktree_naming** defines how worktrees are named based on their source:

| Source | Template | Example |
|--------|----------|---------|
| `prompt` | `prompt-{number}-{slug}` | `prompt-006-git-worktree-integration` |
| `github` | `gh-{number}-{slug}` | `gh-123-fix-login-redirect` |
| `jira` | `{project}-{number}-{slug}` | `PROJ-456-add-auth-flow` |
| `default` | `wt-{slug}` | `wt-my-feature` |

**Available variables:**
- `{number}` - Issue/prompt number
- `{slug}` - Sanitized title (max 30 chars, lowercase, hyphens)
- `{project}` - Jira project key
- `{date}` - Current date (YYYY-MM-DD)
- `{branch}` - Base branch name

### Future: Environment Setup (Planned)

```xml
<founder_mode_config>
worktree_setup:
  detect: true
  hooks:
    - ./scripts/setup-env.sh
</founder_mode_config>
```

When implemented, this will auto-detect project type and run setup after worktree creation.

## Available Commands

### /fm:commit

Create a git commit following the Conventional Commits specification.

```
/fm:commit [--amend] [--no-verify]
```

**Arguments:**
- `--amend` - Amend the previous commit
- `--no-verify` - Skip pre-commit hooks

Analyzes staged changes to determine commit type (feat, fix, docs, etc.), writes a properly formatted message, and prompts for documentation updates when relevant.

**Examples:**
```
/fm:commit
/fm:commit --amend
```

### /fm:run-prompt

Execute a prompt with Claude or other AI models.

```
/fm:run-prompt <prompt-file> [--model claude|codex|gemini] [--background] [--worktree]
```

**Arguments:**
- `<prompt-file>` - Path to prompt .md file (required)
- `--model` - Model to use (default: `claude`)
- `--background` - Run in background
- `--worktree` - Create isolated git worktree

**Examples:**
```
/fm:run-prompt prompts/001-setup.md
/fm:run-prompt prompts/001-setup.md --model codex --worktree
```

### /fm:orchestrate

Execute multiple prompts with dependency management and parallel execution.

```
/fm:orchestrate <orchestrator-file|prompt-list> [--model ?|claude|codex|...] [--pending-only]
```

**Arguments:**
- `<input>` - Orchestrator .md file OR comma-separated prompt IDs
- `--model` - Default model. Use `?` for per-prompt selection.
- `--pending-only` - Skip prompts marked complete in orchestrator
- `--worktree` - Create isolated worktree per prompt
- `--background` - Run non-Claude models in background

**Examples:**
```
/fm:orchestrate prompts/phase-completion/000-orchestrator.md
/fm:orchestrate 003-01,003-02,003-03 --model codex
/fm:orchestrate prompts/000-orchestrator.md --pending-only --background
```

## Deviation Handling

During prompt execution, follow the deviation rules in `references/deviation-rules.md`:

- **Rules 1-3:** Auto-fix bugs, critical functionality, and blockers
- **Rule 4:** Checkpoint for architectural decisions

Always document deviations in output.
