# Workflow XML Schema

XML format for defining prompt execution workflows with dependency management.

## Quick Example

```xml
<workflow id="my-feature" base="feature-branch" branch="feature-complete">
  <on_complete create_pr="true" delete_worktree="false" />

  <prompt id="foundation">
    <path>prompts/001-foundation.md</path>
  </prompt>

  <prompt id="core-logic">
    <path>prompts/002-core-logic.md</path>
    <after>foundation</after>
  </prompt>

  <prompt id="integration">
    <path>prompts/003-integration.md</path>
    <after>foundation</after>
    <after>core-logic</after>
  </prompt>
</workflow>
```

## Elements

### `<workflow>`

Root element. A file can contain multiple `<workflow>` elements.

**Attributes:**
- `id` (required) - Unique identifier for this workflow
- `base` (required) - Base branch to create worktrees from
- `branch` (required) - Target branch for the completed work

### `<on_complete>`

Child of `<workflow>`. Defines post-execution behavior.

**Attributes:**
- `create_pr` - If "true", create a pull request on completion
- `merge_to` - Branch to merge into on completion (mutually exclusive with `create_pr`)
- `delete_worktree` - If "true", delete the worktree after completion

`create_pr` and `merge_to` are mutually exclusive. Use one or neither.

### `<prompt>`

Child of `<workflow>`. Defines a single prompt to execute.

**Attributes:**
- `id` (required) - Unique identifier referenced by `<after>` elements

**Children:**
- `<path>` (required, exactly one) - Relative path to the prompt .md file
- `<after>` (zero or more) - ID of a prompt that must complete before this one runs
- `<model>` (zero or one) - Model override for this prompt (e.g., `claude-zai`, `codex`)

Each `<after>` element contains the `id` of exactly one dependency. Use multiple `<after>` elements for multiple dependencies.

## DAG Rules

The prompts in a workflow form a directed acyclic graph (DAG). The following rules apply:

### Single Sink

Every workflow must have exactly one sink node: a prompt that no other prompt depends on. This is the final prompt that runs after all others complete. All execution paths must converge at this sink.

**Valid** - single sink (verification):
```xml
<prompt id="a"><path>a.md</path></prompt>
<prompt id="b"><path>b.md</path><after>a</after></prompt>
<prompt id="c"><path>c.md</path><after>a</after></prompt>
<prompt id="sink"><path>sink.md</path><after>b</after><after>c</after></prompt>
```

**Invalid** - two sinks (b and c have nothing depending on them):
```xml
<prompt id="a"><path>a.md</path></prompt>
<prompt id="b"><path>b.md</path><after>a</after></prompt>
<prompt id="c"><path>c.md</path><after>a</after></prompt>
```

### No Cycles

The dependency graph must not contain cycles. If A depends on B and B depends on A, the workflow is invalid.

### All References Valid

Every `<after>` value must match the `id` of another `<prompt>` in the same workflow.

### All Paths Reach Sink

Every prompt must have a path (through dependents) that reaches the sink node. No orphaned subgraphs.

## Validation Checklist

Before executing a workflow, verify:

1. Every `<prompt>` has a unique `id` attribute
2. Every `<prompt>` has exactly one `<path>` child
3. Every `<after>` value matches an existing prompt `id`
4. Every `<path>` points to a file that exists on disk
5. The graph has no cycles (topological sort succeeds)
6. There is exactly one sink node (one prompt with no dependents)
7. All prompts are reachable from at least one source (prompt with no dependencies)
8. `create_pr` and `merge_to` are not both set on `<on_complete>`

## Wave Computation

Waves are computed from the DAG using topological layering:

- **Wave 1**: All prompts with zero dependencies (source nodes)
- **Wave N**: All prompts whose dependencies are entirely in waves 1 through N-1

Prompts within the same wave execute in parallel. Waves execute sequentially.

## Multiple Workflows Per File

A file can define multiple workflows. Select one by ID when invoking:

```
/fm:orchestrate prompts/workflows.xml my-workflow-id
```

If a file has only one workflow, the ID argument is optional.

## Full Schema Summary

```
<workflow id="..." base="..." branch="...">
  <on_complete create_pr="..." merge_to="..." delete_worktree="..." />

  <prompt id="...">
    <path>...</path>
    <after>...</after>    <!-- zero or more -->
    <model>...</model>    <!-- zero or one -->
  </prompt>

  <!-- more <prompt> elements -->
</workflow>
```
