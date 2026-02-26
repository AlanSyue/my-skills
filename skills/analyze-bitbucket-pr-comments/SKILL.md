---
name: analyze-bitbucket-pr-comments
description: Fetch Bitbucket PR review comments, analyze whether code changes are needed, and reply after user confirmation.
---

# Analyze Bitbucket PR Comments

## What this skill does
Given a Bitbucket PR URL, this skill fetches all open review comments, analyzes each one to determine if code changes are needed or a reply is sufficient, presents a summary for user confirmation, then executes the approved actions.

## Inputs
- Bitbucket PR URL (e.g. https://bitbucket.org/workspace/repo/pull-requests/123)

## Requirements
- Local environment variables (in `$HOME/my-skills/.env`):
  - ATLASSIAN_EMAIL (your Atlassian account email)
  - BITBUCKET_API_TOKEN (Bitbucket App Password with scopes: **Account: Read**, **Pull requests: Read**, **Pull requests: Write**)
  - BITBUCKET_ACCOUNT_ID (optional, your Bitbucket account ID — used as fallback if the token lacks Account: Read scope)
- Script: `scripts/analyze_bitbucket_pr_comments.sh` must be executable.
- Script: `scripts/reply_bitbucket_pr_comment.sh` must be executable.

## Steps
1. Parse the PR URL and execute `$HOME/my-skills/scripts/analyze_bitbucket_pr_comments.sh <pr-url>` to fetch PR info and comments.
   - The script automatically filters out deleted comments, your own top-level comments, and comments where the last reply is from yourself.
   - **If the output contains `"comments": []` but you suspect the self-filtering is not working** (e.g. comments that should be filtered still appear), it likely means the script cannot identify the current user. STOP and ask the user to either:
     1. Add **Account: Read** scope to their Bitbucket App Password, OR
     2. Set `BITBUCKET_ACCOUNT_ID` in `$HOME/my-skills/.env` (can be found from any Bitbucket API response containing their user info)
   - If the returned comments array is empty, inform the user "No open comments require attention" and stop.
2. **Guard check — verify the local repo matches the PR:**
   - **Repo name**: Compare the `repo` field from the script output with the current directory name (or git remote slug). If they don't match, STOP and warn the user they are in the wrong repository.
   - **Branch**: Run `git branch --show-current` and compare with the `source` field. If they don't match, STOP and warn the user to switch to the correct branch first.
   - **Commit**: Run `git rev-parse HEAD` and compare with the `latestCommit` field. If they don't match, warn the user that the local branch is not in sync with the remote PR (may need `git pull` or `git push`). Ask the user whether to continue or abort.
   - Only proceed to the next step after all checks pass or the user explicitly chooses to continue.
3. For each comment that has an `anchor` (file-level comment), read the relevant source file at `anchor.path` around `anchor.line` to understand the context.
4. Analyze each comment and classify it:
   - **Needs fix**: The reviewer's feedback requires a code change. Provide a concrete implementation plan (affected files, what to change).
   - **Reply only**: The comment can be addressed with a reply (explanation, acknowledgment, or disagreement with justification). Draft the reply text.
5. Present the analysis as a table:

   | # | Comment (author) | File:Line | Classification | Action |
   |---|------------------|-----------|----------------|--------|
   | 1 | "..." (Reviewer) | src/foo.ts:42 | Needs fix | [implementation plan summary] |
   | 2 | "..." (Reviewer) | — | Reply only | [draft reply] |

6. **STOP and wait for user confirmation.** Do NOT proceed until the user explicitly approves. The user may modify classifications, edit reply text, or skip specific comments.
7. After confirmation, execute approved actions:
   - For "Needs fix" items: implement the code changes.
   - For every comment (both types): execute `$HOME/my-skills/scripts/reply_bitbucket_pr_comment.sh <pr-url> <comment-id> "<reply-text>"` to post the reply on Bitbucket.
8. Output an execution summary listing what was changed and which replies were posted.

## Constraints
- **Step 2 is mandatory**: Never skip the repo/branch/commit guard check. Code changes on the wrong branch can cause serious issues.
- **Step 6 is mandatory**: Never execute code changes or post replies without explicit user confirmation.
- Reply text should be professional and concise.
- When implementing fixes, make minimal, focused changes that address only the reviewer's feedback.
- If a comment references code outside the current repository, note it as out of scope.

## Example
/analyze-bitbucket-pr-comments https://bitbucket.org/my-workspace/my-repo/pull-requests/123
