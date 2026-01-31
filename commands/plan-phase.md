---
name: founder-mode:plan-phase
description: Create executable PLAN.md files with pre-execution validation loop
argument-hint: [N] [--gaps] [--skip-validation]
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - Task
  - AskUserQuestion
---

# Plan Phase

Create executable PLAN.md files that Claude can implement without interpretation. Plans are prompts, not documents that become prompts.

## Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `N` | positional | current | Phase number to plan (reads from STATE.md if omitted) |
| `--gaps` | flag | false | Gap closure mode: create plans from VERIFICATION.md or UAT.md failures |
| `--skip-validation` | flag | false | Skip the planner-checker validation loop |

## Purpose

Planning transforms phase goals into executable work units. Each PLAN.md contains everything needed for autonomous execution: objective, context, tasks, verification, and success criteria.

**Problem:** Vague plans require interpretation during execution. Claude makes assumptions, work diverges from intent.

**Solution:** Goal-backward planning with validation loop. Plans specify exactly what to build, how to verify, and what success looks like.

## Execution Flow

---

### Step 1: Validate Environment

<validate_environment>
Check that required project files exist:

```bash
# Check for PROJECT.md
if [ ! -f ".founder-mode/PROJECT.md" ]; then
    echo "No project found. Run /fm:new-project first."
    exit 1
fi

# Check for ROADMAP.md
if [ ! -f ".founder-mode/ROADMAP.md" ]; then
    echo "No roadmap found. Run /fm:new-project first."
    exit 1
fi

# Check for STATE.md
if [ ! -f ".founder-mode/STATE.md" ]; then
    echo "No state found. Run /fm:new-project first."
    exit 1
fi

echo "Environment valid."
```
</validate_environment>

---

### Step 2: Parse Phase

<parse_phase>
Determine which phase to plan:

```bash
# If N provided, use it
# Otherwise read current phase from STATE.md
if [ -z "$N" ]; then
    N=$(grep "^Phase:" .founder-mode/STATE.md | grep -oP '\d+' | head -1)
fi

echo "Phase to plan: $N"
```

Handle decimal phases (inserted phases like 2.1):

```bash
# Check if N contains decimal (inserted phase)
if [[ "$N" == *"."* ]]; then
    echo "Planning inserted phase: $N"
fi
```
</parse_phase>

---

### Step 3: Validate Phase Exists

<validate_phase_exists>
Verify phase exists in ROADMAP.md:

```bash
# Match both "Phase N:" and "Phase N.X:" patterns
if ! grep -qE "Phase $N(\.[0-9]+)?:" .founder-mode/ROADMAP.md; then
    echo "Phase $N not found in ROADMAP.md"

    # List available phases
    echo ""
    echo "Available phases:"
    grep -oP "Phase \d+(\.\d+)?:" .founder-mode/ROADMAP.md

    exit 1
fi
```

Extract phase information:

```bash
# Get phase name and goal
phase_line=$(grep -A 5 "Phase $N:" .founder-mode/ROADMAP.md | head -6)
phase_name=$(echo "$phase_line" | head -1 | sed 's/.*Phase [0-9.]*: //' | sed 's/ -.*//')
phase_goal=$(echo "$phase_line" | grep "Goal:" | sed 's/.*Goal: //')
phase_reqs=$(echo "$phase_line" | grep "Requirements:" | sed 's/.*Requirements: //')
phase_deps=$(echo "$phase_line" | grep "Depends on:" | sed 's/.*Depends on: //')
```

Check if phase is already complete:

```bash
# Check roadmap for completion status
if grep -q "Phase $N:.*Complete" .founder-mode/ROADMAP.md; then
    echo "Phase $N is already complete."
    echo ""
    echo "To re-plan:"
    echo "  /fm:plan-phase $N --force"
    exit 1
fi
```

Report phase details:

```
Planning Phase {N}: {phase_name}
================================

Goal: {phase_goal}
Requirements: {phase_reqs}
Depends on: {phase_deps}
```
</validate_phase_exists>

---

### Step 4: Handle Research

<handle_research>
Check if phase requires research (from ROADMAP.md):

```bash
research_needed=$(grep -A 10 "Phase $N:" .founder-mode/ROADMAP.md | grep "Research:" | sed 's/.*Research: //')
```

