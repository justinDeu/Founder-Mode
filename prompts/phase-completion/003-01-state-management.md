# State Management Foundation

## Objective

Establish the directory structure and state management foundation that all other Phase 3 commands depend on. Create templates, utilities, and configuration schema for founder-mode project management.

## Prerequisites

- Phases 1-2 complete
- commands/ directory exists with create-prompt.md and run-prompt.md

## Context Files to Read

```
.planning/PROJECT.md
.planning/ROADMAP.md
commands/run-prompt.md          - For command file format reference
../get-shit-done/templates/     - For template patterns (if accessible)
```

## Deliverables

### 1. Directory Structure Template

Create `.founder-mode/` directory structure documentation in `references/directory-structure.md`:

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

### 2. PROJECT.md Template

Create `templates/project.md`:

```markdown
# {Project Name}

## What This Is

{One paragraph description of what the project is and does}

## Core Value

{The single most important thing this project must deliver}

## Requirements

### Validated

{Requirements proven by shipped code}

### Active

{Requirements being built}
- [ ] {Requirement 1}
- [ ] {Requirement 2}

### Out of Scope

{Explicitly excluded}
- {Exclusion 1} - {why}

## Context

**Existing tools/code:**
{What already exists}

**Key frustrations to address:**
{Problems being solved}

**Goals:**
{What success looks like}

## Constraints

- **Platform**: {target platform}
- **Architecture**: {architectural constraints}
- **Compatibility**: {compatibility requirements}

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| {choice} | {why} | Pending |

---
*Last updated: {date} after {event}*
```

### 3. ROADMAP.md Template

Create `templates/roadmap.md`:

```markdown
# Roadmap: {Project Name}

## Overview

{Brief description of what this roadmap delivers}

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions

- [ ] **Phase 1: {Name}** - {brief description}
- [ ] **Phase 2: {Name}** - {brief description}
- [ ] **Phase 3: {Name}** - {brief description}

## Phase Details

### Phase 1: {Name}
**Goal**: {Outcome-focused goal, not task description}
**Depends on**: {Prior phases or "Nothing"}
**Research**: {Likely/Unlikely} ({reason})
**Requirements**: {REQ-IDs covered by this phase}
**Plans**: {N} plans (or "TBD" before planning)

Success Criteria:
1. {Observable user behavior}
2. {Observable user behavior}
3. {Observable user behavior}

### Phase 2: {Name}
...

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. {Name} | 0/TBD | Not started | - |
| 2. {Name} | 0/TBD | Not started | - |
```

### 4. STATE.md Template

Create `templates/state.md`:

```markdown
# Project State

## Project Reference

See: .founder-mode/PROJECT.md (updated {date})

**Core value:** {from PROJECT.md}
**Current focus:** Phase {N} - {Name}

## Current Position

Phase: {N} of {total} ({phase name})
Plan: {M} of {plans in phase}
Status: {Not started / In progress / Phase complete}
Last activity: {date} - {what happened}

Progress: {progress bar} {percentage}%

## Performance Metrics

**Velocity:**
- Total plans completed: {N}
- Average duration: {time}
- Total execution time: {time}

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| {N} | {count} | {time} | {time} |

**Recent Trend:**
- Last 5 plans: {list with times}
- Trend: {Improving / Stable / Slowing}

## Accumulated Context

### Decisions

{Table from PROJECT.md Key Decisions, or recent decisions affecting current work}

### Deferred Issues

{Ideas captured but not acted on}

### Blockers/Concerns

{Active blockers or concerns}

## Session Continuity

Last session: {ISO timestamp}
Stopped at: {what was being worked on}
Resume file: {path or "None"}
```

### 5. REQUIREMENTS.md Template

Create `templates/requirements.md`:

```markdown
# Requirements: {Project Name}

## Format

Each requirement has:
- **REQ-ID**: Category prefix + number (AUTH-01, CONTENT-02)
- **Description**: User-centric ("User can X")
- **Priority**: v1 (must have) / v2 (nice to have) / out-of-scope
- **Status**: Pending / In Progress / Complete
- **Phase**: Which phase addresses this requirement

## v1 Requirements

### {Category 1}

| REQ-ID | Description | Status | Phase |
|--------|-------------|--------|-------|
| {CAT}-01 | User can {action} | Pending | {N} |
| {CAT}-02 | User can {action} | Pending | {N} |

### {Category 2}

| REQ-ID | Description | Status | Phase |
|--------|-------------|--------|-------|
| {CAT}-01 | User can {action} | Pending | {N} |

## v2 Requirements (Deferred)

| REQ-ID | Description | Reason Deferred |
|--------|-------------|-----------------|
| {CAT}-XX | User can {action} | {why not v1} |

## Out of Scope

| Item | Reason |
|------|--------|
| {feature} | {why excluded} |

## Traceability

| REQ-ID | Phase | Plan(s) | Status |
|--------|-------|---------|--------|
| AUTH-01 | 3 | 03-01 | Pending |
| AUTH-02 | 3 | 03-01 | Pending |

## Coverage Validation

- Total v1 requirements: {N}
- Mapped to phases: {N}
- Coverage: {percentage}%

**Unmapped requirements:** {list or "None"}
```

### 6. config.json Schema

Create `templates/config.json`:

```json
{
  "workflow_mode": "interactive",
  "worktree_dir": ".worktrees/",
  "logs_dir": ".founder-mode/logs/",
  "prompts_dir": "./prompts/",
  "parallel": true,
  "max_plan_tasks": 3,
  "depth": "standard",
  "auto_commit": true,
  "verification": {
    "pre_execution": true,
    "post_execution": true,
    "max_iterations": 3
  }
}
```

**Field definitions:**

- `workflow_mode`: "interactive" (confirm steps) or "yolo" (auto-approve)
- `worktree_dir`: Where to create git worktrees
- `logs_dir`: Where to store execution logs
- `prompts_dir`: Where prompt files live
- `parallel`: Enable wave-based parallel execution
- `max_plan_tasks`: Maximum tasks per plan (2-3 recommended)
- `depth`: "quick" / "standard" / "comprehensive"
- `auto_commit`: Auto-commit after task completion
- `verification.pre_execution`: Run plan-checker before execution
- `verification.post_execution`: Run verifier after execution
- `verification.max_iterations`: Max planner-checker iterations

### 7. State Management Utilities

Create `references/state-utilities.md` documenting utility patterns:

```markdown
# State Management Utilities

## Reading State

To load project state:

1. Check for .founder-mode/ directory
2. If missing, error: "Project not initialized. Run /founder-mode:new-project"
3. Read STATE.md, parse current position
4. Read config.json for preferences

## Updating STATE.md

After completing a plan:

1. Read current STATE.md
2. Update "Current Position" section:
   - Increment plan number
   - Update status
   - Update progress bar
3. Add any new decisions to "Accumulated Context"
4. Update "Session Continuity" with timestamp
5. Write updated STATE.md

## Progress Bar Calculation

```
total_plans = count all PLAN.md files across all phases
completed_plans = count all SUMMARY.md files
percentage = (completed_plans / total_plans) * 100
bar_length = 10
filled = floor(percentage / 10)
progress_bar = "█" * filled + "░" * (bar_length - filled)
```

## REQ-ID Management

### Assigning New REQ-IDs

1. Read REQUIREMENTS.md
2. Find highest ID in target category (e.g., AUTH-03)
3. Increment: AUTH-04
4. Add to appropriate section

### Updating Requirement Status

1. Find requirement by REQ-ID
2. Change Status column: Pending → In Progress → Complete
3. Update Traceability section with plan reference

## Atomic Updates

Always:
1. Read the full file
2. Make changes
3. Write the full file
4. Commit immediately

Never partially update markdown tables.
```

## Instructions

### Step 1: Create Directory Structure

```bash
mkdir -p templates
mkdir -p references
```

### Step 2: Create Template Files

Create each template file as specified above:
- templates/project.md
- templates/roadmap.md
- templates/state.md
- templates/requirements.md
- templates/config.json

### Step 3: Create Reference Documents

- references/directory-structure.md
- references/state-utilities.md

### Step 4: Verify Structure

```bash
ls -la templates/
ls -la references/
```

Expected output:
```
templates/
  project.md
  roadmap.md
  state.md
  requirements.md
  config.json

references/
  directory-structure.md
  state-utilities.md
```

## Verification

Before declaring complete:

- [ ] templates/ directory exists with 5 files
- [ ] references/ directory exists with 2 files
- [ ] Each template has all required sections
- [ ] config.json is valid JSON
- [ ] REQ-ID format documented (CATEGORY-NN)
- [ ] Progress bar calculation documented
- [ ] Atomic update pattern documented

## Rollback

If this prompt fails:

```bash
rm -rf templates/
rm -rf references/
git checkout -- templates/ references/
```
