# Generate Phase Completion Prompts

## Objective

Read through founder-mode's `.planning/` directory to understand the project state, then create a master prompt and suite of sub-prompts that will complete all outstanding work (Phases 3, 4, and 5).

## Context

founder-mode is a Claude Code plugin that unifies prompt execution (from daplug) with project management (from GSD). Phases 1-2 are complete. Phases 3-5 remain.

## Instructions

### Step 1: Load Project Context

Read and understand the full project state:

```
.planning/PROJECT.md      - Requirements, constraints, key decisions
.planning/ROADMAP.md      - Phase definitions and deliverables
.planning/STATE.md        - Current position and accumulated context
```

Also read completed phase work to understand established patterns:

```
.planning/phases/01-foundation/   - Phase 1 plans and summaries
.planning/phases/02-prompt-workflow/  - Phase 2 plans and summaries
```

Read the existing command implementations to understand the skill file format:

```
commands/create-prompt.md
commands/run-prompt.md
```

### Step 2: Analyze Outstanding Work

From ROADMAP.md, extract the remaining deliverables for:

**Phase 3: Project Management**
- /new-project (unified flow)
- /discuss-phase (user vision capture)
- /plan-phase (with validation loop)
- /execute-phase (wave-based parallel)
- State management with REQ-IDs
- Verification layer (pre-execution + post-execution)

**Phase 4: External Integrations**
- GitHub issue fetching
- Jira ticket fetching
- Issue push to remotes
- /fix-gh-issue workflow

**Phase 5: Parallel Workflows**
- Multi-issue parallel execution
- Sprint execution without /clear loops
- Progress aggregation

### Step 3: Study GSD Patterns

Read the GSD plugin at `../get-shit-done/` to understand patterns founder-mode should adopt:

```
../get-shit-done/agents/gsd-planner.md        - Planning agent architecture
../get-shit-done/agents/gsd-plan-checker.md   - Plan validation dimensions
../get-shit-done/agents/gsd-verifier.md       - Goal-backward verification
../get-shit-done/agents/gsd-executor.md       - Execution patterns
../get-shit-done/commands/gsd/new-project.md  - Unified project flow
../get-shit-done/commands/gsd/discuss-phase.md - Discussion patterns
../get-shit-done/commands/gsd/plan-phase.md   - Planning workflow
../get-shit-done/commands/gsd/execute-phase.md - Execution orchestration
```

### Step 4: Create Prompt Structure

Create the following files in `prompts/phase-completion/`:

#### Master Orchestrator Prompt
`prompts/phase-completion/000-orchestrator.md`

This prompt:
- Coordinates execution of all sub-prompts
- Tracks completion state
- Handles dependencies between prompts
- Provides rollback instructions if something fails

#### Phase 3 Sub-Prompts

`prompts/phase-completion/003-01-state-management.md`

**Purpose:** Establish the directory structure and state management foundation that all other Phase 3 commands depend on.

**Deliverables:**
- `.founder-mode/` directory structure with subdirectories:
  - `phases/` - Phase-specific plans, summaries, context files
  - `research/` - Domain research outputs
  - `todos/pending/` and `todos/done/` - Todo management
- `PROJECT.md` template with sections:
  - Vision and core value statement
  - Requirements (Validated, Active, Out of Scope)
  - Context (existing tools, frustrations, goals)
  - Constraints (platform, architecture, compatibility)
  - Key Decisions table (Decision, Rationale, Outcome)
- `ROADMAP.md` template with:
  - Overview section
  - Phase list with checkboxes
  - Phase Details (Goal, Depends on, Research topics, Plans)
  - Progress table (Phase, Plans Complete, Status, Completed date)
- `STATE.md` template with:
  - Project reference pointer
  - Current position (Phase X of Y, Plan X of Y, Status)
  - Progress bar visualization
  - Performance metrics (velocity, by-phase breakdown, recent trend)
  - Accumulated context (decisions, deferred issues, blockers)
  - Session continuity (last session, stopped at, resume file)
- `REQUIREMENTS.md` template with:
  - REQ-ID format (e.g., REQ-001, REQ-002)
  - Requirement text, priority (v1/v2/out-of-scope), status (pending/in-progress/complete)
  - Phase mapping (which phase addresses this requirement)
  - 100% coverage validation logic
- `config.json` schema:
  - `workflow_mode`: "interactive" | "yolo"
  - `worktree_dir`: path for worktree creation
  - `logs_dir`: path for execution logs
  - `prompts_dir`: path for prompt files
  - `parallel`: true | false
  - `max_plan_tasks`: number (default 3)
- Helper utilities for:
  - Reading/writing STATE.md atomically
  - Updating progress percentages
  - Managing REQ-ID assignment and status updates

---

`prompts/phase-completion/003-02-new-project.md`

**Purpose:** Implement the unified `/fm:new-project` command that initializes a project from scratch with deep context gathering.

