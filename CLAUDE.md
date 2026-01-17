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
logs_dir: .founder_mode/logs/
prompts_dir: ./prompts/
</founder_mode_config>
```

**Settings:**
- `worktree_dir` - Where to create isolated worktrees (default: `.worktrees/`)
- `logs_dir` - Where to store execution logs (default: `.founder_mode/logs/`)
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
