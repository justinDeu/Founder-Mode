---
name: founder-mode:execute-phase
description: Execute all plans in a phase with wave-based parallelization
argument-hint: "[N] [--gaps-only]"
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

Orchestrator stays lean: discover plans, analyze dependencies, group into waves, spawn subagents, collect results. Each subagent loads full context and handles its own plan.

Context budget: ~15% orchestrator, 100% fresh per subagent.

## Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `N` | positional | current | Phase number to execute (reads from STATE.md if omitted) |
| `--gaps-only` | flag | false | Execute only gap closure plans (plans with `gap_closure: true`) |

## Execution Flow

---

### Step 1: Validate Phase

<validate_phase>
Check that required project files exist and phase is valid:

```bash
# Check for project
if [ ! -d ".founder-mode" ]; then
    echo "No project found. Run /founder-mode:new-project first."
    exit 1
fi

# Check for STATE.md
if [ ! -f ".founder-mode/STATE.md" ]; then
    echo "No state found. Run /founder-mode:new-project first."
    exit 1
fi

# Parse phase number from argument or STATE.md
if [ -z "$N" ]; then
    N=$(grep "^Phase:" .founder-mode/STATE.md | grep -oP '\d+' | head -1)
fi

# Normalize phase to two digits
PHASE=$(printf "%02d" $N)

# Find phase directory
PHASE_DIR=$(ls -d .founder-mode/plans/phase-${PHASE}* 2>/dev/null | head -1)

if [ -z "$PHASE_DIR" ]; then
    echo "Phase ${N} not found."
    echo ""
    echo "Available phases:"
    ls -d .founder-mode/plans/phase-* 2>/dev/null | sed 's/.*phase-/  Phase /'
    exit 1
fi

echo "Executing Phase ${N}: $PHASE_DIR"
```

Extract phase goal from ROADMAP.md:

```bash
PHASE_GOAL=$(grep -A 5 "Phase $N:" .founder-mode/ROADMAP.md | grep "Goal:" | sed 's/.*Goal: //')
PHASE_NAME=$(grep "Phase $N:" .founder-mode/ROADMAP.md | head -1 | sed 's/.*Phase [0-9]*: //' | sed 's/ -.*//')
```
</validate_phase>

---

### Step 2: Discover Plans

<discover_plans>
List all PLAN.md files and determine which are incomplete:

```bash
# List all PLAN.md files
PLANS=$(ls ${PHASE_DIR}/*-PLAN.md 2>/dev/null)

if [ -z "$PLANS" ]; then
    echo "No plans found in ${PHASE_DIR}"
    echo ""
    echo "Run /founder-mode:plan-phase ${N} first."
    exit 1
fi

# Check which have SUMMARY.md (already complete)
PENDING_PLANS=()
COMPLETE_PLANS=()

for plan in $PLANS; do
    summary="${plan/-PLAN.md/-SUMMARY.md}"
    if [ -f "$summary" ]; then
        COMPLETE_PLANS+=("$plan")
        echo "COMPLETE: $(basename $plan)"
    else
        PENDING_PLANS+=("$plan")
        echo "PENDING: $(basename $plan)"
    fi
done

# If --gaps-only: filter to gap_closure: true plans
if [ "$GAPS_ONLY" = true ]; then
    PENDING_PLANS=$(grep -l "gap_closure: true" ${PHASE_DIR}/*-PLAN.md 2>/dev/null)
    echo ""
    echo "Gap closure mode: executing only gap closure plans"
fi

# Check if anything to execute
if [ ${#PENDING_PLANS[@]} -eq 0 ]; then
    echo ""
    echo "No incomplete plans. Phase may already be complete."
    echo "Run /founder-mode:execute-phase ${N} --force to re-execute."
    exit 0
fi
```

Report discovery:

```
Discovered Plans
================

Phase: {N} - {phase_name}
Total plans: {total}
Complete: {complete_count}
Pending: {pending_count}

Pending:
- {plan_id}: {objective from frontmatter}
- {plan_id}: {objective from frontmatter}
```
</discover_plans>

---

### Step 3: Group by Wave

<group_by_wave>
Read `wave` from each plan's frontmatter and group:

```bash
declare -A WAVES

for plan in ${PENDING_PLANS[@]}; do
    wave=$(grep "^wave:" "$plan" | cut -d: -f2 | tr -d ' ')
    wave=${wave:-1}  # Default to wave 1 if not specified

    if [ -z "${WAVES[$wave]}" ]; then
        WAVES[$wave]="$plan"
    else
        WAVES[$wave]="${WAVES[$wave]} $plan"
    fi
done

# Sort waves
SORTED_WAVES=($(echo "${!WAVES[@]}" | tr ' ' '\n' | sort -n))
```

