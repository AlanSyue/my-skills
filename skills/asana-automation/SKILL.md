---
name: asana-automation
description: Query an Asana task by ID or title keyword via the Asana API, retrieve its title and description, then analyze and process it.
---

# Asana Task Query & Processing

## Environment Variables

Managed in `$HOME/my-skills/.env` (see `.env.example` for reference):
- `ASANA_ACCESS_TOKEN` — Asana Personal Access Token
- `ASANA_WORKSPACE_GID` — Asana Workspace GID (required when searching by title)
- `ASANA_DONE_SECTION_NAME` — Section name to move the task to after completion (default: `To Be Test`)

Load them before making API calls:

```bash
source "$HOME/my-skills/.env"
```

## Workflow

### 1. Determine Input Type
The user runs `/asana <ID or keyword>`:
- If `$ARGUMENTS` is purely numeric, treat it as a **Task GID** and query directly
- Otherwise, treat it as a **title keyword** and use the search API to find matching tasks

### 2. Query by Task GID

```bash
curl -sS -H "Authorization: Bearer $ASANA_ACCESS_TOKEN" \
  "https://app.asana.com/api/1.0/tasks/$ARGUMENTS?opt_fields=name,notes,assignee.name,due_on,completed,created_by.gid,created_by.name,memberships.project.gid,memberships.project.name,memberships.section.gid,memberships.section.name,custom_fields.name,custom_fields.display_value" \
  | jq '{
    gid: .data.gid,
    name: .data.name,
    notes: .data.notes,
    assignee: .data.assignee.name,
    due_on: .data.due_on,
    completed: .data.completed,
    created_by: { gid: .data.created_by.gid, name: .data.created_by.name },
    memberships: [.data.memberships[] | { project_gid: .project.gid, project_name: .project.name, section_gid: .section.gid, section_name: .section.name }],
    custom_fields: [.data.custom_fields[] | select(.display_value != null) | {name: .name, value: .display_value}]
  }'
```

Remember the `created_by` (reporter) GID and the `project_gid` from the query — these will be needed when completing the task later.

### 3. Search by Title Keyword

```bash
QUERY=$(echo "$ARGUMENTS" | jq -sRr @uri)
curl -sS -H "Authorization: Bearer $ASANA_ACCESS_TOKEN" \
  "https://app.asana.com/api/1.0/workspaces/$ASANA_WORKSPACE_GID/tasks/search?text=$QUERY&opt_fields=name,notes,assignee.name,due_on,completed,memberships.project.name&is_subtask=false&sort_by=modified_at&limit=10" \
  | jq '.data[] | {gid, name, assignee: .assignee.name, due_on, completed}'
```

If multiple results are found, list them and let the user choose, then query the full details using the selected GID.

### 4. Present Task Information

After querying, present the task information in the following format:

```
## Task: <title>
- **GID**: <gid>
- **Project**: <project name>
- **Assignee**: <assignee>
- **Due**: <due date>
- **Status**: <completion status>

### Description
<notes content>
```

### 5. Analyze & Process

After presenting the task information:
1. Analyze the requirements or issues described in the task
2. Find related code in the codebase
3. Ask the user: "Would you like to start working on this task?"
4. If the user agrees, begin implementation

### 6. Move Task to Done Section and Reassign to Reporter After Completion

After implementation is complete and committed, perform the following steps:

#### 6a. Find the done section

List all sections in the task's project and find the one whose name contains `$ASANA_DONE_SECTION_NAME` (case-insensitive):

```bash
curl -sS -H "Authorization: Bearer $ASANA_ACCESS_TOKEN" \
  "https://app.asana.com/api/1.0/projects/<PROJECT_GID>/sections?opt_fields=name"
```

#### 6b. Move the task to the done section

```bash
curl -sS -X POST \
  -H "Authorization: Bearer $ASANA_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data":{"task":"<TASK_GID>"}}' \
  "https://app.asana.com/api/1.0/sections/<TO_BE_TEST_SECTION_GID>/addTask"
```

#### 6c. Reassign the task to the reporter (created_by)

```bash
curl -sS -X PUT \
  -H "Authorization: Bearer $ASANA_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data":{"assignee":"<REPORTER_GID>"}}' \
  "https://app.asana.com/api/1.0/tasks/<TASK_GID>"
```

Remember the Task GID, Project GID, and Reporter GID from the query, and automatically execute the above steps after the commit is complete.
