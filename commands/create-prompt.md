---
name: fm:create-prompt
description: Create optimized prompts with clarifying questions
argument-hint: [task description] [--folder path]
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Skill
  - AskUserQuestion
---

# Create Prompt

Create well-structured prompt files through guided questions and template selection.

## Arguments

Parse `$ARGUMENTS` for:

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `[description]` | positional | none | Task description in natural language |
| `--folder` | option | none | Subfolder under ./prompts/ for the new prompt |

## Core Process

<thinking_framework>
Before generating, analyze the request:

1. **Clarity Check**: Would a colleague with minimal context understand what's being asked?
   - Are there ambiguous terms that could mean multiple things?
   - Are there missing constraints or requirements?
   - Is the goal clear?

2. **Task Complexity**: Simple (single file, clear goal) or complex (multi-file, research needed)?

3. **Task Type Detection**: Match keywords to determine template:
   - **coding**: build, implement, fix, refactor, create, add, modify, update, change
   - **research**: research, investigate, explore, understand, learn, discover
   - **analysis**: analyze, compare, audit, review, assess, evaluate, examine
   - Default to coding if unclear

4. **Reasoning Depth**: Does this need extended thinking triggers?
   - Simple/straightforward: Standard prompt
   - Complex reasoning, multiple constraints: Include phrases like "thoroughly analyze", "consider multiple approaches"
</thinking_framework>

### Step 1: Clarification

If the description is vague, ambiguous, or missing critical details, ask targeted questions.

<clarification_triggers>
Ask questions when:
- Description is fewer than 5 words
- Contains vague terms: "fix it", "make it work", "improve", "update"
- Missing target: no file, component, or feature specified
- Missing goal: unclear what success looks like
- Multiple interpretations possible
</clarification_triggers>

<clarification_examples>
**Vague request:** "Fix the bug"
**Questions to ask:**
1. Which bug? Can you describe the expected vs actual behavior?
2. Where does it occur? Which file or component?
3. How can I reproduce it?

**Vague request:** "Add authentication"
**Questions to ask:**
1. What type? JWT, OAuth, session-based?
2. Which providers? Google, GitHub, email/password?
3. Which routes or pages need protection?

**Vague request:** "Optimize performance"
**Questions to ask:**
1. What specific performance issues? Load time, memory, database queries?
2. What are the current metrics?
3. What's the target improvement?
</clarification_examples>

Keep clarifications minimal: 1-3 targeted questions max, then proceed.

### Step 2: Complexity Assessment

Determine complexity level for prompt structure:

| Level | Characteristics | Template Depth |
|-------|-----------------|----------------|
| Simple | Single file, clear goal, no research needed | Minimal, focused |
| Moderate | Multiple files, clear goal, some context needed | Standard with verification |
| Complex | Multi-step, research needed, architectural impact | Comprehensive with sections |

### Step 3: Template Selection

Based on task type detection, select the appropriate template.

<template_keywords>
| Template | Keywords | When to Use |
|----------|----------|-------------|
| **coding** | build, implement, fix, refactor, create, add, modify, update, change | Building or modifying code, features, components |
| **research** | research, investigate, explore, understand, learn, discover | Gathering information, learning about a topic |
| **analysis** | analyze, compare, audit, review, assess, evaluate, examine | Examining existing code, data, or systems |
</template_keywords>

<template_selection>
```
if keywords match ["build", "implement", "fix", "refactor", "create", "add", "modify", "update", "change"]:
    use coding_template
elif keywords match ["research", "investigate", "explore", "understand", "learn", "discover"]:
    use research_template
elif keywords match ["analyze", "compare", "audit", "review", "assess", "evaluate", "examine"]:
    use analysis_template
else:
    use coding_template  # default
```

**Default behavior:** When no keywords match or the task type is ambiguous, default to the coding template since most prompts involve code changes.
</template_selection>

### Step 4: Prompt Numbering

Determine the next prompt number:

```bash
# Find highest existing number in ./prompts/
ls -1 ./prompts/*.md 2>/dev/null | grep -oE '[0-9]+' | sort -n | tail -1
# If none exist, start with 001
# Increment by 1 for new prompt
```

Naming format:
- Number: 001, 002, 003, etc. (zero-padded to 3 digits)
- Name: lowercase, hyphen-separated, max 5 words
- Example: `001-fix-auth-token-bug.md`

### Step 5: Generate and Save

1. Generate prompt using selected template
2. Save to `./prompts/{folder}/{number}-{name}.md`
   - If `--folder` specified, create subfolder if needed
   - If no folder, save directly to `./prompts/`

### Step 6: Post-Save Options

After saving, present options:

```
Prompt saved to: ./prompts/001-implement-feature.md

What's next?

1. Run now - Execute with Claude
2. Edit first - Review and modify the prompt
3. Save for later - Done for now

Choose (1-3):
```