Display wave structure:

```
Wave Structure
==============

| Wave | Plans | What it builds |
|------|-------|----------------|
| 1 | 01, 02 | Foundation components |
| 2 | 03 | Integration layer |
| 3 | 04 | API endpoints |

Total waves: {count}
```

Check for checkpoint plans:

```bash
# Plans with autonomous: false have checkpoints
CHECKPOINT_PLANS=()
for plan in ${PENDING_PLANS[@]}; do
    if grep -q "autonomous: false" "$plan"; then
        CHECKPOINT_PLANS+=("$plan")
    fi
done

if [ ${#CHECKPOINT_PLANS[@]} -gt 0 ]; then
    echo ""
    echo "Plans with checkpoints (will pause for user input):"
    for plan in ${CHECKPOINT_PLANS[@]}; do
        echo "  - $(basename $plan)"
    done
fi
```
</group_by_wave>

---

### Step 4: Execute Waves

<execute_waves>
For each wave in order:

**4a. Report wave start:**

```
Executing Wave {N}
==================

Plans in this wave:
- {plan_id}: {objective}
- {plan_id}: {objective}

Spawning {count} parallel executor(s)...
```

**4b. Spawn executor agents (PARALLEL):**

CRITICAL: Spawn ALL tasks for the wave in a SINGLE message with multiple Task calls.

```
# For each plan in wave, spawn in parallel:
Task(
  prompt: """
Execute plan: {plan_id}

Plan: @{plan_path}
Project state: @.founder-mode/STATE.md

Execute all tasks in the plan:
1. Read and parse the PLAN.md file
2. Execute each task sequentially
3. Make per-task atomic commits (see commit format below)
4. Run task verification after each task
5. Track any deviations (auto-fixes, additions)
6. Create SUMMARY.md when complete

Commit format per task:
{type}({phase}-{plan}): {task description}

Types: feat, fix, test, refactor, perf, docs, style, chore

SUMMARY.md location: {phase_dir}/{plan_id}-SUMMARY.md

When complete, report:
- Tasks completed: N/N
- Commits made: [list]
- Deviations: [list or "None"]
- SUMMARY path: {path}
""",
  subagent_type: "general-purpose",
  description: "Execute {plan_id}"
)
```

Spawn all plans in wave simultaneously.

**4c. Wait for wave completion:**

Task tool blocks until all complete.

**4d. Verify SUMMARYs created:**

```bash
for plan in $WAVE_PLANS; do
    summary="${plan/-PLAN.md/-SUMMARY.md}"
    if [ ! -f "$summary" ]; then
        echo "MISSING SUMMARY: $summary"
        # Mark wave as incomplete
    fi
done
```

**4e. Report wave results:**

```
Wave {N} Complete
=================

| Plan | Tasks | Status | Duration |
|------|-------|--------|----------|
| 01 | 3/3 | SUCCESS | 2m 15s |
| 02 | 2/2 | SUCCESS | 1m 42s |

Proceeding to Wave {N+1}...
```

**4f. Handle failures:**

If any plan in wave fails:

```
Wave {N} had failures:

- {plan_id}: FAILED
  Error: {error message}
  Last completed task: {task name}

Options:
1. Retry failed plan(s) only
2. Skip and continue to next wave
3. Abort execution
```

Use AskUserQuestion to let user decide.
</execute_waves>

---

### Step 5: Per-Task Atomic Commits

<per_task_commits>
Each task gets its own commit. Executors follow this pattern:

**Commit format:**

```
{type}({phase}-{plan}): {task description}

- {key change 1}
- {key change 2}
```

**Types:**

| Type | When to Use |
|------|-------------|
| `feat` | New feature, endpoint, component, functionality |
| `fix` | Bug fix, error correction |
| `test` | Test-only changes |
| `refactor` | Code cleanup, no behavior change |
| `perf` | Performance improvement |
| `docs` | Documentation changes |
| `style` | Formatting, linting fixes |
| `chore` | Config, tooling, dependencies |

**Example commit sequence:**

```
abc123 feat(03-01): create project initialization command
def456 feat(03-01): add state management utilities
ghi789 feat(03-02): implement questioning flow
jkl012 test(03-02): add flow tests
```

**Benefits:**
- Git bisect finds exact failing task
- Each task independently revertable
- Clear history for future sessions
- Git blame traces lines to specific task context

