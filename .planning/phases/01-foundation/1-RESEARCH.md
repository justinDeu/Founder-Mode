# Phase 1: Foundation - Research

**Researched:** 2026-01-16
**Domain:** Claude Code plugin architecture, skill systems, sub-agent handling
**Confidence:** HIGH

<research_summary>
## Summary

Researched daplug and GSD to understand how to build a Claude Code plugin foundation. The critical finding is the **ralph-wiggum problem**: sub-agents spawned via Task tool don't inherit skill context from the parent conversation. Daplug solves this through explicit context injection via executor.py, which resolves all paths/metadata upfront and returns JSON that the orchestrator interpolates into Task prompts.

The standard approach for configuration is XML blocks in CLAUDE.md (`<daplug_config>`) with project-level overriding user-level. Skills are markdown files with YAML frontmatter. State persists to disk (JSON/markdown) so agents can resume where others stopped.

**Primary recommendation:** Use daplug's executor pattern for sub-agent handling. Configuration via CLAUDE.md XML blocks. State in .planning/ directory. Skills as self-contained markdown with allowed-tools frontmatter.
</research_summary>

<standard_stack>
## Standard Stack

### Core Components
| Component | Implementation | Purpose | Why Standard |
|-----------|---------------|---------|--------------|
| Skills | `~/.claude/commands/{namespace}/*.md` | User-invocable commands | Claude Code native pattern |
| Configuration | `<daplug_config>` in CLAUDE.md | User settings | Readable, editable, version-controllable |
| State | `.planning/STATE.md` | Project memory | Visible, auditable, git-tracked |
| Sub-agent handling | Python executor script | Context injection | Solves ralph-wiggum problem |

### Supporting Components
| Component | Implementation | Purpose | When to Use |
|-----------|---------------|---------|-------------|
| Agents | `~/.claude/agents/*.md` | Background task definitions | Specialized monitoring/execution |
| Workflows | `~/.claude/get-shit-done/workflows/*.md` | Complex orchestration | Multi-step processes |
| Templates | `~/.claude/get-shit-done/templates/*.md` | Reusable structures | Consistent file generation |
| Hooks | `hooks/*.json` or shell scripts | Event automation | Post-tool actions |

### File Locations
```
~/.claude/
├── commands/founder-mode/     # Slash commands
├── agents/                    # Background agents
├── settings.json              # Permissions, hooks
└── CLAUDE.md                  # User config

.planning/                     # Project state (in repo)
├── PROJECT.md
├── STATE.md
├── ROADMAP.md
└── phases/XX-name/
```

**Installation:** Skills are markdown files. No npm/pip dependencies for core functionality.
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Recommended Skill File Structure
```yaml
---
name: founder-mode:command-name
description: One-line description
argument-hint: "<required>" or "[optional]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Task
  - AskUserQuestion
---

<objective>What/why/when</objective>
<execution_context>@references/to/templates</execution_context>
<context>Dynamic content: $ARGUMENTS, @file-refs</context>
<process><step name="step-name">Implementation</step></process>
<success_criteria>Measurable checklist</success_criteria>
```

### Pattern 1: Executor Pattern (Ralph-Wiggum Solution)
**What:** Python script resolves all context upfront, returns JSON for orchestrator to interpolate into Task prompts
**When to use:** Any skill that spawns sub-agents
**How it works:**
```
1. User invokes skill (e.g., /founder-mode:run-prompt 123)
2. Skill calls executor.py with arguments
3. Executor resolves:
   - Prompt file path and content
   - Worktree creation if needed
   - Log file paths
   - State file paths
4. Executor returns JSON with complete context
5. Skill parses JSON, spawns Task with interpolated values:

   Task(
     subagent_type: "general-purpose",
     prompt: """
       Working in: {worktree_path}
       Execute: {prompt_content}
       Log to: {log_file}
     """
   )
```

**Key insight:** Sub-agents receive ALL context via prompt text. Nothing is inherited.

### Pattern 2: Configuration via CLAUDE.md
**What:** XML blocks in CLAUDE.md store settings, priority is project > user
**When to use:** Any user-configurable setting
**Example:**
```python
# From daplug config.py
def resolve_setting(key, project, user):
    if key in project.data:
        return project.data[key], "project"
    if key in user.data:
        return user.data[key], "user"
    return None, "none"
```

