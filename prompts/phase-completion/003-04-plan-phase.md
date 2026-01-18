# Plan Phase Command

## Objective

Implement `/founder-mode:plan-phase [N]` command with pre-execution validation loop. Creates executable PLAN.md files that Claude can implement without interpretation.

## Prerequisites

- 003-01-state-management.md complete
- 003-02-new-project.md complete
- 003-03-discuss-phase.md complete
- 003-06-verification-agents.md complete (for plan-checker reference)

## Context Files to Read

```
commands/discuss-phase.md   # For command pattern
references/state-utilities.md
../get-shit-done/agents/gsd-planner.md        # Planning patterns
../get-shit-done/agents/gsd-plan-checker.md   # Validation dimensions
```

## Deliverables

Create `commands/plan-phase.md`:

```markdown
---
name: founder-mode:plan-phase
description: Create detailed execution plan for a phase with validation loop
argument-hint: "[phase] [--skip-research] [--gaps] [--skip-verify]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - Task
  - WebFetch
  - AskUserQuestion
---

# Plan Phase

Create executable phase prompts (PLAN.md files) with integrated research and verification.

## Arguments

Parse from $ARGUMENTS:
- Phase number (optional): Auto-detects next unplanned phase if not provided
- `--skip-research`: Skip domain research
- `--gaps`: Gap closure mode (reads VERIFICATION.md)
- `--skip-verify`: Skip plan validation loop

## Process

### Step 1: Validate Environment

```bash
[ -d .founder-mode ] || { echo "ERROR: No project"; exit 1; }
```

### Step 2: Parse and Normalize Phase

```bash
# Normalize to zero-padded format
if [[ "$PHASE" =~ ^[0-9]+$ ]]; then
  PHASE=$(printf "%02d" "$PHASE")
fi

