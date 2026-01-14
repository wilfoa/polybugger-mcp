# User Story: Python Debug Relay Server

**Document Version:** 1.0
**Created:** January 13, 2026
**Status:** Discovery Phase
**Priority:** High
**Epic:** AI-Assisted Development Tooling

---

## Executive Summary

Build a robust HTTP relay server that enables AI coding agents to perform full interactive debugging of Python applications. The server bridges the gap between non-interactive command execution and interactive debugging by exposing debugpy/DAP (Debug Adapter Protocol) functionality via REST endpoints.

---

## 1. Problem Statement

### The Gap

AI coding agents (Claude, GPT, Copilot, etc.) have transformed software development by reading code, executing commands, and analyzing output. However, a critical capability gap exists: **interactive debugging**.

### Current State

| Capability | AI Agents Today |
|------------|-----------------|
| Read source code | Yes |
| Execute shell commands | Yes |
| See command output | Yes |
| Set breakpoints | No |
| Inspect runtime state | No |
| Step through code | No |
| Evaluate expressions at runtime | No |

### Root Cause

Traditional debuggers (pdb, debugpy, gdb) require:
- **Continuous interactive sessions** - Agents execute discrete commands
- **Bidirectional stdin/stdout** - Agents have unidirectional command execution
- **Stateful connections** - Agents are stateless between invocations

### Impact

Without debugging capabilities, AI agents must:
- Rely on print statement debugging (slow, pollutes code)
- Make educated guesses about runtime state
- Ask users to manually debug and report findings
- Miss subtle bugs that only manifest at runtime

### Opportunity

By creating an HTTP bridge to debugpy, we enable AI agents to:
- Set breakpoints and pause execution at precise locations
- Inspect variable values and object state at runtime
- Step through code to understand execution flow
- Evaluate expressions in the current execution context
- Debug complex multi-file applications systematically

---

## 2. User Personas

### Primary Persona: AI Coding Agent

**Name:** Agent Claude
**Type:** AI-powered coding assistant
**Environment:** CLI tool, IDE extension, or web interface

**Characteristics:**
- Executes discrete bash/shell commands
- Cannot maintain persistent interactive sessions
- Processes structured data (JSON) efficiently
- Has no native GUI or visual interface
- Operates with HTTP client capabilities

**Goals:**
- Debug Python scripts to find root cause of bugs
- Inspect runtime state without modifying source code
- Step through complex logic to understand behavior
- Validate fixes by observing execution

**Pain Points:**
- Cannot use pdb or IDE debuggers interactively
- Must ask humans to debug and report back
- Print-debugging requires code changes and cleanup
- Guessing at runtime state leads to incorrect fixes

**Technical Requirements:**
- RESTful API with JSON payloads
- Synchronous request/response (no WebSockets required for MVP)
- Clear error messages for self-correction
- Stateless requests (session state managed server-side)

---

### Secondary Persona: Automation Developer

**Name:** Dana DevOps
**Role:** Developer automating debug workflows
**Environment:** CI/CD pipelines, testing frameworks, custom tooling

**Characteristics:**
- Writes Python/Bash scripts for automation
- Integrates tools via APIs
- Values scriptability over GUIs
- Needs reproducible debugging sessions

**Goals:**
- Script debugging workflows for regression testing
- Capture runtime state during test failures
- Automate variable inspection at specific points
- Build custom debugging dashboards/tools

**Pain Points:**
- IDE debuggers don't integrate with automation
- pdb requires interactive terminal
- Difficult to capture debug state programmatically
- No way to script "debug this test and dump state"

**Technical Requirements:**
- Stable, versioned API
- Comprehensive endpoint documentation
- Bulk operations (set multiple breakpoints)
- Session export/import capabilities

---

### Tertiary Persona: Remote Developer

**Name:** Ray Remote
**Role:** Developer working with containerized/remote Python apps
**Environment:** Docker, Kubernetes, remote servers

**Characteristics:**
- Applications run in isolated containers
- Limited direct access to execution environment
- Needs to debug without IDE attachment
- Works across network boundaries

**Goals:**
- Debug applications running in containers
- Attach to running processes without restart
- Debug across SSH tunnels
- Maintain debugging context across reconnects

**Pain Points:**
- IDE remote debugging is complex to configure
- Container debugging requires special setup
- Losing debugging context on disconnection
- Port forwarding complexity

---

## 3. User Flows

### 3.1 Happy Path: Basic Debug Session

```
Start Session --> Set Breakpoints --> Launch Script --> Hit Breakpoint --> Inspect State --> Step Through --> Continue --> Session Ends
```

**Detailed Flow:**

