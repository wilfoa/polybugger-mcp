---
name: python-debug
description: Debug Python code interactively using the Python Debugger MCP - set breakpoints, inspect variables, step through code, and evaluate expressions via HTTP API
license: MIT
compatibility: opencode
metadata:
  language: python
  category: debugging
  requires: python-debugger-mcp server running
---

# Python Debug Skill

This skill enables interactive Python debugging through the Python Debugger MCP. Use this when you need to debug Python code by setting breakpoints, stepping through execution, inspecting variables, and evaluating expressions.

## Prerequisites

The Python Debugger MCP must be running. Start it with:

```bash
cd /path/to/python_debugger_mcp
source .venv/bin/activate
python -m python_debugger_mcp.main
```

The server runs on `http://127.0.0.1:5679` by default.

## When to Use This Skill

Use this skill when:
- You need to debug a Python script or application
- You want to set breakpoints and inspect program state
- You need to step through code line by line
- You want to evaluate expressions in the context of stopped code
- You need to understand why code is behaving unexpectedly

## API Endpoints

### Session Management

**Create a debug session:**
```bash
curl -X POST http://127.0.0.1:5679/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"project_root": "/path/to/project"}'
```

**Launch a program:**
```bash
curl -X POST http://127.0.0.1:5679/api/v1/sessions/{session_id}/launch \
  -H "Content-Type: application/json" \
  -d '{"program": "/path/to/script.py", "stop_on_entry": true}'
```

**Get session status:**
```bash
curl http://127.0.0.1:5679/api/v1/sessions/{session_id}
```

### Breakpoints

**Set breakpoints:**
```bash
curl -X POST http://127.0.0.1:5679/api/v1/sessions/{session_id}/breakpoints \
  -H "Content-Type: application/json" \
  -d '{
    "source": "/path/to/file.py",
    "breakpoints": [
      {"line": 10},
      {"line": 25, "condition": "x > 5"}
    ]
  }'
```

### Execution Control

**Continue execution:**
```bash
curl -X POST http://127.0.0.1:5679/api/v1/sessions/{session_id}/continue
```

**Step over (next line):**
```bash
curl -X POST http://127.0.0.1:5679/api/v1/sessions/{session_id}/step-over
```

**Step into function:**
```bash
curl -X POST http://127.0.0.1:5679/api/v1/sessions/{session_id}/step-into
```

**Step out of function:**
```bash
curl -X POST http://127.0.0.1:5679/api/v1/sessions/{session_id}/step-out
```

**Pause execution:**
```bash
curl -X POST http://127.0.0.1:5679/api/v1/sessions/{session_id}/pause
```

### Inspection

**Get threads:**
```bash
curl http://127.0.0.1:5679/api/v1/sessions/{session_id}/threads
```

**Get stack trace:**
```bash
curl "http://127.0.0.1:5679/api/v1/sessions/{session_id}/stacktrace?thread_id=1"
```

**Get scopes (locals, globals):**
```bash
curl "http://127.0.0.1:5679/api/v1/sessions/{session_id}/scopes?frame_id=1"
```

**Get variables:**
```bash
curl "http://127.0.0.1:5679/api/v1/sessions/{session_id}/variables?ref=1"
```

**Evaluate expression:**
```bash
curl -X POST http://127.0.0.1:5679/api/v1/sessions/{session_id}/evaluate \
  -H "Content-Type: application/json" \
  -d '{"expression": "len(my_list)", "frame_id": 1}'
```

### Events and Output

**Poll for events (long-polling):**
```bash
curl "http://127.0.0.1:5679/api/v1/sessions/{session_id}/events?timeout=10"
```

**Get captured output:**
```bash
curl http://127.0.0.1:5679/api/v1/sessions/{session_id}/output
```

## Debugging Workflow

1. **Create a session** for your project
2. **Set breakpoints** on lines you want to inspect
3. **Launch** the program
4. **Poll for events** to detect when execution stops
5. **Inspect state** using threads, stacktrace, scopes, variables
6. **Evaluate expressions** to test hypotheses
7. **Step** through code or **continue** to next breakpoint
8. **Repeat** until issue is found

## Session States

- `created` - Session initialized, ready to launch
- `launching` - Program is being launched
- `running` - Program is executing
- `paused` - Execution stopped (breakpoint, step, or entry)
- `terminated` - Program has ended
- `failed` - An error occurred

## Event Types

- `stopped` - Execution paused (includes reason: breakpoint, step, entry, exception)
- `continued` - Execution resumed
- `terminated` - Debug session ended
- `exited` - Debuggee process exited
- `output` - Program produced output
- `thread` - Thread started or exited
- `breakpoint` - Breakpoint status changed

## Tips

- Use `stop_on_entry: true` to pause at the first line
- Set conditional breakpoints to stop only when specific conditions are met
- Use `stop_on_exception: true` to break on uncaught exceptions
- Poll events with timeout for efficient long-polling
- The server supports up to 10 concurrent debug sessions
