# Discuss Phase Command

## Objective

Implement `/founder-mode:discuss-phase [N]` command that captures user vision and decisions before planning begins. This prevents Claude from making assumptions about implementation details.

## Prerequisites

- 003-01-state-management.md complete
- 003-02-new-project.md complete
- .founder-mode/ directory structure established

## Context Files to Read

```
commands/new-project.md     # For command pattern
templates/state.md          # For state format
references/state-utilities.md
```

## Deliverables

Create `commands/discuss-phase.md`:

```markdown
---
name: founder-mode:discuss-phase
description: Gather phase context through adaptive questioning before planning
argument-hint: "<phase-number>"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# Discuss Phase

Extract implementation decisions that downstream agents need. Creates CONTEXT.md that guides research and planning.

## Arguments

Parse from $ARGUMENTS:
- Phase number (required): Integer (e.g., 1, 2, 3)

## Process

### Step 1: Validate Phase

```bash
# Check project exists
[ -d .founder-mode ] || { echo "ERROR: No project. Run /founder-mode:new-project"; exit 1; }

# Normalize phase number
PHASE=$(printf "%02d" $PHASE_ARG)

# Check phase exists in roadmap
grep -q "Phase ${PHASE}:" .founder-mode/ROADMAP.md || { echo "ERROR: Phase not found"; exit 1; }
```

### Step 2: Check Existing Context

```bash
PHASE_DIR=$(ls -d .founder-mode/phases/${PHASE}-* 2>/dev/null | head -1)
[ -f "${PHASE_DIR}/${PHASE}-CONTEXT.md" ] && echo "Context exists"
```

**If CONTEXT.md exists:**

Use AskUserQuestion:
- header: "Existing Context"
- question: "Phase {N} already has CONTEXT.md. What do you want to do?"
- options:
  - "View existing" - Show current decisions
  - "Update" - Add to existing context
  - "Start fresh" - Replace with new context
  - "Skip" - Use existing, proceed to planning

### Step 3: Analyze Phase for Gray Areas

Read phase goal from ROADMAP.md. Identify discussable domains based on what's being built:

**Domain Detection:**

| Phase Type | Gray Areas to Surface |
|------------|----------------------|
| UI/Frontend | Layout, density, interactions, states, responsive behavior |
| API/Backend | Response shape, error format, auth approach, versioning |
| CLI | Output format, flags, modes, error messages |
| Data/Models | Schema design, relationships, validation rules |
| Integration | Auth flow, data sync, error handling |

**Generate 3-4 phase-specific gray areas:**

Not generic categories. Specific to what THIS phase builds.

Example for "User authentication phase":
1. Login flow: Form vs modal? Remember me? Social login priority?
2. Error handling: Inline errors vs toast? Specific messages vs generic?
3. Session: Duration? Refresh approach? Multi-device?
4. Security: 2FA now or later? Password requirements?

### Step 4: Present Gray Areas

Use AskUserQuestion:
- header: "Areas to Discuss"
- question: "I've identified areas that could use your input before planning. Which would you like to discuss?"
- multiSelect: true
- options: The generated gray areas

**Important:** Do NOT include "Skip all" option. Minimal discussion is required.

### Step 5: Deep-Dive Each Area

For each selected area, ask 4 focused questions.

**Question types:**
- "How should X look/work?"
- "When Y happens, what should Z do?"
- "Between A and B, which fits your vision?"
- "What's the priority between X and Y?"

Use AskUserQuestion for choices, freeform for open-ended.

**After 4 questions per area:**
- "More questions about {area}, or move to next?"

If more, ask 4 more. Repeat until satisfied.

### Step 6: Scope Guardrails

**Critical rule:** Phase boundary from ROADMAP.md is FIXED.

If user mentions features outside phase scope:
1. Acknowledge: "Good idea"
2. Capture in "Deferred Ideas" section
3. Redirect: "For this phase, let's focus on {phase goal}"
4. Do NOT add to current phase scope

### Step 7: Write CONTEXT.md

Create `.founder-mode/phases/{phase_dir}/{PHASE}-CONTEXT.md`:

```markdown
# Phase {N} Context

## Domain Boundary

**This phase covers:**
{What's in scope}

**This phase does NOT cover:**
{What's explicitly out}

## Decisions by Category

### {Area 1 - e.g., Login Flow}

- **{Decision 1}**: User chose {X} over {Y}
  - Rationale: {why}
- **{Decision 2}**: {choice}

### {Area 2 - e.g., Error Handling}

- **{Decision 1}**: {choice}

### {Area 3}

...

## Claude's Discretion

Areas user chose NOT to discuss. Claude decides during planning:
- {Area not selected}
- {Another area not selected}

## Deferred Ideas

Ideas mentioned but out of scope for this phase:
- {Idea 1} - noted for future consideration
- {Idea 2}

---
*Discussed: {date}*
*Decisions: {count} across {count} areas*
```

### Step 8: Commit and Next Steps

```bash
mkdir -p "${PHASE_DIR}"
git add "${PHASE_DIR}/${PHASE}-CONTEXT.md"
git commit -m "docs(${PHASE}): capture phase context

{N} decisions across {M} areas"
```

**Present completion:**

```
PHASE {N} CONTEXT CAPTURED

{X} decisions across {Y} areas
{Z} deferred ideas noted

Downstream consumers:
- /founder-mode:plan-phase reads this for planning
- Research agent (if used) focuses on undecided areas

Next: /founder-mode:plan-phase {N}
```

## Downstream Consumers

- `plan-phase` loads CONTEXT.md to respect user decisions
- Researcher (if spawned) loads CONTEXT.md to focus research on undecided areas
- These are LOCKED decisions - do not revisit during planning

## Success Criteria

- [ ] Phase validated against roadmap
- [ ] Gray areas generated based on phase type
- [ ] User selected areas to discuss
- [ ] Each selected area explored with 4+ questions
- [ ] Scope creep redirected to deferred ideas
- [ ] CONTEXT.md captures decisions (not vague vision)
- [ ] Committed to git
- [ ] User knows next step
```

## Instructions

### Step 1: Create Command File

Create `commands/discuss-phase.md` with the full content above.

### Step 2: Create Phase Directory Template

The command creates phase directories as needed. Ensure the pattern is:
`.founder-mode/phases/NN-phase-name/`

### Step 3: Verify Gray Area Generation

The command should analyze phase goal and generate SPECIFIC gray areas, not generic categories.

## Verification

- [ ] commands/discuss-phase.md exists
- [ ] Argument parsing handles phase number
- [ ] Gray area generation is domain-aware
- [ ] Multi-select for area selection
- [ ] 4 questions per selected area
- [ ] Scope guardrails prevent creep
- [ ] CONTEXT.md format documented
- [ ] Downstream consumers documented

## Rollback

```bash
rm commands/discuss-phase.md
rm -rf .founder-mode/phases/*/CONTEXT.md
git checkout -- commands/discuss-phase.md
```