| Step | Action | API Call | Expected Response |
|------|--------|----------|-------------------|
| 1 | Create debug session | `POST /sessions` | `{session_id: "abc123", status: "created"}` |
| 2 | Set breakpoint | `POST /sessions/{id}/breakpoints` | `{breakpoint_id: "bp1", verified: true}` |
| 3 | Launch script | `POST /sessions/{id}/launch` | `{status: "running"}` |
| 4 | Check status (poll) | `GET /sessions/{id}/status` | `{status: "paused", reason: "breakpoint", location: {...}}` |
| 5 | Get stack trace | `GET /sessions/{id}/stacktrace` | `{frames: [...]}` |
| 6 | Get variables | `GET /sessions/{id}/frames/{fid}/variables` | `{variables: [...]}` |
| 7 | Evaluate expression | `POST /sessions/{id}/evaluate` | `{result: "value", type: "str"}` |
| 8 | Step over | `POST /sessions/{id}/step-over` | `{status: "paused", location: {...}}` |
| 9 | Continue | `POST /sessions/{id}/continue` | `{status: "running"}` |
| 10 | Check completion | `GET /sessions/{id}/status` | `{status: "terminated", exit_code: 0}` |
| 11 | Clean up | `DELETE /sessions/{id}` | `{deleted: true}` |

---

### 3.2 Alternative Flow: Attach to Running Process

**Scenario:** Debug an already-running Python application (e.g., web server, long-running job)

```
Find Process --> Attach Session --> Set Breakpoints --> Trigger Behavior --> Debug --> Detach
```

| Step | Action | API Call |
|------|--------|----------|
| 1 | List debuggable processes | `GET /processes` |
| 2 | Create attach session | `POST /sessions` with `{mode: "attach", pid: 1234}` |
| 3 | Verify attachment | `GET /sessions/{id}/status` |
| 4 | Set breakpoints | `POST /sessions/{id}/breakpoints` |
| 5 | Wait for breakpoint (user triggers app behavior) | Poll `GET /sessions/{id}/status` |
| 6 | Debug as normal | Various debug endpoints |
| 7 | Detach cleanly | `POST /sessions/{id}/detach` |

**Prerequisites:**
- Target process must have debugpy installed
- Process must be started with `--listen` flag OR accept attach request

---

### 3.3 Alternative Flow: Debug with Arguments and Environment

**Scenario:** Debug a script that requires command-line arguments and environment variables

```python
# Example: python train.py --epochs 10 --data ./data.csv
```

| Step | API Call | Payload |
|------|----------|---------|
| 1 | Create session | `POST /sessions` |
| 2 | Configure launch | `POST /sessions/{id}/launch` | `{script: "train.py", args: ["--epochs", "10", "--data", "./data.csv"], env: {"CUDA_VISIBLE_DEVICES": "0"}, cwd: "/project"}` |

---

### 3.4 Alternative Flow: Debug Unit Tests

**Scenario:** Debug a specific test function in pytest

| Step | Action | API Call |
|------|--------|----------|
| 1 | Create session | `POST /sessions` |
| 2 | Set breakpoint in test | `POST /sessions/{id}/breakpoints` with `{file: "test_math.py", line: 42}` |
| 3 | Launch pytest | `POST /sessions/{id}/launch` with `{module: "pytest", args: ["-xvs", "test_math.py::test_divide"]}` |
| 4 | Debug when breakpoint hits | Normal debug flow |

---

### 3.5 Alternative Flow: Conditional Breakpoints

**Scenario:** Break only when a specific condition is met

```python
# Break only when i > 100 in a loop
for i in range(1000):
    process(i)  # Breakpoint here, but only when i > 100
```

| Step | API Call | Payload |
|------|----------|---------|
| 1 | Set conditional breakpoint | `POST /sessions/{id}/breakpoints` | `{file: "main.py", line: 3, condition: "i > 100"}` |
| 2 | Set hit count breakpoint | `POST /sessions/{id}/breakpoints` | `{file: "main.py", line: 3, hit_condition: "== 50"}` |
| 3 | Set log point (no break) | `POST /sessions/{id}/breakpoints` | `{file: "main.py", line: 3, log_message: "i = {i}"}` |

---

### 3.6 Error Flow: Script Crashes with Exception

```
Launch --> Script Raises Exception --> Capture State --> Inspect --> Terminate
```

| Step | Status Response | Action |
|------|-----------------|--------|
| 1 | `{status: "running"}` | Script executing |
| 2 | `{status: "paused", reason: "exception", exception: {type: "ValueError", message: "...", location: {...}}}` | Exception caught |
| 3 | Agent calls `/stacktrace`, `/variables` | Inspect crash state |
| 4 | Agent calls `/evaluate` | Check values that caused crash |
| 5 | `DELETE /sessions/{id}` | Clean up |

**Configuration:** `POST /sessions/{id}/launch` with `{stop_on_exception: true}` or `{stop_on_exception: "uncaught"}` (only uncaught exceptions)

