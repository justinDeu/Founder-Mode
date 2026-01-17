# Phase 1: Foundation - Context

**Gathered:** 2026-01-16
**Status:** Ready for research

<vision>
## How This Should Work

Skills and configuration are a coupled system. Configuration needs to be consumable by skills, skills need to understand configuration — they go hand in hand.

The foundation should feel Claude Code native. Use CLAUDE.md patterns and settings.json conventions rather than introducing new config formats. Work with the existing Claude Code ecosystem, not against it.

Sub-agent handling is critical. Daplug solved the ralph-wiggum problem (sub-agents not inheriting skill context) with executor.py. Founder-mode needs to understand that approach and why it works before deciding its own solution.

Self-bootstrapping is the goal. Get founder-mode functional enough to use it on itself as early as possible. Phase 1 includes a minimal /run-prompt as proof that the foundation actually works.

</vision>

<essential>
## What Must Be Nailed

- **Configuration flexibility** — Users can override defaults, paths are configurable, nothing hardcoded
- **Skill discoverability** — Skills are easy to find, invoke, and understand what they do
- **Sub-agent reliability** — When skills spawn agents via Task tool, those agents work correctly every time

All three are essential. No shortcuts on foundation work.

</essential>

<boundaries>
## What's Out of Scope

- External integrations (GitHub, Jira) — that's Phase 4
- Full-featured commands beyond the minimal proof-of-concept /run-prompt
- Parallel workflow orchestration — that's Phase 5

</boundaries>

<specifics>
## Specific Ideas

- Configuration should be Claude Code native — CLAUDE.md patterns, settings.json conventions
- Research daplug's executor.py to understand the ralph-wiggum solution and its rationale
- Include minimal /run-prompt to prove foundation works (not just deliver building blocks)

</specifics>

<notes>
## Additional Context

The roadmap lists these deliverables for Phase 1:
- Skill file structure and naming conventions
- Configuration system (flexible, user-controllable)
- Worktree management with configurable locations
- Environment setup abstraction (language-agnostic)
- Progress display utilities

Research phase should investigate daplug's approach to ralph-wiggum handling before planning begins.

</notes>

---

*Phase: 01-foundation*
*Context gathered: 2026-01-16*
