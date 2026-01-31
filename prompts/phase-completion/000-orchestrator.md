# Phase Completion Orchestrator

## Objective

Coordinate execution of all sub-prompts to complete founder-mode Phases 3, 4, and 5. This prompt tracks dependencies, manages execution order, and handles rollback if needed.

## Prerequisites

- Phases 1-2 complete (commands/create-prompt.md and commands/run-prompt.md exist)
- Project initialized at /home/thor/fun/founder-mode/dev
- GSD patterns available at ../get-shit-done/ for reference

## Dependency Graph

```
003-01 (state-management)
    |
    v
003-02 (new-project) ─────────────────────┐
    |                                     |
    v                                     |
003-03 (discuss-phase)                    |
    |                                     |
    v                                     |
003-04 (plan-phase)                       |
    |                                     |
    v                                     |
003-06 (verification-agents) <────────────┤
    |                                     |
    v                                     |
003-05 (execute-phase)                    |
    |                                     |
    v                                     |
004-01 (github) ──────────────────────────┤
    |                                     |
    v                                     |
004-02 (jira) ────────────────────────────┤
    |                                     |
    v                                     |
004-03 (fix-gh-issue) <───────────────────┘
    |
    v
005-01 (parallel-execution)
    |
    v
005-02 (sprint-workflow)
```

## Execution Order

### Wave 1: Foundation (sequential, critical path)

Execute in strict order:

1. `003-01-state-management.md` - Directory structure and state utilities
2. `003-02-new-project.md` - Project initialization command
3. `003-03-discuss-phase.md` - User vision capture command
4. `003-04-plan-phase.md` - Planning with validation loop
5. `003-06-verification-agents.md` - Plan-checker and verifier agents
6. `003-05-execute-phase.md` - Wave-based execution (depends on verification agents)

### Wave 2: External Integrations (can parallelize 004-01 and 004-02)

7. `004-01-github-integration.md` - GitHub issue fetching
8. `004-02-jira-integration.md` - Jira ticket fetching (parallel with 004-01)
9. `004-03-fix-gh-issue.md` - End-to-end fix workflow (after 004-01)

### Wave 3: Parallel Workflows (sequential)

10. `005-01-parallel-execution.md` - Multi-issue parallel execution
11. `005-02-sprint-workflow.md` - Sprint automation

## Execution Protocol

For each prompt:

1. Verify prerequisites from `Prerequisites` section are met
2. Execute the prompt completely
3. Run verification steps from `Verification` section
4. If verification passes, mark complete and proceed
5. If verification fails, diagnose and fix before proceeding
6. Commit all files created/modified

## State Tracking

Track completion state in this file:

```
[x] 003-01-state-management.md
[x] 003-02-new-project.md
[x] 003-03-discuss-phase.md
[x] 003-04-plan-phase.md
[x] 003-06-verification-agents.md
[x] 003-05-execute-phase.md
[x] 004-01-github-integration.md
[x] 004-02-jira-integration.md
[x] 004-03-fix-gh-issue.md
[ ] 005-01-parallel-execution.md
[ ] 005-02-sprint-workflow.md
```

## Rollback Instructions

If a prompt fails and corrupts state:

### For state-management (003-01):

```bash
rm -rf .founder-mode/
git checkout -- .founder-mode/
```

### For command files (003-02 through 005-02):

```bash
git checkout -- commands/{command-name}.md
git checkout -- agents/{agent-name}.md
```

### Full rollback:

```bash
git reset --hard HEAD~N  # Where N is number of commits to undo
```

## Context Files to Read Before Starting

```
.planning/PROJECT.md      - Requirements and constraints
.planning/ROADMAP.md      - Phase definitions
.planning/STATE.md        - Current position
commands/create-prompt.md - Existing command pattern
commands/run-prompt.md    - Existing command pattern
```

## Success Criteria

- [ ] All 12 prompt files executed successfully
- [ ] Each prompt's verification steps pass
- [ ] All commands are callable via /fm:{command}
- [ ] State management utilities work correctly
- [ ] Verification agents can be spawned
- [ ] Integration tests pass (if applicable)

## Notes

- Adapt GSD patterns to founder-mode's skills-based architecture
- Keep commands focused on single responsibility
- Include rollback instructions in each prompt
- Reference existing command patterns for consistency
- Test incrementally as each prompt completes
