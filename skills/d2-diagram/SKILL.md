---
name: d2-diagram
description: Generate a D2 diagram (sequence diagram or flowchart) by tracing an API endpoint or method's execution flow in the current repository. Use when the user wants to visualize code flow.
---

# D2 Diagram Generator

## What this skill does
Given a function name, file:method reference, or API endpoint, this skill traces the call chain in the current repository and generates a D2 diagram file.

## Inputs
- **Target identifier** (via `$ARGUMENTS`):
  - Function/method name: `handleUserLogin`
  - File:method format: `src/auth/controller.ts:handleUserLogin`
  - API endpoint: `POST /api/auth/login`

## Requirements
- Access to the current repository codebase.
- Optional: `d2` CLI for rendering to SVG (`brew install d2`).

## Steps

### 1. Parse Arguments
Extract the target identifier from `$ARGUMENTS`. Supported formats:
- Bare function name → search entire codebase
- `file:method` → go directly to that file and locate the method
- `HTTP_METHOD /path` → search for route/endpoint definitions

### 2. Locate Target
- **Function name**: Grep for function/method definitions (e.g. `def <name>`, `func <name>`, `function <name>`, `<name> =`, `<name>(`) across the codebase.
- **File:method**: Read the specified file and locate the method.
- **API endpoint**: Search for route definitions matching the HTTP method and path (e.g. `router.post('/path')`, `@app.get("/path")`, `@PostMapping`).

If multiple matches are found, list them and ask the user to pick one.

### 3. Trace Call Chain
Read the target function and analyze up to 3 levels deep:
- **Function calls**: Direct calls to other functions/methods, following imports to understand module boundaries.
- **Database operations**: ORM calls (`find`, `save`, `create`, `query`, `SELECT`, `INSERT`, etc.).
- **External API calls**: HTTP clients (`fetch`, `axios`, `requests`, `http.Get`, etc.).
- **Conditional logic**: `if/else`, `switch/case`, `try/catch`, guard clauses.
- **Async operations**: `await`, goroutines, callbacks.

For each call, read the referenced function to understand what it does (1-2 levels deeper). Stop at external library boundaries.

### 4. Determine Diagram Type
Automatically choose based on code structure:

**Sequence diagram** — when the code shows:
- Multiple service/module interactions (controller → service → repository)
- Database or external API calls
- Clear request/response flow between actors

**Flowchart** — when the code shows:
- Multiple conditional branches or decision points
- Loops or retry logic
- Business rule validation chains
- State transitions

### 5. Generate D2 Code

#### Sequence Diagram Format:
```d2
diagram: {
  shape: sequence_diagram

  client
  <controller>
  <service>
  <database>

  client -> <controller>: <request>
  <controller> -> <service>: <method_call>
  <service> -> <database>: <query>
  <database> -> <service>: <result>
  <service> -> <controller>: <return>
  <controller> -> client: <response>
}
```

#### Flowchart Format:
```d2
start: Start {shape: circle}
<step1>: <description>
<decision1>: <condition> {shape: diamond}
<step2>: <description>
end: End {shape: circle}

start -> <step1>
<step1> -> <decision1>
<decision1> -> <step2>: yes
<decision1> -> end: no
<step2> -> end
```

**D2 generation rules**:
- Use descriptive labels derived from code (function names, parameter names, comments).
- Keep diagrams readable: 5-10 main actors/steps. Collapse trivial utility calls.
- Sanitize names: replace dots, slashes, special characters with underscores.
- For recursive functions, show one level and add a note.
- For error/catch paths, include them as alternate flows.

### 6. Write Output
- Filename: `<sanitized-target-name>.d2` (e.g. `handle-user-login.d2`)
- Write to the current working directory.

### 7. Render to SVG (Optional)
Check if `d2` CLI is available:
```bash
command -v d2
```
If available, render:
```bash
d2 <filename>.d2 <filename>.svg
```
If not available, inform the user the `.d2` file is ready and they can render it with `d2 <filename>.d2 <filename>.svg`.

### 8. Output Summary
Display:
- Target analyzed and diagram type chosen
- Output file path
- D2 source code preview
- SVG path if rendered
- Rendering command for future customization

## Constraints
- Focus on readability over completeness — omit trivial utility calls.
- Limit tracing depth to 3 levels to prevent overwhelming diagrams.
- If target cannot be found, suggest similar matches.
- For dynamic dispatch or complex inheritance, show primary paths.
- Database queries are simplified (e.g. "Query users" not full SQL).

## Examples
```
/d2-diagram handleUserLogin
/d2-diagram src/billing/calculator.ts:calculateDiscount
/d2-diagram POST /api/orders
```
