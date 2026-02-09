---
name: plan-from-jira
description: Fetch a Jira ticket via local API script and generate a concrete implementation plan for the current repository. Use this when the user provides a Jira link and asks how to implement the ticket in the current repo.
---

# Plan From Jira (Repo-aware)

## What this skill does
Given a Jira ticket URL, this skill fetches the issue content locally and produces a concrete, repo-specific implementation plan.

## Inputs
- Jira ticket URL (e.g. https://your-domain.atlassian.net/browse/PROJ-123)

## Requirements
- Local environment variables (in `$HOME/my-skills/.env`):
  - ATLASSIAN_BASE_URL (e.g. https://your-domain.atlassian.net)
  - ATLASSIAN_EMAIL
  - ATLASSIAN_API_TOKEN
- Script: `scripts/get_jira_issue.sh` must be executable.
- Script: `scripts/get_confluence_page.sh` must be executable.

## Steps
1. Parse the Jira issue key from the URL.
2. Execute `$HOME/my-skills/scripts/get_jira_issue.sh <jira-url>` to fetch the issue JSON.
3. Summarize the issue:
   - title
   - description
   - acceptance criteria (if any)
4. **Guard check**: If the description field is empty or null, STOP and ask the user to fill in the Jira ticket description before proceeding. Do NOT continue with planning.
5. **Confluence links**: If the description or comments contain Confluence links (matching `*/wiki/spaces/*/pages/*`), execute `$HOME/my-skills/scripts/get_confluence_page.sh <confluence-url>` for each link to fetch the page content, and incorporate it as additional context for the plan.
6. Inspect the current repository:
   - README, docs
   - main source folders (e.g. src/, app/, services/)
7. Map requirements to concrete code changes in THIS repo:
   - affected modules/files
   - API/schema changes
   - migrations/config updates
8. Identify dependencies and risks:
   - cross-service contracts
   - backward compatibility
   - rollout/rollback considerations
9. Output a step-by-step implementation plan.

## Output format
Return a concise plan with:
- Scope summary
- Affected files/modules (with paths)
- Step-by-step tasks (checklist)
- API/contract changes
- Test plan (unit/integration/e2e)
- Risks & notes

## Constraints
- Focus only on the current repository unless the ticket explicitly requires multi-repo changes.
- If multi-repo impact exists, clearly separate:
  - This repo’s tasks
  - Other repos’ tasks (as notes only)

## Example
/plan-from-jira https://your-domain.atlassian.net/browse/PROJ-123