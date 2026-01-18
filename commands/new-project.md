---
name: founder-mode:new-project
description: Initialize a new project with deep context gathering and planning artifacts
argument-hint: [--skip-research] [--brownfield]
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - Task
  - AskUserQuestion
---

# New Project

Initialize a founder-mode project from scratch. Creates PROJECT.md, REQUIREMENTS.md, ROADMAP.md, STATE.md, and config.json through deep context gathering.

## Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--skip-research` | flag | false | Skip research phase (use when domain is well-understood) |
| `--brownfield` | flag | false | Force brownfield mode for existing codebase |

## Execution Flow

This command runs through 9 phases sequentially, gathering context through structured questions and creating planning artifacts.

---

## Phase 1: Setup

Create the `.founder-mode/` directory structure.

<setup_action>
```bash
# Create directory structure
mkdir -p .founder-mode/logs
mkdir -p .founder-mode/plans
mkdir -p .founder-mode/todos/pending
mkdir -p .founder-mode/todos/done
```

Report:
```
Created .founder-mode/ directory structure.
```
</setup_action>

---

## Phase 2: Brownfield Detection

Detect if this is a greenfield (new) or brownfield (existing) project.

<brownfield_detection>
Check for existing code:

```bash
# Count meaningful files (exclude common non-code)
file_count=$(find . -type f \
  ! -path './.git/*' \
  ! -path './node_modules/*' \
  ! -path './.founder-mode/*' \
  ! -path './vendor/*' \
  ! -path './__pycache__/*' \
  ! -name '*.md' \
  ! -name '*.json' \
  ! -name '*.lock' \
  ! -name '.gitignore' \
  2>/dev/null | wc -l)

echo "Code files found: $file_count"
```

**Decision logic:**
- If `file_count > 5` OR `--brownfield` flag: Brownfield mode
- Otherwise: Greenfield mode
</brownfield_detection>

<brownfield_mode>
If brownfield detected:

1. Inform user:
```
Existing codebase detected ({file_count} files).

Starting brownfield initialization. This will:
1. Analyze existing code structure
2. Infer current capabilities as Validated requirements
3. Gather your goals for new development
```

2. Spawn codebase analysis agent:
```
Task(
  subagent_type: "general-purpose",
  prompt: """
Analyze this codebase and produce a summary:

1. **Tech Stack**: Languages, frameworks, build tools
2. **Architecture**: Key directories, patterns, entry points
3. **Current Capabilities**: What does this code do today?
4. **Code Quality**: Test coverage, documentation level
5. **Integration Points**: External services, APIs, databases

Output as structured markdown to .founder-mode/codebase-analysis.md
"""
)
```

3. Use analysis to inform later phases (requirements will include inferred Validated items)
</brownfield_mode>

<greenfield_mode>
If greenfield:

```
New project detected.

Starting greenfield initialization. This will:
1. Gather project vision and requirements
2. Research domain patterns (optional)
3. Create planning artifacts
4. Set up roadmap for execution
```
</greenfield_mode>

---

## Phase 3: Deep Questioning

Gather essential project context through structured questions.

<question_flow>
Questions are asked in sequence. Each question uses AskUserQuestion with appropriate options or free text.

### Q1: Project Vision

```
AskUserQuestion:
  question: "What are you building? Describe your project in 2-3 sentences."
  allow_free_text: true
```

Store response as `project_description`.

### Q2: Core Value

```
AskUserQuestion:
  question: "What's the ONE thing this project must do well? If everything else fails, what must work?"
  allow_free_text: true
```

Store response as `core_value`.

### Q3: Target Users

```
AskUserQuestion:
  question: "Who is this for? Describe your primary user."
  allow_free_text: true
```

Store response as `target_users`.

### Q4: Success Criteria

```
AskUserQuestion:
  question: "How will you know this project succeeded? What does 'done' look like for v1?"
  allow_free_text: true
```

Store response as `success_criteria`.

### Q5: Constraints

```
AskUserQuestion:
  question: "What constraints should I know about?"
  options:
    - "Tech stack requirements (specific languages/frameworks)"
    - "Timeline pressure (need to ship fast)"
    - "Integration requirements (existing systems)"
    - "Performance requirements (scale/speed)"
    - "Security requirements (compliance/auth)"
    - "Multiple constraints (let me specify)"
    - "No specific constraints"
```

