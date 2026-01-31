---
name: founder-mode:discuss-phase
description: Capture user vision and decisions before planning begins, preventing Claude from making assumptions
argument-hint: [N] [--refresh]
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# Discuss Phase

Gather user context and decisions for a phase before planning begins. Creates CONTEXT.md with user decisions, Claude's discretion areas, and deferred ideas.

## Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `N` | positional | current | Phase number to discuss (reads from STATE.md if omitted) |
| `--refresh` | flag | false | Re-discuss existing phase, preserving prior decisions |

## Purpose

Planning fails when Claude makes assumptions about implementation details that should be user decisions. This command surfaces gray areas before planning begins.

**Problem:** Claude picks technologies, patterns, and approaches without asking. The plan looks good but misses user preferences.

**Solution:** Domain-aware gray area detection surfaces questions Claude would otherwise decide alone. User provides direction upfront.

## Execution Flow

---

### Step 1: Validate Phase

<validate_phase>
Determine which phase to discuss:

```bash
# If N provided, use it
# Otherwise read current phase from STATE.md
if [ -z "$N" ]; then
    N=$(grep "^Phase:" .founder-mode/STATE.md | grep -oP '\d+' | head -1)
fi

echo "Phase to discuss: $N"
```

Verify phase exists in ROADMAP.md:

```bash
if ! grep -q "Phase $N:" .founder-mode/ROADMAP.md; then
    echo "Phase $N not found in ROADMAP.md"
    exit 1
fi
```

Extract phase info:
- Phase name
- Phase goal
- Requirements covered (REQ-IDs)
- Dependencies (previous phases)

Report:
```
Discussing Phase {N}: {Name}
============================

Goal: {goal from ROADMAP.md}
Requirements: {REQ-IDs}
Depends on: {dependencies}
```
</validate_phase>

---

### Step 2: Check Existing Context

<check_existing_context>
Look for existing CONTEXT.md for this phase:

```bash
context_file=".founder-mode/plans/phase-${N}/CONTEXT.md"
if [ -f "$context_file" ]; then
    echo "Existing context found: $context_file"
fi
```

If `--refresh` flag and context exists:
```
Previous context found for Phase {N}.

AskUserQuestion:
  question: "How should we handle existing context?"
  options:
    - "Start fresh (discard previous)"
    - "Review and update (preserve decisions)"
    - "Keep current context (exit)"
```

If "Keep current context", exit with:
```
Using existing context: {context_file}
Run /fm:plan-phase {N} to continue.
```

If "Review and update", load existing decisions to present during gray area discussion.
</check_existing_context>

---

### Step 3: Analyze Phase for Gray Areas

<domain_detection>
Detect project domain from PROJECT.md and ROADMAP.md:

| Domain Signals | Detected Domain |
|----------------|-----------------|
| `React`, `Vue`, `Angular`, `frontend` | Web Frontend |
| `Express`, `FastAPI`, `Rails`, `backend` | Web Backend |
| `API`, `REST`, `GraphQL` | API Development |
| `CLI`, `terminal`, `command-line` | CLI Tool |
| `mobile`, `iOS`, `Android`, `React Native` | Mobile App |
| `database`, `SQL`, `PostgreSQL`, `MongoDB` | Data Layer |
| `ML`, `model`, `training`, `inference` | Machine Learning |
| `plugin`, `extension`, `integration` | Plugin/Extension |
| `auth`, `login`, `OAuth`, `JWT` | Authentication |
| `test`, `e2e`, `unit`, `coverage` | Testing |
| `deploy`, `CI/CD`, `Docker`, `Kubernetes` | Infrastructure |

Read PROJECT.md constraints and ROADMAP.md phase details to determine applicable domains.

```bash
# Extract tech stack hints
grep -i "language\|framework\|stack\|technology" .founder-mode/PROJECT.md
grep -i "language\|framework\|stack\|technology" .founder-mode/ROADMAP.md
```
</domain_detection>

