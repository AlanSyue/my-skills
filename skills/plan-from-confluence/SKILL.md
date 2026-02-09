---
name: plan-from-confluence
description: Fetch a Confluence page via local API script and generate a concrete implementation plan for the current repository. Use this when the user provides a Confluence link and asks how to implement the spec in the current repo.
---

# Plan From Confluence (Repo-aware)

## What this skill does
Given a Confluence page URL, this skill fetches the page content locally and produces a concrete, repo-specific implementation plan.

## Inputs
- Confluence page URL (e.g. https://your-domain.atlassian.net/wiki/spaces/SPACE/pages/123456/Page+Title)

## Requirements
- Local environment variables (in `$HOME/my-skills/.env`):
  - ATLASSIAN_BASE_URL (e.g. https://your-domain.atlassian.net)
  - ATLASSIAN_EMAIL
  - ATLASSIAN_API_TOKEN
- Script: `$HOME/my-skills/scripts/get_confluence_page.sh` must be executable.

## Steps
1. Parse the Confluence page ID from the URL.
2. Execute `$HOME/my-skills/scripts/get_confluence_page.sh <confluence-url>` to fetch the page JSON.
3. Summarize the page:
   - title
   - body content
   - any linked requirements or acceptance criteria
4. **Guard check**: If the body content is empty or null, STOP and ask the user to fill in the Confluence page before proceeding. Do NOT continue with planning.
5. **Nested Confluence links**: If the body contains other Confluence links (matching `*/wiki/spaces/*/pages/*`), execute the same script for each link and incorporate as additional context.
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
- Focus only on the current repository unless the page explicitly requires multi-repo changes.
- If multi-repo impact exists, clearly separate:
  - This repo's tasks
  - Other repos' tasks (as notes only)

## Example
/plan-from-confluence https://your-domain.atlassian.net/wiki/spaces/ENG/pages/123456/Feature+Spec