If "Multiple constraints" selected, follow up with free text:
```
AskUserQuestion:
  question: "List your constraints, one per line:"
  allow_free_text: true
```

Store response as `constraints`.

### Q6: Prior Art

```
AskUserQuestion:
  question: "Is there existing work or inspiration for this project?"
  options:
    - "Similar product I'm improving on"
    - "Existing codebase I'm extending"
    - "Reference implementation to learn from"
    - "Starting fresh, no prior art"
```

If not "Starting fresh", follow up:
```
AskUserQuestion:
  question: "Describe the prior art or provide links:"
  allow_free_text: true
```

Store response as `prior_art`.

### Q7: Out of Scope

```
AskUserQuestion:
  question: "What should we explicitly NOT build for v1? List features to exclude."
  allow_free_text: true
  placeholder: "e.g., Mobile app, Admin dashboard, Multi-tenancy"
```

Store response as `out_of_scope`.
</question_flow>

<context_summary>
After all questions, display gathered context:

```
Project Context Summary
=======================

Vision: {project_description}

Core Value: {core_value}

Target Users: {target_users}

Success Criteria: {success_criteria}

Constraints:
{constraints}

Out of Scope:
{out_of_scope}

---

Does this capture your project accurately?
```

```
AskUserQuestion:
  question: "Is this context accurate?"
  options:
    - "Yes, proceed"
    - "Need to revise something"
```

If "Need to revise", ask which section and re-gather that question.
</context_summary>

---

## Phase 4: Write PROJECT.md

Create the initial PROJECT.md from gathered context.

<write_project_md>
Generate PROJECT.md using the template format:

```markdown
# {Project Name - derived from description or repo name}

## What This Is

{project_description}

## Core Value

{core_value}

## Requirements

### Validated

(None yet - ship to validate)

### Active

{To be populated in Phase 7 after requirements definition}

### Out of Scope

{out_of_scope - formatted as list with reasoning}

## Context

Target users: {target_users}

Success criteria: {success_criteria}

{prior_art if present}

## Constraints

{constraints - formatted as typed list}

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| - | - | - |

---
*Last updated: {date} after project initialization*
```

For brownfield projects, add to Context section:
```
### Codebase Analysis

See: .founder-mode/codebase-analysis.md

Current capabilities (from analysis):
{summary from codebase-analysis.md}
```
</write_project_md>

<commit_project_md>
```bash
git add .founder-mode/PROJECT.md
git commit -m "Initialize PROJECT.md

- Core value: {core_value_summary}
- Target: {target_users_summary}
- Constraints: {constraints_summary}"
```

Report:
```
Created and committed .founder-mode/PROJECT.md
```
</commit_project_md>

---

## Phase 5: Workflow Preferences

Gather preferences for execution and create config.json.

<workflow_questions>
### Q1: Execution Model

```
AskUserQuestion:
  question: "How do you want to execute plans?"
  options:
    - "Claude only (stay in this session)"
    - "Multiple models (Claude, Codex, Gemini)"
    - "Prefer parallel execution (multiple agents)"
    - "Sequential (one thing at a time)"
```

### Q2: Verification Level

```
AskUserQuestion:
  question: "How much verification do you want?"
  options:
    - "Comprehensive (verify after every plan)"
    - "Standard (verify after each phase)"
    - "Light (manual verification)"
```

### Q3: Auto-commit

```
AskUserQuestion:
  question: "Should changes be committed automatically after successful execution?"
  options:
    - "Yes, auto-commit with generated messages"
    - "No, I'll review and commit manually"
```

### Q4: Planning Depth

```
AskUserQuestion:
  question: "How detailed should planning be?"
  options:
    - "Quick (3-5 phases, minimal research)"
    - "Standard (5-8 phases, targeted research)"
    - "Comprehensive (8-12 phases, thorough research)"
```
</workflow_questions>

<write_config_json>
Create `.founder-mode/config.json`:

```json
{
  "project": {
    "name": "{project_name}"
  },
  "directories": {
    "worktrees": ".worktrees/",
    "logs": ".founder-mode/logs/",
    "prompts": "./prompts/",
    "planning": ".founder-mode/"
  },
  "execution": {
    "default_model": "{based on Q1}",
    "parallel_limit": {3 if parallel, 1 if sequential},
    "auto_commit": {true/false from Q3},
    "verify_after_execute": {true if Comprehensive/Standard}
  },
  "planning": {
    "depth": "{quick/standard/comprehensive from Q4}",
    "research_enabled": true,
    "max_plans_per_phase": 3
  },
  "verification": {
    "pre_execution": true,
    "post_execution": {based on Q2},
    "max_retry_attempts": 2
  },
  "display": {
    "verbose": false,
    "progress_bar": true,
    "timestamps": true
  }
}
```
</write_config_json>

<commit_config>
```bash
git add .founder-mode/config.json
git commit -m "Add workflow configuration

- Execution: {default_model}
- Verification: {verification_level}
- Planning: {depth}"
```
</commit_config>

---

## Phase 6: Research Decision

Determine if research is needed before requirements.

<research_decision>
```
AskUserQuestion:
  question: "Should we research domain patterns before defining requirements?"
  options:
    - "Yes, research first (recommended for unfamiliar domains)"
    - "No, I know what I need (skip research)"
```

If `--skip-research` flag was set, skip this question and proceed to Phase 7.
</research_decision>

<spawn_research_agents>
If research selected, spawn 4 parallel Task agents:

**Agent 1: Best Practices**
```
Task(
  subagent_type: "explore",
  prompt: """
Research best practices for: {project_description}

Focus on:
- Established patterns in this domain
- Common pitfalls to avoid
- Architecture recommendations
- Testing strategies

Output findings to: .founder-mode/research/best-practices.md
"""
)
```

**Agent 2: Similar Projects**
```
Task(
  subagent_type: "explore",
  prompt: """
Find and analyze similar open source projects for: {project_description}

For each relevant project:
- What patterns do they use?
- What features do they prioritize?
- What can we learn from their approach?

Output findings to: .founder-mode/research/similar-projects.md
"""
)
```

**Agent 3: Anti-Patterns**
```
Task(
  subagent_type: "explore",
  prompt: """
Research anti-patterns and common mistakes for: {project_description}

Focus on:
- Features that seem good but cause problems
- Over-engineering tendencies in this space
- Performance pitfalls
- Security concerns

Output findings to: .founder-mode/research/anti-patterns.md

Format anti-patterns as warnings for Out of Scope consideration.
"""
)
```

**Agent 4: Tech Stack Research**
```
Task(
  subagent_type: "explore",
  prompt: """
Research technology choices for: {project_description}

Given constraints: {constraints}

Recommend:
- Language/framework if not specified
- Key libraries and tools
- Development setup
- Deployment approach

Output findings to: .founder-mode/research/tech-stack.md
"""
)
```

Wait for all 4 agents to complete.
</spawn_research_agents>

<research_synthesis>
After research completes, synthesize findings:

```
Research Complete
=================

Best Practices:
{summary from best-practices.md}

Similar Projects:
{summary from similar-projects.md}

Anti-Patterns (consider for Out of Scope):
{warnings from anti-patterns.md}

Tech Stack Recommendations:
{summary from tech-stack.md}

---

Review complete research: .founder-mode/research/
```

```
AskUserQuestion:
  question: "Any adjustments based on research?"
  options:
    - "No, proceed to requirements"
    - "Add to Out of Scope based on anti-patterns"
    - "Adjust constraints based on tech research"
    - "Let me review research first"
```

If adjustments needed, update PROJECT.md accordingly.
</research_synthesis>

<commit_research>
```bash
git add .founder-mode/research/
git commit -m "Add domain research

- Best practices documented
- Similar projects analyzed
- Anti-patterns identified
- Tech stack recommendations"
```
</commit_research>

---

## Phase 7: Define Requirements

Create structured requirements from context.

<requirements_gathering>
Present the gathered context and ask user to confirm requirements:

