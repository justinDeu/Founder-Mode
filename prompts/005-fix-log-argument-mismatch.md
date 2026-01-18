<objective>
Fix the mismatch between run-prompt.md documentation and executor.py implementation for the --log argument.

The documentation says --log is optional with auto-generation, but executor.py requires it as mandatory.
This causes execution failures when users follow the documented behavior.
</objective>

<context>
@commands/run-prompt.md - Documentation says `--log` has default "auto" (line 27)
@scripts/executor.py - Implementation uses `required=True` for --log (line 197)

The documentation also shows executor calls without --log in lines 290-294:
```bash
python3 "$EXECUTOR" \
  --prompt "$prompt_file" \
  --cwd "$cwd" \
  --model "$model" \
  --run
```

This would fail because executor.py requires --log.
</context>

<requirements>
Update executor.py to make --log optional with auto-generation:

1. Change `--log` from `required=True` to `required=False` with `default=None`
2. Add auto-generation logic when --log is not provided:
   - Generate log path as: `{cwd}/.founder-mode/logs/{prompt_basename}_{timestamp}.log`
   - Create parent directories if needed
3. Ensure the auto-generated path is included in JSON output
</requirements>

<implementation>
In scripts/executor.py:

1. Change argparse definition:
   ```python
   parser.add_argument("--log", help="Path to log file (auto-generated if not provided)")
   ```

2. Add auto-generation after parsing args:
   ```python
   if args.log:
       log_path = Path(args.log)
   else:
       timestamp = time.strftime('%Y%m%d-%H%M%S')
       prompt_basename = Path(args.prompt).stem
       log_path = Path(args.cwd) / ".founder-mode" / "logs" / f"{prompt_basename}_{timestamp}.log"
   ```

3. Remove the existing `log_path = Path(args.log)` line and replace with the logic above
</implementation>

<output>
Modify:
- ./scripts/executor.py - Make --log optional with auto-generation
</output>

<verification>
Before declaring complete:
- [ ] `python3 scripts/executor.py --help` shows --log without [required]
- [ ] Running without --log auto-generates a log path
- [ ] JSON output includes the auto-generated log_path
- [ ] Existing behavior with explicit --log still works
</verification>