If research is "Likely" and no RESEARCH.md exists:

```
AskUserQuestion:
  question: "This phase may need research. How to proceed?"
  options:
    - "Run research first (/fm:research-phase)"
    - "Skip research and plan directly"
    - "Cancel and do manual research"
```

If research selected, report:

```
Research recommended. Run:
  /fm:research-phase {N}

Then return to:
  /fm:plan-phase {N}
```

Exit and let user run research command.
</handle_research>

---

### Step 5: Gather Planning Context

<gather_planning_context>
Load all context needed for planning:

**1. Load phase-specific context:**

```bash
# Create phase directory if needed
mkdir -p .founder-mode/plans/phase-${N}

# Check for CONTEXT.md (from discuss-phase)
context_file=".founder-mode/plans/phase-${N}/CONTEXT.md"
if [ -f "$context_file" ]; then
    echo "Loading user context: $context_file"
fi

# Check for RESEARCH.md (from research-phase)
research_file=".founder-mode/plans/phase-${N}/RESEARCH.md"
if [ -f "$research_file" ]; then
    echo "Loading research: $research_file"
fi
```

**2. Load project state:**

Read from STATE.md:
- Accumulated decisions
- Pending todos (candidates for inclusion)
- Blockers/concerns

**3. Load codebase context (if exists):**

```bash
# Check for codebase analysis
if [ -d ".founder-mode/codebase" ]; then
    echo "Loading codebase context"
    # Load CONVENTIONS.md, STRUCTURE.md, etc. based on phase type
fi
```

**4. Load prior phase summaries:**

```bash
# Find completed phases that affect this one
for summary in .founder-mode/plans/phase-*/SUMMARY.md; do
    if [ -f "$summary" ]; then
        # Read frontmatter to check if it affects current phase
        echo "Checking: $summary"
    fi
done
```

**5. If --gaps mode, load gap sources:**

```bash
# Check for VERIFICATION.md (code verification gaps)
verification_file=".founder-mode/plans/phase-${N}/VERIFICATION.md"

# Check for UAT.md (user testing gaps)
uat_file=".founder-mode/plans/phase-${N}/UAT.md"

if [ -f "$verification_file" ]; then
    echo "Loading verification gaps: $verification_file"
fi

if [ -f "$uat_file" ]; then
    echo "Loading UAT gaps: $uat_file"
fi
```
</gather_planning_context>

---

### Step 6: Create Plans

<create_plans>
**Standard Mode:**

Decompose phase into executable plans using goal-backward methodology.

**Step 6.1: Derive must_haves from phase goal**

Apply goal-backward analysis:

1. **State the Goal** - Take phase goal from ROADMAP.md (outcome, not task)
2. **Derive Observable Truths** - What must be TRUE for goal to be achieved (3-7 truths, user perspective)
3. **Derive Required Artifacts** - What files/components must EXIST for truths to be true
4. **Derive Required Wiring** - What connections between artifacts are needed
5. **Identify Key Links** - Critical connections where failure causes cascading issues

**Step 6.2: Break into tasks**

For each must_have truth:
- What files need to be created/modified?
- What actions produce those files?
- How do we verify the action succeeded?
- What acceptance criteria confirm completion?

**Step 6.3: Build dependency graph**

For each task:
- `needs`: What must exist before this task runs
- `creates`: What this task produces
- `has_checkpoint`: Does this require user interaction?

**Step 6.4: Assign waves**

```
waves = {}

for each plan in plan_order:
  if plan.depends_on is empty:
    plan.wave = 1
  else:
    plan.wave = max(waves[dep] for dep in plan.depends_on) + 1

  waves[plan.id] = plan.wave
```

**Step 6.5: Group into plans**

Rules:
- Each plan: 2-3 tasks maximum
- Same-wave tasks with no file conflicts can be parallel
- Tasks with shared files must be sequential
- Checkpoint tasks mark plan as `autonomous: false`
- Target ~50% context usage per plan

**Step 6.6: Write PLAN.md files**

Write each plan to `.founder-mode/plans/phase-{N}/{N}-{NN}-PLAN.md`:

