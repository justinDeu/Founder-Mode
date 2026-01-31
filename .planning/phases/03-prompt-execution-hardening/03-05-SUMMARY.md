---
phase: 03-prompt-execution-hardening
plan: 05
subsystem: executor
tags: [verification, two-stage, loop, quality]
dependency-graph:
  requires: [03-01, 03-02]
  provides: [two-stage-verification]
  affects: []
tech-stack:
  added: []
  patterns: [staged-verification, multi-pass-validation]
key-files:
  created: []
  modified:
    - main/scripts/executor.py
    - main/commands/run-prompt.md
decisions:
  - Two-stage verification is opt-in via --two-stage flag
  - Requires --loop flag to be enabled
  - Stage 2 only runs after Stage 1 passes
  - stages_completed array tracks progress in result JSON
metrics:
  duration: 2.5 min
  completed: 2026-01-31
---

# Phase 3 Plan 5: Two-Stage Verification Summary

Two-stage verification for executor.py: Stage 1 checks spec compliance, Stage 2 checks code quality. Stage 2 only runs if Stage 1 passes.

## What Was Built

### Two-Stage Verification System

Added optional `--two-stage` flag to executor.py that enables two-pass verification:

1. **Stage 1: Spec Compliance**
   - Verifies output matches requirements
   - Checks all features implemented
   - Confirms tests pass
   - Marker: `SPEC_COMPLIANCE_VERIFIED`

2. **Stage 2: Code Quality**
   - Only runs after Stage 1 passes
   - Checks code organization
   - Verifies error handling
   - Looks for obvious improvements
   - Marker: `QUALITY_VERIFIED`

### Implementation Details

**New verification patterns:**
```python
STAGE1_COMPLETE = "SPEC_COMPLIANCE_VERIFIED"
STAGE2_COMPLETE = "QUALITY_VERIFIED"
TWO_STAGE_PATTERN = re.compile(...)
```

**New function:**
```python
def check_two_stage_verification(log_path: Path) -> tuple[str, str | None]:
    """Returns stage status and optional retry reason."""
```

**Result JSON additions:**
```json
{
  "two_stage": true,
  "stages_completed": ["spec", "quality"]
}
```

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 78edda4 | feat | Add two-stage verification markers |
| ba36bd6 | feat | Add --two-stage flag to executor |
| 28d4ea3 | docs | Document --two-stage flag in run-prompt.md |

## Files Modified

- `main/scripts/executor.py` - Added two-stage verification markers, check function, and --two-stage flag with loop logic
- `main/commands/run-prompt.md` - Added Flags section documenting --two-stage usage

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Two-stage requires --loop | Two-stage verification implies iteration capability |
| stages_completed as array | Allows tracking partial progress (["spec"] vs ["spec", "quality"]) |
| Refactored loop into three modes | Clear separation: two-stage, standard loop, single exec |

## Verification Results

All tests pass:
- Stage 1 marker detection works
- Stage 2 marker detection works
- Stage 1 retry detection works
- Stage 2 retry detection works (distinguishes from Stage 1 retry by checking for STAGE1_COMPLETE in content)

## Next Phase Readiness

This plan completes the optional two-stage verification feature. The executor now supports:
- Background execution
- Verification loop with retry
- State persistence
- Per-iteration logging
- Two-stage verification

No blockers for future work.
