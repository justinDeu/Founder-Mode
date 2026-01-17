# founder-mode

AI-assisted development workflows for Claude Code.

## Overview

founder-mode provides structured workflows for software development using AI assistance. It enables:

- Prompt execution with isolated worktrees
- Parallel task management across multiple agents
- Structured project planning and execution
- Context preservation between sessions

## Configuration

Configure founder-mode using the `<founder_mode_config>` XML block in your project's CLAUDE.md:

```xml
<founder_mode_config>
  <project>
    <name>your-project</name>
    <worktree_base>~/worktrees</worktree_base>
  </project>
  <prompts>
    <directory>.prompts</directory>
  </prompts>
</founder_mode_config>
```

## Available Commands

Commands will be added as the plugin develops.
