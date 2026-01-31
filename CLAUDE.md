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

### /founder-mode:run-prompt

Execute a prompt with Claude or other AI models.

```
/founder-mode:run-prompt <prompt-file> [--model claude|codex|gemini] [--background] [--worktree]
```

**Arguments:**
- `<prompt-file>` - Path to prompt .md file (required)
- `--model` - Model to use (default: `claude`)
- `--background` - Run in background
- `--worktree` - Create isolated git worktree

**Examples:**
```
/founder-mode:run-prompt prompts/001-setup.md
/founder-mode:run-prompt prompts/001-setup.md --model codex --worktree
```

### /founder-mode:orchestrate

Execute multiple prompts with dependency management and parallel execution.

```
/founder-mode:orchestrate <orchestrator-file|prompt-list> [--model ?|claude|codex|...] [--pending-only]
```

**Arguments:**
- `<input>` - Orchestrator .md file OR comma-separated prompt IDs
- `--model` - Default model. Use `?` for per-prompt selection.
- `--pending-only` - Skip prompts marked complete in orchestrator
- `--worktree` - Create isolated worktree per prompt
- `--background` - Run non-Claude models in background

**Examples:**
```
/founder-mode:orchestrate prompts/phase-completion/000-orchestrator.md
/founder-mode:orchestrate 003-01,003-02,003-03 --model codex
/founder-mode:orchestrate prompts/000-orchestrator.md --pending-only --background
```

## Skills

### commit-conventions

Provides conventional commit formatting guidelines. Claude auto-loads this skill when creating commits, staging changes, or finalizing work.

The skill ensures all commits follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Commit Types:** feat, fix, docs, style, refactor, perf, test, build, ci, chore

**Key Guidelines:**
- Use imperative mood in descriptions
- Keep descriptions under 72 characters
- Include body only for complex changes
- Never stage all files without confirmation
- Reference issues in footer when applicable

See `skills/commit/SKILL.md` for full details.

## Deviation Handling

During prompt execution, follow the deviation rules in `references/deviation-rules.md`:

- **Rules 1-3:** Auto-fix bugs, critical functionality, and blockers
- **Rule 4:** Checkpoint for architectural decisions

Always document deviations in output.
