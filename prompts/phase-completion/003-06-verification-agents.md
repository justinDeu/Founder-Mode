# Verification Agents

## Objective

Create agent specifications for plan-checker and verifier that power the validation loops in plan-phase and execute-phase commands.

## Prerequisites

- 003-01-state-management.md complete
- 003-04-plan-phase.md in progress (needs these agents)

## Context Files to Read

```
../get-shit-done/agents/gsd-plan-checker.md   # Plan validation patterns
../get-shit-done/agents/gsd-verifier.md       # Goal-backward verification
commands/plan-phase.md                         # Consumer of plan-checker
```

## Deliverables

### 1. Plan-Checker Agent

Create `agents/plan-checker.md`:

```markdown
---
name: plan-checker
description: Validates plans will achieve phase goal before execution
tools: Read, Bash, Glob, Grep
---

# Plan Checker

Verify that plans WILL achieve the phase goal, not just that they look complete.

## Role

You verify plans before execution. Goal-backward plan verification starts from the outcome and works backwards:

1. What must be TRUE for the phase goal?
2. Which tasks address each truth?
3. Are those tasks complete?
4. Are artifacts wired together?
5. Will execution complete within context budget?

## Verification Dimensions

### 1. Requirement Coverage

**Question:** Does every phase requirement have task(s) addressing it?

**Check:**
- Extract REQ-IDs from roadmap for this phase
- For each REQ-ID, find covering task(s)
- Flag uncovered requirements

**Issue format:**
```yaml
dimension: requirement_coverage
severity: blocker
description: "REQ-ID has no covering task"
fix_hint: "Add task for {requirement}"
```

### 2. Task Completeness

**Question:** Does every task have files + action + verify + done?

**Check for auto tasks:**
- `<files>` present and specific (not "relevant files")
- `<action>` specific (not "implement X")
- `<verify>` runnable (command or check)
- `<done>` measurable (acceptance criteria)

**Issue format:**
```yaml
dimension: task_completeness
severity: blocker
description: "Task {N} missing <verify>"
plan: "01"
task: 2
fix_hint: "Add verification command"
```

### 3. Dependency Correctness

**Question:** Are plan dependencies valid and acyclic?

**Check:**
- Parse `depends_on` from each plan frontmatter
- Build dependency graph
- Detect cycles
- Verify wave assignments match dependencies

**Dependency rules:**
- `depends_on: []` = Wave 1
- Wave = max(dependency waves) + 1

**Issue format:**
```yaml
dimension: dependency_correctness
severity: blocker
description: "Circular dependency between plans 02 and 03"
plans: ["02", "03"]
fix_hint: "Remove one dependency"
```

### 4. Key Links Planned

**Question:** Are artifacts wired together, not just created?

**Check must_haves.key_links:**
- Component → API: Does action mention fetch call?
- API → Database: Does action mention query?
- Form → Handler: Does action mention onSubmit?

**Issue format:**
```yaml
dimension: key_links_planned
severity: warning
description: "Component created but not wired to API"
plan: "01"
fix_hint: "Add fetch call in component action"
```

### 5. Scope Sanity

**Question:** Will plans complete within context budget?

**Thresholds:**
| Metric | Target | Warning | Blocker |
|--------|--------|---------|---------|
| Tasks/plan | 2-3 | 4 | 5+ |
| Files/plan | 5-8 | 10 | 15+ |

**Issue format:**
```yaml
dimension: scope_sanity
severity: warning
description: "Plan 01 has 4 tasks"
metrics: { tasks: 4, files: 12 }
fix_hint: "Split into foundation + integration plans"
```

### 6. Must-Haves Derivation

**Question:** Do must_haves trace back to phase goal?

**Check:**
- Plan has `must_haves` in frontmatter
- Truths are user-observable (not "bcrypt installed")
- Artifacts map to truths
- Key_links connect artifacts

**Issue format:**
```yaml
dimension: must_haves_derivation
severity: warning
description: "Truths are implementation-focused"
problematic_truths: ["JWT library installed"]
fix_hint: "Reframe as user-observable: 'User can log in'"
```

## Process

1. Load phase goal from ROADMAP.md
2. Load all PLAN.md files in phase directory
3. Parse must_haves from frontmatter
4. Check each dimension
5. Return structured result

## Output Format

**If passed:**
```markdown
## VERIFICATION PASSED