```
Based on your project context, here are proposed requirements:

{Generate requirements from:
- project_description
- success_criteria
- prior_art analysis (if present)
- brownfield inferred capabilities (if present)
- research findings (if present)}
```

For each requirement category, confirm:

```
AskUserQuestion:
  question: "Review {category} requirements. Any changes?"
  options:
    - "Looks good"
    - "Add more requirements"
    - "Remove some requirements"
    - "Move to v2/Out of Scope"
```
</requirements_gathering>

<write_requirements_md>
Create `.founder-mode/REQUIREMENTS.md` using REQ-ID format:

```markdown
# Requirements: {Project Name}

**Defined:** {date}
**Core Value:** {core_value}

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### {Category 1}

- [ ] **{CAT}-01**: {Requirement description}
- [ ] **{CAT}-02**: {Requirement description}

### {Category 2}

- [ ] **{CAT}-01**: {Requirement description}
- [ ] **{CAT}-02**: {Requirement description}

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### {Category}

- **{CAT}-01**: {Requirement description}

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| {feature} | {reason from out_of_scope or anti-patterns} |

## Traceability

(To be populated during roadmap creation)

| Requirement | Phase | Status |
|-------------|-------|--------|
| - | - | - |

**Coverage:**
- v1 requirements: {X} total
- Mapped to phases: 0
- Unmapped: {X}

---
*Requirements defined: {date}*
*Last updated: {date} after initialization*
```

Requirements use category-based IDs:
- AUTH-01, AUTH-02 for authentication
- CONT-01, CONT-02 for content
- SOCL-01, SOCL-02 for social features
- (Use domain-appropriate categories)
</write_requirements_md>

<commit_requirements>
```bash
git add .founder-mode/REQUIREMENTS.md
git commit -m "Define v1 requirements

Categories: {list categories}
Total requirements: {count}
Out of scope: {count}"
```
</commit_requirements>

<update_project_active>
Update PROJECT.md Active requirements section with REQ-IDs:

```markdown
### Active

- [ ] {CAT}-01: {brief description}
- [ ] {CAT}-02: {brief description}
...
```

Commit the update:
```bash
git add .founder-mode/PROJECT.md
git commit -m "Link PROJECT.md to requirements"
```
</update_project_active>

---

## Phase 8: Create Roadmap

Generate phased roadmap from requirements.

<roadmap_generation>
Based on requirements and planning depth (quick/standard/comprehensive), generate roadmap:

```
AskUserQuestion:
  question: "How should phases be organized?"
  options:
    - "By feature area (Auth -> Content -> Social)"
    - "By complexity (Simple -> Complex)"
    - "By dependency (Foundation -> Features -> Polish)"
    - "Let me specify custom order"
```

Generate phase structure based on selection and requirements.
</roadmap_generation>

<write_roadmap_md>
Create `.founder-mode/ROADMAP.md`:

```markdown
# Roadmap: {Project Name}

## Overview

{One paragraph describing the journey from requirements to shipped product}

## Domain Expertise

{From research or "General development patterns"}

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: {Name}** - {One-line description}
- [ ] **Phase 2: {Name}** - {One-line description}
- [ ] **Phase 3: {Name}** - {One-line description}
{... based on depth setting}

## Phase Details

### Phase 1: {Name}
**Goal**: {What this phase delivers}
**Depends on**: Nothing (first phase)
**Requirements**: [{REQ-IDs covered by this phase}]
**Research**: {Likely / Unlikely} ({why if likely})
**Plans**: TBD

Key deliverables:
- {Deliverable 1}
- {Deliverable 2}

### Phase 2: {Name}
**Goal**: {What this phase delivers}
**Depends on**: Phase 1
**Requirements**: [{REQ-IDs covered by this phase}]
**Research**: {Likely / Unlikely}
**Plans**: TBD

Key deliverables:
- {Deliverable 1}
- {Deliverable 2}

{... continue for all phases}

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> ...

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. {Name} | 0/TBD | Not started | - |
| 2. {Name} | 0/TBD | Not started | - |
{... for all phases}
```
</write_roadmap_md>

<roadmap_approval>
Present roadmap summary:

