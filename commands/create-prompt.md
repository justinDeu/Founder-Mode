---
name: fm:create-prompt
description: Create optimized prompts for execution by any model
argument-hint: [task description] [--folder path] [--depends refs]
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
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
| `--depends` | option | none | Dependencies (prompt files, issue refs, or descriptions) |

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

### Step 2: Gather Concrete Context

Before generating the prompt, read relevant files to extract specific details:

1. Use Glob to find target files
2. Use Grep to locate specific code sections
3. Use Read to get snippets with line numbers

For each file that needs modification, gather:
- Exact file path
- Line numbers where changes go
- Current code snippet
- Patterns to follow from existing code

Include this in the generated prompt's `<context>` and `<requirements>` sections.

### Step 3: Template Selection

Based on task type, select the appropriate template.

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

### Step 4: Prompt Naming

Determine the prompt filename:

1. **Check config** for `prompt_naming` in `founder_mode_config`
2. **Infer from context**:
   - GitHub issue/PR context: `gh-{number}-{slug}.md`
   - Jira ticket context: `{project}-{number}-{slug}.md`
   - General prompts: `{NNN}-{slug}.md` (find next available number)

```bash
# List existing prompts to find next number if needed
ls -1 ./prompts/*.md 2>/dev/null | grep -oE '^[0-9]+' | sort -n | tail -1
```

Slug format: lowercase, hyphen-separated, max 5 words

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

Key files:
- `[path/to/file.ext]` - [description] (~line N-M)

@[path/to/file.ext]
</context>

<requirements>
## 1. [First change]

[Description with specific location]

```[language]
# Current code (around line N):
[existing code snippet]

# Change to:
[new code snippet]
```

## 2. [Second change]

[Additional requirements with code examples]
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
```bash
# [Test description]
[actual command to run]
# Expected: [expected output]
```

Before declaring complete:
- [ ] [Build/test command passes]
- [ ] [Specific behavior works as expected]
</verification>

<completion_protocol>
When ALL tasks are complete and verified, output this EXACT line as your final output:

<verification>VERIFICATION_COMPLETE</verification>

If anything is incomplete or failing, output this EXACT line with your reason:

<verification>NEEDS_RETRY: [reason]</verification>
</completion_protocol>
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
[Where to save findings - ask user or infer from project structure]
</deliverables>

<evaluation_criteria>
[How to assess quality/relevance of sources]
[Key questions that must be answered]
</evaluation_criteria>

<verification>
Before completing, verify:
- [ ] All key questions are answered
- [ ] Sources are credible and relevant
- [ ] Output file exists at specified path
</verification>

<completion_protocol>
When ALL research is complete, output this EXACT line as your final output:

<verification>VERIFICATION_COMPLETE</verification>

If incomplete, output:

<verification>NEEDS_RETRY: [reason]</verification>
</completion_protocol>
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
[Where to save output - ask user or infer from project structure]
</output_format>

<verification>
[How to validate the analysis is complete and accurate]
- [ ] Output file exists at specified path
</verification>

<completion_protocol>
When ALL analysis is complete, output this EXACT line as your final output:

<verification>VERIFICATION_COMPLETE</verification>

If incomplete, output:

<verification>NEEDS_RETRY: [reason]</verification>
</completion_protocol>
```
</analysis_template>

## Common Elements for All Templates

Every generated prompt should include:

1. **Objective with WHY**: Always explain the purpose and goal
2. **Context with @references**: Point to relevant files when applicable
3. **Verification section**: Clear success criteria
4. **Relative paths**: Use `./` for all file outputs

## Intelligence Rules

1. **Gather Context First**: Read relevant files before generating. Extract line numbers and code snippets.
2. **Be Specific**: "around line 478-496" beats "in the config section"
3. **Show Code**: Include current → desired code as snippets in requirements
4. **Testable Criteria**: Every verification item must be observable or runnable with a command
5. **Always Include Completion Protocol**: Every prompt must include the `<completion_protocol>` section verbatim