**User Flow:**
1. User runs `/fm:new-project`
2. Command asks 4-6 essential questions (vision, core priority, boundaries, constraints)
3. Command offers research path (recommended) or fast path (skip research)
4. If research: spawn parallel research agents to investigate stack, features, architecture, pitfalls
5. Extract requirements from conversation + research into REQUIREMENTS.md with REQ-IDs
6. Generate ROADMAP.md with phases mapped to requirements (100% coverage validation)
7. Initialize STATE.md and config.json
8. Commit all artifacts

**Questioning Flow:**
- "What are you building?" (vision)
- "What's the single most important thing it must do?" (core priority)
- "What's explicitly out of scope?" (boundaries)
- "Any technical constraints?" (platform, language, existing code)
- Use AskUserQuestion tool for structured choices where appropriate
- Freeform for open-ended questions

**Research Integration:**
- Spawn up to 4 parallel Explore agents:
  - Stack researcher (languages, frameworks, dependencies)
  - Feature researcher (similar products, standard features)
  - Architecture researcher (patterns, data flow, common structures)
  - Pitfall researcher (common mistakes, gotchas, security concerns)
- Synthesize research into `.founder-mode/research/SUMMARY.md`
- Research informs requirements extraction and roadmap phases

**Requirements Extraction:**
- Parse conversation for explicit requirements
- Infer implicit requirements from vision/priorities
- Categorize: v1 (must have), v2 (nice to have), out-of-scope
- Assign REQ-IDs (REQ-001, REQ-002, etc.)
- Present to user for confirmation before committing

**Roadmap Generation:**
- Create 3-7 phases based on requirements complexity
- Each phase maps to specific REQ-IDs
- Validate 100% of v1 requirements are covered
- Include dependencies between phases
- Estimate research likelihood per phase

**Files Created:**
- `.founder-mode/PROJECT.md`
- `.founder-mode/REQUIREMENTS.md`
- `.founder-mode/ROADMAP.md`
- `.founder-mode/STATE.md`
- `.founder-mode/config.json`
- `.founder-mode/research/SUMMARY.md` (if research path taken)

---

`prompts/phase-completion/003-03-discuss-phase.md`

**Purpose:** Implement `/fm:discuss-phase [N]` command that captures user vision and decisions before planning begins.

**Why This Exists:**
- Prevents Claude from making assumptions about UI, UX, behavior
- Surfaces gray areas that need user input
- Creates CONTEXT.md that feeds into planner and researcher
- Establishes scope guardrails to prevent creep

**Gray Area Analysis:**
The command should analyze the phase goal and identify discussable domains:
- **UI decisions**: Layout, components, styling approach, responsive behavior
- **UX decisions**: User flows, error handling, loading states, feedback
- **Behavior decisions**: Edge cases, validation rules, default values
- **Integration decisions**: API contracts, data formats, auth flows
- **Architecture decisions**: File structure, state management, patterns

Present identified gray areas to user with multi-select:
"I've identified these areas that could use your input before planning:
[ ] UI: Component layout and styling approach
[ ] UX: Error handling and loading states
[ ] Behavior: Validation rules and edge cases
Select which areas you'd like to discuss (or skip to let me decide):"

**Questioning Per Domain:**
For each selected domain, ask 2-4 focused questions:
- UI: "Should this be a modal, slide-over, or new page?" / "Dark mode support needed?"
- UX: "How should validation errors display?" / "Optimistic or confirmed updates?"
- Behavior: "What happens if X is empty?" / "Should Y be required or optional?"

**Scope Guardrails:**
- If user mentions features outside phase scope, capture in "Deferred Ideas" section
- Do NOT add to current phase scope
- Acknowledge: "Good idea - I've noted that for later. For this phase, let's focus on..."

**CONTEXT.md Output:**
```markdown
# Phase N Context

## Domain Boundary
What this phase covers vs. what it doesn't.

## Decisions by Category

### UI
- Decision 1: User chose X over Y
- Decision 2: ...

### UX
- Decision 1: ...

### Behavior
- Decision 1: ...

## Claude's Discretion
Areas user chose not to discuss - Claude decides during planning.

## Deferred Ideas
Ideas mentioned but out of scope for this phase.
```

**Downstream Consumers:**
- `gsd-phase-researcher` loads CONTEXT.md to focus research
- `gsd-planner` loads CONTEXT.md to respect user decisions
- Document this relationship in the command

---

`prompts/phase-completion/003-04-plan-phase.md`

**Purpose:** Implement `/fm:plan-phase [N]` command with pre-execution validation loop.

**Planning Flow:**
1. Load phase context (ROADMAP goal, REQUIREMENTS for this phase, CONTEXT.md from discuss-phase)
2. Optionally run research if complex domain (spawn researcher agent)
3. Create PLAN.md files (2-3 tasks each, never more than 3)
4. Run plan validation (checker)
5. If issues found: revise and re-validate (max 3 iterations)
6. Present validated plans to user
7. Commit plans