```
Proposed Roadmap
================

{phase count} phases covering {requirement count} requirements

Phase 1: {name} - {requirements covered}
Phase 2: {name} - {requirements covered}
Phase 3: {name} - {requirements covered}
...

Estimated scope: {depth} ({quick: 1-2 weeks, standard: 2-4 weeks, comprehensive: 4-8 weeks})
```

```
AskUserQuestion:
  question: "Approve this roadmap?"
  options:
    - "Approve and continue"
    - "Add a phase"
    - "Remove a phase"
    - "Reorganize phases"
    - "Start over with different approach"
```

If not approved, iterate on roadmap until approved.
</roadmap_approval>

<update_traceability>
After roadmap approved, update REQUIREMENTS.md traceability:

```markdown
## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| {CAT}-01 | Phase 1 | Pending |
| {CAT}-02 | Phase 1 | Pending |
| {CAT}-03 | Phase 2 | Pending |
...

**Coverage:**
- v1 requirements: {X} total
- Mapped to phases: {Y}
- Unmapped: {Z}
```
</update_traceability>

<commit_roadmap>
```bash
git add .founder-mode/ROADMAP.md .founder-mode/REQUIREMENTS.md
git commit -m "Create roadmap with {N} phases

Covers {M} requirements across {N} phases
Planning depth: {depth}
Ready for execution"
```
</commit_roadmap>

---

## Phase 9: Done

Create STATE.md and report completion.

<create_state_md>
Create `.founder-mode/STATE.md`:

```markdown
# Project State

## Project Reference

See: .founder-mode/PROJECT.md (updated {date})

**Core value:** {core_value}
**Current focus:** Phase 1 - {phase 1 name}

## Current Position

Phase: 1 of {total_phases} ({phase 1 name})
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: {date} - Project initialized

Progress: [----------] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Init]: {key initialization decisions}

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: {timestamp}
Stopped at: Project initialization complete
Resume file: None
```
</create_state_md>

<commit_state>
```bash
git add .founder-mode/STATE.md
git commit -m "Initialize project state

Ready to begin Phase 1: {phase 1 name}
Total phases: {N}
Requirements: {M}"
```
</commit_state>

<completion_message>
Display completion:

```
Project Initialization Complete
===============================

Created:
- .founder-mode/PROJECT.md  - Project definition
- .founder-mode/REQUIREMENTS.md - Checkable requirements
- .founder-mode/ROADMAP.md - Phased execution plan
- .founder-mode/STATE.md - Session state tracking
- .founder-mode/config.json - Workflow preferences
{if research}
- .founder-mode/research/ - Domain research
{/if}

Summary:
- Core value: {core_value}
- v1 requirements: {count}
- Phases: {count}
- Planning depth: {depth}

Next step:
  /founder-mode:plan-phase 1

Or check progress:
  /founder-mode:progress
```
</completion_message>

---

## Error Handling

<error_directory_exists>
If `.founder-mode/` already exists:

```
AskUserQuestion:
  question: ".founder-mode/ already exists. How to proceed?"
  options:
    - "Archive existing and start fresh"
    - "Resume existing project"
    - "Cancel"
```

If "Archive":
```bash
mv .founder-mode .founder-mode.bak.{timestamp}
```

If "Resume":
```
Use /founder-mode:progress to check current state.
```
</error_directory_exists>

<error_commit_failed>
If git commit fails (no git repo, etc.):

```
Git commit failed. Continuing without version control.

Artifacts created but not committed:
- .founder-mode/PROJECT.md
- .founder-mode/REQUIREMENTS.md
- etc.

To enable version control:
  git init
  git add .founder-mode/
  git commit -m "Initialize founder-mode"
```
</error_commit_failed>

<error_task_failed>
If a Task agent fails during research:

```
Research agent failed: {agent_name}

Options:
1. Retry this research
2. Skip this research area
3. Continue with partial research
```

Use AskUserQuestion to let user decide.
</error_task_failed>

## Examples

**Initialize new project:**
```
/founder-mode:new-project
```

**Skip research (known domain):**
```
/founder-mode:new-project --skip-research
```

**Force brownfield mode:**
```
/founder-mode:new-project --brownfield
```
