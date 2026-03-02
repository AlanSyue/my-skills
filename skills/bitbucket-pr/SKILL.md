---
name: bitbucket-pr
description: Create or update a Bitbucket Cloud pull request with auto-generated title and description from git diff.
---

# Bitbucket PR — Create or Update

## What this skill does
Automatically creates or updates a Bitbucket Cloud pull request. It detects the repo context from git, analyzes the diff to generate a title and description, supports team PR conventions and repo PR templates, and fetches default reviewers.

## Mode detection
- If `$ARGUMENTS` contains a Bitbucket PR URL (matching `bitbucket.org/.*/pull-requests/\d+`) → **Update Mode**
- Otherwise → **Create Mode** (`$ARGUMENTS` may optionally specify a target branch)

## Inputs
- **Create Mode**: optionally a target branch name (e.g. `/bitbucket-pr develop`)
- **Update Mode**: a Bitbucket PR URL (e.g. `/bitbucket-pr https://bitbucket.org/workspace/repo/pull-requests/123`)

## Requirements
- Local environment variables (in `$HOME/my-skills/.env`):
  - `ATLASSIAN_EMAIL` — your Atlassian account email
  - `BITBUCKET_API_TOKEN` — Bitbucket App Password (scopes: **Account: Read**, **Pull requests: Read**, **Pull requests: Write**)
  - `BITBUCKET_PR_SPEC_PATH` (optional) — path or URL to a PR conventions document
- Scripts (must be executable):
  - `$HOME/my-skills/scripts/detect_bitbucket_repo.sh`
  - `$HOME/my-skills/scripts/create_bitbucket_pr.sh`
  - `$HOME/my-skills/scripts/update_bitbucket_pr.sh`

## Create Mode

### Steps
1. **Detect repo context** — Run `$HOME/my-skills/scripts/detect_bitbucket_repo.sh` and capture the JSON output.
   - If the script returns an error, STOP and inform the user.
   - If `branch` equals `defaultBranch` (or `branch` is empty), STOP and warn the user: "You are on the default branch. Please switch to a feature branch first."

2. **Determine target branch** — If `$ARGUMENTS` specifies a branch name (not a URL), use it as the target. Otherwise, ask the user which branch to target, suggesting `defaultBranch` from step 1 as the default.

3. **Check remote push status** — Run `git log origin/<current-branch>..HEAD --oneline 2>/dev/null` to check for unpushed commits.
   - If there are unpushed commits, warn the user and list them. Ask if they want to continue (the PR will not include these commits) or abort to push first.
   - If `origin/<current-branch>` does not exist, warn the user that the branch has not been pushed to remote yet. STOP and ask them to push first.

4. **Get diff** — Run these commands to gather change information:
   - `git log origin/<target>..HEAD --oneline` for commit list
   - `git diff origin/<target>...HEAD` for the full diff
   - If the diff is empty, STOP and inform the user: "No changes found between the current branch and the target branch."

5. **Load PR spec document** (optional) — If `BITBUCKET_PR_SPEC_PATH` is set in the environment:
   - If it starts with `http://` or `https://`, fetch it using WebFetch.
   - Otherwise, read it as a local file path.
   - Use this document as guidelines for formatting the PR title and description.

6. **Detect PR template** — Check for a PR template file in the repository, in this order:
   - `.bitbucket/PULL_REQUEST_TEMPLATE.md`
   - `PULL_REQUEST_TEMPLATE.md`
   - `docs/PULL_REQUEST_TEMPLATE.md`
   - `.github/PULL_REQUEST_TEMPLATE.md`
   - Use the first one found. If none exists, skip this step.

7. **Generate title and description** — Analyze the diff, commit messages, and branch name:
   - **Title**: Extract ticket number from branch name if present (e.g., `feature/PROJ-123-add-login` → `PROJ-123`), combine with a concise summary of changes. Maximum 72 characters.
   - **Description**:
     - If a PR template was found in step 6, fill in the template sections based on the diff analysis.
     - Else if a PR spec document was loaded in step 5, follow its formatting guidelines.
     - Else use the default format:
       ```
       ## Summary
       <1-3 sentences describing the overall change>

       ## Changes
       - <one bullet per logical change>

       ## Testing
       - <testing approach or steps>

       ## Notes
       - <additional context, migration steps, reviewer notes>
       ```

8. **STOP and wait for user confirmation** — Present the following for review:
   - **Title**: the generated title
   - **Description**: the generated description (in a code block for readability)
   - **Source branch** → **Target branch**
   - Inform the user that default reviewers will be added automatically.
   - Do NOT proceed until the user explicitly approves. The user may edit the title, description, or target branch.

9. **Create the PR** — Pipe the confirmed title and description as JSON to `$HOME/my-skills/scripts/create_bitbucket_pr.sh`:
   ```bash
   echo '{"title":"...","description":"..."}' | $HOME/my-skills/scripts/create_bitbucket_pr.sh <workspace> <repo> <source> <dest>
   ```

10. **Output result** — Parse the API response and display:
    - PR URL (from `links.html.href`)
    - PR ID
    - Reviewers added
    - If the API returns an error, display the error message.

## Update Mode

### Steps
1. **Fetch current PR info** — Use curl to get the PR details:
   ```bash
   curl -s -u "$ATLASSIAN_EMAIL:$BITBUCKET_API_TOKEN" "https://api.bitbucket.org/2.0/repositories/{workspace}/{repo}/pullrequests/{id}"
   ```
   Parse the workspace, repo, and PR ID from the provided URL using the same sed patterns as other Bitbucket scripts. Extract current title, description, source branch, and target branch.

2. **Get diff** — Run `git diff origin/<target>...origin/<source>` for the full diff between the PR branches.
   - Also run `git log origin/<target>..origin/<source> --oneline` for the commit list.

3. **Load PR spec and template** — Same as Create Mode steps 5-6.

4. **Generate new title and description** — Same logic as Create Mode step 7, but also show a comparison:
   - **Current title** vs **Proposed title**
   - **Current description** vs **Proposed description**

5. **STOP and wait for user confirmation** — Present the current vs proposed comparison. The user may choose to keep the current values, use the proposed values, or provide their own edits. Do NOT proceed without explicit approval.

6. **Update the PR** — Pipe the confirmed title and description as JSON to `$HOME/my-skills/scripts/update_bitbucket_pr.sh`:
   ```bash
   echo '{"title":"...","description":"..."}' | $HOME/my-skills/scripts/update_bitbucket_pr.sh <pr-url>
   ```

7. **Output result** — Display the updated PR URL and confirm the changes were applied.

## Constraints
- **Step 8 (Create) / Step 5 (Update) is mandatory**: Never create or update a PR without explicit user confirmation.
- **Step 1 (Create)**: Never create a PR from the default branch.
- Always use `$HOME/my-skills/.env` for credentials — never ask the user for passwords or tokens inline.
- Keep the generated title under 72 characters.
- The description should be in English unless the PR spec document specifies otherwise.

## Example
```
# Create a new PR (auto-detect target branch)
/bitbucket-pr

# Create a PR targeting a specific branch
/bitbucket-pr develop

# Update an existing PR
/bitbucket-pr https://bitbucket.org/my-workspace/my-repo/pull-requests/42
```
