<objective>
Fix the text/graph dependency mismatch in 000-orchestrator.md and add validation to orchestrator.py that warns when wave descriptions contradict the dependency graph.

The immediate problem: Wave 2 text claims "can parallelize 004-01 and 004-02" but the dependency graph shows 004-02 depends on 004-01. The graph is correct; the text is misleading.
</objective>

<context>
@prompts/phase-completion/000-orchestrator.md - Contains the dependency graph and wave descriptions
@scripts/orchestrator.py - Parses orchestrator files and calculates execution waves

The orchestrator.py already parses:
- Dependency graph via `parse_dependency_graph()`
- Wave descriptions via `parse_execution_order()`
- Both are available for comparison
</context>

<requirements>
1. Update 000-orchestrator.md:
   - Fix Wave 2 description to accurately reflect that 004-02 depends on 004-01
   - Remove "(parallel with 004-01)" from 004-02 line item
   - Keep all other content unchanged

2. Add validation to orchestrator.py:
   - Create `validate_text_graph_consistency()` function
   - Compare wave text claims against actual dependency graph
   - Detect when text says prompts are "parallel" but graph shows dependency
   - Emit warnings to stderr (not stdout, which has JSON output)
   - Call validation from `parse_orchestrator()` before returning result
</requirements>

<implementation>
For the text fix:
- Line 62: Change "(can parallelize 004-01 and 004-02)" to "(sequential, 004-02 depends on 004-01)"
- Line 65: Change "parallel with 004-01" to "after 004-01"

For the validation:
- Parse wave text for parallelization claims (look for "parallel", "parallelize", etc.)
- Cross-reference against the dependency graph
- If wave text says A and B are parallel but graph shows A -> B or B -> A, emit warning
- Use sys.stderr.write() for warnings to avoid polluting JSON output
- Return list of warnings from validation function for potential programmatic use
</implementation>

<output>
Modify:
- ./prompts/phase-completion/000-orchestrator.md - Fix misleading wave descriptions
- ./scripts/orchestrator.py - Add validate_text_graph_consistency() and call it
</output>

<verification>
Before declaring complete:
- [ ] 000-orchestrator.md Wave 2 text no longer claims parallelization
- [ ] orchestrator.py has validate_text_graph_consistency() function
- [ ] Running `python scripts/orchestrator.py prompts/phase-completion/000-orchestrator.md --prompts-dir prompts` produces no warnings
- [ ] Test validation by temporarily adding "parallel 003-01 and 003-02" text and confirming warning appears
</verification>
</content>