---

### 3.7 Error Flow: Invalid Breakpoint Location

| Scenario | API Response | Agent Action |
|----------|--------------|--------------|
| File doesn't exist | `{error: "file_not_found", file: "/path/to/missing.py"}` | Check file path |
| Line is blank/comment | `{breakpoint_id: "bp1", verified: false, message: "No executable code at line 5"}` | Adjust line number |
| Line doesn't exist | `{error: "invalid_line", line: 999, max_line: 150}` | Fix line number |
| Syntax error in condition | `{error: "invalid_condition", details: "SyntaxError: ..."}` | Fix condition |

---

### 3.8 Error Flow: Session Timeout

**Scenario:** Session inactive for extended period

| Time | Event | Response |
|------|-------|----------|
| T+0 | Session created | Normal |
| T+30min | No activity, warning | Session metadata: `{warning: "Session will expire in 30 minutes"}` |
| T+60min | Session timeout | Session terminated, status: `{status: "terminated", reason: "timeout"}` |
| T+60min+ | Any request to session | `{error: "session_not_found", id: "abc123"}` |

**Configuration:** Timeout configurable via `POST /sessions` with `{timeout_minutes: 120}` or server config.

---

### 3.9 Error Flow: Connection Issues

| Scenario | HTTP Status | Response | Recovery |
|----------|-------------|----------|----------|
| Server not running | Connection refused | N/A | Start relay server |
| Session crashed | 500 | `{error: "session_crashed", details: "..."}` | Create new session |
| Debug target died | 200 | `{status: "terminated", reason: "target_exited", exit_code: 1}` | Review output, relaunch |
| debugpy timeout | 504 | `{error: "debugpy_timeout", operation: "evaluate"}` | Retry or terminate |

---

## 4. Edge Cases

### 4.1 Script with Syntax Errors

**Scenario:** User tries to debug a script with Python syntax errors.

**Expected Behavior:**
- Launch fails immediately
- Response includes syntax error details with file, line, and offset
- Session remains in "created" state (can fix and retry)

**API Response:**
```json
{
  "error": "syntax_error",
  "details": {
    "file": "/path/to/script.py",
    "line": 15,
    "offset": 23,
    "message": "unexpected EOF while parsing",
    "text": "if x == 1"
  }
}
```

---

### 4.2 Breakpoint in Non-Existent File

**Scenario:** Breakpoint set in file path that doesn't exist or is inaccessible.

**Expected Behavior:**
- Breakpoint creation succeeds but marked as unverified
- Warning returned to agent
- If file appears later (created/mounted), breakpoint auto-verifies

**API Response:**
```json
{
  "breakpoint_id": "bp_123",
  "verified": false,
  "message": "Source file not found. Breakpoint pending.",
  "file": "/path/to/missing.py",
  "line": 10
}
```

---

### 4.3 Multiple Simultaneous Breakpoint Hits (Threading)

**Scenario:** Multi-threaded script hits breakpoints in multiple threads simultaneously.

**Expected Behavior:**
- All threads pause when any breakpoint hit (default)
- Status endpoint returns all stopped threads
- Agent can inspect/control each thread independently
- Configuration option for "stop all" vs "stop only hitting thread"

**API Response:**
```json
{
  "status": "paused",
  "reason": "breakpoint",
  "stopped_threads": [
    {"thread_id": 1, "name": "MainThread", "breakpoint_id": "bp_1", "location": {...}},
    {"thread_id": 2, "name": "Worker-1", "breakpoint_id": "bp_2", "location": {...}}
  ],
  "all_threads": [
    {"thread_id": 1, "name": "MainThread", "status": "paused"},
    {"thread_id": 2, "name": "Worker-1", "status": "paused"},
    {"thread_id": 3, "name": "Worker-2", "status": "paused"}
  ]
}
```

**Thread-specific operations:**
- `POST /sessions/{id}/threads/{tid}/continue` - Resume single thread
- `GET /sessions/{id}/threads/{tid}/stacktrace` - Thread-specific stack

---

### 4.4 Very Long-Running Scripts

**Scenario:** Script runs for hours (e.g., ML training, data processing).

**Considerations:**
- Session must not timeout during legitimate long runs
- Breakpoint management must work while running
- Pause-on-demand functionality needed
- Output buffering must not consume unlimited memory

**Handling:**
- Heartbeat mechanism: `GET /sessions/{id}/ping` resets timeout
- Activity detection: Any debug operation resets timeout
- Output streaming: `GET /sessions/{id}/output?since=cursor` with pagination
- Memory limits: Output buffer capped (configurable), older entries dropped
- Pause anytime: `POST /sessions/{id}/pause` works on running script

---

### 4.5 Scripts Spawning Subprocesses

**Scenario:** Main script spawns child processes (subprocess, multiprocessing).