**Commit rules:**
- NEVER use `git add .` or `git add -A`
- Stage files individually
- One commit per task
- Meaningful commit messages
</per_task_commits>

---

### Step 6: Commit Orchestrator Corrections

<commit_corrections>
Before verification, check for uncommitted changes from orchestrator:

```bash
git status --porcelain
```

If changes exist (orchestrator made corrections between executor completions):

```bash
git add -u
git commit -m "fix(${PHASE}): orchestrator corrections

Corrections made between plan executions:
- {correction 1}
- {correction 2}"
```

If clean: Continue to verification.
</commit_corrections>

---

### Step 7: Verify Phase Goal

<verify_phase_goal>
Spawn verifier agent to check goal achievement:

```
Task(
  prompt: """
Verify Phase ${PHASE} goal achievement.

Phase directory: ${PHASE_DIR}
Phase goal: ${PHASE_GOAL}

Verification process:
1. Load phase context (PLANs and SUMMARYs)
2. Establish must-haves from PLAN frontmatter or derive from goal
3. For each must-have truth:
   - Identify supporting artifacts
   - Check artifact existence (Level 1)
   - Check artifact is substantive, not stub (Level 2)
   - Check artifact is wired to system (Level 3)
4. Verify key links between components
5. Scan for anti-patterns (stubs, TODOs, empty handlers)
6. Determine overall status

Create VERIFICATION.md with:
- Status: passed | gaps_found | human_needed
- Score: N/M must-haves verified
- Detailed report by artifact
- Gap analysis (if gaps_found)
- Human verification items (if human_needed)

DO NOT COMMIT. Return results to orchestrator.
""",
  subagent_type: "verifier",
  description: "Verify Phase ${PHASE}"
)
```

**Handle verifier result:**

| Status | Action |
|--------|--------|
| `passed` | Continue to Step 8 |
| `human_needed` | Present items, collect approval |
| `gaps_found` | Present gaps, offer gap closure |

**If gaps_found:**

```
PHASE {N} GAPS FOUND
====================

Score: {X}/{Y} must-haves verified
Report: {PHASE_DIR}/{PHASE}-VERIFICATION.md

What's Missing:
---------------

1. {Truth that failed}
   - Artifacts: {files with issues}
   - Missing: {what needs to be added}

2. {Truth that failed}
   - Artifacts: {files with issues}
   - Missing: {what needs to be added}

Next step: /founder-mode:plan-phase {N} --gaps
```

**If human_needed:**

```
PHASE {N} HUMAN VERIFICATION REQUIRED
=====================================

Automated checks passed. Manual verification needed:

1. {Test name}
   - Test: {what to do}
   - Expected: {what should happen}
   - Why human: {why can't verify programmatically}

2. {Test name}
   - Test: {what to do}
   - Expected: {what should happen}

Approve verification? [Yes/No/Provide feedback]
```

Use AskUserQuestion to collect approval.
</verify_phase_goal>

---

### Step 8: Update State

<update_state>
**Update ROADMAP.md:**

1. Find phase entry in ROADMAP.md
2. Mark phase checkbox complete:

```markdown
- [x] Phase {N}: {Name}
```

3. Update Progress table:

```markdown
| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| {N}. {Name} | {X}/{X} | Complete | {date} |
```

**Update STATE.md:**

1. Update current position:

```markdown
Phase: {N+1} of {total} ({next_phase_name})
Plan: 0 of {plans_in_next}
Status: Ready to plan
Last activity: {date} - Phase {N} complete
```

2. Update progress bar:

```
total_plans = count all PLAN.md files across all phases
completed_plans = count all SUMMARY.md files
percentage = (completed_plans / total_plans) * 100
```

3. Add any decisions from phase execution

**Update REQUIREMENTS.md (if applicable):**

1. Read ROADMAP.md, find this phase's `Requirements:` line
2. For each REQ-ID in this phase: change Status from "Pending" to "Complete"
3. Write updated REQUIREMENTS.md
</update_state>

---

### Step 9: Commit Phase Completion

<commit_phase_completion>
Bundle all phase metadata updates in one commit:

```bash
git add .founder-mode/ROADMAP.md
git add .founder-mode/STATE.md
git add .founder-mode/REQUIREMENTS.md  # If updated
git add ${PHASE_DIR}/*-VERIFICATION.md

git commit -m "docs(${PHASE}): complete ${PHASE_NAME} phase

Plans executed: {N}
Goal verified: {status}
Duration: {total_time}"
```
</commit_phase_completion>

---

### Step 10: Offer Next Steps

<offer_next_steps>
Route based on status and remaining work:

**Route A: More phases remain (status: passed)**