<generate_gray_areas>
Based on detected domains AND phase requirements, generate gray areas.

**Universal Gray Areas (always include):**
- Error handling approach
- Logging strategy
- Configuration management
- Testing expectations

**Domain-Specific Gray Areas:**

**Web Frontend:**
- Component library choice (custom vs library)
- State management approach
- Styling methodology (CSS-in-JS, Tailwind, etc.)
- Build tooling preferences
- Browser support requirements

**Web Backend:**
- Framework patterns (MVC, DDD, Clean Architecture)
- Database access patterns (ORM, raw SQL, query builder)
- Request validation approach
- Background job handling
- Caching strategy

**API Development:**
- API style (REST, GraphQL, RPC)
- Versioning strategy
- Authentication method
- Rate limiting approach
- Documentation format (OpenAPI, etc.)

**CLI Tool:**
- Argument parsing style
- Output formatting (JSON, human-readable, both)
- Configuration file format
- Interactive vs non-interactive mode
- Shell completion support

**Mobile App:**
- Navigation pattern
- Local storage approach
- Offline support requirements
- Push notification handling
- Deep linking strategy

**Data Layer:**
- Migration approach
- Indexing strategy
- Query optimization priorities
- Connection pooling
- Backup/recovery needs

**Machine Learning:**
- Model serving approach
- Batch vs real-time inference
- Feature store usage
- Experiment tracking
- Model versioning

**Plugin/Extension:**
- Extension point design
- Isolation requirements
- Versioning/compatibility
- Installation mechanism
- Configuration approach

**Authentication:**
- Session management
- Token refresh strategy
- Password requirements
- MFA approach
- Social auth providers

**Testing:**
- Test organization pattern
- Mock/stub approach
- Test data management
- Coverage thresholds
- E2E test scope

**Infrastructure:**
- Environment strategy
- Secret management
- Deployment frequency
- Rollback approach
- Monitoring/alerting scope

For each detected domain, select 3-5 most relevant gray areas based on phase requirements.
</generate_gray_areas>

---

### Step 4: Present Gray Areas

<present_gray_areas>
Display generated gray areas for selection:

```
Phase {N} Gray Areas
====================

Based on the phase requirements and project domain, these decisions could affect planning:

1. [TECH] Component library choice
   Claude might assume: Custom components from scratch
   Alternatives: shadcn/ui, Radix, Headless UI, Material UI

2. [ARCH] State management approach
   Claude might assume: Local component state
   Alternatives: Redux, Zustand, Jotai, Context API

3. [QUAL] Testing expectations
   Claude might assume: Basic happy-path tests
   Alternatives: Full coverage, integration focus, TDD

4. [OPS] Error handling approach
   Claude might assume: Try/catch with console.error
   Alternatives: Error boundaries, error reporting service, graceful degradation

...

Which areas need discussion before planning?
```

Use AskUserQuestion with multi-select:

```
AskUserQuestion:
  question: "Select areas to discuss (comma-separated numbers, or 'all'):"
  allow_free_text: true
  placeholder: "e.g., 1,3,4 or 'all' or 'none'"
```

Parse response:
- `all` - Discuss all areas
- `none` - Skip to Claude's Discretion
- `1,3,4` - Discuss specific areas
</present_gray_areas>

---

### Step 5: Deep-Dive Each Selected Area

<deep_dive_pattern>
For each selected area, ask 4 targeted questions.

**Question Pattern:**
1. Current state/prior art
2. Desired outcome/quality bar
3. Constraints/requirements
4. Trade-off preference

**Example: Component Library Choice**

Q1 (Current state):
```
AskUserQuestion:
  question: "Do you have an existing component library or design system?"
  options:
    - "Yes, using {specify below}"
    - "No, but prefer specific library"
    - "No, open to recommendations"
    - "Want custom components"
  allow_free_text: true
```

Q2 (Desired outcome):
```
AskUserQuestion:
  question: "What's your priority for component selection?"
  options:
    - "Accessibility first"
    - "Design flexibility"
    - "Development speed"
    - "Bundle size"
    - "Consistent look out of box"
```