# Find phase directory
PHASE_DIR=$(ls -d .founder-mode/phases/${PHASE}-* 2>/dev/null | head -1)
if [ -z "$PHASE_DIR" ]; then
  # Create from roadmap
  PHASE_NAME=$(grep "Phase ${PHASE}:" .founder-mode/ROADMAP.md | sed 's/.*: //' | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
  mkdir -p ".founder-mode/phases/${PHASE}-${PHASE_NAME}"
  PHASE_DIR=".founder-mode/phases/${PHASE}-${PHASE_NAME}"
fi
```

### Step 3: Validate Phase Exists

```bash
grep -A5 "Phase ${PHASE}:" .founder-mode/ROADMAP.md || { echo "Phase not found"; exit 1; }
```

Extract phase goal and requirements from ROADMAP.md.

### Step 4: Handle Research (unless --skip-research or --gaps)

**Check for existing research:**
```bash
ls "${PHASE_DIR}"/*-RESEARCH.md 2>/dev/null
```

**If research needed:**

Spawn research agent:
```
Task(
  prompt: "Research how to implement Phase {N}: {name}

  Answer: What do I need to know to PLAN this phase well?

  Phase goal: {goal}
  Requirements: {req-ids}
  Context: @${PHASE_DIR}/${PHASE}-CONTEXT.md

  Output: Write to ${PHASE_DIR}/${PHASE}-RESEARCH.md",
  subagent_type: "Explore",
  description: "Research Phase {N}"
)
```

### Step 5: Gather Planning Context

Identify files for planner:

```bash
STATE=.founder-mode/STATE.md
ROADMAP=.founder-mode/ROADMAP.md
REQUIREMENTS=.founder-mode/REQUIREMENTS.md
CONTEXT="${PHASE_DIR}/${PHASE}-CONTEXT.md"
RESEARCH="${PHASE_DIR}/${PHASE}-RESEARCH.md"
VERIFICATION="${PHASE_DIR}/${PHASE}-VERIFICATION.md"  # For --gaps mode
```

### Step 6: Create Plans

**Planning Philosophy:**
- Plans are prompts, not documents
- 2-3 tasks per plan (quality degrades at 4+)
- Each task: files, action, verify, done
- Goal-backward must_haves derivation

**Plan File Format:**

```yaml
---
phase: NN-name
plan: NN
type: execute
wave: N
depends_on: []
files_modified: []
autonomous: true
must_haves:
  truths: []
  artifacts: []
  key_links: []
---

<objective>
{What this plan accomplishes}

Purpose: {Why this matters}
Output: {Artifacts created}
</objective>

<context>
@.founder-mode/STATE.md
@.founder-mode/ROADMAP.md
@{relevant prior SUMMARYs if needed}
</context>

<tasks>

<task type="auto">
  <name>Task 1: {Action-oriented name}</name>
  <files>{exact paths}</files>
  <action>{Specific implementation}</action>
  <verify>{Command or check}</verify>
  <done>{Acceptance criteria}</done>
</task>

<task type="auto">
  <name>Task 2: {Name}</name>
  <files>{paths}</files>
  <action>{implementation}</action>
  <verify>{check}</verify>
  <done>{criteria}</done>
</task>

</tasks>

<verification>
{Overall plan checks}
</verification>

<success_criteria>
{Measurable completion}
</success_criteria>

<output>
After completion, create ${PHASE_DIR}/${PHASE}-{NN}-SUMMARY.md
</output>
```

**Wave Assignment:**
- Wave 1: Plans with no dependencies
- Wave 2: Plans depending only on Wave 1
- Wave N: max(dependency waves) + 1

**Write plans to disk immediately.**

### Step 7: Validate Plans (unless --skip-verify)

Spawn plan-checker agent:

```
Task(
  prompt: "Verify plans for Phase {N}

  Phase goal: {goal}
  Plans: @${PHASE_DIR}/*-PLAN.md
  Requirements: @.founder-mode/REQUIREMENTS.md

  Check:
  1. Requirement coverage (all REQ-IDs have tasks)
  2. Task completeness (files, action, verify, done)
  3. Dependency correctness (no cycles)
  4. Key links planned (wiring, not just artifacts)
  5. Scope sanity (2-3 tasks/plan)
  6. must_haves derivation (user-observable truths)",
  subagent_type: "general-purpose",
  description: "Verify Phase {N} plans"
)
```

### Step 8: Revision Loop (max 3 iterations)

**If issues found:**

1. Display issues to user
2. Spawn planner in revision mode:
   ```
   Task(
     prompt: "Revise plans to address issues:
     {structured_issues}

     Existing plans: @${PHASE_DIR}/*-PLAN.md

     Make targeted updates. Do NOT replan from scratch.",
     subagent_type: "general-purpose"
   )
   ```
3. Re-run checker
4. Repeat until passed or max iterations

**If max iterations reached:**

Present to user:
- List remaining issues
- Options: Force proceed / Provide guidance / Abort

### Step 9: Update Roadmap

Update ROADMAP.md with plan count:
- Change "Plans: TBD" to "Plans: {N} plans"
- Add plan list under phase

### Step 10: Commit and Present

```bash
git add ${PHASE_DIR}/*-PLAN.md .founder-mode/ROADMAP.md
git commit -m "docs(${PHASE}): create phase plan

Phase ${PHASE}: ${PHASE_NAME}
- {N} plan(s) in {M} wave(s)"
```

**Present completion:**

```
PHASE {N} PLANNED

{N} plan(s) in {M} wave(s)

| Wave | Plans | What it builds |
|------|-------|----------------|
| 1    | 01, 02| {objectives}   |
| 2    | 03    | {objective}    |

Research: {Completed | Used existing | Skipped}
Verification: {Passed | Passed with override}

Next: /founder-mode:execute-phase {N}
```

## Gap Closure Mode (--gaps)

When `--gaps` flag present:

1. Read VERIFICATION.md from failed phase verification
2. Parse `gaps:` section from frontmatter
3. Create plans that specifically close each gap
4. Mark plans with `gap_closure: true` in frontmatter
5. Skip research (VERIFICATION.md provides context)

## Success Criteria

- [ ] Phase directory created if needed
- [ ] Research completed (unless skipped)
- [ ] Plans have valid frontmatter
- [ ] Tasks are specific and actionable
- [ ] Wave structure maximizes parallelism
- [ ] must_haves derived from phase goal
- [ ] Verification passed (unless skipped)
- [ ] Plans committed to git
- [ ] User knows next step
```

## Instructions

### Step 1: Create Command File

Create `commands/plan-phase.md` with the full content above.

### Step 2: Verify Plan Format

Ensure plan format matches the template:
- YAML frontmatter with all required fields
- XML task structure
- Goal-backward must_haves

### Step 3: Test Validation Loop

The planner → checker → revise loop should:
- Pass structured issues between agents
- Make targeted updates (not full replans)
- Stop at 3 iterations

## Verification

- [ ] commands/plan-phase.md exists
- [ ] Phase directory auto-creation works
- [ ] Research spawning documented
- [ ] Plan format matches specification
- [ ] Validation loop documented
- [ ] Gap closure mode documented
- [ ] Wave assignment logic clear
- [ ] Commit includes roadmap update

## Rollback

```bash
rm commands/plan-phase.md
rm -rf .founder-mode/phases/*-PLAN.md
git checkout -- commands/plan-phase.md
```
