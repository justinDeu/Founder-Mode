# Phase 2: Prompt Workflow - Context

**Gathered:** 2026-01-16
**Status:** Ready for research

<vision>
## How This Should Work

/create-prompt works like daplug's: Claude asks clarifying questions to understand intent, generates a well-structured prompt, saves it to a file. No reinvention needed.

/run-prompt (building on Phase 1's foundation) should not overwhelm users with options when they just want to run a quick one-off prompt. Simple case = simple experience. "Just run it in Claude" should be the default path with zero friction. The complex options (worktrees, model selection, loops) exist but don't get in the way.

Background execution spawns read-only log watcher agents like daplug's approach, but with passive + notify behavior. Fire the prompt, get notified when done or failed. Don't spam updates unless something goes wrong.

</vision>

<essential>
## What Must Be Nailed

- **Simple case is simple** - `/run-prompt prompts/fix-bug.md` runs immediately in Claude. No model menus. No worktree questions. No decision fatigue.
- **Create-prompt generates useful prompts** - Like daplug's wizard: clarify intent, structure properly, save ready-to-run
- **Background monitors work reliably** - Spawn, watch, notify on completion or failure

</essential>

<boundaries>
## What's Out of Scope

- External integrations (GitHub, Jira) - that's Phase 4
- Project management (roadmaps, phases, plans) - that's Phase 3
- Full parallel orchestration is Phase 5, but basic parallel execution of multiple prompts may be included here if natural

</boundaries>

<specifics>
## Specific Ideas

- Default model is Claude, runs inline, zero questions asked
- Options like --worktree, --model, --loop only matter when explicitly requested
- Monitor agents use daplug's read-only log watcher pattern
- Notification on completion rather than periodic progress spam
- /create-prompt follows daplug's approach: clarifying questions, detect prompt type, generate structured XML

</specifics>

<notes>
## Additional Context

Phase 1 already delivered:
- Basic /run-prompt command with multi-model support
- executor.py for non-Claude models
- Configuration system via CLAUDE.md

Phase 2 builds on this foundation, not replaces it. The key addition is /create-prompt and refinement of the execution experience to reduce decision fatigue.

Parallel workflow orchestration (coordinating multiple prompts running simultaneously with shared state management) is Phase 5 territory. Phase 2 may include basic "run these 3 prompts in parallel" if it falls out naturally, but sophisticated orchestration is deferred.

</notes>

---

*Phase: 02-prompt-workflow*
*Context gathered: 2026-01-16*