**Expected Behavior (MVP):**
- Child processes NOT automatically debugged
- Clear documentation of limitation
- Main process debugging unaffected

**Future Enhancement:**
- `POST /sessions/{id}/launch` with `{debug_subprocesses: true}`
- Child processes connect to relay automatically
- Unified session manages all processes

**API Response (when subprocess detected):**
```json
{
  "event": "subprocess_spawned",
  "pid": 12345,
  "debuggable": false,
  "message": "Subprocess spawned but not attached. Enable debug_subprocesses for child debugging."
}
```

---

### 4.6 Scripts Requiring User Input (stdin)

**Scenario:** Script calls `input()` or reads from stdin.

**Handling Options:**

1. **Provide input via API:**
```json
POST /sessions/{id}/stdin
{"input": "user response\n"}
```

2. **Pre-configure inputs:**
```json
POST /sessions/{id}/launch
{"stdin_inputs": ["response1", "response2"]}
```

3. **Status indication:**
```json
{
  "status": "waiting_for_input",
  "prompt": "Enter your name: "
}
```

---

### 4.7 Large Variable Inspection (Huge Data Structures)

**Scenario:** Variable is a massive DataFrame, list with millions of items, or deeply nested object.

**Handling:**
- **Lazy loading:** Only return top-level structure initially
- **Pagination:** `GET /sessions/{id}/frames/{fid}/variables/{var_id}/children?offset=0&limit=100`
- **Truncation:** String values truncated with indicator
- **Summary mode:** `GET /sessions/{id}/frames/{fid}/variables?summary=true` returns type/size only

**API Response:**
```json
{
  "name": "large_list",
  "type": "list",
  "length": 1000000,
  "value": "[0, 1, 2, 3, 4, ... (1000000 items)]",
  "truncated": true,
  "expandable": true,
  "variable_reference": 12345
}
```

**Expansion request:**
```json
GET /sessions/{id}/variables/12345?start=0&count=50

{
  "items": [
    {"index": 0, "value": "...", "type": "..."},
    {"index": 1, "value": "...", "type": "..."},
    ...
  ],
  "total": 1000000,
  "has_more": true
}
```

---

### 4.8 Circular References in Objects

**Scenario:** Object contains circular reference (e.g., parent-child, graph nodes).

**Handling:**
- Detect circular references during serialization
- Replace with reference marker
- Provide variable_reference for navigation

**API Response:**
```json
{
  "name": "node",
  "type": "TreeNode",
  "properties": [
    {"name": "value", "value": "root", "type": "str"},
    {"name": "parent", "value": "<circular: node>", "type": "TreeNode", "circular": true},
    {"name": "children", "type": "list", "length": 3, "expandable": true}
  ]
}
```

---

### 4.9 Additional Edge Cases

| Edge Case | Handling |
|-----------|----------|
| **Script modifies its own source** | Breakpoints remain at original lines; warning issued |
| **Debugger step into C extension** | Step completes, marked as "native frame" |
| **Recursive function (deep stack)** | Stack trace paginated, depth limit configurable |
| **Script changes working directory** | Relative paths resolved from original cwd |
| **Multiple Python versions** | Session specifies Python interpreter path |
| **Virtual environment** | Launch config includes venv activation |
| **Script with very fast breakpoint** | Ensure pause happens before response returns |
| **Unicode in variable names/values** | Full UTF-8 support, proper JSON encoding |
| **Binary data in variables** | Base64 encoded with metadata |
| **Exception in __repr__** | Fallback to type/id display |

---

## 5. Feature Requirements

### 5.1 Session Lifecycle Management

| Feature | Endpoint | Description | Priority |
|---------|----------|-------------|----------|
| Create session | `POST /sessions` | Initialize new debug session | P0 |
| List sessions | `GET /sessions` | List all active sessions | P0 |
| Get session status | `GET /sessions/{id}` | Get detailed session state | P0 |
| Terminate session | `DELETE /sessions/{id}` | End session, cleanup resources | P0 |
| Session configuration | `PATCH /sessions/{id}` | Update session settings | P1 |
| Clone session | `POST /sessions/{id}/clone` | Duplicate session config | P2 |

**Session States:**
```
created --> launching --> running --> paused --> running --> terminated
                |                        |
                v                        v
             failed                  terminated (error)
```

---

### 5.2 Program Execution Control

