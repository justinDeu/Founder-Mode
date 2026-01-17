# Roadmap: founder-mode

## Overview

Build a unified Claude Code plugin that combines daplug's execution power (prompts, sub-agents, worktrees, parallel work) with GSD's project management (greenfield init, roadmaps, phases) while fixing both tools' weaknesses. Self-bootstrapping is a priority: get founder-mode functional enough to use it on itself as early as possible.

## Domain Expertise

None

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: Foundation** - Core skill infrastructure and configuration system
- [ ] **Phase 2: Prompt Workflow** - Task creation and execution with sub-agents
- [ ] **Phase 3: Project Management** - Greenfield workflows with progress visibility
- [ ] **Phase 4: External Integrations** - GitHub and Jira connectivity
- [ ] **Phase 5: Parallel Workflows** - Multi-issue and sprint automation

## Phase Details

### Phase 1: Foundation
**Goal**: Establish the skill file structure, configuration system, and core utilities that all other commands depend on
**Depends on**: Nothing (first phase)
**Research**: Unlikely (Claude Code skills are markdown files, patterns established)
**Plans**: TBD

Key deliverables:
- Skill file structure and naming conventions
- Configuration system (flexible, user-controllable)
- Worktree management with configurable locations
- Environment setup abstraction (language-agnostic)
- Progress display utilities

### Phase 2: Prompt Workflow
**Goal**: Implement /create-prompt and /run-prompt with full sub-agent support and model control
**Depends on**: Phase 1
**Research**: Likely (ralph-wiggum technique, Task tool patterns)
**Research topics**: Ralph-wiggum implementation patterns, optimal sub-agent orchestration, model selection strategies
**Plans**: TBD

Key deliverables:
- /create-prompt command
- /run-prompt command with model control
- Sub-agent orchestration layer
- Background execution with progress monitoring
- Simple single-prompt execution path (not overwhelming)

### Phase 3: Project Management
**Goal**: Implement greenfield project workflows that are transparent about decisions and show clear progress
**Depends on**: Phase 2
**Research**: Unlikely (adapting GSD patterns, internal work)
**Plans**: TBD

Key deliverables:
- /new-project with deep context gathering
- /create-roadmap with phase breakdown
- /plan-phase and /execute-plan
- Clean state management
- Progress indicators during execution
- Consultation before assumptions

### Phase 4: External Integrations
**Goal**: Pull tasks from and push issues to GitHub and Jira
**Depends on**: Phase 2
**Research**: Likely (GitHub CLI, Jira API patterns)
**Research topics**: gh CLI for issue management, Jira REST API or CLI options, authentication patterns
**Plans**: TBD

Key deliverables:
- GitHub issue fetching
- Jira ticket fetching
- Issue push to GitHub/Jira
- /fix-gh-issue end-to-end workflow

### Phase 5: Parallel Workflows
**Goal**: Enable multi-issue parallel execution and smooth sprint automation
**Depends on**: Phase 3, Phase 4
**Research**: Likely (parallel agent coordination, worktree management at scale)
**Research topics**: Coordinating multiple background agents, worktree lifecycle management, progress aggregation across parallel work
**Plans**: TBD

Key deliverables:
- "Show my GitHub issues" command
- "Go fix 123, 312, 413" parallel execution
- Sprint execution without abrupt /clear loops
- Progress aggregation across parallel agents

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 1/1 | Complete | 2026-01-16 |
| 2. Prompt Workflow | 1/2 | In progress | - |
| 3. Project Management | 0/TBD | Not started | - |
| 4. External Integrations | 0/TBD | Not started | - |
| 5. Parallel Workflows | 0/TBD | Not started | - |
