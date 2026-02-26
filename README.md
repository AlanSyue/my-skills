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

## Installation

```bash
./install.sh
```

Symlinks the `skills/` directory into `~/.claude/skills`, `~/.gemini/skills`, `~/.agents/skills`, and `~/.copilot/skills`. New skills added to `skills/` are automatically available — no need to re-run.

## Skills

| Skill | Command | Description |
|-------|---------|-------------|
| **plan-from-jira** | `/plan-from-jira <jira-url>` | Fetch a Jira ticket and generate a repo-specific implementation plan. Automatically follows Confluence links in the description. |
| **plan-from-confluence** | `/plan-from-confluence <confluence-url>` | Fetch a Confluence page and generate a repo-specific implementation plan. Recursively follows nested Confluence links. |
| **smart-commit** | `/smart-commit` | Generate and execute a Conventional Commit from the current branch name and staged diff. Extracts ticket number from branch name automatically. |
| **d2-diagram** | `/d2-diagram <target>` | Trace an API endpoint or method's call chain and generate a D2 diagram (sequence diagram or flowchart). Renders to SVG if `d2` CLI is installed. |
| **asana-automation** | `/asana-automation <ID or keyword>` | Query an Asana task by GID or title keyword, analyze the requirements, implement changes, then automatically move the task to the done section and reassign to the reporter. |
| **analyze-bitbucket-pr-comments** | `/analyze-bitbucket-pr-comments <pr-url>` | Fetch Bitbucket PR review comments, analyze each comment, suggest fixes or replies, then execute after confirmation. |