| Feature | Endpoint | Description | Priority |
|---------|----------|-------------|----------|
| Launch program | `POST /sessions/{id}/launch` | Start debugging script | P0 |
| Attach to process | `POST /sessions/{id}/attach` | Attach to running process | P1 |
| Continue | `POST /sessions/{id}/continue` | Resume execution | P0 |
| Pause | `POST /sessions/{id}/pause` | Pause running program | P0 |
| Step over | `POST /sessions/{id}/step-over` | Step to next line | P0 |
| Step into | `POST /sessions/{id}/step-into` | Step into function call | P0 |
| Step out | `POST /sessions/{id}/step-out` | Step out of function | P0 |
| Restart | `POST /sessions/{id}/restart` | Restart program | P1 |
| Detach | `POST /sessions/{id}/detach` | Detach without terminating target | P1 |
| Terminate target | `POST /sessions/{id}/terminate` | Kill debug target only | P1 |

---

### 5.3 Breakpoint Management

| Feature | Endpoint | Description | Priority |
|---------|----------|-------------|----------|
| Add breakpoint | `POST /sessions/{id}/breakpoints` | Set new breakpoint | P0 |
| List breakpoints | `GET /sessions/{id}/breakpoints` | Get all breakpoints | P0 |
| Remove breakpoint | `DELETE /sessions/{id}/breakpoints/{bp_id}` | Remove breakpoint | P0 |
| Update breakpoint | `PATCH /sessions/{id}/breakpoints/{bp_id}` | Modify breakpoint | P1 |
| Disable breakpoint | `PATCH /sessions/{id}/breakpoints/{bp_id}` | Disable without removing | P1 |
| Conditional breakpoint | Via `POST /breakpoints` | Break only on condition | P0 |
| Hit count breakpoint | Via `POST /breakpoints` | Break after N hits | P1 |
| Logpoint | Via `POST /breakpoints` | Log without breaking | P2 |
| Function breakpoint | `POST /sessions/{id}/breakpoints` | Break on function entry | P1 |
| Exception breakpoint | `POST /sessions/{id}/exception-breakpoints` | Break on exceptions | P0 |

**Breakpoint Request Schema:**
```json
{
  "source": {"path": "/path/to/file.py"},
  "line": 42,
  "condition": "x > 10",          // optional
  "hit_condition": ">= 5",        // optional
  "log_message": "x = {x}",       // optional (makes it a logpoint)
  "enabled": true                 // optional, default true
}
```

---

### 5.4 State Inspection

| Feature | Endpoint | Description | Priority |
|---------|----------|-------------|----------|
| Get stack trace | `GET /sessions/{id}/stacktrace` | Get call stack | P0 |
| Get scopes | `GET /sessions/{id}/frames/{frame_id}/scopes` | Get variable scopes | P0 |
| Get variables | `GET /sessions/{id}/scopes/{scope_id}/variables` | Get variables in scope | P0 |
| Expand variable | `GET /sessions/{id}/variables/{var_ref}` | Get child variables | P0 |
| Evaluate expression | `POST /sessions/{id}/evaluate` | Eval in current context | P0 |
| Watch expression | `POST /sessions/{id}/watch` | Add persistent watch | P1 |
| Get threads | `GET /sessions/{id}/threads` | List all threads | P0 |
| Set variable | `POST /sessions/{id}/variables/{var_ref}/set` | Modify variable value | P1 |
| Get completions | `POST /sessions/{id}/completions` | Autocomplete in context | P2 |
| Get hover info | `POST /sessions/{id}/hover` | Variable info at position | P2 |

**Evaluate Request Schema:**
```json
{
  "expression": "len(my_list)",
  "frame_id": 0,                  // optional, default to top frame
  "context": "watch"              // "watch", "repl", or "hover"
}
```

---

### 5.5 Output Handling

| Feature | Endpoint | Description | Priority |
|---------|----------|-------------|----------|
| Get output | `GET /sessions/{id}/output` | Get stdout/stderr | P0 |
| Stream output | `GET /sessions/{id}/output/stream` | SSE output stream | P2 |
| Send input | `POST /sessions/{id}/input` | Send stdin | P1 |
| Clear output | `DELETE /sessions/{id}/output` | Clear output buffer | P2 |

**Output Response Schema:**
```json
{
  "outputs": [
    {"type": "stdout", "text": "Hello, world!\n", "timestamp": "..."},
    {"type": "stderr", "text": "Warning: ...\n", "timestamp": "..."}
  ],
  "cursor": "abc123",
  "has_more": false
}
```

---

### 5.6 Multi-File Support

| Feature | Description | Priority |
|---------|-------------|----------|
| Cross-file breakpoints | Set breakpoints in any project file | P0 |
| Module resolution | Resolve imports to actual file paths | P0 |
| Source mapping | Map executed code to source files | P0 |
| Working directory | Support custom cwd for relative imports | P0 |
| PYTHONPATH config | Configure additional import paths | P1 |
| Virtual environment | Support venv/conda environments | P1 |

---

### 5.7 Persistence Layer

