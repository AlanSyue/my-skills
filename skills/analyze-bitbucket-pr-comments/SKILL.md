---
name: analyze-bitbucket-pr-comments
description: Fetch Bitbucket PR review comments, analyze whether code changes are needed, and reply after user confirmation.
---

# Analyze Bitbucket PR Comments

## What this skill does
Given a Bitbucket PR URL, this skill fetches all open review comments, analyzes each one to determine if code changes are needed or a reply is sufficient, presents a summary for user confirmation, then executes the approved actions.

## Inputs
- Bitbucket PR URL (e.g. https://bitbucket.example.com/projects/PROJ/repos/my-repo/pull-requests/123)

## Requirements
- Local environment variables (in `$HOME/my-skills/.env`):
  - ATLASSIAN_BASE_URL (e.g. https://bitbucket.example.com)
  - ATLASSIAN_EMAIL
  - ATLASSIAN_API_TOKEN
- Script: `scripts/analyze_bitbucket_pr_comments.sh` must be executable.
- Script: `scripts/reply_bitbucket_pr_comment.sh` must be executable.

## Steps
1. Parse the PR URL and execute `$HOME/my-skills/scripts/analyze_bitbucket_pr_comments.sh <pr-url>` to fetch PR info and comments.
   - The script automatically filters out RESOLVED comments and comments where the last reply is from yourself (ATLASSIAN_EMAIL).
   - If the returned comments array is empty, inform the user "No open comments require attention" and stop.
2. For each comment that has an `anchor` (file-level comment), read the relevant source file at `anchor.path` around `anchor.line` to understand the context.
3. Analyze each comment and classify it:
   - **Needs fix**: The reviewer's feedback requires a code change. Provide a concrete implementation plan (affected files, what to change).
   - **Reply only**: The comment can be addressed with a reply (explanation, acknowledgment, or disagreement with justification). Draft the reply text.
4. Present the analysis as a table:

   | # | Comment (author) | File:Line | Classification | Action |
   |---|------------------|-----------|----------------|--------|
   | 1 | "..." (Reviewer) | src/foo.ts:42 | Needs fix | [implementation plan summary] |
   | 2 | "..." (Reviewer) | — | Reply only | [draft reply] |

5. **STOP and wait for user confirmation.** Do NOT proceed until the user explicitly approves. The user may modify classifications, edit reply text, or skip specific comments.
6. After confirmation, execute approved actions:
   - For "Needs fix" items: implement the code changes.
   - For every comment (both types): execute `$HOME/my-skills/scripts/reply_bitbucket_pr_comment.sh <pr-url> <comment-id> "<reply-text>"` to post the reply on Bitbucket.
7. Output an execution summary listing what was changed and which replies were posted.

## Constraints
- **Step 5 is mandatory**: Never execute code changes or post replies without explicit user confirmation.
- Reply text should be professional and concise.
- When implementing fixes, make minimal, focused changes that address only the reviewer's feedback.
- If a comment references code outside the current repository, note it as out of scope.

## Example
/analyze-bitbucket-pr-comments https://bitbucket.example.com/projects/PROJ/repos/my-repo/pull-requests/123
