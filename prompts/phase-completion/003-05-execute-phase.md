# Execute Phase Command

## Objective

Implement `/fm:execute-phase [N]` command with wave-based parallel execution and goal-backward verification.

## Prerequisites

- 003-01-state-management.md complete
- 003-04-plan-phase.md complete
- 003-06-verification-agents.md complete

## Context Files to Read

```
commands/plan-phase.md      # For command pattern
agents/verifier.md          # For verification patterns
references/verification-patterns.md
../get-shit-done/agents/gsd-executor.md       # Execution patterns
../get-shit-done/commands/gsd/execute-phase.md
```

## Deliverables

Create `commands/execute-phase.md`:

```markdown
---
name: founder-mode:execute-phase
description: Execute all plans in a phase with wave-based parallelization
argument-hint: "<phase-number> [--gaps-only]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Task
  - TodoWrite
  - AskUserQuestion
---

# Execute Phase

Execute all plans in a phase using wave-based parallel execution.

## Arguments

Parse from $ARGUMENTS:
- Phase number (required)
- `--gaps-only`: Execute only gap closure plans (plans with `gap_closure: true`)

## Process

### Step 1: Validate Phase

```bash
# Check project exists
[ -d .founder-mode ] || { echo "No project"; exit 1; }

# Normalize phase
PHASE=$(printf "%02d" $PHASE_ARG)