| Feature | Endpoint | Description | Priority |
|---------|----------|-------------|----------|
| Save breakpoints | Automatic | Persist breakpoints to disk | P1 |
| Load breakpoints | Automatic on start | Restore breakpoints on restart | P1 |
| Export session | `GET /sessions/{id}/export` | Export session configuration | P2 |
| Import session | `POST /sessions/import` | Import session configuration | P2 |
| Breakpoint profiles | `GET /breakpoint-profiles` | Named breakpoint sets | P2 |

**Persistence Storage:**
- Location: `~/.opencode-debugger/` or configurable
- Format: JSON files
- Files:
  - `breakpoints.json` - Global breakpoint definitions
  - `sessions/` - Session state backups
  - `config.json` - Server configuration

---

### 5.8 Server Management

| Feature | Endpoint | Description | Priority |
|---------|----------|-------------|----------|
| Health check | `GET /health` | Server health status | P0 |
| Server info | `GET /info` | Version, capabilities | P0 |
| Configuration | `GET /config` | Current server config | P1 |
| Update config | `PATCH /config` | Update runtime config | P2 |
| Shutdown | `POST /shutdown` | Graceful shutdown | P1 |

---

## 6. Success KPIs

### 6.1 Reliability Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Session success rate | > 99% | Sessions completing without crash / Total sessions |
| Breakpoint accuracy | 100% | Breakpoints hit exactly at specified lines |
| State consistency | 100% | Variables match actual runtime values |
| Session recovery | > 95% | Sessions restorable after relay restart |

### 6.2 Performance Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Session creation latency | < 500ms | Time from POST to session ready |
| Breakpoint set latency | < 100ms | Time to set and verify breakpoint |
| Step operation latency | < 200ms | Time for step-over/into/out |
| Variable inspection latency | < 300ms | Time to retrieve scope variables |
| Expression evaluation latency | < 500ms | Time to evaluate simple expressions |
| Status polling latency | < 50ms | Time for status endpoint response |

### 6.3 Feature Coverage

| Category | debugpy Features | Target Coverage |
|----------|------------------|-----------------|
| Execution Control | 8 operations | 100% |
| Breakpoints | 6 types | 100% |
| Inspection | 5 capabilities | 100% |
| Advanced | 4 features | 75% (v1) |

### 6.4 Usability Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| API discoverability | Self-documenting | OpenAPI spec available |
| Error clarity | Actionable errors | All errors include resolution hints |
| Documentation coverage | 100% | All endpoints documented with examples |
| Onboarding time | < 10 minutes | Time for agent to complete first debug session |

### 6.5 Adoption Metrics

| Metric | Target (6 months) | Measurement |
|--------|-------------------|-------------|
| Daily active sessions | 100+ | Unique sessions per day |
| Agent integrations | 3+ | Different AI agents using API |
| Bug resolution improvement | 40% faster | Time to fix bugs with vs without debugger |

---

## 7. Acceptance Criteria

### 7.1 Session Management

- [ ] **AC-SM-1:** Creating a session returns a unique session ID within 500ms
- [ ] **AC-SM-2:** Listing sessions returns all active sessions with their current status
- [ ] **AC-SM-3:** Deleting a session terminates the debug target and cleans up resources
- [ ] **AC-SM-4:** Sessions automatically terminate after configurable idle timeout (default 60 min)
- [ ] **AC-SM-5:** Server supports at least 10 concurrent debug sessions

### 7.2 Program Launching

- [ ] **AC-PL-1:** Launching a script with valid path starts debugging within 2 seconds
- [ ] **AC-PL-2:** Launch with command-line arguments passes them correctly to script
- [ ] **AC-PL-3:** Launch with environment variables makes them available to script
- [ ] **AC-PL-4:** Launch with custom working directory affects relative imports correctly
- [ ] **AC-PL-5:** Launch failure (syntax error) returns detailed error with line number
- [ ] **AC-PL-6:** Launch with Python path uses specified interpreter

### 7.3 Breakpoint Management

- [ ] **AC-BP-1:** Setting breakpoint on valid line returns verified=true
- [ ] **AC-BP-2:** Setting breakpoint on invalid line (comment/blank) returns verified=false with explanation
- [ ] **AC-BP-3:** Conditional breakpoint only pauses when condition is true
- [ ] **AC-BP-4:** Hit count breakpoint pauses after specified number of hits
- [ ] **AC-BP-5:** Removing breakpoint prevents future pauses at that location
- [ ] **AC-BP-6:** Disabled breakpoint does not cause pause
- [ ] **AC-BP-7:** Breakpoints persist across relay server restarts
- [ ] **AC-BP-8:** Exception breakpoints pause on specified exception types

### 7.4 Execution Control

- [ ] **AC-EC-1:** Continue resumes execution until next breakpoint or termination
- [ ] **AC-EC-2:** Step Over advances to next line without entering function calls
- [ ] **AC-EC-3:** Step Into enters function call on current line
- [ ] **AC-EC-4:** Step Out completes current function and pauses at caller
- [ ] **AC-EC-5:** Pause stops running program within 1 second
- [ ] **AC-EC-6:** All step operations return new location in response