**Plan File Format (PLAN.md):**
```yaml
---
phase: 3
plan: 1
wave: 1
depends_on: []
files_modified:
  - src/commands/new-project.md
  - src/lib/state.ts
autonomous: true
must_haves:
  truths:
    - "User can initialize a new project"
    - "PROJECT.md is created with all sections"
  artifacts:
    - path: "src/commands/new-project.md"
      provides: "New project command"
      min_lines: 100
  key_links:
    - from: "new-project.md"
      to: "state.ts"
      via: "imports and calls createProject()"
---

# Plan 03-01: Project Initialization Command

## Objective
Create the /fm:new-project command that initializes projects.

## Requirements Addressed
- REQ-007: Greenfield project initialization
- REQ-008: Deep context gathering

## Tasks

<task type="auto">
  <name>Create project initialization command</name>
  <files>src/commands/new-project.md</files>
  <action>
    Create skill file with:
    1. Command definition and argument parsing
    2. Questioning flow using AskUserQuestion
    3. Research spawning logic (optional path)
    4. Requirements extraction from conversation
    5. Roadmap generation with phase mapping
  </action>
  <verify>File exists and has questioning flow structure</verify>
  <done>Command file created with all sections</done>
</task>

<task type="auto">
  <name>Create state management utilities</name>
  <files>src/lib/state.ts</files>
  <action>
    Create utilities for:
    1. createProject() - initialize .founder-mode/ structure
    2. updateState() - atomic STATE.md updates
    3. addRequirement() - REQ-ID assignment
  </action>
  <verify>Functions exported and callable</verify>
  <done>State utilities available for commands</done>
</task>
```

**Validation Loop:**
After creating plans, spawn plan-checker (or inline validation) to verify:

1. **Requirement Coverage**: Every REQ-ID for this phase has task(s)
2. **Task Completeness**: All tasks have files, action, verify, done
3. **Dependency Correctness**: No cycles, valid references, waves consistent
4. **Key Links Planned**: Artifacts are wired, not isolated
5. **Scope Sanity**: 2-3 tasks per plan (warn at 4, block at 5+)
6. **must_haves Derivation**: Truths are user-observable, not implementation details

If issues found:
- Present issues to user (or auto-fix if minor)
- Revise plans
- Re-validate
- Max 3 iterations before escalating to user

**Research Integration:**
If phase involves unfamiliar domain (3D, audio, ML, payments, etc.):
- Spawn researcher agent before planning
- Researcher produces `.founder-mode/phases/NN-name/RESEARCH.md`
- Planner loads research to inform task specifics

**Flags:**
- `--skip-research`: Skip domain research even if recommended
- `--skip-verify`: Skip plan validation loop (for experienced users)
- `--depth=N`: Control planning depth (1=minimal, 5=comprehensive)

---

`prompts/phase-completion/003-05-execute-phase.md`

**Purpose:** Implement `/fm:execute-phase [N]` command with wave-based parallel execution and goal-backward verification.

**Execution Flow:**
1. Load all PLAN.md files for phase N
2. Group plans by wave (from frontmatter `wave` field)
3. For each wave (sequential):
   a. Describe what this wave builds (narration)
   b. Spawn executor agents for each plan in wave (parallel)
   c. Wait for all agents in wave to complete
   d. Commit any orchestrator corrections
   e. Summarize what was built
4. After all waves: run goal-backward verification
5. If verification passes: mark phase complete, update STATE.md
6. If verification fails: diagnose issues, create fix plans

**Wave-Based Execution:**
```
Wave 1: Plans with depends_on: []
  ├── Plan 01 (parallel)
  └── Plan 02 (parallel)
       ↓ (wait for completion)
Wave 2: Plans with depends_on: ["01"] or ["02"]
  └── Plan 03
       ↓ (wait for completion)
Wave 3: Plans with depends_on: ["03"]
  └── Plan 04
```

Each plan executes in a fresh context via Task tool:
- Spawn with subagent_type appropriate for the work
- Pass plan content as prompt
- Agent executes tasks, makes per-task commits
- Agent returns SUMMARY.md content

**Per-Task Atomic Commits:**
Each task gets its own commit:
```
abc123 feat(03-01): create project initialization command
def456 feat(03-01): create state management utilities
ghi789 feat(03-02): implement questioning flow
```

Benefits:
- Git bisect finds exact failing task
- Each task independently revertable
- Clear history for future Claude sessions

**Ralph Wiggums Integration:**
For non-Claude models (codex, gemini, zai), the executor.py verification loop handles retries:
- Check for `<verification>VERIFICATION_COMPLETE</verification>` or `<verification>NEEDS_RETRY:reason</verification>`
- If NEEDS_RETRY: re-execute with history appended
- Max 3 iterations

For Claude execution via Task tool:
- Agent self-monitors and retries within its context
- Reports final status in return message

