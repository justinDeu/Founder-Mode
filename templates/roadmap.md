# ROADMAP.md Template

Template for `.founder-mode/ROADMAP.md` - the phase structure document.

## Template

```markdown
# Roadmap: [Project Name]

## Overview

[One paragraph describing the journey from start to finish]

## Domain Expertise

[Relevant domain knowledge for execution, or "None" if general development]

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: [Name]** - [One-line description]
- [ ] **Phase 2: [Name]** - [One-line description]
- [ ] **Phase 3: [Name]** - [One-line description]
- [ ] **Phase 4: [Name]** - [One-line description]

## Phase Details

### Phase 1: [Name]
**Goal**: [What this phase delivers]
**Depends on**: Nothing (first phase)
**Requirements**: [REQ-01, REQ-02, REQ-03]
**Research**: [Likely / Unlikely] ([why if likely])
**Plans**: TBD

Key deliverables:
- [Deliverable 1]
- [Deliverable 2]
- [Deliverable 3]

### Phase 2: [Name]
**Goal**: [What this phase delivers]
**Depends on**: Phase 1
**Requirements**: [REQ-04, REQ-05]
**Research**: [Likely / Unlikely] ([why])
**Plans**: TBD

Key deliverables:
- [Deliverable 1]
- [Deliverable 2]

### Phase 2.1: Critical Fix (INSERTED)
**Goal**: [Urgent work inserted between phases]
**Depends on**: Phase 2
**Plans**: 1 plan

Key deliverables:
- [What the fix achieves]

### Phase 3: [Name]
**Goal**: [What this phase delivers]
**Depends on**: Phase 2
**Requirements**: [REQ-06, REQ-07, REQ-08]
**Research**: [Likely / Unlikely] ([why])
**Plans**: TBD

Key deliverables:
- [Deliverable 1]
- [Deliverable 2]
- [Deliverable 3]

### Phase 4: [Name]
**Goal**: [What this phase delivers]
**Depends on**: Phase 3
**Requirements**: [REQ-09, REQ-10]
**Research**: [Likely / Unlikely] ([why])
**Plans**: TBD

Key deliverables:
- [Deliverable 1]
- [Deliverable 2]

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 2.1 -> 2.2 -> 3 -> 3.1 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. [Name] | 0/TBD | Not started | - |
| 2. [Name] | 0/TBD | Not started | - |
| 3. [Name] | 0/TBD | Not started | - |
| 4. [Name] | 0/TBD | Not started | - |
```

## Guidelines

### Initial Planning

- Phase count depends on project scope (3-5 for quick, 5-8 standard, 8-12 comprehensive)
- Each phase delivers something coherent
- Phases can have 1+ plans (split if >3 tasks or multiple subsystems)
- Plans use naming: `{phase}-{plan}-PLAN.md` (e.g., `01-02-PLAN.md`)
- No time estimates (this isn't enterprise PM)
- Progress table updated by execute workflow
- Plan count can be "TBD" initially, refined during planning

### Phase Structure

- **Goal**: What this phase delivers (user-facing outcome)
- **Depends on**: Previous phase or "Nothing" for first phase
- **Requirements**: REQ-IDs from REQUIREMENTS.md
- **Research**: Whether domain research is needed before planning
- **Plans**: Number of execution plans or "TBD"
- **Key deliverables**: Concrete artifacts/features

### Status Values

- `Not started` - Haven't begun
- `In progress` - Currently working
- `Complete` - Done (add completion date)
- `Deferred` - Pushed to later (with reason)

### Inserted Phases

Decimal phases (2.1, 2.2) handle urgent work inserted between planned phases:

- Marked with "(INSERTED)" in title
- Execute in numeric order (2 -> 2.1 -> 2.2 -> 3)
- Keep original phases numbered (don't renumber everything)
- Created via insert-phase command

### After Milestones Ship

- Collapse completed milestones in `<details>` tags
- Add new milestone sections for upcoming work
- Keep continuous phase numbering (never restart at 01)

## Milestone-Grouped Roadmap

After completing first milestone, reorganize with milestone groupings:

```markdown
# Roadmap: [Project Name]

## Milestones

- [x] **v1.0 MVP** - Phases 1-4 (shipped YYYY-MM-DD)
- [ ] **v1.1 [Name]** - Phases 5-6 (in progress)
- [ ] **v2.0 [Name]** - Phases 7-10 (planned)

## Phases

<details>
<summary>v1.0 MVP (Phases 1-4) - SHIPPED YYYY-MM-DD</summary>

### Phase 1: [Name]
**Goal**: [What this phase delivers]
**Plans**: 3 plans

Plans:
- [x] 01-01: [Brief description]
- [x] 01-02: [Brief description]
- [x] 01-03: [Brief description]

[... remaining v1.0 phases ...]

</details>

### v1.1 [Name] (In Progress)

**Milestone Goal:** [What v1.1 delivers]

#### Phase 5: [Name]
**Goal**: [What this phase delivers]
**Depends on**: Phase 4
**Plans**: 2 plans

Plans:
- [ ] 05-01: [Brief description]
- [ ] 05-02: [Brief description]

[... remaining v1.1 phases ...]
```