### 7.5 State Inspection

- [ ] **AC-SI-1:** Stack trace returns all frames with file, line, and function name
- [ ] **AC-SI-2:** Variables request returns all local variables with values
- [ ] **AC-SI-3:** Complex objects are expandable via variable reference
- [ ] **AC-SI-4:** Expression evaluation returns correct result and type
- [ ] **AC-SI-5:** Invalid expression evaluation returns clear error message
- [ ] **AC-SI-6:** Large variables are truncated with expandable indicator
- [ ] **AC-SI-7:** Circular references are detected and marked

### 7.6 Multi-File Support

- [ ] **AC-MF-1:** Breakpoints can be set in imported modules
- [ ] **AC-MF-2:** Stack trace shows frames from multiple files
- [ ] **AC-MF-3:** Step Into follows into imported module code
- [ ] **AC-MF-4:** Source file content retrievable for any frame

### 7.7 Output Handling

- [ ] **AC-OH-1:** stdout output from script is captured and retrievable
- [ ] **AC-OH-2:** stderr output from script is captured and retrievable
- [ ] **AC-OH-3:** Output includes timestamps for ordering
- [ ] **AC-OH-4:** Output is paginated to handle large volumes

### 7.8 Error Handling

- [ ] **AC-EH-1:** All error responses include error code and human-readable message
- [ ] **AC-EH-2:** Invalid session ID returns 404 with clear message
- [ ] **AC-EH-3:** Invalid request body returns 400 with validation errors
- [ ] **AC-EH-4:** Server errors return 500 with debugging information
- [ ] **AC-EH-5:** Timeout errors return 504 with retry guidance

### 7.9 Persistence

- [ ] **AC-PE-1:** Breakpoints are saved automatically when set
- [ ] **AC-PE-2:** Breakpoints are restored when relay restarts
- [ ] **AC-PE-3:** Persistence file location is configurable
- [ ] **AC-PE-4:** Invalid persistence data handled gracefully (start fresh)

### 7.10 Security

- [ ] **AC-SE-1:** Server binds to localhost only by default
- [ ] **AC-SE-2:** Configurable bind address with security warning for non-localhost
- [ ] **AC-SE-3:** No arbitrary code execution outside debug target
- [ ] **AC-SE-4:** File access limited to readable files (respects OS permissions)

---

## 8. Out of Scope (v1)

The following features are explicitly **NOT** included in v1:

### 8.1 Definitely Out

| Feature | Reason | Future Version |
|---------|--------|----------------|
| **WebSocket/real-time events** | Polling sufficient for MVP; adds complexity | v2 |
| **GUI/Web dashboard** | Agent-first; GUIs can be built on API later | v2+ |
| **Remote debugging (non-localhost)** | Security implications; requires auth | v2 |
| **Multi-language support** | Python-only focus for v1 | v3+ |
| **Profiling/performance analysis** | Separate concern from debugging | v2+ |
| **Memory debugging/leak detection** | Specialized tooling needed | v3+ |
| **Distributed debugging** | Complex; needs design | v3+ |
| **IDE plugins** | API is the interface; plugins can be built later | Community |
| **Hot code reloading** | Complex Python feature | v3+ |
| **Time-travel debugging** | Requires execution recording | v3+ |

### 8.2 Simplified for v1

| Feature | v1 Behavior | Full Behavior (Later) |
|---------|-------------|----------------------|
| **Subprocess debugging** | Main process only | All child processes |
| **Thread control** | Stop all threads | Per-thread control |
| **Async debugging** | Basic support | Full coroutine inspection |
| **Just My Code** | Debug all code | Filter out library code |
| **Authentication** | None (localhost only) | API keys, OAuth |
| **Rate limiting** | None | Configurable limits |
| **Metrics/observability** | Basic health endpoint | Full OpenTelemetry |

### 8.3 Assumptions for v1

1. **One Python version per session** - No mixed-version debugging
2. **Local filesystem access** - Script files must be on same machine as relay
3. **Standard Python** - CPython only, no PyPy/Jython
4. **Single machine** - Debug target and relay on same host
5. **No container awareness** - Works in containers but not container-specific features

---

## 9. Technical Notes

### 9.1 Architecture Overview

```
+----------------+     HTTP/JSON      +-------------------+     DAP      +----------+
|   AI Agent     | <----------------> |  Debug Relay      | <----------> |  debugpy |
| (Claude, etc.) |                    |  Server (Python)  |              |          |
+----------------+                    +-------------------+              +----------+
                                             |                                 |
                                             v                                 v
                                      +--------------+                  +-----------+
                                      | Persistence  |                  |  Target   |
                                      | (JSON files) |                  |  Script   |
                                      +--------------+                  +-----------+
```

