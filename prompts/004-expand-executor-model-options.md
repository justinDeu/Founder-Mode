<objective>
Expand executor.py model options to support additional CLI + model pairings:

1. **opencode CLI** with zai models (GLM-4.7) or codex models (gpt-5.2-codex)
2. **codex CLI** with codex models (existing, may need model variants)
3. **claude code CLI** with zai backend (environment variable override)

This enables users to choose their preferred CLI tool independent of the underlying model provider.
</objective>

<context>
@scripts/executor.py - Current minimal executor with 3 models
@commands/run-prompt.md - Command spec with model reference table

Current MODEL_COMMANDS structure:
```python
MODEL_COMMANDS = {
    "codex": lambda prompt: (["codex", "exec", "--full-auto", "-"], prompt, True),
    "gemini": lambda prompt: (["gemini", "-y", "-p", prompt], None, False),
    "zai": lambda prompt: (["zai", "-p", prompt], None, False),
}
```
</context>

<requirements>
**New model entries to add:**

| Entry Key | CLI Tool | Model/Backend | Invocation Pattern |
|-----------|----------|---------------|-------------------|
| `opencode` | opencode | default (zen) | `opencode run "prompt"` |
| `opencode-zai` | opencode | zai/GLM-4.7 | `opencode --model zai/glm-4.7 run "prompt"` |
| `opencode-codex` | opencode | gpt-5.2-codex | `opencode --model openai/gpt-5.2-codex run "prompt"` |
| `claude-zai` | claude | zai backend | Requires env vars, then `claude -p "prompt" --dangerously-skip-permissions` |

**CLI invocation patterns (from docs):**

- **opencode**: `opencode run "prompt"` with optional `--model provider/model` flag
- **codex**: `codex exec --full-auto -` (stdin mode) with optional `--model` flag
- **claude with zai**: Set `ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic` and `ANTHROPIC_AUTH_TOKEN` env vars before invoking claude

**Considerations:**

1. For `claude-zai`, the executor must set environment variables before spawning the subprocess
2. The opencode CLI uses positional prompt in `run` subcommand, not stdin
3. Model flags use `provider/model` format for opencode (e.g., `zai/glm-4.7`, `openai/gpt-5.2-codex`)
</requirements>

<implementation>
1. Refactor MODEL_COMMANDS to support:
   - Environment variable injection (for claude-zai)
   - Different stdin modes (stdin vs positional arg)
   - Model specification flags

2. Consider restructuring to a dict with explicit fields:
```python
MODEL_CONFIG = {
    "opencode": {
        "command": ["opencode", "run"],
        "stdin_mode": "positional",  # prompt as positional arg
        "env": {},
    },
    "opencode-zai": {
        "command": ["opencode", "--model", "zai/glm-4.7", "run"],
        "stdin_mode": "positional",
        "env": {},
    },
    "claude-zai": {
        "command": ["claude", "-p"],
        "stdin_mode": "positional",
        "env": {
            "ANTHROPIC_BASE_URL": "https://api.z.ai/api/anthropic",
            # API key must come from user's environment
        },
    },
}
```

3. Update run_cli() to handle:
   - Environment variable merging
   - Positional argument placement

4. Keep backward compatibility with existing codex, gemini, zai entries
</implementation>

<output>
Modify:
- ./scripts/executor.py - Add new model configurations
- ./commands/run-prompt.md - Update Model Reference table

Do NOT create new files.
</output>

<verification>
Before declaring complete:
- [ ] All existing models (codex, gemini, zai) still work
- [ ] New opencode variants added: opencode, opencode-zai, opencode-codex
- [ ] claude-zai entry added with env var support
- [ ] run_cli() handles env vars and different stdin modes
- [ ] Model Reference table in run-prompt.md updated
- [ ] Code has no syntax errors: `python3 -m py_compile scripts/executor.py`
</verification>
