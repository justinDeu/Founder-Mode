# REQUIREMENTS.md Template

Template for `.founder-mode/REQUIREMENTS.md` - checkable requirements that define "done."

## Template

```markdown
# Requirements: [Project Name]

**Defined:** [date]
**Core Value:** [from PROJECT.md]

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### [Category 1]

- [ ] **[CAT]-01**: [Requirement description]
- [ ] **[CAT]-02**: [Requirement description]
- [ ] **[CAT]-03**: [Requirement description]

### [Category 2]

- [ ] **[CAT]-01**: [Requirement description]
- [ ] **[CAT]-02**: [Requirement description]

### [Category 3]

- [ ] **[CAT]-01**: [Requirement description]
- [ ] **[CAT]-02**: [Requirement description]

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### [Category]

- **[CAT]-01**: [Requirement description]
- **[CAT]-02**: [Requirement description]

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| [Feature] | [Why excluded] |
| [Feature] | [Why excluded] |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| [CAT]-01 | Phase 1 | Pending |
| [CAT]-02 | Phase 1 | Pending |
| [CAT]-03 | Phase 2 | Pending |

**Coverage:**
- v1 requirements: [X] total
- Mapped to phases: [Y]
- Unmapped: [Z]

---
*Requirements defined: [date]*
*Last updated: [date] after [trigger]*
```

## REQ-ID Format

Requirements use category-based IDs:

```
[CATEGORY]-[NUMBER]
```

**Format rules:**
- Category: 2-4 uppercase letters
- Number: Two digits, zero-padded (01, 02, 03...)
- Separator: Hyphen

**Examples:**
- AUTH-01: User can sign up with email
- AUTH-02: User can reset password
- CONT-01: User can create posts
- SOCL-01: User can follow others

### Common Categories

| Category | Full Name | Description |
|----------|-----------|-------------|
| AUTH | Authentication | Login, signup, sessions |
| PROF | Profiles | User profiles, settings |
| CONT | Content | Creating, editing content |
| SOCL | Social | Following, likes, comments |
| NOTF | Notifications | Alerts, emails |
| MODR | Moderation | Reporting, admin actions |
| SRCH | Search | Finding content/users |
| ANLZ | Analytics | Metrics, dashboards |
| INTG | Integration | External services |
| PERF | Performance | Speed, optimization |

## Guidelines

### Requirement Format

- ID: `[CATEGORY]-[NUMBER]`
- Description: User-centric, testable, atomic
- Checkbox: Only for v1 requirements (v2 are not yet actionable)

Good requirement: "User can reset password via email link"
Bad requirement: "Password reset functionality"

### v1 vs v2

- **v1**: Committed scope, will be in roadmap phases
- **v2**: Acknowledged but deferred, not in current roadmap
- Moving v2 to v1 requires roadmap update

### Out of Scope

- Explicit exclusions with reasoning
- Prevents "why didn't you include X?" later
- Anti-features from research belong here with warnings

### Traceability

- Empty initially, populated during roadmap creation
- Each requirement maps to exactly one phase
- Unmapped requirements = roadmap gap

### Status Values

| Status | Meaning |
|--------|---------|
| Pending | Not started |
| In Progress | Phase is active |
| Complete | Requirement verified |
| Blocked | Waiting on external factor |

## Evolution

**After each phase completes:**

1. Mark covered requirements as Complete
2. Update traceability status
3. Note any requirements that changed scope

**After roadmap updates:**

1. Verify all v1 requirements still mapped
2. Add new requirements if scope expanded
3. Move requirements to v2/out of scope if descoped

**Requirement completion criteria:**

- Feature is implemented
- Feature is verified (tests pass, manual check done)
- Feature is committed

## Example

```markdown
# Requirements: TaskManager

**Defined:** 2026-01-18
**Core Value:** Users can track and complete tasks efficiently

## v1 Requirements

### Tasks

- [ ] **TASK-01**: User can create a task with title and description
- [ ] **TASK-02**: User can mark task as complete
- [ ] **TASK-03**: User can delete a task
- [ ] **TASK-04**: User can set task due date

### Organization

- [ ] **ORG-01**: User can create projects
- [ ] **ORG-02**: User can assign tasks to projects
- [ ] **ORG-03**: User can filter tasks by project

## v2 Requirements

### Collaboration

- **COLLAB-01**: User can share projects with others
- **COLLAB-02**: User can assign tasks to team members

## Out of Scope

| Feature | Reason |
|---------|--------|
| Mobile app | Web-first for v1 |
| Calendar sync | Complex integration, defer |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| TASK-01 | Phase 1 | Pending |
| TASK-02 | Phase 1 | Pending |
| TASK-03 | Phase 1 | Pending |
| TASK-04 | Phase 1 | Pending |
| ORG-01 | Phase 2 | Pending |
| ORG-02 | Phase 2 | Pending |
| ORG-03 | Phase 2 | Pending |

**Coverage:**
- v1 requirements: 7 total
- Mapped to phases: 7
- Unmapped: 0
```