### 9.2 Technology Stack (Recommended)

| Component | Technology | Rationale |
|-----------|------------|-----------|
| HTTP Server | FastAPI | Async, auto-docs, Pydantic validation |
| Debug Backend | debugpy | Official VS Code adapter, well-maintained |
| Persistence | JSON files | Simple, human-readable, no dependencies |
| Testing | pytest | Standard, debugpy compatible |

### 9.3 Key Dependencies

- Python 3.9+ (for typing features)
- debugpy >= 1.6.0 (DAP protocol support)
- FastAPI >= 0.100.0 (HTTP framework)
- uvicorn (ASGI server)
- pydantic (request/response validation)

---

## 10. Open Questions

| # | Question | Impact | Owner | Status |
|---|----------|--------|-------|--------|
| 1 | Should sessions auto-save state for resume after relay crash? | Reliability | TBD | Open |
| 2 | What's the maximum reasonable number of concurrent sessions? | Resource planning | TBD | Open |
| 3 | Should we support debugpy's "just my code" feature in v1? | Scope | TBD | Open |
| 4 | How should we handle very large output (>100MB)? | Memory | TBD | Open |
| 5 | Should breakpoint persistence be per-project or global? | UX | TBD | Open |

---

## 11. Appendix

### A. Example API Interaction (Complete Session)

```bash
# 1. Create session
curl -X POST http://localhost:5678/sessions \
  -H "Content-Type: application/json" \
  -d '{"name": "debug-my-script"}'
# Response: {"session_id": "sess_abc123", "status": "created"}

# 2. Set breakpoint
curl -X POST http://localhost:5678/sessions/sess_abc123/breakpoints \
  -H "Content-Type: application/json" \
  -d '{"source": {"path": "/code/main.py"}, "line": 10}'
# Response: {"breakpoint_id": "bp_1", "verified": true}

# 3. Launch program
curl -X POST http://localhost:5678/sessions/sess_abc123/launch \
  -H "Content-Type: application/json" \
  -d '{"script": "/code/main.py", "args": ["--verbose"]}'
# Response: {"status": "running"}

# 4. Poll for status (would hit breakpoint)
curl http://localhost:5678/sessions/sess_abc123/status
# Response: {"status": "paused", "reason": "breakpoint", "location": {"file": "/code/main.py", "line": 10}}

# 5. Get stack trace
curl http://localhost:5678/sessions/sess_abc123/stacktrace
# Response: {"frames": [{"id": 0, "name": "main", "file": "/code/main.py", "line": 10}, ...]}

# 6. Get variables
curl http://localhost:5678/sessions/sess_abc123/frames/0/scopes
# Response: {"scopes": [{"name": "Locals", "reference": 1000}, {"name": "Globals", "reference": 1001}]}

curl http://localhost:5678/sessions/sess_abc123/scopes/1000/variables
# Response: {"variables": [{"name": "x", "value": "42", "type": "int"}, ...]}

# 7. Evaluate expression
curl -X POST http://localhost:5678/sessions/sess_abc123/evaluate \
  -H "Content-Type: application/json" \
  -d '{"expression": "x * 2"}'
# Response: {"result": "84", "type": "int"}

# 8. Step over
curl -X POST http://localhost:5678/sessions/sess_abc123/step-over
# Response: {"status": "paused", "location": {"file": "/code/main.py", "line": 11}}

# 9. Continue
curl -X POST http://localhost:5678/sessions/sess_abc123/continue
# Response: {"status": "running"}

# 10. Check completion
curl http://localhost:5678/sessions/sess_abc123/status
# Response: {"status": "terminated", "exit_code": 0}

# 11. Cleanup
curl -X DELETE http://localhost:5678/sessions/sess_abc123
# Response: {"deleted": true}
```

### B. Error Response Format

```json
{
  "error": {
    "code": "BREAKPOINT_INVALID_LINE",
    "message": "Cannot set breakpoint at line 5: line contains only whitespace",
    "details": {
      "file": "/code/main.py",
      "line": 5,
      "content": "    ",
      "suggestion": "Try line 6 which contains: 'def process_data(items):'"
    }
  }
}
```

### C. Status Response States

| Status | Description | Next Actions |
|--------|-------------|--------------|
| `created` | Session initialized, no program | Launch or attach |
| `launching` | Program starting | Wait for running/paused |
| `running` | Program executing | Pause, wait for breakpoint |
| `paused` | Stopped at breakpoint/step | Inspect, step, continue |
| `terminated` | Program ended | Get output, delete session |
| `failed` | Error occurred | Check error, retry or delete |

---

**Document Revision History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-13 | Product Manager Agent | Initial comprehensive user story |