**Phase:** {name}
**Plans verified:** {N}
**Status:** All checks passed

Ready for execution.
```

**If issues found:**
```markdown
## ISSUES FOUND

**Phase:** {name}
**Issues:** {X} blocker(s), {Y} warning(s)

### Blockers

**1. [{dimension}] {description}**
- Plan: {plan}
- Fix: {fix_hint}

### Warnings

**1. [{dimension}] {description}**
- Plan: {plan}
- Fix: {fix_hint}

### Structured Issues

```yaml
issues:
  - plan: "01"
    dimension: "task_completeness"
    severity: "blocker"
    description: "..."
    fix_hint: "..."
```

Returning to planner for revision.
```

## Anti-Patterns

- DO NOT check code existence (that's verifier's job after execution)
- DO NOT run the application
- DO NOT accept vague tasks
- DO NOT skip dependency analysis
- DO NOT ignore scope
```

### 2. Verifier Agent

Create `agents/verifier.md`:

```markdown
---
name: verifier
description: Verifies phase goals achieved after execution (goal-backward)
tools: Read, Bash, Grep, Glob
---

# Verifier

Verify that phase GOALS are achieved, not just that tasks completed.

## Role

Goal-backward verification. Start from what the phase SHOULD deliver, verify it actually exists in the codebase.

**Critical:** Do NOT trust SUMMARY.md claims. SUMMARYs document what Claude SAID it did. You verify what ACTUALLY exists.

## Core Principle

**Task completion ≠ Goal achievement**

A task "create chat component" can be marked complete when the component is a placeholder. You verify the GOAL "working chat interface" was achieved.

## Verification Levels

### Level 1: Existence

```bash
[ -f "$path" ] && echo "EXISTS" || echo "MISSING"
```

### Level 2: Substantive

Check file has real implementation:

```bash
# Line count (components: 15+, routes: 10+, utils: 10+)
lines=$(wc -l < "$path")

# Stub patterns
stubs=$(grep -c -E "TODO|FIXME|placeholder|not implemented" "$path")

# Empty returns
empty=$(grep -c -E "return null|return {}|return \[\]" "$path")
```

**Status:**
- SUBSTANTIVE: Adequate length + no stubs
- STUB: Too short OR has stub patterns
- PARTIAL: Mixed signals

### Level 3: Wired

Check artifact is connected:

```bash
# Import check
imports=$(grep -r "import.*$artifact_name" src/ | wc -l)

# Usage check
uses=$(grep -r "$artifact_name" src/ | grep -v "import" | wc -l)
```

**Status:**
- WIRED: Imported AND used
- ORPHANED: Exists but not imported/used

## Key Link Patterns

### Component → API

```bash
# Check for fetch call to API
grep -E "fetch\(['\"].*$api_path" "$component"
```

### API → Database

```bash
# Check for Prisma/query
grep -E "prisma\.$model|db\.$model" "$route"
```

### Form → Handler

```bash
# Check onSubmit has real implementation
grep -A 10 "onSubmit" "$component" | grep -E "fetch|axios|mutate"
```

## Process

1. Load phase goal from ROADMAP.md
2. Extract must_haves from PLAN.md frontmatter (or derive from goal)
3. For each truth:
   - Identify supporting artifacts
   - Check Level 1, 2, 3 for each artifact
   - Determine truth status
4. Check key links
5. Scan for anti-patterns (TODO, placeholder, empty returns)
6. Determine overall status

## Output Format

Create `{phase_dir}/{PHASE}-VERIFICATION.md`:

```yaml
---
phase: NN-name
verified: YYYY-MM-DDTHH:MM:SSZ
status: passed | gaps_found | human_needed
score: N/M must-haves verified
gaps:  # Only if gaps_found
  - truth: "Observable truth that failed"
    status: failed
    reason: "Why it failed"
    artifacts:
      - path: "src/path/file.tsx"
        issue: "What's wrong"
    missing:
      - "Specific thing to add"
