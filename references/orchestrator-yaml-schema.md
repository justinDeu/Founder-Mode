# Orchestrator YAML Schema

Complete schema definition for workflow configuration files.

## Overview

Orchestrator YAML files define workflow DAGs (Directed Acyclic Graphs) for executing multiple prompts with dependency management.

**Key principle:** Every workflow MUST converge to a single sink node (the final prompt with no dependents).

## Complete Schema

```yaml
workflows:                        # REQUIRED, map, non-empty
  <workflow-id>:                  # string key, user-defined identifier
    base: <branch-name>           # REQUIRED, string, non-empty, branch to create from
    branch: <branch-name>         # REQUIRED, string, valid git branch name, working branch

    on_complete:                  # OPTIONAL, map, actions when sink completes
      create_pr: <bool>           # OPTIONAL, default false, create GitHub PR
      merge_to: <branch-name>     # OPTIONAL, mutually exclusive with create_pr
      delete_worktree: <bool>     # OPTIONAL, default true, cleanup temp worktrees

    prompts:                      # REQUIRED, map, non-empty, DAG of prompts
      <prompt-id>:                # string key, user-defined identifier
        path: <file-path>         # REQUIRED, string, file must exist relative to repo root
        after: [<prompt-ids>]     # OPTIONAL, list of strings, default [], dependencies
        model: <model-name>       # OPTIONAL, enum, default "claude", model to use
```

## Field Constraints

### workflows

**Type:** Map (string → workflow object)
**Required:** Yes
**Constraints:** Non-empty, no unknown keys at workflow level

**Example:**
```yaml
workflows:
  auth-feature:
    base: main
    branch: gh-123-auth
    prompts: {...}

  logging-feature:
    base: main
    branch: gh-124-logging
    prompts: {...}
```

### workflows.<id>.base

**Type:** String
**Required:** Yes
**Constraints:** Non-empty, must be valid git branch

**Purpose:** Branch to create the workflow worktree from

### workflows.<id>.branch

**Type:** String
**Required:** Yes
**Constraints:** Non-empty, valid git branch name (no special chars)

**Purpose:** Working branch name for this workflow

### workflows.<id>.on_complete

**Type:** Map
**Required:** No
**Allowed keys:** `create_pr`, `merge_to`, `delete_worktree`

**Constraints:**
- `create_pr` and `merge_to` are mutually exclusive
- No other keys allowed

**Fields:**
- `create_pr` (bool, default: false) - Create GitHub PR when sink completes
- `merge_to` (string) - Merge workflow branch into this branch (mutually exclusive with create_pr)
- `delete_worktree` (bool, default: true) - Remove temp worktrees after completion

**Example:**
```yaml
on_complete:
  create_pr: true
  delete_worktree: true
```

### workflows.<id>.prompts

**Type:** Map (string → prompt object)
**Required:** Yes
**Constraints:** Non-empty, no unknown keys at prompt level

### workflows.<id>.prompts.<id>.path

**Type:** String
**Required:** Yes
**Constraints:** File must exist relative to repository root

**Purpose:** Path to prompt .md file

**Example:** `prompts/001-setup.md`

### workflows.<id>.prompts.<id>.after

**Type:** List of strings
**Required:** No
**Default:** []
**Constraints:** All items must be valid prompt IDs in the same workflow

**Purpose:** Dependencies - this prompt runs after all listed prompts complete

**Example:**
```yaml
prompts:
  setup:
    path: prompts/001-setup.md

  impl:
    path: prompts/002-impl.md
    after: [setup]  # impl runs after setup
```

### workflows.<id>.prompts.<id>.model

**Type:** String (enum)
**Required:** No
**Default:** "claude"
**Allowed values:**

| Value | Description |
|-------|-------------|
| `claude` | Claude via Task subagent |
| `codex` | OpenAI Codex via executor |
| `gemini` | Gemini via executor |
| `zai` | Z.AI via executor |
| `opencode` | OpenCode via executor |
| `opencode-zai` | OpenCode with Z.AI backend |
| `opencode-codex` | OpenCode with Codex backend |
| `claude-zai` | Claude via Z.AI API |

**Purpose:** Override default model for this specific prompt

## DAG Rules

Every workflow forms a Directed Acyclic Graph (DAG) that MUST converge to a single sink node.

### Rule 1: Exactly One Sink

The sink is the prompt with no dependents (no other prompt lists it in `after`).

**Valid (single sink):**
```yaml
workflows:
  test:
    base: main
    branch: test-branch
    prompts:
      setup: {path: prompts/001.md}
      impl: {path: prompts/002.md, after: [setup]}
      tests: {path: prompts/003.md, after: [impl]}  # <- sink (no dependents)
```

**Invalid (multiple sinks):**
```yaml
workflows:
  test:
    base: main
    branch: test-branch
    prompts:
      setup: {path: prompts/001.md}
      tests: {path: prompts/002.md, after: [setup]}  # <- sink
      docs: {path: prompts/003.md, after: [setup]}   # <- sink (ERROR!)
```

**Error:** `Multiple sinks found: {'tests', 'docs'}. DAG must converge to single sink.`

### Rule 2: No Cycles

Prompts cannot depend on each other directly or indirectly.

**Invalid (cycle):**
```yaml
workflows:
  test:
    base: main
    branch: test-branch
    prompts:
      a: {path: prompts/001.md, after: [b]}
      b: {path: prompts/002.md, after: [a]}  # <- cycle!
```

**Error:** `Cycle detected in dependency graph`

### Rule 3: All Paths Reach Sink

Every prompt must be reachable from an entry point (no `after`) and must be able to reach the sink.

