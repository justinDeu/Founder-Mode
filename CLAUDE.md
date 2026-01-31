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
worktree_dir: ~/.worktrees/
logs_dir: .founder-mode/logs/
prompts_dir: ./prompts/
</founder_mode_config>
```

**Settings:**
- `worktree_dir` - Where to create isolated worktrees (default: `.worktrees/`)
- `logs_dir` - Where to store execution logs (default: `.founder-mode/logs/`)
- `prompts_dir` - Where prompts live (default: `./prompts/`)

Priority: project CLAUDE.md > user ~/.claude/CLAUDE.md

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

## Deviation Handling

During prompt execution, follow the deviation rules in `references/deviation-rules.md`:

- **Rules 1-3:** Auto-fix bugs, critical functionality, and blockers
- **Rule 4:** Checkpoint for architectural decisions

Always document deviations in output.
