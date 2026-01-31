---
name: fm:commit
description: Create conventional commits with optional doc updates
argument-hint: [--amend] [--no-verify]
allowed-tools:
  - Read
  - Edit
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# Commit

Create a git commit following the Conventional Commits specification.

## Arguments

Parse from `$ARGUMENTS`:

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--amend` | flag | false | Amend the previous commit |
| `--no-verify` | flag | false | Skip pre-commit hooks |

## Conventional Commits Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types

| Type | When to Use |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no code change |
| `refactor` | Code change that neither fixes nor adds |
| `perf` | Performance improvement |
| `test` | Adding or correcting tests |
| `build` | Build system or dependencies |
| `ci` | CI configuration |
| `chore` | Other changes (tooling, config) |

### Breaking Changes

Use `!` after type/scope for breaking changes:
```
feat!: remove deprecated API
feat(api)!: change response format
```

Or add footer:
```
BREAKING CHANGE: endpoint now returns JSON instead of XML
```

## Process

### Step 1: Analyze Changes

```bash
# Get staged and unstaged changes
git status --porcelain

# Get diff of staged changes
git diff --cached --stat

# Get detailed diff for analysis
git diff --cached
```

### Step 2: Determine Commit Type

Based on the changes:
- New files with features: `feat`
- Modified files fixing issues: `fix`
- Only `.md` files changed: `docs`
- Test files only: `test`
- Formatting/whitespace: `style`
- Restructuring without behavior change: `refactor`

If unclear, ask:

```
AskUserQuestion(
  questions: [{
    question: "What type of change is this?",
    header: "Commit Type",
    options: [
      { label: "feat", description: "New feature" },
      { label: "fix", description: "Bug fix" },
      { label: "refactor", description: "Code restructuring" },
      { label: "docs", description: "Documentation only" }
    ]
  }]
)
```

### Step 3: Determine Scope (Optional)

Scope is optional but helpful for larger projects. Derive from:
- Directory name: `feat(api): ...`
- Component name: `fix(auth): ...`
- Feature area: `refactor(payments): ...`

### Step 4: Write Description

Keep the description:
- Under 50 characters
- Imperative mood ("add" not "added")
- No period at end
- Lowercase first letter

Good: `feat: add user authentication`
Bad: `feat: Added user authentication.`

### Step 5: Decide on Body

Add body only when:
- The "why" is not obvious from the description
- There are important implementation details
- Breaking changes need explanation

Skip body for:
- Simple, obvious changes
- Single-file fixes
- Documentation updates

### Step 6: Check for Documentation Updates

If the commit includes:
- New feature: Check if README needs update
- API change: Check if API docs need update
- Config change: Check if setup docs need update
- Breaking change: Ensure migration notes exist

```bash
# Find potentially affected docs
grep -r "related_feature_name" README.md docs/ --include="*.md"
```

If docs need updating, prompt:

```
AskUserQuestion(
  questions: [{
    question: "This change may require documentation updates. Update docs now?",
    header: "Docs",
    options: [
      { label: "Yes", description: "Update docs before committing" },
      { label: "No", description: "Commit without doc changes" },
      { label: "Separate commit", description: "Create docs commit after" }
    ]
  }]
)
```

### Step 7: Stage and Commit

```bash
# Stage all changes (or specific files)
git add <files>

# Commit with message
git commit -m "<type>[scope]: <description>" [-m "<body>"]
```

For multi-line body, use heredoc:

```bash
git commit -m "$(cat <<'EOF'
feat(auth): add OAuth2 support

Implements OAuth2 flow with Google and GitHub providers.
Adds token refresh handling and session management.

Closes #123
EOF
)"
```

### Step 8: Post-Commit Check

After committing:
1. Verify commit was created: `git log -1 --oneline`
2. If tests are configured, suggest running them
3. Show next steps (push, create PR, etc.)

## Examples

### Simple Feature
```
feat: add dark mode toggle
```

### Bug Fix with Scope
```
fix(auth): prevent session timeout on refresh
```

### Breaking Change
```
feat(api)!: change response format to JSON

BREAKING CHANGE: All API responses now return JSON instead of XML.
Clients must update their parsers accordingly.

Migration guide: docs/migration-v2.md
```

### Documentation Update
```
docs: add API authentication guide
```

### With Issue Reference
```
fix(payments): handle declined card gracefully

Catches PaymentDeclined exception and shows user-friendly message
instead of generic error.

Closes #456
```

## Error Handling

**No staged changes:**
```
No changes staged for commit.

Stage changes with:
  git add <file>       # Stage specific file
  git add -p           # Stage interactively
  git add .            # Stage all (use with caution)
```

**Pre-commit hook fails:**
```
Pre-commit hook failed. Common fixes:
1. Fix linting errors shown above
2. Run formatter: npm run format
3. Skip hooks (not recommended): --no-verify
```

## Success Output

```
Created commit: abc1234

  feat(auth): add OAuth2 support

Files changed:
  - src/auth/oauth.ts (new)
  - src/auth/index.ts (modified)
  - tests/auth/oauth.test.ts (new)

Next steps:
  git push              # Push to remote
  gh pr create          # Create pull request
```
