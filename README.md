# My Skills

A collection of reusable agent skills compatible with Claude Code, Gemini CLI, Codex CLI, and GitHub Copilot.

Skills live in the `skills/` directory. Each subfolder contains a `SKILL.md` file.

## Prerequisites

Copy `.env.example` and fill in the credentials for the services you use:

```bash
cp .env.example .env
# Fill in your credentials in .env
```

- **Atlassian** (Jira, Confluence): `ATLASSIAN_BASE_URL`, `ATLASSIAN_EMAIL`, `ATLASSIAN_API_TOKEN`
- **Bitbucket**: `BITBUCKET_API_TOKEN` ([App Password](https://bitbucket.org/account/settings/app-passwords/) with scopes: Account Read, Pull requests Read/Write), shares `ATLASSIAN_EMAIL`. Optionally set `BITBUCKET_ACCOUNT_ID` if the token lacks Account Read scope.
- **Asana**: `ASANA_ACCESS_TOKEN`, `ASANA_WORKSPACE_GID`, `ASANA_DONE_SECTION_NAME`
- **Google Slides**: `GOOGLE_CREDENTIALS_FILE` (path to GCP credential JSON — supports both [Service Account](https://cloud.google.com/iam/docs/service-accounts) and OAuth2 Desktop Client), `GOOGLE_SLIDES_SHARE_EMAIL` (email to share presentations with). Requires Python packages in a venv — see [Google Slides Setup](#google-slides-setup) below.

## Installation

```bash
./install.sh
```

Symlinks the `skills/` directory into `~/.claude/skills`, `~/.gemini/skills`, `~/.agents/skills`, and `~/.copilot/skills`. New skills added to `skills/` are automatically available — no need to re-run.

### Google Slides Setup

The `generate-slides` skill requires Python packages. Set up a virtual environment:

```bash
python3 -m venv ~/my-skills/.venv
~/my-skills/.venv/bin/pip install google-api-python-client google-auth google-auth-oauthlib
```

Then run the script using the venv Python:

```bash
~/my-skills/.venv/bin/python3 scripts/create_google_slides.py presentation.md
```

**Credential types:**

| Type | Use case | Notes |
|------|----------|-------|
| Service Account | CI/CD, automated pipelines | No browser needed, but requires domain-wide delegation for Google Workspace |
| OAuth2 Desktop | Local development | Opens browser for first-time authorization, caches token in `.cache/` |

## Skills

| Skill | Command | Description |
|-------|---------|-------------|
| **plan-from-jira** | `/plan-from-jira <jira-url>` | Fetch a Jira ticket and generate a repo-specific implementation plan. Automatically follows Confluence links in the description. |
| **plan-from-confluence** | `/plan-from-confluence <confluence-url>` | Fetch a Confluence page and generate a repo-specific implementation plan. Recursively follows nested Confluence links. |
| **smart-commit** | `/smart-commit` | Generate and execute a Conventional Commit from the current branch name and staged diff. Extracts ticket number from branch name automatically. |
| **d2-diagram** | `/d2-diagram <target>` | Trace an API endpoint or method's call chain and generate a D2 diagram (sequence diagram or flowchart). Renders to SVG if `d2` CLI is installed. |
| **asana-automation** | `/asana-automation <ID or keyword>` | Query an Asana task by GID or title keyword, analyze the requirements, implement changes, then automatically move the task to the done section and reassign to the reporter. |
| **analyze-bitbucket-pr-comments** | `/analyze-bitbucket-pr-comments <pr-url>` | Fetch Bitbucket PR review comments, analyze each comment, suggest fixes or replies, then execute after confirmation. |
| **generate-slides** | `/generate-slides <topic>` | Generate a slide deck from a topic or context, then convert it into a Google Slides presentation after user confirmation. |