<post_save_actions>
**Option 1 (Run now):**
Invoke via Skill tool: `/fm:run-prompt ./prompts/{filename}`

**Option 2 (Edit first):**
Display: "The prompt is saved at ./prompts/{filename}. Edit it with your preferred editor, then run with `/fm:run-prompt {filename}`"

**Option 3 (Save for later):**
Display: "Prompt saved. Run later with `/fm:run-prompt {filename}`"
</post_save_actions>

## Prompt Templates

<coding_template>
### Coding Task Template

```xml
<objective>
[Clear statement of what needs to be built/fixed/refactored]
[WHY this matters and the end goal]
</objective>

<context>
[Project type, tech stack, relevant constraints]
@[relevant files to examine]
</context>

<requirements>
[Specific functional requirements]
[Performance or quality requirements]
</requirements>

<implementation>
[Specific approaches or patterns to follow]
[What to avoid and WHY]
</implementation>

<output>
Create/modify files:
- ./path/to/file.ext - [description]
</output>

<verification>
Before declaring complete:
- [ ] [Build/test command passes]
- [ ] [Specific behavior works as expected]
</verification>
```
</coding_template>

<research_template>
### Research Task Template

```xml
<research_objective>
[What information needs to be gathered]
[Intended use of the research]
</research_objective>

<scope>
[Boundaries of the research]
[Sources to prioritize or avoid]
[Time period or version constraints]
</scope>

<deliverables>
[Format of research output]
[Level of detail needed]
Save findings to: ./research/[topic].md
</deliverables>

<evaluation_criteria>
[How to assess quality/relevance of sources]
[Key questions that must be answered]
</evaluation_criteria>

<verification>
Before completing, verify:
- [ ] All key questions are answered
- [ ] Sources are credible and relevant
</verification>
```
</research_template>

<analysis_template>
### Analysis Task Template

```xml
<objective>
[What to analyze and why]
[What the analysis will be used for]
</objective>

<data_sources>
@[files or data to analyze]
![relevant commands to gather data]
</data_sources>

<analysis_requirements>
[Specific metrics or patterns to identify]
[Depth of analysis needed]
[Any comparisons or benchmarks]
</analysis_requirements>

<output_format>
[How results should be structured]
Save analysis to: ./analyses/[descriptive-name].md
</output_format>

<verification>
[How to validate the analysis is complete and accurate]
</verification>
```
</analysis_template>

## Common Elements for All Templates

Every generated prompt should include:

1. **Objective with WHY**: Always explain the purpose and goal
2. **Context with @references**: Point to relevant files when applicable
3. **Verification section**: Clear success criteria
4. **Relative paths**: Use `./` for all file outputs

## Intelligence Rules

1. **Clarity First**: If anything is unclear, ask before proceeding
2. **Match Complexity**: Simple tasks get concise prompts, complex tasks get comprehensive structure
3. **Precision Over Brevity**: A longer, clear prompt beats a short, ambiguous one
4. **Explicit Instructions**: Tell Claude exactly what to do
5. **Verification Always**: Every prompt includes success criteria

## Examples

**Example 1: Simple coding task**

User: "Add a dark mode toggle to the settings page"

Generated prompt (001-add-dark-mode-toggle.md):
```xml
<objective>
Add a dark mode toggle to the settings page.
This allows users to switch between light and dark themes based on their preference.
</objective>

<context>
@src/pages/Settings.tsx
@src/styles/theme.css
</context>

<requirements>
- Add toggle switch component to settings page
- Persist preference to localStorage
- Apply theme class to document root
</requirements>

<implementation>
- Use existing toggle component if available
- Follow current styling patterns
- Avoid inline styles
</implementation>

<output>
Modify:
- ./src/pages/Settings.tsx - Add toggle and state management
- ./src/styles/theme.css - Add dark theme variables
</output>

<verification>
- [ ] Toggle appears on settings page
- [ ] Clicking toggle switches theme
- [ ] Preference persists after page reload
</verification>
```

**Example 2: Research task**

User: "Research GraphQL vs REST for our mobile app"

Generated prompt (002-research-graphql-vs-rest.md):
```xml
<research_objective>
Compare GraphQL and REST for the mobile app API layer.
This will inform the architecture decision for the upcoming API redesign.
</research_objective>

<scope>
- Focus on mobile client use cases
- Consider current React Native stack
- Evaluate performance, caching, and offline support
</scope>

<deliverables>
Save findings to: ./research/graphql-vs-rest.md

Include:
- Pros/cons comparison table
- Performance considerations for mobile
- Recommendation with rationale
</deliverables>

<evaluation_criteria>
- Is each approach evaluated for mobile-specific concerns?
- Are caching strategies addressed?
- Is the recommendation actionable?
</evaluation_criteria>

<verification>
- [ ] Both approaches evaluated fairly
- [ ] Mobile-specific concerns addressed
- [ ] Clear recommendation provided
</verification>
```
