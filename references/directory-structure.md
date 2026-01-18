# Directory Structure

Standard directory layout for founder-mode project management.

## Structure

```
.founder-mode/
├── PROJECT.md              # Project context, requirements, decisions
├── REQUIREMENTS.md         # REQ-ID tracked requirements with traceability
├── ROADMAP.md              # Phase structure with requirement mappings
├── STATE.md                # Current position, progress, session continuity
├── config.json             # Workflow preferences
├── phases/                 # Phase-specific artifacts
│   └── NN-phase-name/
│       ├── NN-CONTEXT.md   # User decisions from discuss-phase
│       ├── NN-RESEARCH.md  # Domain research outputs
│       ├── NN-XX-PLAN.md   # Execution plans
│       └── NN-XX-SUMMARY.md # Completion summaries
├── research/               # Project-level research (from new-project)
│   ├── STACK.md
│   ├── FEATURES.md
│   ├── ARCHITECTURE.md
│   ├── PITFALLS.md
│   └── SUMMARY.md
└── todos/
    ├── pending/            # Active todo items
    └── done/               # Completed todo items
```

## Files

### Root Files

| File | Purpose | Created | Updated |
|------|---------|---------|---------|
| PROJECT.md | Living project context | new-project | After decisions, scope changes |
| REQUIREMENTS.md | Checkable requirements | new-project | After phase completion |
| ROADMAP.md | Phase structure | new-project | After phases complete |
| STATE.md | Current position | new-project | After every action |
| config.json | Preferences | new-project | By user |

### Phase Artifacts

Phase directories follow naming: `NN-phase-name/` where NN is zero-padded phase number.

| File | Purpose |
|------|---------|
| NN-CONTEXT.md | User decisions captured during discuss-phase |
| NN-RESEARCH.md | Technical research for the phase |
| NN-XX-PLAN.md | Execution plan for plan XX |
| NN-XX-SUMMARY.md | Completion summary for plan XX |

### Research Files

Created during new-project research phase.

| File | Purpose |
|------|---------|
| STACK.md | Technology decisions and rationale |
| FEATURES.md | Feature inventory organized by category |
| ARCHITECTURE.md | System design and patterns |
| PITFALLS.md | Common mistakes and anti-patterns |
| SUMMARY.md | Synthesis of all research |

### Todo Files

Individual markdown files in `pending/` and `done/` directories.

Format: `YYYY-MM-DD-HH-MM-slug.md`

```markdown
# [Brief title]

Created: YYYY-MM-DD HH:MM
Source: [Phase X / User request / During execution]

## Description

[What needs to be done]

## Context

[Why this came up, relevant background]
```

## Directory Creation

Commands will auto-create directories as needed:

- `new-project`: Creates full structure
- `discuss-phase`: Creates `phases/NN-phase-name/`
- `plan-phase`: Creates plan files in phase directory
- `add-todo`: Creates `todos/pending/` if missing

## Path Conventions

All paths relative to repository root:

- `.founder-mode/` - management artifacts
- `.founder-mode/phases/` - per-phase work
- `.founder-mode/research/` - project research
- `.founder-mode/todos/` - captured tasks

Paths in commands use these conventions for consistency.
