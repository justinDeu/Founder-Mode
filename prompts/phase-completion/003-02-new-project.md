# New Project Command

## Objective

Implement the unified `/founder-mode:new-project` command that initializes a project from scratch with deep context gathering. This is the entry point for all new founder-mode projects.

## Prerequisites

- 003-01-state-management.md complete
- templates/ directory exists with all template files
- references/ directory exists with state utilities

## Context Files to Read

```
templates/project.md
templates/roadmap.md
templates/state.md
templates/requirements.md
templates/config.json
references/state-utilities.md
commands/run-prompt.md      # For command file format
```

## Deliverables

Create `commands/new-project.md`:

```markdown
---
name: founder-mode:new-project
description: Initialize a new project with deep context gathering
allowed-tools:
  - Read
  - Bash
  - Write
  - Task
  - AskUserQuestion
---

# New Project

Initialize a new founder-mode project through a unified flow: questioning → research (optional) → requirements → roadmap.

## Process

### Phase 1: Setup

**Execute before any user interaction:**

1. Check for existing project:
   ```bash
   [ -f .founder-mode/PROJECT.md ] && echo "ERROR: Project exists" && exit 1
   ```

2. Initialize git if needed:
   ```bash
   [ -d .git ] || git init
   ```

3. Detect existing code (brownfield):
   ```bash
   CODE_FILES=$(find . -name "*.ts" -o -name "*.js" -o -name "*.py" -o -name "*.go" -o -name "*.rs" 2>/dev/null | grep -v node_modules | grep -v .git | head -20)
   HAS_PACKAGE=$([ -f package.json ] || [ -f requirements.txt ] || [ -f Cargo.toml ] || [ -f go.mod ] && echo "yes")
   ```

### Phase 2: Brownfield Detection

If existing code detected, use AskUserQuestion:

- header: "Existing Code"
- question: "I found existing code. How should I proceed?"
- options:
  - "Acknowledge existing code (Recommended)" - Document what exists in PROJECT.md
  - "Treat as greenfield" - Start fresh, ignore existing code

### Phase 3: Deep Questioning

**Start the conversation:**

Ask inline (freeform): "What do you want to build?"

Wait for response, then follow threads:

- What excited them about this idea
- What problem sparked this
- What they mean by vague terms
- What it would actually look like
- What's already decided vs open

**Use AskUserQuestion for structured choices:**

For decisions with clear options (tech stack, auth method, etc.), present as multi-choice.
For open-ended exploration, use freeform conversation.

**Essential questions to cover:**

1. "What are you building?" (vision)
2. "What's the single most important thing it must do?" (core priority)
3. "What's explicitly out of scope?" (boundaries)
4. "Any technical constraints?" (platform, language, existing code)

**Decision gate:**

When ready to create PROJECT.md, use AskUserQuestion:

- header: "Ready?"
- question: "I think I understand. Ready to create PROJECT.md?"
- options:
  - "Create PROJECT.md" - Let's proceed
  - "Keep exploring" - More to discuss

### Phase 4: Write PROJECT.md

Synthesize context into `.founder-mode/PROJECT.md` using the template.

**For greenfield:**
- Requirements section: All in "Active" (hypotheses to validate)

**For brownfield:**
- Infer "Validated" requirements from existing code
- New work goes in "Active"

**Commit immediately:**
```bash
mkdir -p .founder-mode
git add .founder-mode/PROJECT.md
git commit -m "docs: initialize project