### Pattern 3: State as Persistent Memory
**What:** STATE.md tracks project position, decisions, blockers across sessions
**When to use:** Any multi-session workflow
**Structure:**
```markdown
## Current Position
Phase: 1 of 5 (Foundation)
Plan: 1 of 3
Status: In progress

## Accumulated Context
### Decisions
- Decision 1: [rationale]

### Deferred Issues
- Issue 1: [why deferred]
```

### Pattern 4: Checkpoint + Continuation
**What:** When an agent pauses, return structured state for next agent to continue
**When to use:** Long-running tasks that may be interrupted
**Example from GSD:**
```xml
<completed_tasks>
  <task name="Task 1" commit="abc123">Done</task>
  <task name="Task 2" commit="def456">Done</task>
</completed_tasks>
<resume_from>Task 3</resume_from>
```

Next agent receives this in prompt, verifies commits exist, continues from Task 3.

### Anti-Patterns to Avoid
- **Assuming context inheritance:** Task sub-agents start fresh, always inject context explicitly
- **Hidden state in ~/.claude/:** Keep project state in .planning/ so it's visible and version-controlled
- **Hardcoded paths:** Always use configuration, never assume paths
- **Silent defaults:** If config is missing, prompt user rather than assuming
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Config reading | Custom parser | Daplug's config.py pattern | Handles priority, legacy migration, validation |
| Sub-agent context | Hoping for inheritance | Executor pattern with JSON | Ralph-wiggum problem is real |
| Worktree management | Manual git commands | Executor with dependency install | Edge cases: conflicts, permissions, cleanup |
| State persistence | In-memory variables | Markdown files in .planning/ | Sessions end, files persist |
| Loop verification | Manual re-running | Loop state with markers | Need history, retry reasons, suggested next steps |
| Permission setup | Manual settings.json editing | Programmatic via config.py | Consistent, won't break existing permissions |

**Key insight:** Daplug has solved these problems. The executor.py pattern handles worktree creation, dependency installation, CLI launching, verification loops, and state management. Don't rebuild this from scratch.
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Ralph-Wiggum (Context Loss in Sub-Agents)
**What goes wrong:** Sub-agent doesn't know about skills, state, or previous conversation
**Why it happens:** Task tool starts fresh context, no automatic inheritance
**How to avoid:**
- Executor resolves ALL context before spawning
- Interpolate everything into Task prompt text
- Include file paths, state, and explicit instructions
**Warning signs:** Sub-agent asks "what file?" or "where should I look?"

### Pitfall 2: Shell Breaks After Worktree Deletion
**What goes wrong:** All bash commands fail with "No such file or directory"
**Why it happens:** CWD was the worktree being deleted
**How to avoid:** Always `cd "$REPO_ROOT"` before removing worktree
**Warning signs:** Exit code 1 on every bash command, even `echo test`

### Pitfall 3: Configuration Not Found Silently
**What goes wrong:** Skill uses wrong path or default when user expected configured value
**Why it happens:** Falling back to default without checking config
**How to avoid:**
- Always check config first
- If missing, prompt user with AskUserQuestion
- Store their choice in CLAUDE.md
**Warning signs:** Worktrees appearing in unexpected locations

### Pitfall 4: Permissions Missing for Worktrees
**What goes wrong:** Claude can't read/write files in worktree directory
**Why it happens:** Worktree may be outside repo, needs explicit permission
**How to avoid:**
- Check/update ~/.claude/settings.json programmatically
- Add to `permissions.allow` and `additionalDirectories`
**Warning signs:** Permission denied errors, files not visible to Claude

### Pitfall 5: State Drift Across Sessions
**What goes wrong:** Resume finds unexpected state, decisions lost
**Why it happens:** State only in memory, not persisted
**How to avoid:**
- Write STATE.md after every significant action
- Include timestamp, position, and recent decisions
- Use checkpoint pattern for long-running work
**Warning signs:** "What was I doing?" questions, repeated work
</common_pitfalls>

<code_examples>
## Code Examples

### Skill File Structure
```yaml
# Source: daplug/commands/run-prompt.md
---
name: run-prompt
description: Execute prompts from ./prompts/
argument-hint: <prompt(s)> [--model] [--worktree]
---
```

### Executor Pattern - Context Resolution
```python
# Source: daplug/skills/prompt-executor/scripts/executor.py
def main():
    # Resolve prompt file
    prompt_files = resolve_prompts(prompts_dir, args.prompts)

    # Create worktree if requested
    if args.worktree:
        worktree_info = create_worktree(repo_root, prompt_file, args.base_branch)
        execution_cwd = worktree_info["worktree_path"]

    # Build complete context
    prompt_info = {
        "file": str(prompt_file),
        "content": content,
        "worktree": worktree_info,
        "log": str(log_file)
    }

    # Return JSON for orchestrator
    print(json.dumps(result, indent=2))
```

