---
name: commit-conventions
description: Conventional commit formatting guidelines. Apply when creating commits, writing commit messages, staging changes, or finalizing work.
user-invocable: false
---

# Conventional Commits

Follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification when creating commits.

## Message Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

## Commit Types

| Type | Use When |
|------|----------|
| `feat` | Adding new functionality |
| `fix` | Fixing a bug |
| `docs` | Documentation only |
| `style` | Formatting, whitespace (no logic change) |
| `refactor` | Restructuring code without behavior change |
| `perf` | Performance improvement |
| `test` | Adding or updating tests |
| `build` | Build system or dependencies |
| `ci` | CI/CD configuration |
| `chore` | Maintenance, config, other |

## Description Guidelines

- Use imperative mood: "add feature" not "added feature"
- Keep under 72 characters
- Be specific but concise
- No period at the end

## When to Include Body

**Include body for:**
- Multiple distinct changes in one commit
- Complex implementation needing explanation
- Breaking changes requiring migration notes
- Performance optimizations needing context

**Skip body for:**
- Simple, obvious bug fixes
- Single-file changes
- Typo corrections
- Minor style fixes

Body format when needed:
```
- Change one description
- Change two description
- Change three description
```

## Breaking Changes

For breaking changes:
1. Add `!` after type: `feat!:` or `feat(scope)!:`
2. Add footer: `BREAKING CHANGE: description of what breaks and how to migrate`

## Issue References

When closing issues, add footer:
```
Fixes #123
Closes #456
```

## Staging Changes

Never use `git add -A` or `git add .` without explicit confirmation. Stage specific files:
```bash
git add <file1> <file2>
```

## Examples

Simple feature:
```
feat: add user profile page
```

Bug fix with issue reference:
```
fix: resolve login token expiration

Fixes #42
```

Complex feature:
```
feat: implement OAuth2 authentication

- Add Google OAuth provider
- Add GitHub OAuth provider
- Implement token refresh mechanism
```

Breaking change:
```
feat!: migrate to JWT authentication

- Replace session-based auth with JWT
- Update all protected routes

BREAKING CHANGE: Removed session support. Clients must use JWT tokens.
```
