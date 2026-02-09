# My Skills

A collection of reusable agent skills compatible with Claude Code, Gemini CLI, and Codex CLI.

Skills live in the `skills/` directory. Each subfolder contains a `SKILL.md` file.

## Prerequisites

If you use Atlassian services (Jira, Confluence):

```bash
cp .env.example .env
# Fill in your Atlassian credentials in .env
```

## Installation

```bash
./install.sh
```

Symlinks the `skills/` directory into `~/.claude/skills`, `~/.gemini/skills`, and `~/.agents/skills`. New skills added to `skills/` are automatically available — no need to re-run.

## Skills

| Skill | Command | Description |
|-------|---------|-------------|
| **plan-from-jira** | `/plan-from-jira <jira-url>` | Fetch a Jira ticket and generate a repo-specific implementation plan. Automatically follows Confluence links in the description. |
| **plan-from-confluence** | `/plan-from-confluence <confluence-url>` | Fetch a Confluence page and generate a repo-specific implementation plan. Recursively follows nested Confluence links. |
| **smart-commit** | `/smart-commit` | Generate and execute a Conventional Commit from the current branch name and staged diff. Extracts ticket number from branch name automatically. |
| **d2-diagram** | `/d2-diagram <target>` | Trace an API endpoint or method's call chain and generate a D2 diagram (sequence diagram or flowchart). Renders to SVG if `d2` CLI is installed. |