```
PHASE {N} COMPLETE
==================

Phase {N}: {Name}

{X} plans executed
Goal verified

Next Up
-------

Phase {N+1}: {Name} - {Goal from ROADMAP.md}

/founder-mode:discuss-phase {N+1} - gather context and clarify approach

Also available:
- /founder-mode:plan-phase {N+1} - skip discussion, plan directly
- /founder-mode:verify-work {N} - manual acceptance testing before continuing
```

**Route B: Last phase complete (status: passed)**

```
MILESTONE COMPLETE
==================

v{version}

{total_phases} phases completed
All phase goals verified

Next Up
-------

Audit milestone - verify requirements, cross-phase integration, E2E flows

/founder-mode:audit-milestone

Also available:
- /founder-mode:verify-work - manual acceptance testing
- /founder-mode:complete-milestone - skip audit, archive directly
```

**Route C: Gaps found (status: gaps_found)**

```
PHASE {N} GAPS FOUND
====================

Phase {N}: {Name}

Score: {X}/{Y} must-haves verified
Report: {PHASE_DIR}/{PHASE}-VERIFICATION.md

What's Missing
--------------

{Gap summaries from VERIFICATION.md}

Next Up
-------

Plan gap closure - create additional plans to complete the phase

/founder-mode:plan-phase {N} --gaps

Also available:
- cat {PHASE_DIR}/{PHASE}-VERIFICATION.md - see full report
- /founder-mode:verify-work {N} - manual testing before planning
```

**Gap closure loop:**

After user runs `/founder-mode:plan-phase {N} --gaps`:
1. Planner reads VERIFICATION.md gaps
2. Creates additional plans (04, 05, etc.) to close gaps
3. User runs `/founder-mode:execute-phase {N}` again
4. Execute-phase runs only incomplete plans (04, 05...)
5. Verifier runs again
6. Loop until passed
</offer_next_steps>

---

## Checkpoint Handling

<checkpoint_handling>
Plans with `autonomous: false` have checkpoints requiring user interaction.

**Checkpoint types:**

| Type | Purpose | User Action |
|------|---------|-------------|
| `checkpoint:human-verify` | Verify Claude's work | Test and confirm |
| `checkpoint:decision` | Make implementation choice | Select option |
| `checkpoint:human-action` | Unavoidable manual step | Perform action |

**At checkpoint:**

1. Executor returns structured checkpoint state:

```yaml
checkpoint:
  type: human-verify
  plan: 03-02
  completed_tasks:
    - task: 1
      commit: abc123
    - task: 2
      commit: def456
  current_task: 3
  what_built: |
    Created authentication flow with JWT tokens.
    User login/logout working locally.
  how_to_verify: |
    1. Run `npm run dev`
    2. Navigate to /login
    3. Enter test credentials
    4. Verify redirect to dashboard
  resume_signal: "Reply 'approved' to continue"
```

2. Orchestrator presents to user:

```
CHECKPOINT: Human Verification
==============================

Plan: 03-02 (2/4 tasks complete)

What was built:
{what_built content}

How to verify:
{how_to_verify content}

Reply 'approved' to continue, or provide feedback.
```

3. User responds

4. Spawn FRESH continuation agent (not resume):

```
Task(
  prompt: """
Continue plan 03-02 from task 3.

<completed_tasks>
- Task 1: {description} (commit: abc123)
- Task 2: {description} (commit: def456)
</completed_tasks>

User feedback: {user_response}

Plan: @{plan_path}
Resume from: Task 3

Continue execution, picking up where previous agent left off.
""",
  subagent_type: "general-purpose",
  description: "Continue 03-02 from task 3"
)
```

**Decision checkpoint example:**

```
CHECKPOINT: Decision Required
=============================

Plan: 03-03 (1/3 tasks complete)

Decision: Database schema for user sessions

Context:
Sessions need to be fast and support ~10k concurrent users.

Options:
1. PostgreSQL with connection pooling
   - Pros: ACID, familiar
   - Cons: Higher latency

2. Redis
   - Pros: Sub-millisecond reads
   - Cons: No persistence by default

3. Hybrid (PostgreSQL + Redis cache)
   - Pros: Best of both
   - Cons: More complexity

Select option (1, 2, or 3):
```
</checkpoint_handling>

---

## Deviation Rules

<deviation_rules>
During execution, handle discoveries automatically:

**Rule 1: Auto-fix bugs**

Trigger: Code doesn't work as intended (errors, incorrect output)

Action: Fix immediately, document in SUMMARY.md

