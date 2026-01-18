<objective>
Document Z.AI provider differences and add validation to prevent silent API failures.

The MODEL_CONFIG for "opencode-zai" originally used `zai/glm-4.7` but the correct provider is `zai-coding-plan/glm-4.7`. Different Z.AI endpoints have different API access requirements. Using the wrong provider causes silent failures where requests appear to succeed but produce no useful output.
</objective>

<context>
@scripts/executor.py - MODEL_CONFIG section with zai provider configurations

Current state:
- `opencode-zai` now correctly uses `zai-coding-plan/glm-4.7`
- No documentation explains why this provider vs `zai/glm-4.7`
- No validation or warning when users specify custom zai providers
</context>

<requirements>
1. **Document Z.AI provider differences** in code comments:
   - `zai/glm-4.7` - Base provider, may have restricted API access
   - `zai-coding-plan/glm-4.7` - Coding-specific endpoint with proper API access
   - Explain why the distinction matters (silent failures vs working requests)

2. **Add provider validation** (optional enhancement):
   - Warn if user specifies a zai provider that differs from known-working ones
   - Log which provider is being used for debugging
</requirements>

<implementation>
1. Add documentation block above or within MODEL_CONFIG explaining:
   - Z.AI provider naming conventions
   - Known-working vs problematic providers
   - How to troubleshoot silent failures

2. Consider adding a validation function:
```python
ZAI_KNOWN_WORKING_PROVIDERS = ["zai-coding-plan/glm-4.7"]
ZAI_PROBLEMATIC_PROVIDERS = ["zai/glm-4.7"]

def validate_zai_provider(provider: str) -> None:
    """Warn if using a problematic Z.AI provider."""
    if provider in ZAI_PROBLEMATIC_PROVIDERS:
        print(f"Warning: {provider} may have API access issues. "
              f"Consider using one of: {ZAI_KNOWN_WORKING_PROVIDERS}",
              file=sys.stderr)
```

3. Do not break existing functionality - this is additive documentation and optional warnings
</implementation>

<output>
Modify:
- ./scripts/executor.py - Add provider documentation and optional validation

Do NOT create separate documentation files. Keep it in-code for discoverability.
</output>

<verification>
Before declaring complete:
- [ ] Code comments explain zai vs zai-coding-plan difference
- [ ] Reason for choosing zai-coding-plan is documented (API access)
- [ ] No syntax errors: `python3 -m py_compile scripts/executor.py`
- [ ] Existing model configurations unchanged
- [ ] If validation added, it only warns (does not block execution)
</verification>
</content>
</invoke>