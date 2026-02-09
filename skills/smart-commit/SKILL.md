---
name: smart-commit
description: Generate a conventional commit message from the current branch name and staged diff, then commit. Use when the user wants to commit staged changes with a well-formatted message.
---

# Smart Commit

Generate a git commit command using Conventional Commits format, derived from the branch name and staged diff.

## Steps

1. Run `git branch --show-current` to get the current branch name.
2. Run `git diff --staged` to get the staged changes.
3. If there are no staged changes, inform the user and stop.
4. Extract the ticket number from the branch name (e.g. `feature/CORE-101-login` → `CORE-101`).
5. Analyze the diff to determine the commit type and write a concise description.
6. Generate and execute a `git commit` command using multiple `-m` flags:
   - First `-m`: subject line (<=72 chars) in format `<type>[optional scope]: <ticket-num>,<description>`
   - Second `-m`: optional body with brief explanation of the changes.

## Commit Types

- `fix`: patches a bug
- `feat`: introduces a new feature
- `BREAKING CHANGE`: introduces a breaking API change (use `!` or footer)
- Others: `build`, `chore`, `ci`, `docs`, `style`, `refactor`, `perf`, `test`

## Rules

- Subject line MUST be <= 72 characters.
- If no ticket number is found in the branch name, omit it from the subject.
- Avoid overly verbose descriptions or unnecessary details.
- If `$ARGUMENTS` is provided, use it as additional context for the commit message.

## Example

Branch: `feature/CORE-101-login`

Diff:
```diff
diff --git a/src/auth.ts b/src/auth.ts
- console.log("debug");
+ if (!user) throw new Error("Unauthorized");
```

Output:
```bash
git commit -m "feat(auth): CORE-101,add unauthorized error handling" -m "Implemented user validation check and removed debug logs."
```