# Find phase directory
PHASE_DIR=$(ls -d .founder-mode/phases/${PHASE}-* 2>/dev/null | head -1)
[ -z "$PHASE_DIR" ] && { echo "Phase not found"; exit 1; }
```

### Step 2: Discover Plans

```bash
# List all PLAN.md files
PLANS=$(ls ${PHASE_DIR}/*-PLAN.md 2>/dev/null)

# Check which have SUMMARY.md (already complete)
for plan in $PLANS; do
  summary="${plan/-PLAN.md/-SUMMARY.md}"
  [ -f "$summary" ] && echo "COMPLETE: $plan" || echo "PENDING: $plan"
done

# If --gaps-only: filter to gap_closure: true plans
if [ "$GAPS_ONLY" = true ]; then
  PLANS=$(grep -l "gap_closure: true" ${PHASE_DIR}/*-PLAN.md)
fi
```

Build list of incomplete plans.

### Step 3: Group by Wave

Read `wave` from each plan's frontmatter:

```bash
for plan in $PENDING_PLANS; do
  wave=$(grep "^wave:" "$plan" | cut -d: -f2 | tr -d ' ')
  echo "$wave:$plan"
done | sort -n
```

Group plans by wave number.

**Display wave structure:**
```
Wave Structure:

| Wave | Plans | What it builds |
|------|-------|----------------|
| 1    | 01, 02| Foundation     |
| 2    | 03    | Integration    |
```

### Step 4: Execute Waves

For each wave in order:

**Describe wave:**
```
Executing Wave {N}: {plan objectives}
```

**Spawn executor agents (parallel):**

For each plan in wave, spawn Task:

```
Task(
  prompt: "Execute plan at ${plan_path}

  Plan: @${plan_path}
  Project state: @.founder-mode/STATE.md

  Execute all tasks, make per-task commits, create SUMMARY.md.",
  subagent_type: "general-purpose",
  description: "Execute ${plan_id}"
)
```

Spawn all plans in wave with single message (parallel execution).

**Wait for completion:**

Task tool blocks until all complete.

**Verify SUMMARYs created:**
```bash
for plan in $WAVE_PLANS; do
  summary="${plan/-PLAN.md/-SUMMARY.md}"
  [ -f "$summary" ] || echo "MISSING: $summary"
done
```

**Summarize wave:**
```
Wave {N} complete: {N} plans executed
```

Proceed to next wave.

### Step 5: Per-Task Atomic Commits

Each task gets its own commit:

```
abc123 feat(03-01): create project initialization command
def456 feat(03-01): create state management utilities
ghi789 feat(03-02): implement questioning flow
```

**Commit format:**
```
{type}({phase}-{plan}): {task description}

- {key change 1}
- {key change 2}
```

**Types:** feat, fix, test, refactor, perf, docs, style, chore

**Benefits:**
- Git bisect finds exact failing task
- Each task independently revertable
- Clear history for future sessions

### Step 6: Commit Orchestrator Corrections

Before verification, check for uncommitted changes:

```bash
git status --porcelain
```

If changes exist (orchestrator made corrections):
```bash
git add -u && git commit -m "fix(${PHASE}): orchestrator corrections"
```

### Step 7: Verify Phase Goal

Spawn verifier agent:

```
Task(
  prompt: "Verify Phase ${PHASE} goal achievement

  Phase directory: ${PHASE_DIR}
  Phase goal: ${PHASE_GOAL}

  Check must_haves against actual codebase.
  Create VERIFICATION.md with detailed report.",
  subagent_type: "general-purpose",
  description: "Verify Phase ${PHASE}"
)
```

**Handle verifier result:**

| Status | Action |
|--------|--------|
| passed | Continue to step 8 |
| human_needed | Present items, get approval |
| gaps_found | Present gaps, offer `/fm:plan-phase {N} --gaps` |

### Step 8: Update State

**Update ROADMAP.md:**
- Mark phase checkbox complete
- Update Progress table

**Update STATE.md:**
- Update current position
- Update progress bar
- Add any decisions made

**Update REQUIREMENTS.md:**
- Mark phase requirements as Complete

### Step 9: Commit Phase Completion

```bash
git add .founder-mode/ROADMAP.md .founder-mode/STATE.md
git add .founder-mode/REQUIREMENTS.md  # If updated
git add ${PHASE_DIR}/*-VERIFICATION.md
git commit -m "docs(${PHASE}): complete ${PHASE_NAME} phase

Plans executed: {N}
Goal verified: {status}"
```

### Step 10: Offer Next Steps

**If more phases remain:**
```
PHASE {N} COMPLETE

{X} plans executed
Goal verified ✓

Next: /fm:discuss-phase {N+1}
```

**If last phase:**
```
MILESTONE COMPLETE

All phases executed
Ready for review

Next: /fm:verify-work (manual testing)
```

**If gaps found:**
```
PHASE {N} GAPS FOUND

Score: {X}/{Y} must-haves verified

What's Missing:
{Gap summaries from VERIFICATION.md}

Next: /fm:plan-phase {N} --gaps
```

## Checkpoint Handling

Plans with `autonomous: false` have checkpoints.

**At checkpoint:**
1. Executor returns structured checkpoint state
2. Orchestrator presents to user
3. User responds
4. Spawn fresh continuation agent

**Checkpoint types:**
- `checkpoint:human-verify`: Verify Claude's work
- `checkpoint:decision`: Make implementation choice
- `checkpoint:human-action`: Unavoidable manual step (rare)

## Deviation Rules

During execution, handle discoveries automatically:

1. **Auto-fix bugs**: Fix immediately, document in Summary
2. **Auto-add critical**: Security/correctness gaps, add and document
3. **Auto-fix blockers**: Can't proceed without fix
4. **Ask about architectural**: Major structural changes, stop and ask

Only rule 4 requires user intervention.

## SUMMARY.md Format

Each plan produces a SUMMARY.md:

```yaml
---
phase: NN-name
plan: NN
status: complete
started: YYYY-MM-DDTHH:MM:SSZ
completed: YYYY-MM-DDTHH:MM:SSZ
duration: Xm
tasks_completed: N
commits:
  - hash: "abc123"
    message: "feat(NN-NN): task description"
---

# Plan {NN-NN} Summary

## What Was Built

- {Artifact 1}
- {Artifact 2}

## Files Changed

- `path/to/file.ts` (created, {N} lines)
- `path/to/other.ts` (modified)

## Verification Results

- [x] {Check 1}
- [x] {Check 2}

## Deviations from Plan

{If any auto-fixes or additions, document here}
{Or: "None - plan executed exactly as written"}
```

## Success Criteria

- [ ] All incomplete plans in phase executed
- [ ] Each plan has SUMMARY.md
- [ ] Per-task atomic commits
- [ ] Phase goal verified (must_haves checked)
- [ ] VERIFICATION.md created
- [ ] STATE.md updated
- [ ] ROADMAP.md updated
- [ ] REQUIREMENTS.md updated (if applicable)
- [ ] User informed of next steps
```

## Instructions

### Step 1: Create Command File

Create `commands/execute-phase.md` with the full content above.

### Step 2: Verify Wave Execution Pattern

Ensure parallel spawning pattern is clear:
- Single message with multiple Task calls
- All plans in wave run simultaneously
- Wait for all to complete before next wave

### Step 3: Document Checkpoint Flow

The checkpoint → user → continuation flow should be clear.

## Verification

- [ ] commands/execute-phase.md exists
- [ ] Wave-based execution documented
- [ ] Parallel spawning pattern clear
- [ ] Per-task commit format documented
- [ ] Verifier spawning documented
- [ ] Gap handling documented
- [ ] SUMMARY.md format documented
- [ ] Checkpoint handling documented

## Rollback

```bash
rm commands/execute-phase.md
git checkout -- commands/execute-phase.md
```