Examples:
- Wrong SQL query
- Logic errors
- Type errors
- Security vulnerabilities

**Rule 2: Auto-add critical functionality**

Trigger: Code missing essential features for correctness/security

Action: Add immediately, document in SUMMARY.md

Examples:
- Missing error handling
- No input validation
- Missing authentication on protected routes

**Rule 3: Auto-fix blockers**

Trigger: Can't proceed without fix

Action: Fix and document

Examples:
- Missing dependency
- Broken import
- Environment misconfiguration

**Rule 4: Ask about architectural changes**

Trigger: Major structural changes discovered

Action: STOP and ask user

Examples:
- Different framework needed
- Database schema redesign
- API contract changes

Only Rule 4 requires user intervention. Rules 1-3 are documented in SUMMARY.md but don't pause execution.
</deviation_rules>

---

## SUMMARY.md Format

<summary_format>
Each plan produces a SUMMARY.md with YAML frontmatter:

```yaml
---
phase: NN-name
plan: NN
status: complete
started: YYYY-MM-DDTHH:MM:SSZ
completed: YYYY-MM-DDTHH:MM:SSZ
duration: Xm Ys

subsystem: "{category based on phase focus}"
tags: ["{tech}", "{keywords}"]

dependencies:
  requires: ["{prior phases built upon}"]
  provides: ["{what was delivered}"]
  affects: ["{future phases that might need this}"]

tech_stack:
  added: ["{new libraries}"]
  patterns: ["{architectural patterns established}"]

key_files:
  created:
    - path: "{file path}"
      purpose: "{what it does}"
  modified:
    - path: "{file path}"
      changes: "{what changed}"

tasks_completed: N
commits:
  - hash: "abc123"
    message: "feat(NN-NN): task description"
  - hash: "def456"
    message: "feat(NN-NN): another task"

decisions:
  - decision: "{what was decided}"
    rationale: "{why}"
    alternatives_considered: ["{other options}"]
---

# Plan {NN-NN} Summary

{One-liner: substantive description of what was built}

## What Was Built

- {Artifact 1}: {description}
- {Artifact 2}: {description}

## Files Changed

- `path/to/file.ts` (created, {N} lines) - {purpose}
- `path/to/other.ts` (modified) - {what changed}

## Verification Results

- [x] {Check 1 from plan}
- [x] {Check 2 from plan}
- [x] {Success criteria 1}

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] {description}**
- Found during: Task {N}
- Issue: {what was wrong}
- Fix: {what was done}
- Files: {files modified}
- Commit: {hash}

{Or: "None - plan executed exactly as written."}

## Next Phase Readiness

{Any blockers or concerns for next phase}
{Or: "Ready to proceed."}
```

**One-liner requirements:**
- MUST be substantive
- Good: "JWT auth with refresh rotation using jose library"
- Bad: "Authentication implemented"
</summary_format>

---

## Error Handling

<error_no_project>
If .founder-mode/ doesn't exist:

```
No project found.

Run /founder-mode:new-project first to initialize.
```
</error_no_project>

<error_no_plans>
If no PLAN.md files in phase directory:

```
No plans found for Phase {N}.

Run /founder-mode:plan-phase {N} first to create plans.
```
</error_no_plans>

<error_phase_not_found>
If phase directory doesn't exist:

```
Phase {N} not found.

Available phases:
{list phases from .founder-mode/plans/}

Use: /founder-mode:execute-phase {valid_phase_number}
```
</error_phase_not_found>

<error_executor_failed>
If executor agent fails:

```
Plan {plan_id} execution failed.

Error: {error message}
Last successful task: {task name}
Commit history: {list commits}

Options:
1. Retry this plan
2. Skip and continue with wave
3. Abort phase execution

Retry with: /founder-mode:execute-phase {N}
(Will only run incomplete plans)
```
</error_executor_failed>

---

## Examples

**Execute current phase:**
```
/founder-mode:execute-phase
```

**Execute specific phase:**
```
/founder-mode:execute-phase 3
```

**Execute gap closure plans only:**
```
/founder-mode:execute-phase 2 --gaps-only
```

---

## Success Criteria

- [ ] All incomplete plans in phase executed
- [ ] Each plan has SUMMARY.md
- [ ] Per-task atomic commits (one commit per task)
- [ ] Phase goal verified (must_haves checked against codebase)
- [ ] VERIFICATION.md created in phase directory
- [ ] STATE.md reflects phase completion
- [ ] ROADMAP.md updated (phase checkbox, progress table)
- [ ] REQUIREMENTS.md updated (if applicable)
- [ ] User informed of next steps