```markdown
---
phase: {N}-{phase_name}
plan: {NN}
type: execute
wave: {wave_number}
depends_on: [{dependency_plan_ids}]
files_modified: [{files_this_plan_touches}]
autonomous: {true|false}
user_setup: []

must_haves:
  truths:
    - "{Observable behavior 1}"
    - "{Observable behavior 2}"
  artifacts:
    - path: "{file_path}"
      provides: "{what it provides}"
      min_lines: {estimate}
  key_links:
    - from: "{source_file}"
      to: "{target}"
      via: "{connection_method}"
      pattern: "{regex_to_verify}"
---

<objective>
{What this plan accomplishes}

Purpose: {Why this matters for the project}
Output: {What artifacts will be created}
</objective>

<context>
@.founder-mode/PROJECT.md
@.founder-mode/ROADMAP.md
@.founder-mode/STATE.md

{@prior_plan_summaries if genuinely needed}
{@source_files if needed}
</context>

<tasks>

<task type="auto">
  <name>Task 1: {Action-oriented name}</name>
  <files>{path/to/file.ext}</files>
  <action>{Specific implementation instructions}</action>
  <verify>{Command or check to confirm}</verify>
  <done>{Acceptance criteria}</done>
</task>

<task type="auto">
  <name>Task 2: {Action-oriented name}</name>
  <files>{path/to/file.ext}</files>
  <action>{Specific implementation instructions}</action>
  <verify>{Command or check to confirm}</verify>
  <done>{Acceptance criteria}</done>
</task>

</tasks>

<verification>
{Overall phase checks - commands to run}
</verification>

<success_criteria>
{Measurable completion state}
</success_criteria>

<output>
After completion, create `.founder-mode/plans/phase-{N}/{N}-{NN}-SUMMARY.md`
</output>
```

**Gap Closure Mode (--gaps):**

When `--gaps` flag is present:

1. Parse gaps from VERIFICATION.md or UAT.md
2. Load existing SUMMARYs to understand what's built
3. Find next plan number (if plans 01, 02, 03 exist, next is 04)
4. Group related gaps into plans
5. Create gap closure tasks with `gap_closure: true` in frontmatter

Gap closure plan frontmatter:

```yaml
---
phase: {N}-{phase_name}
plan: {NN}
type: execute
wave: 1
depends_on: []
files_modified: [{files_to_fix}]
autonomous: true
gap_closure: true
---
```
</create_plans>

---

### Step 7: Validate Plans

<validate_plans>
**Skip if --skip-validation flag is set.**

Run plan checker to verify plans will achieve phase goal.

**Validation Dimensions:**

1. **Requirement Coverage** - Every phase requirement has task(s) addressing it
2. **Task Completeness** - Every task has Files + Action + Verify + Done
3. **Dependency Correctness** - No cycles, all references valid, waves consistent
4. **Key Links Planned** - Artifacts wired together, not created in isolation
5. **Scope Sanity** - 2-3 tasks per plan, within context budget
6. **must_haves Derivation** - Truths are user-observable, artifacts support truths

**Checker Process:**

```bash
# For each PLAN.md file
for plan in .founder-mode/plans/phase-${N}/*-PLAN.md; do
    echo "Checking: $plan"

    # Check task count
    task_count=$(grep -c "<task" "$plan")
    if [ "$task_count" -gt 4 ]; then
        echo "WARNING: $plan has $task_count tasks (max 3 recommended)"
    fi

    # Check for missing verify elements
    if grep -q "<task" "$plan" && ! grep -q "<verify>" "$plan"; then
        echo "ERROR: $plan missing <verify> elements"
    fi

    # Check for missing done elements
    if grep -q "<task" "$plan" && ! grep -q "<done>" "$plan"; then
        echo "ERROR: $plan missing <done> elements"
    fi
done
```

**Checker Output Format:**

```yaml
status: passed | issues_found

issues:
  - plan: "{N}-{NN}"
    dimension: "{requirement_coverage|task_completeness|...}"
    severity: "{blocker|warning|info}"
    description: "{What's wrong}"
    fix_hint: "{How to fix}"
```
</validate_plans>

---

### Step 8: Revision Loop

<revision_loop>
If validation finds issues, revise plans.

**Maximum 3 iterations of planner -> checker -> revise.**

**Iteration Flow:**

1. Checker reports issues
2. Display issues to planner context:

```
Validation Issues Found
=======================

Blockers (must fix):
1. [{dimension}] {description}
   - Plan: {plan}
   - Fix: {fix_hint}

Warnings (should fix):
1. [{dimension}] {description}
   - Plan: {plan}
   - Fix: {fix_hint}
```

