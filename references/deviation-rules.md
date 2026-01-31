# Deviation Rules

When executing prompts, unexpected work will be discovered. These rules define when to fix automatically vs when to checkpoint for user input.

## The Four Rules

### Rule 1: Auto-fix Bugs

**Trigger:** Code doesn't work as intended

**Action:** Fix immediately, document in output

**Examples:**
- Logic errors (inverted condition, off-by-one)
- Type errors, null references
- Security vulnerabilities (SQL injection, XSS)
- Broken validation
- Incorrect API calls
- Race conditions, deadlocks
- Memory leaks, resource leaks

**Why auto-fix:** Bugs are unambiguously wrong. Fixing them doesn't change design intent.

---

### Rule 2: Auto-add Critical Functionality

**Trigger:** Missing functionality required for correctness, security, or basic operation

**Action:** Add immediately, document in output

**Examples:**
- Input validation for user-provided data
- Authentication checks on protected routes
- Authorization checks (users accessing others' data)
- Error handling for external API calls
- Null/undefined guards
- Required environment variable checks
- CSRF protection, CORS configuration
- Rate limiting on public APIs

**Why auto-add:** These are security/stability requirements, not design decisions. Code is incomplete without them.

---

### Rule 3: Auto-fix Blocking Issues

**Trigger:** Execution cannot continue without the fix

**Action:** Fix immediately, document in output

**Examples:**
- Missing dependencies (import errors, package not installed)
- Broken imports (wrong path, file moved)
- Config errors (missing required fields)
- Build failures (webpack, tsconfig, etc.)
- Type mismatches blocking compilation
- Circular dependencies
- Missing environment variables (app won't start)

**Why auto-fix:** The prompt cannot complete without resolving blockers.

---

### Rule 4: Checkpoint for Architectural Decisions

**Trigger:** Change affects system design or scope

**Action:** STOP and return to user with options

**Examples:**
- Adding new database tables (not just columns)
- Major refactors (extracting services, changing patterns)
- Framework/library changes (React to Vue, REST to GraphQL)
- API contract changes (breaking changes to endpoints)
- New external service integrations
- Changing authentication approach (sessions to JWT)
- Adding new infrastructure (message queue, cache layer)
- New deployment environments

**Why checkpoint:** Design decisions need human input. The executor shouldn't assume intent.

---

## Decision Flow

```
Discovered unexpected work
         |
         v
    Is it a bug?
    +----+----+
   Yes       No
    |         |
    v         v
 Rule 1    Is it critical
 Auto-fix  functionality?
           +----+----+
          Yes       No
           |         |
           v         v
        Rule 2    Is it blocking
        Auto-add  execution?
                  +----+----+
                 Yes       No
                  |         |
                  v         v
               Rule 3    Does it affect
               Auto-fix  architecture?
                         +----+----+
                        Yes       No
                         |         |
                         v         v
                      Rule 4    Probably
                      Checkpoint safe to
                                 auto-fix
```

**Rule Priority:** When multiple rules could apply:
1. If Rule 4 applies, STOP and checkpoint (architectural decision)
2. If Rules 1-3 apply, fix automatically and document
3. If genuinely unsure, apply Rule 4 (checkpoint for user decision)

---

## Documenting Deviations

All auto-fixes must be documented in the output. Use this format:

```markdown
## Deviations

### Auto-fixed (Rule 1: Bug)
- Fixed off-by-one error in pagination logic
- Corrected inverted condition in auth check

### Auto-added (Rule 2: Critical)
- Added input validation for email field
- Added rate limiting to /api/login endpoint

### Auto-fixed (Rule 3: Blocker)
- Added missing `lodash` dependency
- Fixed import path after file rename
```

If no deviations occurred: "None - executed exactly as planned."

---

## Examples by Domain

### Backend/API

| Situation | Rule | Action |
|-----------|------|--------|
| Missing auth middleware | Rule 2 | Auto-add |
| N+1 query detected | Rule 1 | Auto-fix |
| New database migration needed | Rule 4 | Checkpoint |
| Missing error handler | Rule 2 | Auto-add |
| SQL injection vulnerability | Rule 1 | Auto-fix |
| API returns wrong status code | Rule 1 | Auto-fix |
| Need to add caching layer | Rule 4 | Checkpoint |
| Missing request validation | Rule 2 | Auto-add |

### Frontend

| Situation | Rule | Action |
|-----------|------|--------|
| Missing loading state | Rule 2 | Auto-add |
| Component crashes on null | Rule 1 | Auto-fix |
| Needs new global state | Rule 4 | Checkpoint |
| Missing form validation | Rule 2 | Auto-add |
| XSS vulnerability in render | Rule 1 | Auto-fix |
| Missing error boundary | Rule 2 | Auto-add |
| Major component restructure | Rule 4 | Checkpoint |
| Accessibility issue (missing ARIA) | Rule 2 | Auto-add |

### Infrastructure

| Situation | Rule | Action |
|-----------|------|--------|
| Missing env var check | Rule 2 | Auto-add |
| Dockerfile has security issue | Rule 1 | Auto-fix |
| Needs new cloud service | Rule 4 | Checkpoint |
| Build script fails | Rule 3 | Auto-fix |
| Missing health check endpoint | Rule 2 | Auto-add |
| Secrets exposed in logs | Rule 1 | Auto-fix |
| Need to change deployment strategy | Rule 4 | Checkpoint |
| Missing dependency in package.json | Rule 3 | Auto-fix |

---

## Edge Cases

**"This validation is missing"** - Rule 2 (critical for security)

**"This crashes on null"** - Rule 1 (bug)

**"Need to add table"** - Rule 4 (architectural)

**"Need to add column"** - Rule 1 or 2 (depends on whether fixing bug or adding critical field)

**When in doubt:** Ask yourself "Does this affect correctness, security, or ability to complete task?"
- YES: Rules 1-3 (fix automatically)
- MAYBE: Rule 4 (checkpoint for user decision)
