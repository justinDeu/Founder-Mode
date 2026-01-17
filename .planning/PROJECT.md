# founder-mode

## What This Is

A unified Claude Code plugin that combines the capabilities of daplug (prompt creation, sub-agents, worktrees, parallel execution) and GSD (project management, greenfield workflows, roadmaps) while fixing both their shortcomings. One tool that handles everything from quick one-off tasks to full project lifecycles.

## Core Value

Moving rapidly in the right direction at all times with a clear vision.

## Requirements

### Validated

(None yet - ship to validate)

### Active

**Prompt & Task Execution (from daplug)**
- [ ] /create-prompt for one-off task creation
- [ ] /run-prompt for executing prompts with model control
- [ ] Sub-agent orchestration with configurable models
- [ ] Background agent execution with progress monitoring
- [ ] Worktree management with configurable locations
- [ ] Ralph-wiggum technique for running work

**Project Management (from GSD)**
- [ ] Greenfield project initialization with in-depth decision gathering
- [ ] Roadmap creation with phases
- [ ] Plan creation and execution
- [ ] Progress tracking and state management

**External Integrations**
- [ ] Pull tasks from GitHub issues
- [ ] Pull tasks from Jira tickets
- [ ] Push issues to remote sources (GitHub, Jira)
- [ ] End-to-end workflows like /fix-gh-issue that autonomously handle worktree setup, code reading, prompt creation, and execution

**Parallel Workflows**
- [ ] Multi-issue parallel execution via sub-agents
- [ ] "Show my GitHub issues" -> "Go fix 123, 312, 413" workflow
- [ ] Sprint execution that runs through tasks without abrupt /clear loops

**Configuration & Flexibility**
- [ ] Language-agnostic environment setup (user specifies how)
- [ ] Configurable worktree locations (top-level, not hidden in .worktrees/)
- [ ] All options flexible, nothing hardcoded in Python
- [ ] User preferences in CLAUDE.md respected

**State & Visibility**
- [ ] Clean internal state that's easy to navigate
- [ ] Clear progress indicators during execution
- [ ] Consistent issue tracking
- [ ] True memory system integration (beads or internal)

**Transparency**
- [ ] Explicit about decisions being made
- [ ] Consultation before assumptions
- [ ] Clear visibility into what will be executed (like reading a prompt in daplug)
- [ ] Architecture and purpose confirmed upfront in greenfield workflows

### Out of Scope

- Enterprise/team features - this is for solo founder-mode work
- GUI/web interface - CLI only
- Non-Claude AI providers - Claude Code specific

## Context

**Existing tools being unified:**
- daplug: Prompt-based workflow tool with sub-agents, worktrees, parallel execution. Strengths in execution, weaknesses in configuration rigidity and complexity.
- GSD (Get Shit Done): Project management framework with phases and plans. Strengths in getting started fast, weaknesses in assumptions, no sub-agents, poor progress visibility, abrupt workflow.

**Key frustrations to address:**
- GSD makes assumptions without asking, unclear what it will actually do
- daplug's /run-prompt became overwhelming with too many options
- Neither shows progress during execution
- GSD's constant /clear-and-run-next loop breaks flow
- Inconsistent issue tracking in GSD
- daplug hardcodes too much in Python, not language-agnostic

**Self-bootstrapping goal:**
Use founder-mode to build founder-mode as quickly as possible. The tool should be functional enough early to assist in its own development.

## Constraints

- **Platform**: Must work with Claude Code CLI as skills/commands
- **Architecture**: Built as Claude Code skills (markdown command files), not Python plugins
- **Compatibility**: Must integrate with existing Claude Code tooling (Task, Bash, etc.)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Unify daplug + GSD | Both tools have complementary strengths; combining avoids context switching | - Pending |
| Full scope in v1 | Core value is moving rapidly; artificial constraints slow momentum | - Pending |
| Skills-based architecture | Avoids daplug's Python rigidity, keeps everything in user-configurable markdown | - Pending |

---
*Last updated: 2026-01-16 after initialization*