{one-liner from What This Is section}"
```

### Phase 5: Workflow Preferences

Use single AskUserQuestion with 3 questions:

```
questions: [
  {
    header: "Mode",
    question: "How do you want to work?",
    options: [
      { label: "YOLO (Recommended)", description: "Auto-approve, just execute" },
      { label: "Interactive", description: "Confirm at each step" }
    ]
  },
  {
    header: "Depth",
    question: "How thorough should planning be?",
    options: [
      { label: "Quick", description: "3-5 phases, 1-3 plans each" },
      { label: "Standard", description: "5-8 phases, 3-5 plans each" },
      { label: "Comprehensive", description: "8-12 phases, 5-10 plans each" }
    ]
  },
  {
    header: "Parallel",
    question: "Run plans in parallel?",
    options: [
      { label: "Parallel (Recommended)", description: "Independent plans run simultaneously" },
      { label: "Sequential", description: "One plan at a time" }
    ]
  }
]
```

Create `.founder-mode/config.json` and commit.

### Phase 6: Research Decision

Use AskUserQuestion:

- header: "Research"
- question: "Research the domain before defining requirements?"
- options:
  - "Research first (Recommended)" - Discover standard stacks, patterns, pitfalls
  - "Skip research" - Go straight to requirements

**If research:**

Create `.founder-mode/research/` directory.

Spawn 4 parallel Explore agents:

1. **Stack researcher**: "What's the standard 2025 stack for {domain}?"
2. **Features researcher**: "What features do {domain} products have? Table stakes vs differentiators?"
3. **Architecture researcher**: "How are {domain} systems structured? Components, data flow?"
4. **Pitfalls researcher**: "What do {domain} projects commonly get wrong?"

Each writes to `.founder-mode/research/{STACK|FEATURES|ARCHITECTURE|PITFALLS}.md`.

After all complete, synthesize into `.founder-mode/research/SUMMARY.md`.

### Phase 7: Define Requirements

**If research exists:** Present features by category, use multi-select for scoping.

**If no research:** Gather through conversation.

For each category, use AskUserQuestion:

- header: "{Category}"
- question: "Which {category} features are in v1?"
- multiSelect: true
- options: Features from research or conversation

Track:
- Selected → v1 requirements
- Unselected table stakes → v2
- Unselected differentiators → out of scope

Generate `.founder-mode/REQUIREMENTS.md` with REQ-IDs.

**Present full list for confirmation:**

Show every requirement (not counts). Get approval before proceeding.

### Phase 8: Create Roadmap

Spawn gsd-roadmapper (or use inline logic) with context:

```
@.founder-mode/PROJECT.md
@.founder-mode/REQUIREMENTS.md
@.founder-mode/research/SUMMARY.md (if exists)
@.founder-mode/config.json
```

**Roadmapper produces:**
- `.founder-mode/ROADMAP.md` with phases, requirement mappings, success criteria
- `.founder-mode/STATE.md` initialized
- Updated REQUIREMENTS.md with traceability

**Present roadmap for approval:**

Show phase overview table. Get user approval before committing.

**Commit roadmap:**
```bash
git add .founder-mode/ROADMAP.md .founder-mode/STATE.md .founder-mode/REQUIREMENTS.md
git commit -m "docs: create roadmap ({N} phases)

All v1 requirements mapped to phases."
```

### Phase 9: Done

Present completion summary:

```
PROJECT INITIALIZED

{Project Name}

| Artifact     | Location                     |
|--------------|------------------------------|
| Project      | .founder-mode/PROJECT.md     |
| Config       | .founder-mode/config.json    |
| Research     | .founder-mode/research/      |
| Requirements | .founder-mode/REQUIREMENTS.md|
| Roadmap      | .founder-mode/ROADMAP.md     |

{N} phases | {X} requirements | Ready to build

Next: /founder-mode:discuss-phase 1
```

## Success Criteria

- [ ] .founder-mode/ directory created
- [ ] Git repo initialized
- [ ] Deep questioning completed
- [ ] PROJECT.md captures context → committed
- [ ] config.json has preferences → committed
- [ ] Research completed (if selected) → committed
- [ ] REQUIREMENTS.md with REQ-IDs → committed
- [ ] ROADMAP.md with phases → committed
- [ ] STATE.md initialized → committed
- [ ] User knows next step
```

## Instructions

### Step 1: Create Command File

Create `commands/new-project.md` with the full content above.

### Step 2: Verify Command Structure

Check that command file has:
- Valid frontmatter with name, description, allowed-tools
- All 9 phases documented
- AskUserQuestion patterns for structured choices
- Commit commands at each artifact creation
- Success criteria checklist

### Step 3: Test Command Registration

The command should be accessible via `/founder-mode:new-project` when founder-mode plugin is loaded.

## Verification

- [ ] commands/new-project.md exists
- [ ] Frontmatter is valid YAML
- [ ] All phases documented
- [ ] Questioning flow includes essential questions
- [ ] Research spawns 4 parallel agents
- [ ] Requirements use REQ-ID format
- [ ] Roadmap gets user approval before commit
- [ ] Completion message shows next step

## Rollback

```bash
rm commands/new-project.md
git checkout -- commands/new-project.md
```