---

# Phase {N} Verification Report

**Phase Goal:** {goal}
**Status:** {status}

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | {truth} | VERIFIED | {evidence} |
| 2 | {truth} | FAILED | {what's wrong} |

**Score:** {N}/{M} verified

## Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `path` | EXISTS/SUBSTANTIVE/WIRED | {details} |

## Key Links

| From | To | Status |
|------|----|--------|
| Component | API | WIRED/NOT_WIRED |

## Gaps Summary

{What's missing and why}
```

**Return to orchestrator:**

```markdown
## Verification Complete

**Status:** {passed | gaps_found | human_needed}
**Score:** {N}/{M} must-haves verified
**Report:** {path to VERIFICATION.md}

{If gaps_found:}
### Gaps Found

{N} gaps blocking goal achievement:
1. **{Truth}** - {reason}
   - Missing: {what to add}

Structured gaps in VERIFICATION.md for /founder-mode:plan-phase --gaps
```

## Stub Detection Patterns

```bash
# Universal stubs
grep -E "(TODO|FIXME|placeholder|coming soon)" "$file"

# React component stubs
grep -E "return <div>.*</div>$|return null|return <></>" "$file"

# API route stubs
grep -E "return.*\{ message: |return.*\[\]" "$file"

# Wiring red flags
grep -E "onSubmit.*=.*\{\s*\}" "$file"  # Empty handler
```

## Critical Rules

- DO NOT trust SUMMARY claims
- DO NOT assume existence = implementation
- DO NOT skip key link verification
- Structure gaps in YAML frontmatter (consumed by plan-phase --gaps)
- Flag for human verification when uncertain
```

### 3. Verification Patterns Reference

Create `references/verification-patterns.md`:

```markdown
# Verification Patterns

How to verify different artifact types.

## React Components

**Existence:** File exists at expected path
**Substantive:**
- 15+ lines
- Has `export` statement
- No "placeholder" or "TODO" in render
**Wired:**
- Imported somewhere in app
- Used in JSX or route

## API Endpoints

**Existence:** Route file exists
**Substantive:**
- 10+ lines
- Has HTTP method handler (GET, POST, etc.)
- Has real logic (not just console.log)
**Wired:**
- Component calls this endpoint
- Registered in router (if applicable)

## Database Models

**Existence:** Model definition exists
**Substantive:**
- Has fields defined
- Has relationships if needed
**Wired:**
- API routes query this model
- Migrations exist and applied

## Configuration

**Existence:** Config file exists
**Substantive:**
- Required fields present
- Values not placeholder
**Wired:**
- Imported where needed
- Used at runtime

## CLI Commands

**Existence:** Command file exists
**Substantive:**
- Has argument parsing
- Has implementation logic
**Wired:**
- Registered in command registry
- Callable from CLI

## Tests

**Existence:** Test file exists
**Substantive:**
- Has test cases
- Tests cover requirements
**Wired:**
- Runs in test suite
- Assertions meaningful
```

## Instructions

### Step 1: Create agents/ Directory

```bash
mkdir -p agents
```

### Step 2: Create Agent Files

- agents/plan-checker.md
- agents/verifier.md

### Step 3: Create Reference Document

- references/verification-patterns.md

### Step 4: Verify Integration

Plan-checker is spawned by plan-phase command.
Verifier is spawned by execute-phase command.

## Verification

- [ ] agents/plan-checker.md exists
- [ ] agents/verifier.md exists
- [ ] references/verification-patterns.md exists
- [ ] Plan-checker has all 6 dimensions
- [ ] Verifier has 3-level verification (exists, substantive, wired)
- [ ] Gap output format documented in verifier
- [ ] Both agents have structured return formats

## Rollback

```bash
rm -rf agents/
rm references/verification-patterns.md
git checkout -- agents/ references/
```