**Goal-Backward Verification (Post-Execution):**
After all plans complete, verify the phase GOAL was achieved:

1. **Truths**: What must be TRUE for the goal?
   - "User can initialize a new project"
   - "All PROJECT.md sections are populated"

2. **Artifacts**: What must EXIST for those truths?
   - `commands/new-project.md` exists, >100 lines
   - `.founder-mode/PROJECT.md` template exists

3. **Key Links**: What must be WIRED for artifacts to work?
   - new-project.md imports state utilities
   - Command is registered and callable

Verification checks:
- File existence and minimum size (catches stub completion)
- Import/export relationships (catches isolated artifacts)
- Runnable verification commands from plan (catches broken code)

If verification fails:
- Identify which truths are not met
- Diagnose root cause
- Create fix plan
- Execute fix plan
- Re-verify

**SUMMARY.md Output:**
```yaml
---
phase: 3
plan: 1
status: complete
started: 2026-01-18T10:00:00Z
completed: 2026-01-18T10:15:00Z
duration: 15m
tasks_completed: 2
commits:
  - abc123: "feat(03-01): create project initialization command"
  - def456: "feat(03-01): create state management utilities"
---

# Plan 03-01 Summary

## What Was Built
- /fm:new-project command with questioning flow
- State management utilities (createProject, updateState, addRequirement)

## Files Changed
- src/commands/new-project.md (created, 150 lines)
- src/lib/state.ts (created, 80 lines)

## Verification Results
- [x] Command file exists and has structure
- [x] State utilities exported and callable
- [x] Integration test passes

## Issues Encountered
None.

## Notes
Research was skipped (familiar domain).
```

**Flags:**
- `--plan=N`: Execute only specific plan, not whole phase
- `--gaps-only`: Execute only gap-closure plans from previous verification
- `--dry-run`: Show what would execute without running

---

`prompts/phase-completion/003-06-verification-agents.md`

**Purpose:** Create the agent specifications for plan-checker and verifier that power the validation loops.

**Why Agents:**
- Fresh context for each validation (no pollution from planning)
- Specialized prompts with deep methodology
- Reusable across phases
- Can be spawned in parallel for multiple plans

**Plan-Checker Agent Specification:**

Create `agents/plan-checker.md`:

```markdown
---
name: plan-checker
description: Validates plans will achieve phase goal before execution
tools: Read, Bash, Glob, Grep
---

<role>
You verify that plans WILL achieve the phase goal, not just that they look complete.
</role>

<verification_dimensions>
1. Requirement Coverage
2. Task Completeness
3. Dependency Correctness
4. Key Links Planned
5. Scope Sanity
6. must_haves Derivation
</verification_dimensions>

<process>
1. Load phase goal from ROADMAP.md
2. Load all PLAN.md files
3. Check each dimension
4. Return structured issues or PASSED
</process>

<output_format>
If passed:
  status: passed
  plans_verified: N

If issues:
  status: issues_found
  blockers: [...]
  warnings: [...]
</output_format>
```

**Verifier Agent Specification:**

Create `agents/verifier.md`:

```markdown
---
name: verifier
description: Verifies phase goals are achieved after execution (goal-backward)
tools: Read, Bash, Glob, Grep, LSP
---

<role>
You verify that phase GOALS are achieved, not just that tasks completed.
Goal-backward analysis: start from outcome, work backwards to evidence.
</role>

<methodology>
1. Extract phase goal
2. Derive must-be-true statements (truths)
3. Derive must-exist artifacts
4. Derive must-be-wired connections (key links)
5. Verify each level against codebase
</methodology>

<verification_patterns>
- Stub detection: File exists but <10 lines or only boilerplate
- Isolation detection: Component created but not imported anywhere
- Wiring verification: API endpoint exists AND component calls it
- Behavior verification: Run tests, check outputs
</verification_patterns>

<output_format>
status: passed | failed
truths:
  - truth: "User can log in"
    status: verified | failed
    evidence: "Login endpoint returns 200, cookie set"
artifacts:
  - path: "src/api/auth/login.ts"
    status: exists | missing | stub
    lines: 45
key_links:
  - from: "LoginForm.tsx"
    to: "/api/auth/login"
    status: wired | missing
    evidence: "fetch call on line 23"
```

**Verification Patterns Reference:**

Create `references/verification-patterns.md` documenting how to verify different artifact types:

- React components: Check exports, props interface, render output
- API endpoints: Check route registration, handler logic, response shape
- Database models: Check schema definition, migrations, queries
- Configuration: Check file exists, required fields present
- CLI commands: Check registration, argument parsing, execution
- Tests: Check file exists, test cases cover requirements
- Documentation: Check sections present, links valid

**Integration with Commands:**

- `/fm:plan-phase` spawns plan-checker after creating plans
- `/fm:execute-phase` spawns verifier after execution completes
- Both agents return structured output for orchestrator to process
- Orchestrator presents results to user and handles fix flows

---

#### Phase 4 Sub-Prompts