3. Revise plans based on feedback:
   - For task_completeness: Add missing elements to existing task
   - For requirement_coverage: Add task(s) to cover missing requirement
   - For dependency_correctness: Fix depends_on array, recompute waves
   - For key_links_planned: Add wiring task or update action
   - For scope_sanity: Split plan into multiple smaller plans
   - For must_haves_derivation: Derive and add must_haves to frontmatter

4. Re-run checker on revised plans

5. If blockers remain after 3 iterations:

```
Validation incomplete after 3 iterations.

Remaining blockers:
{list remaining blockers}

Options:
1. Force proceed (plans may fail during execution)
2. Continue manual revision
3. Cancel and restart planning

AskUserQuestion:
  question: "How to proceed?"
  options:
    - "Force proceed with current plans"
    - "Let me manually fix the issues"
    - "Cancel planning"
```

**Revision Success:**

When all blockers resolved:

```
Validation Passed
=================

Plans verified: {count}
Iterations: {count}

Wave Structure:
| Wave | Plans | Autonomous |
|------|-------|------------|
| 1 | {plans} | {yes/no} |
| 2 | {plans} | {yes/no} |

Ready for execution.
```
</revision_loop>

---

### Step 9: Update Roadmap

<update_roadmap>
Update ROADMAP.md with plan information:

1. Read `.founder-mode/ROADMAP.md`
2. Find the phase entry (`### Phase {N}:`)
3. Update plan count and list:

**Before:**
```markdown
### Phase 1: Foundation
**Goal**: Set up project structure
**Depends on**: Nothing
**Requirements**: [SETUP-01, SETUP-02]
**Research**: Unlikely
**Plans**: TBD
```

**After:**
```markdown
### Phase 1: Foundation
**Goal**: Set up project structure
**Depends on**: Nothing
**Requirements**: [SETUP-01, SETUP-02]
**Research**: Unlikely
**Plans**: 3 plans

Plans:
- [ ] 1-01-PLAN.md - Project scaffolding and configuration
- [ ] 1-02-PLAN.md - Database schema and migrations
- [ ] 1-03-PLAN.md - Development environment setup
```

4. Update progress table:

```markdown
| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/3 | Ready to execute | - |
```

5. Write updated ROADMAP.md
</update_roadmap>

---

### Step 10: Commit and Present

<commit_plans>
Commit all plan files and updated roadmap:

```bash
git add .founder-mode/plans/phase-${N}/*.md
git add .founder-mode/ROADMAP.md

git commit -m "Plan Phase ${N}: ${phase_name}

- ${plan_count} plan(s) in ${wave_count} wave(s)
- ${parallel_count} parallel, ${sequential_count} sequential
- Ready for execution"
```
</commit_plans>

<update_state>
Update STATE.md:

```markdown
Status: Ready to execute
Last activity: {date} - Phase {N} planned ({plan_count} plans)
```

```bash
git add .founder-mode/STATE.md
git commit -m "Update state: Phase ${N} ready to execute"
```
</update_state>

<completion_message>
Display completion:

```
Phase {N} Planning Complete
===========================

Plans created: {count}
Waves: {count}

Wave Structure:
| Wave | Plans | Autonomous |
|------|-------|------------|
| 1 | {plan_ids} | {yes/no} |
| 2 | {plan_ids} | {yes/no} |

Plans Summary:
| Plan | Objective | Tasks | Files |
|------|-----------|-------|-------|
| {N}-01 | {brief} | {count} | {files} |
| {N}-02 | {brief} | {count} | {files} |

{if any checkpoints}
Checkpoints:
- {plan_id}: {checkpoint_type} - {description}
{/if}

Next step:
  /fm:execute-phase {N}

Or review plans:
  cat .founder-mode/plans/phase-{N}/*-PLAN.md
```
</completion_message>

---

## Plan File Format Reference

### YAML Frontmatter