### Configuration Reading
```python
# Source: daplug/skills/config-reader/scripts/config.py
def resolve_setting(key, project, user):
    if key in project.data:
        return project.data[key], "project"
    if key in user.data:
        return user.data[key], "user"
    return None, "none"

# Priority: project CLAUDE.md > user ~/.claude/CLAUDE.md
```

### Verification Loop State
```python
# Source: daplug/skills/prompt-executor/scripts/executor.py
def create_loop_state(prompt_number, ...):
    return {
        "prompt_number": prompt_number,
        "iteration": 0,
        "max_iterations": max_iterations,
        "completion_marker": completion_marker,
        "status": "pending",
        "history": [],
        "suggested_next_steps": []
    }
```

### Task Spawning with Injected Context
```markdown
# Source: daplug/commands/run-prompt.md
Task(
  subagent_type: "general-purpose",
  description: "Execute prompt {NUMBER}",
  run_in_background: true,
  prompt: """
    {If worktree: You are working in: {WORK_DIR}}

    Execute this task completely:

    {PROMPT_CONTENT}

    After implementation:
    1. Make atomic commits
    2. Verify changes work
    3. Return summary
  """
)
```
</code_examples>

<sota_updates>
## State of the Art (2025-2026)

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Python plugins | Markdown skills | 2024 | Skills are self-contained, no installation |
| Manual sub-agent handling | Task tool with subagent_type | 2025 | Standardized parallel execution |
| INI/JSON config | CLAUDE.md XML blocks | 2025 | Human-readable, version-controlled |

**New patterns to consider:**
- **Skill tool:** Can invoke skills directly, not just via slash commands
- **allowed-tools frontmatter:** Restrict what tools a skill can use
- **run_in_background:** Task parameter for non-blocking execution

**Deprecated/outdated:**
- **Python plugins with setup.py:** Use markdown skills instead
- **Relying on context inheritance:** Always inject context explicitly
- **Hidden config files:** Use CLAUDE.md which is visible in repo
</sota_updates>

<open_questions>
## Open Questions

1. **Skill registration for founder-mode namespace**
   - What we know: Skills in `~/.claude/commands/founder-mode/` with `name: founder-mode:command`
   - What's unclear: Whether to use GSD's marketplace structure or simpler flat directory
   - Recommendation: Start with flat directory, add structure if needed

2. **Executor script location**
   - What we know: Daplug uses `skills/{skill-name}/scripts/` pattern
   - What's unclear: Whether founder-mode needs its own executor or can share patterns
   - Recommendation: Create minimal executor focused on founder-mode needs

3. **Progress display utilities**
   - What we know: GSD has patterns (progress bars, status tables, emoji indicators)
   - What's unclear: What's the minimal set needed for Phase 1
   - Recommendation: Start with simple markdown tables, add fancier displays later
</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- `/home/thor/fun/founder-mode/daplug/skills/prompt-executor/scripts/executor.py` - Ralph-wiggum solution, verification loops
- `/home/thor/fun/founder-mode/daplug/skills/config-reader/scripts/config.py` - Configuration pattern
- `/home/thor/fun/founder-mode/daplug/commands/run-prompt.md` - Task spawning pattern
- `/home/thor/fun/founder-mode/daplug/CLAUDE.md` - Architecture overview
- `/home/thor/fun/founder-mode/get-shit-done/` - GSD skill and state patterns

### Secondary (MEDIUM confidence)
- Explore agent research on GSD patterns - comprehensive but summarized
- Explore agent research on Claude Code native patterns - inferred from ~/.claude structure
</sources>

<metadata>
## Metadata

**Research scope:**
- Core technology: Claude Code skills (markdown), Task tool, sub-agent handling
- Ecosystem: Daplug executor pattern, GSD state management
- Patterns: Executor, configuration, state persistence, checkpoints
- Pitfalls: Ralph-wiggum, shell breaks, permissions, state drift

**Confidence breakdown:**
- Standard stack: HIGH - directly read daplug source code
- Architecture: HIGH - executor.py is the canonical solution
- Pitfalls: HIGH - documented in code comments and skill files
- Code examples: HIGH - copied from actual source files

**Research date:** 2026-01-16
**Valid until:** 2026-02-16 (30 days - patterns are stable)
</metadata>

---

*Phase: 01-foundation*
*Research completed: 2026-01-16*
*Ready for planning: yes*