`prompts/phase-completion/004-01-github-integration.md`

**Purpose:** Implement GitHub issue fetching and the `/fm:list-github-issues` command.

**Why This Matters:**
- Pull work items directly from GitHub instead of manual copy-paste
- Enable automated workflows (fetch issue → fix → PR)
- Foundation for /fix-gh-issue command

**gh CLI Integration:**
Use the `gh` CLI (GitHub's official CLI) for all GitHub operations:

```bash
# List issues assigned to current user
gh issue list --assignee @me --state open

# List issues with specific labels
gh issue list --label "bug" --label "priority:high"

# Get issue details
gh issue view 123 --json title,body,labels,assignees,milestone

# List issues in JSON for parsing
gh issue list --json number,title,body,labels,state
```

**Command: /fm:list-github-issues**

```markdown
# List GitHub Issues

## Arguments
- `--assignee`: Filter by assignee (default: @me)
- `--label`: Filter by label (repeatable)
- `--state`: open | closed | all (default: open)
- `--limit`: Max issues to return (default: 20)
- `--repo`: Override repo (default: current repo)

## Output
Present issues in scannable format:

```
GitHub Issues (5 open, assigned to @me)

#123 [bug] Fix login redirect loop
     Labels: bug, priority:high
     Created: 2 days ago

#456 [feature] Add dark mode support
     Labels: enhancement, ui
     Created: 1 week ago

#789 [bug] API timeout on large requests
     Labels: bug, backend
     Created: 3 days ago

Commands:
  /fm:fix-gh-issue 123    Fix issue #123
  /fm:fix-gh-issue 123 456 789    Fix multiple issues
```

**Issue Normalization:**
Parse GitHub issue into internal format:

```typescript
interface NormalizedIssue {
  source: "github";
  id: string;           // "123"
  url: string;          // "https://github.com/owner/repo/issues/123"
  title: string;
  body: string;
  labels: string[];
  assignees: string[];
  milestone?: string;
  created: string;
  updated: string;
}
```

**Files Created:**
- `commands/list-github-issues.md` - Command skill file
- `lib/github.ts` - GitHub integration utilities (if needed beyond gh CLI)
- `lib/issue-types.ts` - Normalized issue interface

**Error Handling:**
- `gh` not installed: Show installation instructions
- Not authenticated: Run `gh auth login`
- No repo context: Prompt for `--repo` flag
- Rate limiting: Show wait time and retry

---

`prompts/phase-completion/004-02-jira-integration.md`

**Purpose:** Implement Jira ticket fetching and the `/fm:list-jira-tickets` command.

**Jira API Options:**

Option 1: Jira CLI (if available)
```bash
jira issue list --project PROJ --assignee currentUser()
jira issue view PROJ-123
```

Option 2: Direct REST API
```bash
curl -u email:api_token \
  "https://your-domain.atlassian.net/rest/api/3/search?jql=assignee=currentUser()"
```

Option 3: Official Jira CLI (`atlassian-cli`)
```bash
acli jira --action getIssueList --project PROJ --assignee currentUser
```

**Authentication Handling:**
Jira requires API tokens. Configuration options:

1. Environment variable: `JIRA_API_TOKEN`
2. Config file: `~/.config/founder-mode/jira.json`
3. Prompt on first use, save securely

```json
{
  "domain": "your-domain.atlassian.net",
  "email": "you@example.com",
  "api_token": "your-api-token"
}
```

**Command: /fm:list-jira-tickets**

```markdown
# List Jira Tickets

## Arguments
- `--project`: Jira project key (required or from config)
- `--assignee`: Filter by assignee (default: currentUser())
- `--status`: Filter by status (e.g., "To Do", "In Progress")
- `--type`: Filter by issue type (Bug, Story, Task)
- `--limit`: Max tickets to return (default: 20)

## Output
```
Jira Tickets (PROJ, 5 open, assigned to you)

PROJ-123 [Bug] Fix login redirect loop
         Status: To Do | Priority: High
         Sprint: Sprint 23

PROJ-456 [Story] Add dark mode support
         Status: In Progress | Priority: Medium
         Sprint: Sprint 23

Commands:
  /fm:fix-jira-ticket PROJ-123
```

**Issue Normalization:**
Same interface as GitHub, with source: "jira":

```typescript
interface NormalizedIssue {
  source: "jira";
  id: string;           // "PROJ-123"
  url: string;          // "https://domain.atlassian.net/browse/PROJ-123"
  title: string;        // summary field
  body: string;         // description field
  labels: string[];     // labels field
  assignees: string[];
  milestone?: string;   // sprint name
  created: string;
  updated: string;
  // Jira-specific
  status?: string;
  priority?: string;
  issueType?: string;
}
```

**Files Created:**
- `commands/list-jira-tickets.md` - Command skill file
- `lib/jira.ts` - Jira integration utilities
- `lib/issue-types.ts` - Updated with Jira fields

**Error Handling:**
- Not configured: Guide through setup
- Invalid credentials: Clear error with re-auth instructions
- Project not found: List available projects
- Rate limiting: Handle gracefully

---

`prompts/phase-completion/004-03-fix-gh-issue.md`

**Purpose:** Implement the end-to-end `/fm:fix-gh-issue` workflow that goes from issue to PR.

**Complete Workflow:**

```
/fm:fix-gh-issue 123
       ↓
1. Fetch issue details from GitHub
       ↓
2. Analyze issue (bug vs feature, scope, affected areas)
       ↓
3. Create worktree (optional, based on config or --worktree flag)
       ↓
4. Read relevant codebase files (guided by issue content)
       ↓
5. Create implementation plan (mini plan-phase)
       ↓
6. Execute fix (with Ralph Wiggums retry if needed)
       ↓
7. Run tests and verification
       ↓
8. Create PR with issue reference
       ↓
9. Output PR URL
```

**Command: /fm:fix-gh-issue**

```markdown
# Fix GitHub Issue

## Arguments
- Issue number(s): `123` or `123 456 789` for multiple
- `--worktree`: Create isolated worktree for fix
- `--branch`: Custom branch name (default: fix/issue-{number})
- `--no-pr`: Skip PR creation, just commit
- `--draft`: Create draft PR instead of ready for review

## Flow

### Step 1: Fetch Issue
```bash
gh issue view {number} --json title,body,labels,comments
```

Parse issue to understand:
- What's broken or needed (from title/body)
- Reproduction steps (if bug)
- Acceptance criteria (if feature)
- Related files mentioned
- Labels for context (bug, feature, area:auth, etc.)

### Step 2: Analyze Scope
Determine:
- Is this a bug fix or feature?
- Single file or multi-file change?
- Tests needed?
- Breaking change?

For bugs: Find reproduction, locate root cause
For features: Understand requirements, identify files to create/modify

### Step 3: Create Worktree (if --worktree)
```bash
# Get worktree directory from config
WORKTREE_DIR=$(cat .founder-mode/config.json | jq -r '.worktree_dir')

# Create worktree
git worktree add "$WORKTREE_DIR/issue-{number}" -b fix/issue-{number}

# Switch context to worktree
cd "$WORKTREE_DIR/issue-{number}"
```

### Step 4: Codebase Analysis
Using issue content as guide:
- Search for relevant files (Grep for error messages, function names)
- Read files that will need modification
- Understand current implementation
- Identify test files

### Step 5: Plan Fix
Create lightweight plan:
- What files to modify
- What changes to make
- How to verify fix works

For simple fixes: Skip formal planning, just fix
For complex fixes: Create mini-PLAN.md

### Step 6: Execute Fix
Make the code changes:
- Implement fix/feature
- Add/update tests if needed
- Run linting and formatting

Use Ralph Wiggums pattern if execution fails:
- Check for errors in output
- Retry with error context
- Max 3 attempts

### Step 7: Verify
Run verification:
```bash
# Run tests
npm test
# or
pytest
# or whatever the project uses

# Run linting
npm run lint

# Build check
npm run build
```

### Step 8: Create PR
```bash
git add .
git commit -m "fix: {issue title}

Fixes #{number}"

git push -u origin fix/issue-{number}

gh pr create \
  --title "Fix: {issue title}" \
  --body "## Summary
Fixes #{number}

## Changes
- {change 1}
- {change 2}

## Testing
- {how it was tested}" \
  --assignee @me
```

### Step 9: Output
```
Issue #123 fixed!

Branch: fix/issue-123
PR: https://github.com/owner/repo/pull/456

Changes made:
- src/auth/login.ts: Fixed redirect loop by checking session before redirect
- src/auth/login.test.ts: Added test for redirect loop scenario

Verification:
- [x] Tests pass (23 passed, 0 failed)
- [x] Lint clean
- [x] Build successful
```

**Files Created:**
- `commands/fix-gh-issue.md` - Command skill file
- `lib/issue-workflow.ts` - Shared workflow utilities

**Error Handling:**
- Issue not found: Clear error
- Worktree conflict: Suggest cleanup
- Tests fail: Show failures, offer retry or abort
- PR creation fails: Show error, manual instructions

---

#### Phase 5 Sub-Prompts

`prompts/phase-completion/005-01-parallel-execution.md`

**Purpose:** Enable fixing multiple issues in parallel with progress aggregation.

**User Story:**
"I have 5 bugs assigned to me. I want to say 'fix these' and have founder-mode work on all of them in parallel, showing me progress, and delivering 5 PRs."

**Command: /fm:fix-issues**

```markdown
# Fix Multiple Issues

## Arguments
- Issue identifiers: `123 456 789` or `PROJ-123 PROJ-456`
- `--source`: github | jira (auto-detected from format)
- `--parallel`: Max concurrent fixes (default: 3)
- `--worktree`: Use worktrees for isolation (recommended for parallel)

## Flow

### Step 1: Parse and Fetch Issues
For each issue ID:
- Detect source (github if numeric, jira if has project prefix)
- Fetch issue details
- Normalize to common format

### Step 2: Create Execution Plan
```
Issues to fix: 3
  #123 [bug] Login redirect loop
  #456 [feature] Dark mode
  #789 [bug] API timeout

Parallel workers: 3
Estimated time: ~10 min (parallel) vs ~30 min (sequential)

Proceed? [Y/n]
```

### Step 3: Spawn Parallel Workers
For each issue, spawn a Task agent:
```typescript
const workers = issues.map(issue =>
  spawnTask({
    subagent_type: "general-purpose",
    prompt: buildFixPrompt(issue),
    run_in_background: true
  })
);
```

Each worker:
- Creates its own worktree (if --worktree)
- Executes fix-gh-issue flow
- Returns result (success/failure, PR URL, summary)

### Step 4: Progress Aggregation
While workers are running, poll for status:
```
Fixing 3 issues in parallel...

#123 Login redirect loop     [████████░░] 80% - Running tests
#456 Dark mode               [██████████] 100% - PR created
#789 API timeout             [██░░░░░░░░] 20% - Analyzing code

Completed: 1/3  |  In Progress: 2  |  Failed: 0
```

Use Task tool's output_file to check progress:
```bash
tail -20 /tmp/claude-task-{id}.log
```

### Step 5: Collect Results
When all workers complete:
```
All issues fixed!

Results:
  #123 Login redirect loop    ✓ PR #501 https://github.com/...
  #456 Dark mode              ✓ PR #502 https://github.com/...
  #789 API timeout            ✓ PR #503 https://github.com/...

Summary:
  - 3 PRs created
  - 12 files changed
  - 45 tests added
  - Total time: 8 min 23 sec
```

**Failure Handling:**
If a worker fails:
```
Issue #789 failed:
  Error: Tests failing after fix attempt

  Options:
  1. Retry this issue
  2. Skip and continue
  3. Abort all

  [1/2/3]:
```

**Progress Display:**
Use terminal updates for live progress:
- Spinner for active work
- Progress bar based on stage (fetch → analyze → plan → fix → test → PR)
- Color coding (green=done, yellow=in-progress, red=failed)

**Files Created:**
- `commands/fix-issues.md` - Parallel fix command
- `lib/parallel-executor.ts` - Worker spawning and progress aggregation

---

`prompts/phase-completion/005-02-sprint-workflow.md`

**Purpose:** Enable continuous sprint execution without /clear loops.

**The Problem with /clear Loops:**
GSD and other tools use `/clear` between tasks to reset context. This:
- Loses conversational context
- Requires re-loading project state each time
- Feels disjointed to user
- Makes it hard to track overall progress

**Sprint Execution Model:**
Instead of clearing context, use a queue-based approach:

```
Sprint Queue:
  1. [pending]  #123 Login redirect loop
  2. [pending]  #456 Dark mode
  3. [pending]  #789 API timeout
  4. [pending]  #101 Update docs

Current: Waiting to start
Progress: 0/4 complete
```

**Command: /fm:run-sprint**

```markdown
# Run Sprint

## Arguments
- `--issues`: Comma-separated issue IDs, or "assigned" for all assigned
- `--from-jira`: Use Jira sprint (fetches current sprint issues)
- `--from-github`: Use GitHub milestone
- `--max`: Maximum issues to process (default: 10)
- `--parallel`: Run N issues in parallel (default: 1 for sequential)

## Flow

### Step 1: Build Queue
```bash
# From explicit list
/fm:run-sprint --issues 123,456,789

# From GitHub assigned issues
/fm:run-sprint --from-github --assignee @me

# From Jira sprint
/fm:run-sprint --from-jira --sprint "Sprint 23"
```

### Step 2: Present Sprint Plan
```
Sprint Plan: 4 issues

Priority order:
  1. #123 [bug][high] Login redirect loop
  2. #789 [bug][medium] API timeout
  3. #456 [feature][medium] Dark mode
  4. #101 [docs][low] Update README

Estimated: 2-3 hours

Options:
  [Enter] Start sprint
  [r] Reorder issues
  [x] Remove issue from sprint
  [q] Cancel
```

### Step 3: Execute Queue
For each issue in queue:
1. Show "Starting issue #N"
2. Execute fix workflow (in fresh agent context)
3. On completion: Show result, update queue
4. On failure: Offer retry/skip/abort
5. Move to next issue

**Key: Fresh Contexts Without /clear**
Use Task tool to spawn each fix in a fresh context:
```typescript
for (const issue of queue) {
  // This runs in fresh context (no /clear needed)
  const result = await spawnTask({
    subagent_type: "general-purpose",
    prompt: buildFixPrompt(issue)
  });

  // Orchestrator stays lean, just tracking progress
  updateQueue(issue, result);
  displayProgress();
}
```

The orchestrator context stays small (just queue management).
Each fix gets a fresh 200k context.
No /clear needed.

### Step 4: Progress Between Issues
After each issue completes:
```
Issue #123 complete! PR #501 created.

Sprint Progress: ████░░░░░░ 1/4 (25%)

Next up: #789 API timeout
  Type: bug
  Priority: medium
  Files likely affected: src/api/*, src/lib/http.ts

[Enter] Continue to #789
[s] Skip #789
[p] Pause sprint (can resume later)
[q] End sprint early
```

### Step 5: Sprint Summary
When queue is empty or user ends sprint:
```
Sprint Complete!

Results:
  ✓ #123 Login redirect loop     → PR #501 (merged)
  ✓ #789 API timeout             → PR #502 (open)
  ✓ #456 Dark mode               → PR #503 (open)
  ○ #101 Update README           → Skipped

Stats:
  - Duration: 2h 15m
  - PRs created: 3
  - Issues skipped: 1
  - Files changed: 34
  - Tests added: 12

Session saved to: .founder-mode/sprints/2026-01-18-sprint.md
```

**Pause and Resume:**
Sprint state is saved to disk:
```yaml
# .founder-mode/sprints/active.yaml
started: 2026-01-18T10:00:00Z
queue:
  - id: "123"
    status: complete
    pr: "https://..."
  - id: "789"
    status: in_progress
    started: 2026-01-18T10:45:00Z
  - id: "456"
    status: pending
  - id: "101"
    status: pending
```

Resume with:
```
/fm:run-sprint --resume
```

**Issue Queue Management:**
Allow mid-sprint queue modifications:
```
/fm:sprint-add 999    # Add issue to queue
/fm:sprint-remove 456 # Remove from queue
/fm:sprint-priority 789 1  # Move #789 to position 1
```

**Files Created:**
- `commands/run-sprint.md` - Sprint execution command
- `commands/sprint-add.md` - Add issue to active sprint
- `commands/sprint-remove.md` - Remove issue from sprint
- `lib/sprint-queue.ts` - Queue management and persistence

### Step 5: Prompt Format Requirements

Each sub-prompt MUST follow this structure:

```markdown
# [Title]

## Objective
One sentence describing what this prompt accomplishes.

## Prerequisites
- Files that must exist
- Commands that must be available
- Prior prompts that must complete first

## Context Files to Read
List specific files the executor should read before starting.

## Deliverables
Explicit list of files to create or modify.

## Instructions
Step-by-step implementation instructions.

## Verification
How to confirm the work is complete:
- Commands to run
- Expected outputs
- Success criteria

## Rollback
How to undo this work if needed.
```

### Step 6: Write All Files

Create the directory and all prompt files:

1. Create `prompts/phase-completion/` directory
2. Write `000-orchestrator.md`
3. Write all Phase 3 sub-prompts (003-01 through 003-06)
4. Write all Phase 4 sub-prompts (004-01 through 004-03)
5. Write all Phase 5 sub-prompts (005-01 through 005-02)

### Step 7: Create Dependency Graph

In `000-orchestrator.md`, include a dependency graph showing execution order:

```
003-01 (state-management)
    ↓
003-02 (new-project) ──────────────────┐
    ↓                                  │
003-03 (discuss-phase)                 │
    ↓                                  │
003-04 (plan-phase)                    │
    ↓                                  │
003-06 (verification-agents) ←─────────┤
    ↓                                  │
003-05 (execute-phase)                 │
    ↓                                  │
004-01 (github) ───────────────────────┤
    ↓                                  │
004-02 (jira) ─────────────────────────┤
    ↓                                  │
004-03 (fix-gh-issue) ←────────────────┘
    ↓
005-01 (parallel-execution)
    ↓
005-02 (sprint-workflow)
```

## Output

When complete, the `prompts/phase-completion/` directory should contain:

```
prompts/phase-completion/
├── 000-orchestrator.md
├── 003-01-state-management.md
├── 003-02-new-project.md
├── 003-03-discuss-phase.md
├── 003-04-plan-phase.md
├── 003-05-execute-phase.md
├── 003-06-verification-agents.md
├── 004-01-github-integration.md
├── 004-02-jira-integration.md
├── 004-03-fix-gh-issue.md
├── 005-01-parallel-execution.md
└── 005-02-sprint-workflow.md
```

## Success Criteria

- [ ] All 12 prompt files created
- [ ] Each prompt follows the required format
- [ ] Dependency graph is accurate
- [ ] GSD patterns are appropriately adapted (not copy-pasted)
- [ ] Prompts are specific enough to execute without additional context
- [ ] Verification steps are concrete and runnable

## Notes

- Adapt GSD patterns to founder-mode's architecture (skills-based, not agent-heavy)
- Keep prompts focused - one responsibility per prompt
- Include rollback instructions for each prompt
- Reference existing commands/patterns where applicable