```yaml
---
phase: {N}-{phase_name}        # Phase identifier (e.g., "01-foundation")
plan: {NN}                     # Plan number within phase (01, 02, ...)
type: execute                  # "execute" for standard, "tdd" for TDD plans
wave: {N}                      # Execution wave (1, 2, 3...)
depends_on: []                 # Plan IDs this plan requires
files_modified: []             # Files this plan touches
autonomous: true               # false if plan has checkpoints

user_setup: []                 # Human-required setup (omit if empty)

must_haves:
  truths: []                   # Observable behaviors (user perspective)
  artifacts: []                # Files that must exist
  key_links: []                # Critical connections
---
```

### XML Task Structure

```xml
<task type="auto">
  <name>{Action-oriented name}</name>
  <files>{Exact file paths}</files>
  <action>{Specific implementation with what to avoid and WHY}</action>
  <verify>{Command or check to confirm}</verify>
  <done>{Acceptance criteria}</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>{What Claude automated}</what-built>
  <how-to-verify>{Exact steps to test}</how-to-verify>
  <resume-signal>{How to continue}</resume-signal>
</task>

<task type="checkpoint:decision" gate="blocking">
  <decision>{What's being decided}</decision>
  <context>{Why this matters}</context>
  <options>
    <option id="option-a">
      <name>{Name}</name>
      <pros>{Benefits}</pros>
      <cons>{Tradeoffs}</cons>
    </option>
  </options>
  <resume-signal>{How to select}</resume-signal>
</task>
```

### must_haves Format

```yaml
must_haves:
  truths:
    - "User can see existing messages"
    - "User can send a message"
    - "Messages persist across refresh"

  artifacts:
    - path: "src/components/Chat.tsx"
      provides: "Message list rendering"
      min_lines: 30
    - path: "src/app/api/chat/route.ts"
      provides: "Message CRUD operations"
      exports: ["GET", "POST"]

  key_links:
    - from: "src/components/Chat.tsx"
      to: "/api/chat"
      via: "fetch in useEffect"
      pattern: "fetch.*api/chat"
    - from: "src/app/api/chat/route.ts"
      to: "prisma.message"
      via: "database query"
      pattern: "prisma\\.message\\.(find|create)"
```

---

## Error Handling

<error_no_project>
If .founder-mode/PROJECT.md doesn't exist:

```
No project found.

Run /fm:new-project first to initialize.
```
</error_no_project>

<error_no_roadmap>
If .founder-mode/ROADMAP.md doesn't exist:

```
No roadmap found.

Run /fm:new-project to create roadmap.
```
</error_no_roadmap>

<error_phase_not_found>
If phase number doesn't exist:

```
Phase {N} not found in ROADMAP.md.

Available phases:
{list phases from ROADMAP.md}

Use: /fm:plan-phase {valid_phase_number}
```
</error_phase_not_found>

<error_phase_complete>
If phase is already marked complete:

```
Phase {N} is already complete.

To re-plan (will archive existing plans):
  /fm:plan-phase {N} --force
```
</error_phase_complete>

<error_validation_failed>
If validation fails after max iterations:

```
Validation incomplete.

{blocker_count} blockers remain after 3 iterations.

Options:
1. /fm:plan-phase {N} --skip-validation
2. Manually edit plans in .founder-mode/plans/phase-{N}/
3. /fm:discuss-phase {N} to gather more context
```
</error_validation_failed>

---

## Examples

**Plan current phase:**
```
/fm:plan-phase
```

**Plan specific phase:**
```
/fm:plan-phase 3
```

**Plan inserted phase:**
```
/fm:plan-phase 2.1
```

**Gap closure mode:**
```
/fm:plan-phase 2 --gaps
```

**Skip validation (force):**
```
/fm:plan-phase 1 --skip-validation
```

---

## Success Criteria

- [ ] Phase number parsed correctly (from arg or STATE.md)
- [ ] Phase validated against ROADMAP.md
- [ ] Phase directory created (.founder-mode/plans/phase-{N}/)
- [ ] Context gathered (CONTEXT.md, RESEARCH.md, prior SUMMARYs)
- [ ] must_haves derived using goal-backward methodology
- [ ] Tasks decomposed with needs/creates analysis
- [ ] Dependency graph built
- [ ] Waves assigned based on dependencies
- [ ] PLAN.md files written with correct format
- [ ] Validation loop completed (unless --skip-validation)
- [ ] All blockers resolved (or user forced proceed)
- [ ] ROADMAP.md updated with plan list
- [ ] STATE.md updated
- [ ] Git commit created with plans and roadmap