**Valid:**
```yaml
prompts:
  setup: {path: prompts/001.md}          # entry (no deps)
  db: {path: prompts/002.md}             # entry (no deps)
  impl: {path: prompts/003.md, after: [setup, db]}  # waits for both
  tests: {path: prompts/004.md, after: [impl]}      # sink
```

**Invalid (disconnected):**
```yaml
prompts:
  setup: {path: prompts/001.md}
  impl: {path: prompts/002.md, after: [setup]}
  tests: {path: prompts/003.md, after: [impl]}
  orphan: {path: prompts/999.md}  # <- can't reach sink, sink can't reach it
```

**Error:** `DAG has disconnected nodes or unreachable paths`

### Rule 4: References Must Exist

All `after` references must point to valid prompt IDs in the same workflow.

**Invalid:**
```yaml
prompts:
  impl: {path: prompts/002.md, after: [setup]}  # <- 'setup' doesn't exist
```

**Error:** `Invalid reference: 'setup' not found in prompts`

## Wave Computation

Waves are computed via topological sort:

1. **Wave 1:** All prompts with no `after` dependencies (entry points)
2. **Wave N:** All prompts whose `after` deps are satisfied by waves 1..N-1
3. **Sink reached:** Wave containing the sink prompt

**Example:**
```yaml
prompts:
  a: {path: prompts/001.md}           # Wave 1
  b: {path: prompts/002.md}           # Wave 1
  c: {path: prompts/003.md, after: [a]}  # Wave 2
  d: {path: prompts/004.md, after: [a, b]}  # Wave 2
  e: {path: prompts/005.md, after: [c, d]}  # Wave 3 (sink)
```

**Waves:** `[[a, b], [c, d], [e]]`

## Validation Errors

### Unknown Field

```yaml
workflows:
  test:
    base: main
    branch: test-branch
    promts:  # <- typo
      a: {path: prompts/001.md}
```

**Error:** `Unknown field 'workflows.test.promts' (did you mean 'prompts'?)`

### Invalid Model

```yaml
prompts:
  a: {path: prompts/001.md, model: gpt-4}  # <- not in enum
```

**Error:** `Invalid model 'gpt-4' in 'workflows.test.prompts.a' (allowed: claude, codex, gemini, zai, opencode, opencode-zai, opencode-codex, claude-zai)`

### Mutual Exclusivity Violation

```yaml
on_complete:
  create_pr: true
  merge_to: main  # <- can't have both
```

**Error:** `Cannot specify both 'create_pr' and 'merge_to' in on_complete`

### Missing File

```yaml
prompts:
  a: {path: prompts/missing.md}  # <- file doesn't exist
```

**Error:** `Prompt path does not exist: prompts/missing.md`

## Examples

### Example 1: Single Prompt

```yaml
workflows:
  simple:
    base: main
    branch: gh-100-simple-fix
    on_complete:
      create_pr: true

    prompts:
      fix:
        path: prompts/001-fix-bug.md
```

**Waves:** `[[fix]]`

### Example 2: Serial Chain

```yaml
workflows:
  chain:
    base: main
    branch: gh-101-feature-chain

    prompts:
      design:
        path: prompts/010-design.md

      implement:
        path: prompts/011-implement.md
        after: [design]

      test:
        path: prompts/012-test.md
        after: [implement]

      review:
        path: prompts/013-review.md
        after: [test]  # sink
```

**Waves:** `[[design], [implement], [test], [review]]`

### Example 3: Parallel Then Merge

```yaml
workflows:
  parallel-feature:
    base: main
    branch: gh-102-parallel

    prompts:
      setup:
        path: prompts/020-setup.md

      frontend:
        path: prompts/021-frontend.md
        after: [setup]

      backend:
        path: prompts/022-backend.md
        after: [setup]

      integration:
        path: prompts/023-integration.md
        after: [frontend, backend]  # waits for both (sink)
```

**Waves:** `[[setup], [frontend, backend], [integration]]`

### Example 4: Complex DAG

```yaml
workflows:
  auth-overhaul:
    base: main
    branch: gh-103-auth
    on_complete:
      create_pr: true

    prompts:
      # Wave 1: Foundation
      db-schema:
        path: prompts/100-db.md
        model: codex

      models:
        path: prompts/101-models.md

      # Wave 2: Implementation
      backend-auth:
        path: prompts/102-backend.md
        after: [db-schema, models]

      # Wave 3: Frontend (depends on backend)
      frontend-auth:
        path: prompts/103-frontend.md
        after: [backend-auth]

      # Wave 4: Testing (sink)
      auth-tests:
        path: prompts/104-tests.md
        after: [frontend-auth]
```

**Waves:** `[[db-schema, models], [backend-auth], [frontend-auth], [auth-tests]]`

### Example 5: Multiple Workflows

```yaml
workflows:
  auth-feature:
    base: main
    branch: gh-200-auth
    prompts:
      setup: {path: prompts/200-setup.md}
      impl: {path: prompts/201-impl.md, after: [setup]}

  logging-feature:
    base: main
    branch: gh-201-logging
    prompts:
      add-logging: {path: prompts/210-logging.md}
      verify: {path: prompts/211-verify.md, after: [add-logging]}
```

## Migration from Markdown Orchestrator

**Before (markdown):**
```markdown
## Dependency Graph
```
003-01 (state-management)
    |
    v
003-02 (new-project)
```

### Wave 1: Foundation
1. `003-01-state-management.md` - Setup
```

**After (YAML):**
```yaml
workflows:
  phase-3:
    base: main
    branch: gh-3-phase-3

    prompts:
      state-management:
        path: prompts/003-01-state-management.md

      new-project:
        path: prompts/003-02-new-project.md
        after: [state-management]  # sink
```