Q3 (Constraints):
```
AskUserQuestion:
  question: "Any component library constraints?"
  allow_free_text: true
  placeholder: "e.g., must work with Tailwind, no jQuery dependencies, needs SSR support"
```

Q4 (Trade-off):
```
AskUserQuestion:
  question: "Component customization vs development speed?"
  options:
    - "Favor customization (more time, exact design)"
    - "Favor speed (use defaults, ship faster)"
    - "Balance (customize key components only)"
```

Store all responses for CONTEXT.md.
</deep_dive_pattern>

<deep_dive_templates>
**Error Handling:**
1. "How are errors currently handled in the codebase (if any)?"
2. "What should users see when errors occur?"
3. "Any error reporting requirements (Sentry, logging service)?"
4. "Silent recovery vs fail-fast preference?"

**Testing Expectations:**
1. "Current test coverage and approach?"
2. "Test coverage target for this phase?"
3. "Testing constraints (time, tooling)?"
4. "Unit tests vs integration tests priority?"

**State Management:**
1. "Current state management approach?"
2. "Complexity of state (simple, moderate, complex cross-component)?"
3. "Any existing patterns or libraries to match?"
4. "Performance vs simplicity trade-off?"

**API Style:**
1. "Existing API patterns in codebase?"
2. "Who consumes the API (internal, public, both)?"
3. "Versioning requirements?"
4. "REST vs GraphQL preference?"

**Authentication:**
1. "Existing auth system to integrate with?"
2. "Required auth methods (password, OAuth, MFA)?"
3. "Session duration and security requirements?"
4. "Password policy requirements?"

**Database Access:**
1. "Existing database patterns?"
2. "ORM vs raw SQL preference?"
3. "Performance requirements (read-heavy, write-heavy)?"
4. "Migration approach?"

**Styling Approach:**
1. "Current CSS approach in codebase?"
2. "Design system or style guide?"
3. "Responsive design requirements?"
4. "CSS-in-JS vs utility-first vs traditional?"

**Deployment:**
1. "Target deployment environment?"
2. "CI/CD requirements?"
3. "Rollback strategy needs?"
4. "Environment configuration approach?"
</deep_dive_templates>

---

### Step 6: Scope Guardrails

<scope_guardrails>
After deep-dive, confirm scope boundaries to prevent creep during planning.

```
Scope Check
===========

Based on our discussion, Phase {N} will:

DO:
- {inferred scope items from discussion}
- {inferred scope items from discussion}

NOT DO (explicit exclusions):
- {from out-of-scope or deferred}
- {from out-of-scope or deferred}
```

Use AskUserQuestion:

```
AskUserQuestion:
  question: "Any additional scope constraints for this phase?"
  options:
    - "Scope looks correct"
    - "Add exclusions (let me specify)"
    - "Reduce scope (let me specify)"
    - "Expand scope (let me specify)"
  allow_free_text: true
```

If user wants to modify scope:
- Add exclusions: Document in CONTEXT.md "Not in This Phase"
- Reduce scope: Note specific features to defer
- Expand scope: Warn about requirements drift, confirm addition

```
AskUserQuestion:
  question: "You're expanding phase scope. This may affect timeline. Confirm?"
  options:
    - "Yes, expand scope"
    - "No, keep original scope"
```
</scope_guardrails>

---

### Step 7: Write CONTEXT.md

<context_md_format>
Create `.founder-mode/plans/phase-{N}/CONTEXT.md`:

```markdown
# Phase {N} Context: {Phase Name}

**Discussed:** {date}
**Phase goal:** {goal from ROADMAP.md}
**Requirements:** {REQ-IDs}

## Decisions by Category

### {Category 1: e.g., Technology Choices}

**{Area}: {Decision}**
- Context: {Why this decision matters}
- Decision: {What user decided}
- Rationale: {User's reasoning from discussion}
- Constraints: {Any specific constraints mentioned}

### {Category 2: e.g., Architecture Patterns}

**{Area}: {Decision}**
- Context: {Why this decision matters}
- Decision: {What user decided}
- Rationale: {User's reasoning from discussion}
- Constraints: {Any specific constraints mentioned}

### {Category 3: e.g., Quality Standards}

**{Area}: {Decision}**
- Context: {Why this decision matters}
- Decision: {What user decided}
- Rationale: {User's reasoning from discussion}
- Constraints: {Any specific constraints mentioned}

## Claude's Discretion

The following areas were NOT discussed. Claude may make reasonable decisions during planning:

- {Area not selected}: Default to {sensible default}
- {Area not selected}: Default to {sensible default}

If any of these become significant, surface for discussion before proceeding.

## Scope Guardrails

### In Scope
- {explicit inclusions}

### Not in This Phase
- {explicit exclusions from discussion}
- {deferrals from scope check}

### Deferred Ideas

Ideas mentioned during discussion for future consideration:

- {idea}: {brief description} - Suggested phase: {N+X or "backlog"}

## For Downstream Consumers

### plan-phase
When creating PLAN.md for Phase {N}:
- Reference decisions in "Decisions by Category" section
- Respect "Not in This Phase" exclusions
- Use "Claude's Discretion" defaults only when not overridden by decisions
- Include deferred items in plan notes for tracking

### execute-plan
When executing plans:
- Validate implementation matches decisions
- Flag deviations from stated decisions
- If blocked by decision, surface for re-discussion

### verify-work
When verifying work:
- Check deliverables against scope guardrails
- Ensure deferred items weren't accidentally included
- Confirm decisions were followed

---
*Context gathered: {date}*
*Valid until: Phase {N} complete*
```
</context_md_format>

<write_context_md>
Create directory and write file:

```bash
mkdir -p .founder-mode/plans/phase-${N}
```

Write CONTEXT.md with gathered information.

Report:
```
Created: .founder-mode/plans/phase-{N}/CONTEXT.md
```
</write_context_md>

---

### Step 8: Commit and Next Steps

<commit_context>
Commit the context file:

```bash
git add .founder-mode/plans/phase-${N}/CONTEXT.md
git commit -m "Discuss Phase ${N}: capture decisions

Decisions documented:
- {summary of key decisions}

Ready for planning."
```
</commit_context>

<update_state>
Update STATE.md:

```markdown
Status: Ready to plan
Last activity: {date} - Phase {N} context gathered
```
</update_state>

<completion_message>
Display completion:

```
Phase {N} Discussion Complete
=============================

Context documented: .founder-mode/plans/phase-{N}/CONTEXT.md

Key decisions:
- {Category}: {Brief decision}
- {Category}: {Brief decision}
- {Category}: {Brief decision}

Claude's discretion: {count} areas
Deferred ideas: {count} items

Next step:
  /fm:plan-phase {N}
```
</completion_message>

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

Use: /fm:discuss-phase {valid_phase_number}
```
</error_phase_not_found>

<error_phase_complete>
If phase is already marked complete:
```
Phase {N} is already complete.

To re-discuss for iteration:
  /fm:discuss-phase {N} --refresh
```
</error_phase_complete>

---

## Examples

**Discuss current phase:**
```
/fm:discuss-phase
```

**Discuss specific phase:**
```
/fm:discuss-phase 3
```

**Re-discuss with existing context:**
```
/fm:discuss-phase 2 --refresh
```

---

## Success Criteria

- [ ] Phase number parsed correctly (from arg or STATE.md)
- [ ] Phase validated against ROADMAP.md
- [ ] Domain detected from project context
- [ ] Gray areas generated based on domain + phase
- [ ] Multi-select for area selection works
- [ ] 4 questions asked per selected area
- [ ] Scope guardrails confirmed
- [ ] CONTEXT.md written in correct format
- [ ] Downstream consumer sections documented
- [ ] STATE.md updated
- [ ] Git commit created
