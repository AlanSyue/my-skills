---
name: run-pipeline
description: Trigger a Bitbucket Cloud pipeline on the current branch, with interactive pipeline selection and variable support. Polls for completion and reports results.
---

# run-pipeline

## What this skill does
Triggers a Bitbucket Cloud pipeline, supports default and custom pipelines with an interactive selection menu, allows passing variables, and polls until completion to report the result.

## Inputs
- `$ARGUMENTS` is optional:
  - Empty → show interactive menu
  - `custom:<pipeline-name>` → run specific custom pipeline
  - `custom:<pipeline-name> VAR1=value1 VAR2=value2` → run with variables

## Requirements
- Local environment variables (in `$HOME/my-skills/.env`):
  - `ATLASSIAN_EMAIL` — your Atlassian account email
  - `BITBUCKET_API_TOKEN` — Bitbucket App Password (needs **Pipelines: Read + Write** scope in addition to existing scopes)
- Scripts (must be executable):
  - `$HOME/my-skills/scripts/detect_bitbucket_repo.sh`
  - `$HOME/my-skills/scripts/run_bitbucket_pipeline.sh`
  - `$HOME/my-skills/scripts/get_bitbucket_pipeline.sh`

## Steps

### 1. Detect repo context
Run `$HOME/my-skills/scripts/detect_bitbucket_repo.sh` and capture JSON output. If the script returns an error, STOP and inform the user.

### 2. Parse arguments
Check `$ARGUMENTS`:
- If empty → go to step 3 (interactive menu)
- If starts with `custom:` → extract pipeline name and any `KEY=value` pairs after it. Skip to step 4.

### 3. Interactive pipeline selection
Read `bitbucket-pipelines.yml` from the repository root. Parse all available pipelines and present a selection menu:

```
可用的 Pipelines（branch: feature/my-branch）：

| #  | 類型     | Pipeline 名稱      |
|----|---------|-------------------|
| 1  | default | (default)         |
| 2  | custom  | deploy-staging    |
| 3  | custom  | deploy-production |
| 4  | custom  | run-integration   |

請選擇要執行的 pipeline（輸入編號）
```

Parse pipelines from YAML:
- `pipelines.default` → listed as type "default"
- `pipelines.custom.*` → each key listed as type "custom"
- `pipelines.branches.*` → each key listed as type "branch"
- `pipelines.tags.*` → each key listed as type "tag"

Wait for user to select. If user also provides variables (e.g., `3 ENV=staging`), parse them.

### 4. Parse variables
If any `KEY=value` pairs were provided, construct the variables array:
- If a key is prefixed with `SECRET:` (e.g., `SECRET:PASSWORD=abc`), set `"secured": true`
- Otherwise set `"secured": false`

### 5. Confirmation
Present the execution plan and STOP for user confirmation:
```
即將執行 Pipeline：
- Branch: feature/my-branch
- Pipeline: deploy-staging (custom)
- Variables: ENV=staging, VERSION=1.0

確認執行？
```
Do NOT proceed without explicit user confirmation.

### 6. Trigger pipeline
Construct the API payload JSON and pipe it to `$HOME/my-skills/scripts/run_bitbucket_pipeline.sh`:
```bash
echo '<payload>' | $HOME/my-skills/scripts/run_bitbucket_pipeline.sh <workspace> <repo>
```

For default pipeline:
```json
{
  "target": {
    "ref_type": "branch",
    "type": "pipeline_ref_target",
    "ref_name": "<branch>"
  }
}
```

For custom pipeline:
```json
{
  "target": {
    "ref_type": "branch",
    "type": "pipeline_ref_target",
    "ref_name": "<branch>",
    "selector": {
      "type": "custom",
      "pattern": "<pipeline-name>"
    }
  }
}
```

For branch-type pipeline, omit selector (the branch name in `ref_name` is what matters).

Add `"variables"` array at root level if variables were provided.

Parse the response — extract `uuid` from the response. If error, display it and STOP.

### 7. Poll for completion
Every 15 seconds, run:
```bash
$HOME/my-skills/scripts/get_bitbucket_pipeline.sh <workspace> <repo> <pipeline_uuid>
```

Check `state.name` and `state.result.name`:
- If `state.name` is `PENDING` or `RUNNING` → continue polling, show brief status update
- If `state.name` is `COMPLETED`:
  - `state.result.name` = `SUCCESSFUL` → report success
  - `state.result.name` = `FAILED` → report failure
  - `state.result.name` = `STOPPED` → report stopped
  - `state.result.name` = `ERROR` → report error

Timeout after 30 minutes of polling. If timeout, inform user and provide the pipeline URL to check manually.

During polling, show periodic status updates like:
```
⏳ Pipeline 執行中... (已經過 1m 30s)
```

### 8. Report result
Display:
- Status: ✅ SUCCESSFUL / ❌ FAILED / ⛔ STOPPED / ⚠️ ERROR
- Pipeline URL: `https://bitbucket.org/{workspace}/{repo}/addon/pipelines/home#!/results/{build_number}`
- Duration: from `duration_in_seconds` in the response
- Build number: from `build_number` in the response

## Constraints
- **Step 5 is mandatory**: Never trigger a pipeline without explicit user confirmation.
- Always use `$HOME/my-skills/.env` for credentials — never ask the user for passwords or tokens inline.
- The interactive menu text should be in Traditional Chinese (繁體中文).
- Status update messages during polling should also be in Traditional Chinese.
- Pipeline URL and technical details remain in English.

## Example
```
# Interactive selection
/run-pipeline

# Run specific custom pipeline
/run-pipeline custom:deploy-staging

# Run with variables
/run-pipeline custom:deploy-staging ENV=staging VERSION=1.0

# Run with a secured variable
/run-pipeline custom:deploy-production SECRET:API_KEY=abc123
```
