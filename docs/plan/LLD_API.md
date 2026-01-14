# Low-Level Design: API Specification

**Project:** OpenCode Debug Relay Server
**Document Version:** 1.0
**Created:** January 13, 2026
**Status:** Design Complete
**Author:** API Designer Agent

---

## Table of Contents

1. [API Overview](#1-api-overview)
2. [Common Patterns](#2-common-patterns)
3. [Endpoint Specifications](#3-endpoint-specifications)
4. [Request/Response Schemas](#4-requestresponse-schemas)
5. [Error Codes](#5-error-codes)
6. [Event Types](#6-event-types)
7. [OpenAPI Spec Outline](#7-openapi-spec-outline)
8. [Client Usage Examples](#8-client-usage-examples)

---

## 1. API Overview

### 1.1 Base Configuration

| Property | Value |
|----------|-------|
| Base URL | `http://localhost:5679/api/v1/` |
| Protocol | HTTP/1.1 |
| Content-Type | `application/json` |
| Character Encoding | UTF-8 |
| Authentication | None (localhost only) |
| Rate Limiting | None (v1) |
| Max Request Body | 10MB |
| Default Timeout | 30 seconds |

### 1.2 HTTP Methods

| Method | Usage |
|--------|-------|
| GET | Retrieve resources, read-only operations |
| POST | Create resources, execute actions |
| DELETE | Remove resources |
| PATCH | Partial updates (reserved for future use) |

### 1.3 URL Structure

```
/api/v1/{resource}[/{id}][/{sub-resource}][/{sub-id}]
```

**Examples:**
- `/api/v1/sessions` - Session collection
- `/api/v1/sessions/sess_abc123` - Specific session
- `/api/v1/sessions/sess_abc123/breakpoints` - Breakpoints for session
- `/api/v1/sessions/sess_abc123/breakpoints/bp_1` - Specific breakpoint

### 1.4 ID Format

| Resource | Format | Example |
|----------|--------|---------|
| Session | `sess_{uuid8}` | `sess_a1b2c3d4` |
| Breakpoint | `bp_{sequence}` | `bp_1`, `bp_42` |
| Thread | Integer | `1`, `2`, `3` |
| Frame | Integer (0-indexed) | `0`, `1`, `2` |
| Variable Reference | Integer | `1000`, `1001` |
| Request ID | UUID v4 | `550e8400-e29b-41d4-a716-446655440000` |

---

## 2. Common Patterns

### 2.1 Response Envelope

All API responses use a consistent envelope structure:

**Success Response:**
```json
{
  "success": true,
  "data": {
    "...response data..."
  },
  "error": null,
  "meta": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2026-01-13T10:30:00.123Z"
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "SESSION_NOT_FOUND",
    "message": "Session with ID 'sess_invalid' not found",
    "details": {
      "session_id": "sess_invalid",
      "suggestion": "Use GET /api/v1/sessions to list active sessions"
    }
  },
  "meta": {
    "request_id": "550e8400-e29b-41d4-a716-446655440001",
    "timestamp": "2026-01-13T10:30:01.456Z"
  }
}
```

### 2.2 Pagination

For endpoints returning collections:

**Query Parameters:**
| Parameter | Type | Default | Max | Description |
|-----------|------|---------|-----|-------------|
| `offset` | integer | 0 | - | Number of items to skip |
| `limit` | integer | 100 | 1000 | Maximum items to return |

**Response Fields:**
```json
{
  "success": true,
  "data": {
    "items": [...],
    "total": 250,
    "offset": 0,
    "limit": 100,
    "has_more": true
  }
}
```

### 2.3 Cursor-Based Pagination

For output/events streams with continuous data:

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `cursor` | string | Opaque cursor from previous response |
| `limit` | integer | Maximum items to return |

**Response Fields:**
```json
{
  "success": true,
  "data": {
    "items": [...],
    "next_cursor": "eyJvZmZzZXQiOjEwMH0=",
    "has_more": true
  }
}
```

### 2.4 Common Headers

**Request Headers:**
| Header | Required | Value |
|--------|----------|-------|
| `Content-Type` | Yes (for POST) | `application/json` |
| `Accept` | No | `application/json` |
| `X-Request-ID` | No | Client-provided request ID |

**Response Headers:**
| Header | Description |
|--------|-------------|
| `Content-Type` | `application/json; charset=utf-8` |
| `X-Request-ID` | Request tracking ID (echoes client or generated) |

### 2.5 Source Location Format

Used throughout API for file/line references:

```json
{
  "path": "/absolute/path/to/file.py",
  "line": 42,
  "column": 8,
  "end_line": 42,
  "end_column": 15
}
```

---

## 3. Endpoint Specifications

### 3.1 Server Endpoints

---

### GET /health

**Description:** Check server health and readiness status.

**Request:**
- Headers: None required
- Path params: None
- Query params: None
- Body: None

**Response:**

| Status | Description |
|--------|-------------|
| 200 | Server is healthy |
| 503 | Server is unhealthy |

**200 Response Schema:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "uptime_seconds": 3600,
    "active_sessions": 3,
    "debugpy_available": true
  },
  "error": null,
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  }
}
```

**Example:**
```bash
curl http://localhost:5679/api/v1/health
```

```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "uptime_seconds": 7245,
    "active_sessions": 2,
    "debugpy_available": true
  },
  "error": null,
  "meta": {
    "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "timestamp": "2026-01-13T14:30:00.000Z"
  }
}
```

---

### GET /info

**Description:** Get server information and capabilities.

**Request:**
- Headers: None required
- Path params: None
- Query params: None
- Body: None

**Response:**

| Status | Description |
|--------|-------------|
| 200 | Server information |

**200 Response Schema:**
```json
{
  "success": true,
  "data": {
    "name": "OpenCode Debug Relay Server",
    "version": "1.0.0",
    "api_version": "v1",
    "python_version": "3.11.5",
    "debugpy_version": "1.8.0",
    "capabilities": {
      "supports_conditional_breakpoints": true,
      "supports_hit_conditional_breakpoints": true,
      "supports_log_points": true,
      "supports_exception_breakpoints": true,
      "supports_function_breakpoints": true,
      "supports_evaluate": true,
      "supports_set_variable": false,
      "supports_restart": true,
      "supports_attach": true,
      "max_sessions": 10
    },
    "endpoints": [
      "/api/v1/sessions",
      "/api/v1/health",
      "/api/v1/info"
    ]
  },
  "error": null,
  "meta": {...}
}
```

**Example:**
```bash
curl http://localhost:5679/api/v1/info
```

---

### 3.2 Session Management

---

### POST /sessions

**Description:** Create a new debug session. A session represents a single debug context that can be used to launch or attach to a debuggee.

**Request:**
- Headers: `Content-Type: application/json`
- Path params: None
- Query params: None

**Request Body Schema:**
```json
{
  "name": "string (optional)",
  "project_root": "string (optional)",
  "python_path": "string (optional)",
  "timeout_minutes": "integer (optional, default: 60)",
  "stop_on_entry": "boolean (optional, default: false)"
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | No | auto-generated | Human-readable session name |
| `project_root` | string | No | cwd | Root directory for project |
| `python_path` | string | No | system python | Python interpreter path |
| `timeout_minutes` | integer | No | 60 | Session idle timeout |
| `stop_on_entry` | boolean | No | false | Pause at program entry |

**Response:**

| Status | Description |
|--------|-------------|
| 201 | Session created |
| 400 | Invalid request body |
| 429 | Session limit reached |

**201 Response Schema:**
```json
{
  "success": true,
  "data": {
    "session_id": "sess_a1b2c3d4",
    "name": "debug-my-script",
    "status": "created",
    "created_at": "2026-01-13T10:30:00.000Z",
    "expires_at": "2026-01-13T11:30:00.000Z",
    "config": {
      "project_root": "/path/to/project",
      "python_path": "/usr/bin/python3",
      "stop_on_entry": false
    }
  },
  "error": null,
  "meta": {...}
}
```

**Example:**
```bash
curl -X POST http://localhost:5679/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "debug-my-script",
    "project_root": "/Users/dev/myproject",
    "python_path": "/usr/local/bin/python3.11"
  }'
```

---

### GET /sessions

**Description:** List all active debug sessions.

**Request:**
- Headers: None required
- Path params: None
- Query params:
  - `offset` (integer, optional): Pagination offset
  - `limit` (integer, optional): Pagination limit
  - `status` (string, optional): Filter by status

**Response:**

| Status | Description |
|--------|-------------|
| 200 | List of sessions |

**200 Response Schema:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "session_id": "sess_a1b2c3d4",
        "name": "debug-my-script",
        "status": "paused",
        "created_at": "2026-01-13T10:30:00.000Z",
        "program": "/path/to/script.py"
      }
    ],
    "total": 3,
    "offset": 0,
    "limit": 100,
    "has_more": false
  },
  "error": null,
  "meta": {...}
}
```

**Example:**
```bash
curl "http://localhost:5679/api/v1/sessions?status=paused"
```

---

### GET /sessions/{session_id}

**Description:** Get detailed information about a specific session including current execution state.

**Request:**
- Headers: None required
- Path params:
  - `session_id` (string, required): Session identifier
- Query params: None

**Response:**

| Status | Description |
|--------|-------------|
| 200 | Session details |
| 404 | Session not found |

**200 Response Schema:**
```json
{
  "success": true,
  "data": {
    "session_id": "sess_a1b2c3d4",
    "name": "debug-my-script",
    "status": "paused",
    "stop_reason": "breakpoint",
    "created_at": "2026-01-13T10:30:00.000Z",
    "expires_at": "2026-01-13T11:30:00.000Z",
    "config": {
      "project_root": "/path/to/project",
      "python_path": "/usr/bin/python3",
      "stop_on_entry": false
    },
    "program": {
      "script": "/path/to/script.py",
      "args": ["--verbose"],
      "cwd": "/path/to/project",
      "env": {}
    },
    "current_location": {
      "path": "/path/to/script.py",
      "line": 42,
      "column": 0,
      "function": "process_data"
    },
    "stopped_thread_id": 1,
    "breakpoint_count": 3,
    "exception": null
  },
  "error": null,
  "meta": {...}
}
```

**Session Status Values:**

| Status | Description |
|--------|-------------|
| `created` | Session initialized, no program launched |
| `launching` | Program is starting |
| `running` | Program is executing |
| `paused` | Execution paused (breakpoint/step/pause) |
| `terminated` | Program has ended |
| `failed` | Session encountered an error |

**Stop Reason Values (when status=paused):**

| Reason | Description |
|--------|-------------|
| `breakpoint` | Hit a breakpoint |
| `step` | Completed a step operation |
| `exception` | Exception was raised |
| `pause` | Manual pause requested |
| `entry` | Stopped at program entry |

**Example:**
```bash
curl http://localhost:5679/api/v1/sessions/sess_a1b2c3d4
```

---

### DELETE /sessions/{session_id}

**Description:** Terminate a debug session and release all resources. This will kill the debuggee if running.

**Request:**
- Headers: None required
- Path params:
  - `session_id` (string, required): Session identifier
- Query params:
  - `force` (boolean, optional): Force kill if graceful fails

**Response:**

| Status | Description |
|--------|-------------|
| 200 | Session terminated |
| 404 | Session not found |

**200 Response Schema:**
```json
{
  "success": true,
  "data": {
    "session_id": "sess_a1b2c3d4",
    "deleted": true,
    "final_status": "terminated",
    "exit_code": 0,
    "runtime_seconds": 125.5
  },
  "error": null,
  "meta": {...}
}
```

**Example:**
```bash
curl -X DELETE http://localhost:5679/api/v1/sessions/sess_a1b2c3d4
```

---

### 3.3 Program Control

---

### POST /sessions/{session_id}/launch

**Description:** Launch a Python script for debugging. The session must be in `created` status.

**Request:**
- Headers: `Content-Type: application/json`
- Path params:
  - `session_id` (string, required): Session identifier

**Request Body Schema:**
```json
{
  "script": "string (required)",
  "args": ["array of strings (optional)"],
  "cwd": "string (optional)",
  "env": {"object (optional)": "value"},
  "stop_on_entry": "boolean (optional)",
  "stop_on_exception": "boolean | string (optional)",
  "console": "string (optional)",
  "module": "string (optional)",
  "python_args": ["array of strings (optional)"]
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `script` | string | Yes* | - | Path to Python script |
| `module` | string | Yes* | - | Module to run (like `python -m`) |
| `args` | string[] | No | [] | Command-line arguments |
| `cwd` | string | No | project_root | Working directory |
| `env` | object | No | {} | Additional environment variables |
| `stop_on_entry` | boolean | No | false | Pause at first line |
| `stop_on_exception` | boolean/string | No | "uncaught" | Exception handling |
| `console` | string | No | "internalConsole" | Console type |
| `python_args` | string[] | No | [] | Python interpreter args |

*Either `script` or `module` must be provided, not both.

**stop_on_exception Values:**
- `true` - Stop on all exceptions
- `false` - Never stop on exceptions
- `"uncaught"` - Stop only on uncaught exceptions
- `"raised"` - Stop when exception is raised

**Response:**

| Status | Description |
|--------|-------------|
| 200 | Program launched |
| 400 | Invalid request |
| 404 | Session not found |
| 409 | Invalid session state |

**200 Response Schema:**
```json
{
  "success": true,
  "data": {
    "session_id": "sess_a1b2c3d4",
    "status": "running",
    "pid": 12345,
    "program": {
      "script": "/path/to/script.py",
      "args": ["--verbose"],
      "cwd": "/path/to/project"
    }
  },
  "error": null,
  "meta": {...}
}
```

**Example:**
```bash
curl -X POST http://localhost:5679/api/v1/sessions/sess_a1b2c3d4/launch \
  -H "Content-Type: application/json" \
  -d '{
    "script": "/Users/dev/myproject/main.py",
    "args": ["--input", "data.csv", "--verbose"],
    "cwd": "/Users/dev/myproject",
    "env": {
      "DEBUG": "1",
      "LOG_LEVEL": "DEBUG"
    },
    "stop_on_entry": true
  }'
```

**Example (module mode):**
```bash
curl -X POST http://localhost:5679/api/v1/sessions/sess_a1b2c3d4/launch \
  -H "Content-Type: application/json" \
  -d '{
    "module": "pytest",
    "args": ["-xvs", "tests/test_math.py::test_divide"],
    "cwd": "/Users/dev/myproject"
  }'
```

---

### POST /sessions/{session_id}/attach

**Description:** Attach to a running Python process that has debugpy enabled.

**Request:**
- Headers: `Content-Type: application/json`
- Path params:
  - `session_id` (string, required): Session identifier

**Request Body Schema:**
```json
{
  "pid": "integer (optional)",
  "host": "string (optional, default: localhost)",
  "port": "integer (optional)",
  "connect_timeout": "integer (optional, default: 10)"
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `pid` | integer | Yes* | - | Process ID to attach |
| `host` | string | No | "localhost" | debugpy host |
| `port` | integer | Yes* | - | debugpy listen port |
| `connect_timeout` | integer | No | 10 | Connection timeout (seconds) |

*Provide either `pid` or `host`+`port`.

**Response:**

| Status | Description |
|--------|-------------|
| 200 | Attached successfully |
| 400 | Invalid request |
| 404 | Session not found |
| 409 | Invalid session state |
| 504 | Connection timeout |

**200 Response Schema:**
```json
{
  "success": true,
  "data": {
    "session_id": "sess_a1b2c3d4",
    "status": "running",
    "attached": true,
    "pid": 12345,
    "host": "localhost",
    "port": 5678
  },
  "error": null,
  "meta": {...}
}
```

**Example:**
```bash
curl -X POST http://localhost:5679/api/v1/sessions/sess_a1b2c3d4/attach \
  -H "Content-Type: application/json" \
  -d '{
    "host": "localhost",
    "port": 5678,
    "connect_timeout": 15
  }'
```

---

### 3.4 Breakpoint Management

---

### POST /sessions/{session_id}/breakpoints

**Description:** Set one or more breakpoints in the debugging session.

**Request:**
- Headers: `Content-Type: application/json`
- Path params:
  - `session_id` (string, required): Session identifier

**Request Body Schema:**
```json
{
  "breakpoints": [
    {
      "source": {
        "path": "string (required)"
      },
      "line": "integer (required)",
      "condition": "string (optional)",
      "hit_condition": "string (optional)",
      "log_message": "string (optional)",
      "enabled": "boolean (optional, default: true)"
    }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `breakpoints` | array | Yes | Array of breakpoint definitions |
| `source.path` | string | Yes | Absolute path to source file |
| `line` | integer | Yes | Line number (1-indexed) |
| `condition` | string | No | Break only when expression is truthy |
| `hit_condition` | string | No | Break on hit count (e.g., ">5", "==10") |
| `log_message` | string | No | Log message instead of breaking (logpoint) |
| `enabled` | boolean | No | Whether breakpoint is active |

**Response:**

| Status | Description |
|--------|-------------|
| 200 | Breakpoints set |
| 400 | Invalid request |
| 404 | Session not found |

**200 Response Schema:**
```json
{
  "success": true,
  "data": {
    "breakpoints": [
      {
        "id": "bp_1",
        "verified": true,
        "source": {
          "path": "/path/to/script.py"
        },
        "line": 42,
        "condition": "x > 10",
        "hit_condition": null,
        "log_message": null,
        "enabled": true,
        "message": null
      },
      {
        "id": "bp_2",
        "verified": false,
        "source": {
          "path": "/path/to/other.py"
        },
        "line": 15,
        "condition": null,
        "hit_condition": null,
        "log_message": null,
        "enabled": true,
        "message": "No executable code at line 15"
      }
    ]
  },
  "error": null,
  "meta": {...}
}
```

**Example:**
```bash
curl -X POST http://localhost:5679/api/v1/sessions/sess_a1b2c3d4/breakpoints \
  -H "Content-Type: application/json" \
  -d '{
    "breakpoints": [
      {
        "source": {"path": "/Users/dev/myproject/main.py"},
        "line": 42
      },
      {
        "source": {"path": "/Users/dev/myproject/utils.py"},
        "line": 15,
        "condition": "len(items) > 100"
      },
      {
        "source": {"path": "/Users/dev/myproject/main.py"},
        "line": 50,
        "log_message": "Processing item: {item.name}"
      }
    ]
  }'
```

---

### GET /sessions/{session_id}/breakpoints

**Description:** List all breakpoints in the session.

**Request:**
- Headers: None required
- Path params:
  - `session_id` (string, required): Session identifier
- Query params:
  - `file` (string, optional): Filter by file path
  - `verified` (boolean, optional): Filter by verification status

**Response:**

| Status | Description |
|--------|-------------|
| 200 | List of breakpoints |
| 404 | Session not found |

**200 Response Schema:**
```json
{
  "success": true,
  "data": {
    "breakpoints": [
      {
        "id": "bp_1",
        "verified": true,
        "source": {
          "path": "/path/to/script.py"
        },
        "line": 42,
        "condition": null,
        "hit_condition": null,
        "log_message": null,
        "enabled": true,
        "hit_count": 3
      }
    ],
    "total": 5
  },
  "error": null,
  "meta": {...}
}
```

**Example:**
```bash
curl "http://localhost:5679/api/v1/sessions/sess_a1b2c3d4/breakpoints?verified=true"
```

---

### DELETE /sessions/{session_id}/breakpoints/{breakpoint_id}

**Description:** Remove a specific breakpoint.

**Request:**
- Headers: None required
- Path params:
  - `session_id` (string, required): Session identifier
  - `breakpoint_id` (string, required): Breakpoint identifier

**Response:**

| Status | Description |
|--------|-------------|
| 200 | Breakpoint removed |
| 404 | Session or breakpoint not found |

**200 Response Schema:**
```json
{
  "success": true,
  "data": {
    "id": "bp_1",
    "deleted": true
  },
  "error": null,
  "meta": {...}
}
```

**Example:**
```bash
curl -X DELETE http://localhost:5679/api/v1/sessions/sess_a1b2c3d4/breakpoints/bp_1
```

---

### 3.5 Execution Control

---

### POST /sessions/{session_id}/continue

**Description:** Resume program execution until next breakpoint or termination.

**Request:**
- Headers: `Content-Type: application/json` (optional)
- Path params:
  - `session_id` (string, required): Session identifier

**Request Body Schema (optional):**
```json
{
  "thread_id": "integer (optional)"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `thread_id` | integer | No | Specific thread to continue (all if omitted) |

**Response:**

| Status | Description |
|--------|-------------|
| 200 | Execution resumed |
| 404 | Session not found |
| 409 | Session not in paused state |

**200 Response Schema:**
```json
{
  "success": true,
  "data": {
    "session_id": "sess_a1b2c3d4",
    "status": "running",
    "continued": true
  },
  "error": null,
  "meta": {...}
}
```

**Example:**
```bash
curl -X POST http://localhost:5679/api/v1/sessions/sess_a1b2c3d4/continue
```

---

### POST /sessions/{session_id}/pause

**Description:** Pause program execution as soon as possible.

**Request:**
- Headers: `Content-Type: application/json` (optional)
- Path params:
  - `session_id` (string, required): Session identifier

**Request Body Schema (optional):**
```json
{
  "thread_id": "integer (optional)"
}
```

**Response:**

| Status | Description |
|--------|-------------|
| 200 | Pause requested |
| 404 | Session not found |
| 409 | Session not in running state |

**200 Response Schema:**
```json
{
  "success": true,
  "data": {
    "session_id": "sess_a1b2c3d4",
    "status": "paused",
    "stop_reason": "pause",
    "current_location": {
      "path": "/path/to/script.py",
      "line": 55,
      "column": 0,
      "function": "main"
    }
  },
  "error": null,
  "meta": {...}
}
```

**Example:**
```bash
curl -X POST http://localhost:5679/api/v1/sessions/sess_a1b2c3d4/pause
```

---

### POST /sessions/{session_id}/step-over

**Description:** Execute the current line and pause at the next line, stepping over function calls.

**Request:**
- Headers: `Content-Type: application/json` (optional)
- Path params:
  - `session_id` (string, required): Session identifier

**Request Body Schema (optional):**
```json
{
  "thread_id": "integer (optional)",
  "granularity": "string (optional, default: 'line')"
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `thread_id` | integer | No | stopped thread | Thread to step |
| `granularity` | string | No | "line" | "line" or "statement" |

**Response:**

| Status | Description |
|--------|-------------|
| 200 | Step completed |
| 404 | Session not found |
| 409 | Session not in paused state |

**200 Response Schema:**
```json
{
  "success": true,
  "data": {
    "session_id": "sess_a1b2c3d4",
    "status": "paused",
    "stop_reason": "step",
    "current_location": {
      "path": "/path/to/script.py",
      "line": 43,
      "column": 0,
      "function": "process_data"
    },
    "thread_id": 1
  },
  "error": null,
  "meta": {...}
}
```

**Example:**
```bash
curl -X POST http://localhost:5679/api/v1/sessions/sess_a1b2c3d4/step-over
```

---

### POST /sessions/{session_id}/step-into

**Description:** Execute the current line and pause at the next executable location, stepping into function calls.

**Request:**
- Headers: `Content-Type: application/json` (optional)
- Path params:
  - `session_id` (string, required): Session identifier

**Request Body Schema (optional):**
```json
{
  "thread_id": "integer (optional)",
  "granularity": "string (optional, default: 'line')"
}
```

**Response:**

| Status | Description |
|--------|-------------|
| 200 | Step completed |
| 404 | Session not found |
| 409 | Session not in paused state |

**200 Response Schema:**
```json
{
  "success": true,
  "data": {
    "session_id": "sess_a1b2c3d4",
    "status": "paused",
    "stop_reason": "step",
    "current_location": {
      "path": "/path/to/utils.py",
      "line": 10,
      "column": 0,
      "function": "helper_function"
    },
    "thread_id": 1
  },
  "error": null,
  "meta": {...}
}
```

**Example:**
```bash
curl -X POST http://localhost:5679/api/v1/sessions/sess_a1b2c3d4/step-into
```

---

### POST /sessions/{session_id}/step-out

**Description:** Continue execution until the current function returns, then pause.

**Request:**
- Headers: `Content-Type: application/json` (optional)
- Path params:
  - `session_id` (string, required): Session identifier

**Request Body Schema (optional):**
```json
{
  "thread_id": "integer (optional)"
}
```

**Response:**

| Status | Description |
|--------|-------------|
| 200 | Step completed |
| 404 | Session not found |
| 409 | Session not in paused state |

**200 Response Schema:**
```json
{
  "success": true,
  "data": {
    "session_id": "sess_a1b2c3d4",
    "status": "paused",
    "stop_reason": "step",
    "current_location": {
      "path": "/path/to/script.py",
      "line": 45,
      "column": 0,
      "function": "main"
    },
    "thread_id": 1,
    "return_value": {
      "type": "list",
      "value": "[1, 2, 3]"
    }
  },
  "error": null,
  "meta": {...}
}
```

**Example:**
```bash
curl -X POST http://localhost:5679/api/v1/sessions/sess_a1b2c3d4/step-out
```

---

### 3.6 Inspection

---

### GET /sessions/{session_id}/threads

**Description:** Get a list of all threads in the debuggee.

**Request:**
- Headers: None required
- Path params:
  - `session_id` (string, required): Session identifier

**Response:**

| Status | Description |
|--------|-------------|
| 200 | List of threads |
| 404 | Session not found |
| 409 | Program not running/paused |

**200 Response Schema:**
```json
{
  "success": true,
  "data": {
    "threads": [
      {
        "id": 1,
        "name": "MainThread",
        "status": "paused",
        "is_current": true
      },
      {
        "id": 2,
        "name": "Worker-1",
        "status": "paused",
        "is_current": false
      }
    ],
    "stopped_thread_id": 1
  },
  "error": null,
  "meta": {...}
}
```

**Example:**
```bash
curl http://localhost:5679/api/v1/sessions/sess_a1b2c3d4/threads
```

---

### GET /sessions/{session_id}/stacktrace

**Description:** Get the call stack for the current or specified thread.

**Request:**
- Headers: None required
- Path params:
  - `session_id` (string, required): Session identifier
- Query params:
  - `thread_id` (integer, optional): Thread ID (default: stopped thread)
  - `start_frame` (integer, optional): Start frame index (default: 0)
  - `levels` (integer, optional): Number of frames to return (default: 20)

**Response:**

| Status | Description |
|--------|-------------|
| 200 | Stack trace |
| 404 | Session not found |
| 409 | Program not paused |

**200 Response Schema:**
```json
{
  "success": true,
  "data": {
    "thread_id": 1,
    "frames": [
      {
        "id": 0,
        "name": "process_item",
        "source": {
          "path": "/path/to/script.py",
          "name": "script.py"
        },
        "line": 42,
        "column": 8,
        "module_name": "__main__",
        "presentation_hint": "normal"
      },
      {
        "id": 1,
        "name": "process_all",
        "source": {
          "path": "/path/to/script.py",
          "name": "script.py"
        },
        "line": 30,
        "column": 12,
        "module_name": "__main__",
        "presentation_hint": "normal"
      },
      {
        "id": 2,
        "name": "main",
        "source": {
          "path": "/path/to/script.py",
          "name": "script.py"
        },
        "line": 55,
        "column": 4,
        "module_name": "__main__",
        "presentation_hint": "normal"
      }
    ],
    "total_frames": 3
  },
  "error": null,
  "meta": {...}
}
```

**Example:**
```bash
curl "http://localhost:5679/api/v1/sessions/sess_a1b2c3d4/stacktrace?thread_id=1&levels=50"
```

---

### GET /sessions/{session_id}/scopes

**Description:** Get variable scopes for a specific stack frame.

**Request:**
- Headers: None required
- Path params:
  - `session_id` (string, required): Session identifier
- Query params:
  - `frame_id` (integer, optional): Frame ID from stacktrace (default: 0, top frame)

**Response:**

| Status | Description |
|--------|-------------|
| 200 | List of scopes |
| 404 | Session not found |
| 409 | Program not paused |

**200 Response Schema:**
```json
{
  "success": true,
  "data": {
    "frame_id": 0,
    "scopes": [
      {
        "name": "Locals",
        "presentation_hint": "locals",
        "variables_reference": 1000,
        "named_variables": 5,
        "indexed_variables": 0,
        "expensive": false
      },
      {
        "name": "Globals",
        "presentation_hint": "globals",
        "variables_reference": 1001,
        "named_variables": 25,
        "indexed_variables": 0,
        "expensive": false
      }
    ]
  },
  "error": null,
  "meta": {...}
}
```

**Example:**
```bash
curl "http://localhost:5679/api/v1/sessions/sess_a1b2c3d4/scopes?frame_id=0"
```

---

### GET /sessions/{session_id}/variables

**Description:** Get variables for a scope or expand a complex variable.

**Request:**
- Headers: None required
- Path params:
  - `session_id` (string, required): Session identifier
- Query params:
  - `variables_reference` (integer, required): Reference from scope or parent variable
  - `start` (integer, optional): Start index for indexed variables
  - `count` (integer, optional): Number of variables to return
  - `filter` (string, optional): "indexed" or "named"

**Response:**

| Status | Description |
|--------|-------------|
| 200 | List of variables |
| 404 | Session or reference not found |
| 409 | Program not paused |

**200 Response Schema:**
```json
{
  "success": true,
  "data": {
    "variables_reference": 1000,
    "variables": [
      {
        "name": "items",
        "value": "[1, 2, 3, 4, 5]",
        "type": "list",
        "variables_reference": 1002,
        "named_variables": 0,
        "indexed_variables": 5,
        "presentation_hint": {
          "kind": "data"
        }
      },
      {
        "name": "count",
        "value": "42",
        "type": "int",
        "variables_reference": 0,
        "named_variables": 0,
        "indexed_variables": 0
      },
      {
        "name": "config",
        "value": "{'debug': True, 'verbose': False}",
        "type": "dict",
        "variables_reference": 1003,
        "named_variables": 2,
        "indexed_variables": 0
      },
      {
        "name": "large_list",
        "value": "[0, 1, 2, ... (10000 items)]",
        "type": "list",
        "variables_reference": 1004,
        "named_variables": 0,
        "indexed_variables": 10000,
        "truncated": true
      }
    ]
  },
  "error": null,
  "meta": {...}
}
```

**Note on variables_reference:**
- `0` means variable is a primitive (no children)
- Non-zero means variable can be expanded by calling this endpoint again with that reference

**Example:**
```bash
# Get locals
curl "http://localhost:5679/api/v1/sessions/sess_a1b2c3d4/variables?variables_reference=1000"

# Expand a list (get items 100-199)
curl "http://localhost:5679/api/v1/sessions/sess_a1b2c3d4/variables?variables_reference=1004&start=100&count=100"
```

---

### POST /sessions/{session_id}/evaluate

**Description:** Evaluate an expression in the context of the current stack frame.

**Request:**
- Headers: `Content-Type: application/json`
- Path params:
  - `session_id` (string, required): Session identifier

**Request Body Schema:**
```json
{
  "expression": "string (required)",
  "frame_id": "integer (optional, default: 0)",
  "context": "string (optional, default: 'repl')"
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `expression` | string | Yes | - | Python expression to evaluate |
| `frame_id` | integer | No | 0 | Frame context for evaluation |
| `context` | string | No | "repl" | Evaluation context |

**Context Values:**
- `watch` - Expression in watch window (read-only intent)
- `repl` - Interactive evaluation (may have side effects)
- `hover` - Tooltip/hover evaluation (read-only intent)

**Response:**

| Status | Description |
|--------|-------------|
| 200 | Evaluation result |
| 400 | Invalid expression |
| 404 | Session not found |
| 409 | Program not paused |

**200 Response Schema:**
```json
{
  "success": true,
  "data": {
    "result": "84",
    "type": "int",
    "variables_reference": 0,
    "named_variables": 0,
    "indexed_variables": 0,
    "presentation_hint": null
  },
  "error": null,
  "meta": {...}
}
```

**200 Response (complex result):**
```json
{
  "success": true,
  "data": {
    "result": "{'name': 'test', 'values': [1, 2, 3]}",
    "type": "dict",
    "variables_reference": 1005,
    "named_variables": 2,
    "indexed_variables": 0
  },
  "error": null,
  "meta": {...}
}
```

**200 Response (evaluation error):**
```json
{
  "success": true,
  "data": {
    "result": null,
    "type": null,
    "error": "NameError: name 'undefined_var' is not defined"
  },
  "error": null,
  "meta": {...}
}
```

**Example:**
```bash
curl -X POST http://localhost:5679/api/v1/sessions/sess_a1b2c3d4/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "expression": "len(items) * 2",
    "frame_id": 0,
    "context": "repl"
  }'
```

---

### 3.7 Output & Events

---

### GET /sessions/{session_id}/output

**Description:** Get captured stdout/stderr output from the debuggee.

**Request:**
- Headers: None required
- Path params:
  - `session_id` (string, required): Session identifier
- Query params:
  - `cursor` (string, optional): Resume from cursor position
  - `limit` (integer, optional): Maximum entries to return (default: 100)
  - `category` (string, optional): Filter by "stdout", "stderr", or "console"

**Response:**

| Status | Description |
|--------|-------------|
| 200 | Output entries |
| 404 | Session not found |

**200 Response Schema:**
```json
{
  "success": true,
  "data": {
    "entries": [
      {
        "category": "stdout",
        "output": "Processing file 1 of 10...\n",
        "timestamp": "2026-01-13T10:30:01.123Z",
        "source": null,
        "line": null
      },
      {
        "category": "stderr",
        "output": "Warning: deprecated function used\n",
        "timestamp": "2026-01-13T10:30:01.456Z",
        "source": "/path/to/script.py",
        "line": 42
      },
      {
        "category": "console",
        "output": "Debugger attached\n",
        "timestamp": "2026-01-13T10:30:00.100Z",
        "source": null,
        "line": null
      }
    ],
    "next_cursor": "eyJvZmZzZXQiOjEwMH0=",
    "has_more": false
  },
  "error": null,
  "meta": {...}
}
```

**Example:**
```bash
# Get all output
curl "http://localhost:5679/api/v1/sessions/sess_a1b2c3d4/output"

# Get only stderr
curl "http://localhost:5679/api/v1/sessions/sess_a1b2c3d4/output?category=stderr"

# Continue from previous cursor
curl "http://localhost:5679/api/v1/sessions/sess_a1b2c3d4/output?cursor=eyJvZmZzZXQiOjEwMH0="
```

---

### GET /sessions/{session_id}/events

**Description:** Poll for debug events. This is the primary mechanism for clients to detect state changes.

**Request:**
- Headers: None required
- Path params:
  - `session_id` (string, required): Session identifier
- Query params:
  - `cursor` (string, optional): Resume from cursor position
  - `limit` (integer, optional): Maximum events to return (default: 100)
  - `timeout` (integer, optional): Long-poll timeout in seconds (default: 0, no wait)

**Response:**

| Status | Description |
|--------|-------------|
| 200 | Event list |
| 404 | Session not found |

**200 Response Schema:**
```json
{
  "success": true,
  "data": {
    "events": [
      {
        "seq": 1,
        "type": "stopped",
        "timestamp": "2026-01-13T10:30:05.000Z",
        "body": {
          "reason": "breakpoint",
          "thread_id": 1,
          "all_threads_stopped": true,
          "hit_breakpoint_ids": ["bp_1"],
          "description": "Paused on breakpoint",
          "text": null
        }
      },
      {
        "seq": 2,
        "type": "output",
        "timestamp": "2026-01-13T10:30:05.100Z",
        "body": {
          "category": "stdout",
          "output": "Processing...\n"
        }
      }
    ],
    "next_cursor": "eyJzZXEiOjJ9",
    "has_more": false,
    "session_status": "paused"
  },
  "error": null,
  "meta": {...}
}
```

**Example:**
```bash
# Poll for new events
curl "http://localhost:5679/api/v1/sessions/sess_a1b2c3d4/events"

# Long-poll (wait up to 30s for events)
curl "http://localhost:5679/api/v1/sessions/sess_a1b2c3d4/events?timeout=30"

# Continue from cursor
curl "http://localhost:5679/api/v1/sessions/sess_a1b2c3d4/events?cursor=eyJzZXEiOjJ9"
```

---

## 4. Request/Response Schemas

### 4.1 Request Schemas

#### CreateSessionRequest

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CreateSessionRequest",
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "Human-readable session name",
      "maxLength": 255
    },
    "project_root": {
      "type": "string",
      "description": "Root directory for the project"
    },
    "python_path": {
      "type": "string",
      "description": "Path to Python interpreter"
    },
    "timeout_minutes": {
      "type": "integer",
      "description": "Session idle timeout in minutes",
      "minimum": 1,
      "maximum": 1440,
      "default": 60
    },
    "stop_on_entry": {
      "type": "boolean",
      "description": "Pause at program entry",
      "default": false
    }
  },
  "additionalProperties": false
}
```

#### LaunchRequest

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "LaunchRequest",
  "type": "object",
  "properties": {
    "script": {
      "type": "string",
      "description": "Path to Python script to debug"
    },
    "module": {
      "type": "string",
      "description": "Python module to run (like python -m)"
    },
    "args": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Command-line arguments",
      "default": []
    },
    "cwd": {
      "type": "string",
      "description": "Working directory for the program"
    },
    "env": {
      "type": "object",
      "additionalProperties": {"type": "string"},
      "description": "Environment variables to set",
      "default": {}
    },
    "stop_on_entry": {
      "type": "boolean",
      "description": "Pause at first line",
      "default": false
    },
    "stop_on_exception": {
      "oneOf": [
        {"type": "boolean"},
        {"type": "string", "enum": ["uncaught", "raised"]}
      ],
      "description": "When to stop on exceptions",
      "default": "uncaught"
    },
    "console": {
      "type": "string",
      "enum": ["internalConsole", "integratedTerminal", "externalTerminal"],
      "description": "Console type",
      "default": "internalConsole"
    },
    "python_args": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Arguments passed to Python interpreter",
      "default": []
    }
  },
  "oneOf": [
    {"required": ["script"]},
    {"required": ["module"]}
  ],
  "additionalProperties": false
}
```

#### AttachRequest

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "AttachRequest",
  "type": "object",
  "properties": {
    "pid": {
      "type": "integer",
      "description": "Process ID to attach to"
    },
    "host": {
      "type": "string",
      "description": "debugpy host",
      "default": "localhost"
    },
    "port": {
      "type": "integer",
      "description": "debugpy port",
      "minimum": 1,
      "maximum": 65535
    },
    "connect_timeout": {
      "type": "integer",
      "description": "Connection timeout in seconds",
      "minimum": 1,
      "maximum": 300,
      "default": 10
    }
  },
  "oneOf": [
    {"required": ["pid"]},
    {"required": ["port"]}
  ],
  "additionalProperties": false
}
```

#### SetBreakpointsRequest

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SetBreakpointsRequest",
  "type": "object",
  "properties": {
    "breakpoints": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "source": {
            "type": "object",
            "properties": {
              "path": {
                "type": "string",
                "description": "Absolute path to source file"
              }
            },
            "required": ["path"]
          },
          "line": {
            "type": "integer",
            "description": "Line number (1-indexed)",
            "minimum": 1
          },
          "condition": {
            "type": "string",
            "description": "Conditional expression"
          },
          "hit_condition": {
            "type": "string",
            "description": "Hit count condition (e.g., '>5', '==10')"
          },
          "log_message": {
            "type": "string",
            "description": "Log message (makes this a logpoint)"
          },
          "enabled": {
            "type": "boolean",
            "description": "Whether breakpoint is active",
            "default": true
          }
        },
        "required": ["source", "line"]
      },
      "minItems": 1
    }
  },
  "required": ["breakpoints"],
  "additionalProperties": false
}
```

#### EvaluateRequest

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "EvaluateRequest",
  "type": "object",
  "properties": {
    "expression": {
      "type": "string",
      "description": "Python expression to evaluate",
      "minLength": 1
    },
    "frame_id": {
      "type": "integer",
      "description": "Frame context for evaluation",
      "minimum": 0,
      "default": 0
    },
    "context": {
      "type": "string",
      "enum": ["watch", "repl", "hover"],
      "description": "Evaluation context",
      "default": "repl"
    }
  },
  "required": ["expression"],
  "additionalProperties": false
}
```

### 4.2 Response Schemas

#### SessionResponse

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SessionResponse",
  "type": "object",
  "properties": {
    "session_id": {"type": "string"},
    "name": {"type": "string"},
    "status": {
      "type": "string",
      "enum": ["created", "launching", "running", "paused", "terminated", "failed"]
    },
    "stop_reason": {
      "type": "string",
      "enum": ["breakpoint", "step", "exception", "pause", "entry", null]
    },
    "created_at": {"type": "string", "format": "date-time"},
    "expires_at": {"type": "string", "format": "date-time"},
    "config": {
      "type": "object",
      "properties": {
        "project_root": {"type": "string"},
        "python_path": {"type": "string"},
        "stop_on_entry": {"type": "boolean"}
      }
    },
    "program": {
      "type": "object",
      "properties": {
        "script": {"type": "string"},
        "module": {"type": "string"},
        "args": {"type": "array", "items": {"type": "string"}},
        "cwd": {"type": "string"},
        "env": {"type": "object"}
      }
    },
    "current_location": {"$ref": "#/$defs/SourceLocation"},
    "stopped_thread_id": {"type": "integer"},
    "breakpoint_count": {"type": "integer"},
    "exception": {
      "type": "object",
      "properties": {
        "type": {"type": "string"},
        "message": {"type": "string"},
        "traceback": {"type": "string"}
      }
    }
  },
  "required": ["session_id", "status", "created_at"],
  "$defs": {
    "SourceLocation": {
      "type": "object",
      "properties": {
        "path": {"type": "string"},
        "line": {"type": "integer"},
        "column": {"type": "integer"},
        "function": {"type": "string"}
      }
    }
  }
}
```

#### SessionListResponse

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SessionListResponse",
  "type": "object",
  "properties": {
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "session_id": {"type": "string"},
          "name": {"type": "string"},
          "status": {"type": "string"},
          "created_at": {"type": "string", "format": "date-time"},
          "program": {"type": "string"}
        }
      }
    },
    "total": {"type": "integer"},
    "offset": {"type": "integer"},
    "limit": {"type": "integer"},
    "has_more": {"type": "boolean"}
  },
  "required": ["items", "total", "offset", "limit", "has_more"]
}
```

#### BreakpointResponse

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "BreakpointResponse",
  "type": "object",
  "properties": {
    "breakpoints": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string"},
          "verified": {"type": "boolean"},
          "source": {
            "type": "object",
            "properties": {
              "path": {"type": "string"}
            }
          },
          "line": {"type": "integer"},
          "condition": {"type": "string"},
          "hit_condition": {"type": "string"},
          "log_message": {"type": "string"},
          "enabled": {"type": "boolean"},
          "hit_count": {"type": "integer"},
          "message": {"type": "string"}
        },
        "required": ["id", "verified", "source", "line"]
      }
    }
  },
  "required": ["breakpoints"]
}
```

#### StackTraceResponse

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "StackTraceResponse",
  "type": "object",
  "properties": {
    "thread_id": {"type": "integer"},
    "frames": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "integer"},
          "name": {"type": "string"},
          "source": {
            "type": "object",
            "properties": {
              "path": {"type": "string"},
              "name": {"type": "string"}
            }
          },
          "line": {"type": "integer"},
          "column": {"type": "integer"},
          "module_name": {"type": "string"},
          "presentation_hint": {
            "type": "string",
            "enum": ["normal", "label", "subtle"]
          }
        },
        "required": ["id", "name", "line"]
      }
    },
    "total_frames": {"type": "integer"}
  },
  "required": ["thread_id", "frames", "total_frames"]
}
```

#### ScopesResponse

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ScopesResponse",
  "type": "object",
  "properties": {
    "frame_id": {"type": "integer"},
    "scopes": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "presentation_hint": {
            "type": "string",
            "enum": ["locals", "globals", "registers"]
          },
          "variables_reference": {"type": "integer"},
          "named_variables": {"type": "integer"},
          "indexed_variables": {"type": "integer"},
          "expensive": {"type": "boolean"}
        },
        "required": ["name", "variables_reference"]
      }
    }
  },
  "required": ["frame_id", "scopes"]
}
```

#### VariablesResponse

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "VariablesResponse",
  "type": "object",
  "properties": {
    "variables_reference": {"type": "integer"},
    "variables": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "value": {"type": "string"},
          "type": {"type": "string"},
          "variables_reference": {"type": "integer"},
          "named_variables": {"type": "integer"},
          "indexed_variables": {"type": "integer"},
          "presentation_hint": {
            "type": "object",
            "properties": {
              "kind": {"type": "string"},
              "attributes": {"type": "array", "items": {"type": "string"}},
              "visibility": {"type": "string"}
            }
          },
          "truncated": {"type": "boolean"}
        },
        "required": ["name", "value", "type", "variables_reference"]
      }
    }
  },
  "required": ["variables_reference", "variables"]
}
```

#### EvaluateResponse

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "EvaluateResponse",
  "type": "object",
  "properties": {
    "result": {"type": "string"},
    "type": {"type": "string"},
    "variables_reference": {"type": "integer"},
    "named_variables": {"type": "integer"},
    "indexed_variables": {"type": "integer"},
    "presentation_hint": {
      "type": "object",
      "properties": {
        "kind": {"type": "string"}
      }
    },
    "error": {"type": "string"}
  }
}
```

#### OutputResponse

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "OutputResponse",
  "type": "object",
  "properties": {
    "entries": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "category": {
            "type": "string",
            "enum": ["stdout", "stderr", "console"]
          },
          "output": {"type": "string"},
          "timestamp": {"type": "string", "format": "date-time"},
          "source": {"type": "string"},
          "line": {"type": "integer"}
        },
        "required": ["category", "output", "timestamp"]
      }
    },
    "next_cursor": {"type": "string"},
    "has_more": {"type": "boolean"}
  },
  "required": ["entries", "has_more"]
}
```

#### EventsResponse

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "EventsResponse",
  "type": "object",
  "properties": {
    "events": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "seq": {"type": "integer"},
          "type": {
            "type": "string",
            "enum": ["stopped", "continued", "terminated", "output", "breakpoint", "thread", "module"]
          },
          "timestamp": {"type": "string", "format": "date-time"},
          "body": {"type": "object"}
        },
        "required": ["seq", "type", "timestamp", "body"]
      }
    },
    "next_cursor": {"type": "string"},
    "has_more": {"type": "boolean"},
    "session_status": {"type": "string"}
  },
  "required": ["events", "has_more", "session_status"]
}
```

---

## 5. Error Codes

### 5.1 Error Code Catalog

| Code | HTTP Status | Category | Description |
|------|-------------|----------|-------------|
| `SESSION_NOT_FOUND` | 404 | Session | Session ID doesn't exist or has expired |
| `SESSION_LIMIT_REACHED` | 429 | Session | Maximum concurrent sessions (10) exceeded |
| `SESSION_EXPIRED` | 410 | Session | Session timed out due to inactivity |
| `INVALID_SESSION_STATE` | 409 | Session | Operation not valid in current session state |
| `BREAKPOINT_NOT_FOUND` | 404 | Breakpoint | Breakpoint ID doesn't exist |
| `BREAKPOINT_INVALID_LINE` | 400 | Breakpoint | Line number is invalid or has no executable code |
| `BREAKPOINT_INVALID_CONDITION` | 400 | Breakpoint | Condition expression has syntax error |
| `BREAKPOINT_FILE_NOT_FOUND` | 400 | Breakpoint | Source file does not exist |
| `THREAD_NOT_FOUND` | 404 | Thread | Thread ID doesn't exist |
| `FRAME_NOT_FOUND` | 404 | Frame | Frame ID doesn't exist |
| `VARIABLE_NOT_FOUND` | 404 | Variable | Variables reference doesn't exist |
| `EVALUATE_ERROR` | 400 | Evaluate | Expression evaluation failed |
| `LAUNCH_FAILED` | 500 | Launch | Failed to start debuggee |
| `LAUNCH_SCRIPT_NOT_FOUND` | 400 | Launch | Script file does not exist |
| `LAUNCH_SYNTAX_ERROR` | 400 | Launch | Script has Python syntax error |
| `ATTACH_FAILED` | 500 | Attach | Failed to attach to process |
| `ATTACH_TIMEOUT` | 504 | Attach | Connection to debugpy timed out |
| `ATTACH_REFUSED` | 502 | Attach | Target process refused connection |
| `DEBUGPY_ERROR` | 500 | Internal | Internal debugpy error |
| `DEBUGPY_TIMEOUT` | 504 | Internal | debugpy operation timed out |
| `INVALID_REQUEST` | 400 | Request | Request body validation failed |
| `MISSING_PARAMETER` | 400 | Request | Required parameter is missing |
| `INVALID_PARAMETER` | 400 | Request | Parameter value is invalid |
| `INTERNAL_ERROR` | 500 | Internal | Unexpected server error |

### 5.2 Error Response Examples

**Session Not Found:**
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "SESSION_NOT_FOUND",
    "message": "Session with ID 'sess_invalid' not found",
    "details": {
      "session_id": "sess_invalid",
      "suggestion": "Use GET /api/v1/sessions to list active sessions"
    }
  },
  "meta": {...}
}
```

**Invalid Session State:**
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "INVALID_SESSION_STATE",
    "message": "Cannot step-over: session is not paused",
    "details": {
      "current_state": "running",
      "required_state": "paused",
      "suggestion": "Call POST /sessions/{id}/pause first or wait for a breakpoint"
    }
  },
  "meta": {...}
}
```

**Breakpoint Invalid Line:**
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "BREAKPOINT_INVALID_LINE",
    "message": "Cannot set breakpoint at line 5: line contains only whitespace",
    "details": {
      "file": "/path/to/script.py",
      "line": 5,
      "content": "    ",
      "suggestion": "Try line 6 which contains: 'def process_data(items):'"
    }
  },
  "meta": {...}
}
```

**Launch Syntax Error:**
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "LAUNCH_SYNTAX_ERROR",
    "message": "Python syntax error in script",
    "details": {
      "file": "/path/to/script.py",
      "line": 15,
      "offset": 23,
      "error_message": "unexpected EOF while parsing",
      "text": "if x == 1"
    }
  },
  "meta": {...}
}
```

**Validation Error:**
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Request validation failed",
    "details": {
      "errors": [
        {
          "field": "breakpoints[0].line",
          "message": "Line number must be a positive integer",
          "value": -5
        },
        {
          "field": "breakpoints[1].source.path",
          "message": "Path must be absolute",
          "value": "relative/path.py"
        }
      ]
    }
  },
  "meta": {...}
}
```

---

## 6. Event Types

### 6.1 Event Type Catalog

Events are returned by the `GET /sessions/{id}/events` endpoint. Each event has a `type` and a `body` with type-specific fields.

#### stopped

Fired when execution stops (breakpoint, step, exception, pause).

```json
{
  "seq": 1,
  "type": "stopped",
  "timestamp": "2026-01-13T10:30:05.000Z",
  "body": {
    "reason": "breakpoint",
    "description": "Paused on breakpoint",
    "thread_id": 1,
    "preserve_focus_hint": false,
    "text": null,
    "all_threads_stopped": true,
    "hit_breakpoint_ids": ["bp_1"]
  }
}
```

**Reason Values:**
| Reason | Description |
|--------|-------------|
| `breakpoint` | Hit a breakpoint |
| `step` | Completed a step operation |
| `exception` | Exception was raised |
| `pause` | Manual pause requested |
| `entry` | Stopped at program entry |
| `goto` | Stopped due to goto |
| `function breakpoint` | Hit a function breakpoint |
| `data breakpoint` | Data breakpoint triggered |

**Exception Stopped Event:**
```json
{
  "seq": 5,
  "type": "stopped",
  "timestamp": "2026-01-13T10:35:00.000Z",
  "body": {
    "reason": "exception",
    "description": "Paused on exception",
    "thread_id": 1,
    "text": "ValueError: invalid literal for int()",
    "all_threads_stopped": true,
    "exception_info": {
      "exception_id": "ValueError",
      "description": "invalid literal for int() with base 10: 'abc'",
      "break_mode": "always",
      "details": {
        "type_name": "ValueError",
        "full_type_name": "builtins.ValueError",
        "message": "invalid literal for int() with base 10: 'abc'",
        "stack_trace": "Traceback (most recent call last):\n  ..."
      }
    }
  }
}
```

#### continued

Fired when execution resumes.

```json
{
  "seq": 2,
  "type": "continued",
  "timestamp": "2026-01-13T10:30:10.000Z",
  "body": {
    "thread_id": 1,
    "all_threads_continued": true
  }
}
```

#### terminated

Fired when the debuggee has terminated.

```json
{
  "seq": 10,
  "type": "terminated",
  "timestamp": "2026-01-13T10:45:00.000Z",
  "body": {
    "exit_code": 0,
    "restart": false
  }
}
```

**Terminated with Error:**
```json
{
  "seq": 10,
  "type": "terminated",
  "timestamp": "2026-01-13T10:45:00.000Z",
  "body": {
    "exit_code": 1,
    "restart": false,
    "error": "Process exited with code 1"
  }
}
```

#### output

Fired when the debuggee produces output.

```json
{
  "seq": 3,
  "type": "output",
  "timestamp": "2026-01-13T10:30:05.100Z",
  "body": {
    "category": "stdout",
    "output": "Processing item 1 of 100...\n",
    "source": null,
    "line": null,
    "column": null
  }
}
```

**Category Values:**
| Category | Description |
|----------|-------------|
| `stdout` | Standard output |
| `stderr` | Standard error |
| `console` | Debug console messages |
| `important` | Important messages |
| `telemetry` | Telemetry data |

#### breakpoint

Fired when a breakpoint's status changes.

```json
{
  "seq": 4,
  "type": "breakpoint",
  "timestamp": "2026-01-13T10:30:00.500Z",
  "body": {
    "reason": "changed",
    "breakpoint": {
      "id": "bp_1",
      "verified": true,
      "line": 42,
      "message": null
    }
  }
}
```

**Reason Values:**
| Reason | Description |
|--------|-------------|
| `changed` | Breakpoint was modified |
| `new` | New breakpoint was set |
| `removed` | Breakpoint was removed |

#### thread

Fired when a thread starts or exits.

```json
{
  "seq": 6,
  "type": "thread",
  "timestamp": "2026-01-13T10:32:00.000Z",
  "body": {
    "reason": "started",
    "thread_id": 2
  }
}
```

**Reason Values:**
| Reason | Description |
|--------|-------------|
| `started` | New thread started |
| `exited` | Thread terminated |

#### module

Fired when a module is loaded.

```json
{
  "seq": 7,
  "type": "module",
  "timestamp": "2026-01-13T10:30:01.000Z",
  "body": {
    "reason": "new",
    "module": {
      "id": 1,
      "name": "main",
      "path": "/path/to/script.py",
      "is_optimized": false,
      "is_user_code": true,
      "version": null
    }
  }
}
```

### 6.2 Event Polling Strategy

**Recommended Polling Pattern:**

```
1. Initial poll: GET /sessions/{id}/events
2. Store next_cursor from response
3. Process events
4. Wait appropriate interval (100ms - 1s depending on status)
5. Poll with cursor: GET /sessions/{id}/events?cursor={next_cursor}
6. Repeat from step 2
```

**Long-Polling (Optional):**

For reduced latency, use the `timeout` parameter:
```
GET /sessions/{id}/events?cursor={cursor}&timeout=30
```

This will wait up to 30 seconds for new events before returning an empty list.

---

## 7. OpenAPI Spec Outline

The following is the structure for the OpenAPI 3.1 specification. The actual `openapi.yaml` will be auto-generated from FastAPI route definitions with Pydantic models.

```yaml
openapi: 3.1.0
info:
  title: OpenCode Debug Relay Server API
  description: REST API for controlling Python debugpy debugging sessions
  version: 1.0.0
  contact:
    name: OpenCode Debug Team
  license:
    name: MIT

servers:
  - url: http://localhost:5679/api/v1
    description: Local development server

tags:
  - name: Server
    description: Server health and information
  - name: Sessions
    description: Debug session management
  - name: Program Control
    description: Launch, attach, and control execution
  - name: Breakpoints
    description: Breakpoint management
  - name: Execution
    description: Step, continue, pause operations
  - name: Inspection
    description: Threads, stacks, variables, evaluation
  - name: Output
    description: Program output and events

paths:
  /health:
    get:
      tags: [Server]
      summary: Health check
      operationId: getHealth
      responses:
        '200':
          description: Server is healthy
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthResponse'

  /info:
    get:
      tags: [Server]
      summary: Server information
      operationId: getInfo
      responses:
        '200':
          description: Server info
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/InfoResponse'

  /sessions:
    get:
      tags: [Sessions]
      summary: List sessions
      operationId: listSessions
      parameters:
        - $ref: '#/components/parameters/OffsetParam'
        - $ref: '#/components/parameters/LimitParam'
        - name: status
          in: query
          schema:
            type: string
      responses:
        '200':
          description: Session list
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SessionListResponse'

    post:
      tags: [Sessions]
      summary: Create session
      operationId: createSession
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateSessionRequest'
      responses:
        '201':
          description: Session created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SessionResponse'
        '429':
          $ref: '#/components/responses/SessionLimitReached'

  /sessions/{session_id}:
    parameters:
      - $ref: '#/components/parameters/SessionIdParam'
    get:
      tags: [Sessions]
      summary: Get session
      operationId: getSession
      responses:
        '200':
          description: Session details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SessionResponse'
        '404':
          $ref: '#/components/responses/SessionNotFound'

    delete:
      tags: [Sessions]
      summary: Delete session
      operationId: deleteSession
      responses:
        '200':
          description: Session deleted
        '404':
          $ref: '#/components/responses/SessionNotFound'

  /sessions/{session_id}/launch:
    parameters:
      - $ref: '#/components/parameters/SessionIdParam'
    post:
      tags: [Program Control]
      summary: Launch program
      operationId: launchProgram
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/LaunchRequest'
      responses:
        '200':
          description: Program launched
        '400':
          $ref: '#/components/responses/InvalidRequest'
        '404':
          $ref: '#/components/responses/SessionNotFound'
        '409':
          $ref: '#/components/responses/InvalidSessionState'

  /sessions/{session_id}/attach:
    parameters:
      - $ref: '#/components/parameters/SessionIdParam'
    post:
      tags: [Program Control]
      summary: Attach to process
      operationId: attachProcess
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AttachRequest'
      responses:
        '200':
          description: Attached successfully
        '404':
          $ref: '#/components/responses/SessionNotFound'
        '504':
          $ref: '#/components/responses/AttachTimeout'

  /sessions/{session_id}/breakpoints:
    parameters:
      - $ref: '#/components/parameters/SessionIdParam'
    get:
      tags: [Breakpoints]
      summary: List breakpoints
      operationId: listBreakpoints
      responses:
        '200':
          description: Breakpoint list
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BreakpointListResponse'

    post:
      tags: [Breakpoints]
      summary: Set breakpoints
      operationId: setBreakpoints
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SetBreakpointsRequest'
      responses:
        '200':
          description: Breakpoints set
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BreakpointResponse'

  /sessions/{session_id}/breakpoints/{breakpoint_id}:
    parameters:
      - $ref: '#/components/parameters/SessionIdParam'
      - $ref: '#/components/parameters/BreakpointIdParam'
    delete:
      tags: [Breakpoints]
      summary: Remove breakpoint
      operationId: removeBreakpoint
      responses:
        '200':
          description: Breakpoint removed
        '404':
          $ref: '#/components/responses/BreakpointNotFound'

  /sessions/{session_id}/continue:
    parameters:
      - $ref: '#/components/parameters/SessionIdParam'
    post:
      tags: [Execution]
      summary: Continue execution
      operationId: continueExecution
      responses:
        '200':
          description: Execution resumed
        '409':
          $ref: '#/components/responses/InvalidSessionState'

  /sessions/{session_id}/pause:
    parameters:
      - $ref: '#/components/parameters/SessionIdParam'
    post:
      tags: [Execution]
      summary: Pause execution
      operationId: pauseExecution
      responses:
        '200':
          description: Execution paused

  /sessions/{session_id}/step-over:
    parameters:
      - $ref: '#/components/parameters/SessionIdParam'
    post:
      tags: [Execution]
      summary: Step over
      operationId: stepOver
      responses:
        '200':
          description: Step completed

  /sessions/{session_id}/step-into:
    parameters:
      - $ref: '#/components/parameters/SessionIdParam'
    post:
      tags: [Execution]
      summary: Step into
      operationId: stepInto
      responses:
        '200':
          description: Step completed

  /sessions/{session_id}/step-out:
    parameters:
      - $ref: '#/components/parameters/SessionIdParam'
    post:
      tags: [Execution]
      summary: Step out
      operationId: stepOut
      responses:
        '200':
          description: Step completed

  /sessions/{session_id}/threads:
    parameters:
      - $ref: '#/components/parameters/SessionIdParam'
    get:
      tags: [Inspection]
      summary: List threads
      operationId: listThreads
      responses:
        '200':
          description: Thread list
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ThreadsResponse'

  /sessions/{session_id}/stacktrace:
    parameters:
      - $ref: '#/components/parameters/SessionIdParam'
    get:
      tags: [Inspection]
      summary: Get stack trace
      operationId: getStackTrace
      parameters:
        - name: thread_id
          in: query
          schema:
            type: integer
        - name: start_frame
          in: query
          schema:
            type: integer
        - name: levels
          in: query
          schema:
            type: integer
      responses:
        '200':
          description: Stack trace
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/StackTraceResponse'

  /sessions/{session_id}/scopes:
    parameters:
      - $ref: '#/components/parameters/SessionIdParam'
    get:
      tags: [Inspection]
      summary: Get scopes
      operationId: getScopes
      parameters:
        - name: frame_id
          in: query
          schema:
            type: integer
      responses:
        '200':
          description: Scope list
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ScopesResponse'

  /sessions/{session_id}/variables:
    parameters:
      - $ref: '#/components/parameters/SessionIdParam'
    get:
      tags: [Inspection]
      summary: Get variables
      operationId: getVariables
      parameters:
        - name: variables_reference
          in: query
          required: true
          schema:
            type: integer
        - name: start
          in: query
          schema:
            type: integer
        - name: count
          in: query
          schema:
            type: integer
      responses:
        '200':
          description: Variable list
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/VariablesResponse'

  /sessions/{session_id}/evaluate:
    parameters:
      - $ref: '#/components/parameters/SessionIdParam'
    post:
      tags: [Inspection]
      summary: Evaluate expression
      operationId: evaluate
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/EvaluateRequest'
      responses:
        '200':
          description: Evaluation result
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/EvaluateResponse'

  /sessions/{session_id}/output:
    parameters:
      - $ref: '#/components/parameters/SessionIdParam'
    get:
      tags: [Output]
      summary: Get output
      operationId: getOutput
      parameters:
        - name: cursor
          in: query
          schema:
            type: string
        - name: limit
          in: query
          schema:
            type: integer
        - name: category
          in: query
          schema:
            type: string
      responses:
        '200':
          description: Output entries
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/OutputResponse'

  /sessions/{session_id}/events:
    parameters:
      - $ref: '#/components/parameters/SessionIdParam'
    get:
      tags: [Output]
      summary: Poll events
      operationId: pollEvents
      parameters:
        - name: cursor
          in: query
          schema:
            type: string
        - name: limit
          in: query
          schema:
            type: integer
        - name: timeout
          in: query
          schema:
            type: integer
      responses:
        '200':
          description: Event list
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/EventsResponse'

components:
  parameters:
    SessionIdParam:
      name: session_id
      in: path
      required: true
      schema:
        type: string
      description: Session identifier

    BreakpointIdParam:
      name: breakpoint_id
      in: path
      required: true
      schema:
        type: string
      description: Breakpoint identifier

    OffsetParam:
      name: offset
      in: query
      schema:
        type: integer
        default: 0
      description: Pagination offset

    LimitParam:
      name: limit
      in: query
      schema:
        type: integer
        default: 100
        maximum: 1000
      description: Pagination limit

  responses:
    SessionNotFound:
      description: Session not found
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'

    SessionLimitReached:
      description: Session limit reached
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'

    InvalidSessionState:
      description: Invalid session state for operation
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'

    InvalidRequest:
      description: Invalid request
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'

    BreakpointNotFound:
      description: Breakpoint not found
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'

    AttachTimeout:
      description: Attach timeout
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'

  schemas:
    # All schemas from Section 4 would be defined here
    ApiResponse:
      type: object
      properties:
        success:
          type: boolean
        data:
          type: object
        error:
          $ref: '#/components/schemas/ApiError'
        meta:
          $ref: '#/components/schemas/ResponseMeta'

    ApiError:
      type: object
      properties:
        code:
          type: string
        message:
          type: string
        details:
          type: object

    ResponseMeta:
      type: object
      properties:
        request_id:
          type: string
          format: uuid
        timestamp:
          type: string
          format: date-time

    ErrorResponse:
      allOf:
        - $ref: '#/components/schemas/ApiResponse'
        - type: object
          properties:
            success:
              const: false
            data:
              const: null

    # ... remaining schemas from Section 4
```

---

## 8. Client Usage Examples

### 8.1 Basic Debug Session

A complete workflow for debugging a simple Python script.

**Scenario:** Debug `main.py` that processes a CSV file, set a breakpoint, inspect variables, and step through.

```bash
#!/bin/bash
# Basic debug session workflow

BASE_URL="http://localhost:5679/api/v1"

# 1. Create a debug session
echo "=== Creating session ==="
SESSION=$(curl -s -X POST "$BASE_URL/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "csv-processor-debug",
    "project_root": "/Users/dev/myproject"
  }')
SESSION_ID=$(echo $SESSION | jq -r '.data.session_id')
echo "Session ID: $SESSION_ID"

# 2. Set a breakpoint at line 25 where data processing happens
echo "=== Setting breakpoint ==="
curl -s -X POST "$BASE_URL/sessions/$SESSION_ID/breakpoints" \
  -H "Content-Type: application/json" \
  -d '{
    "breakpoints": [
      {
        "source": {"path": "/Users/dev/myproject/main.py"},
        "line": 25
      }
    ]
  }' | jq '.data.breakpoints'

# 3. Launch the program
echo "=== Launching program ==="
curl -s -X POST "$BASE_URL/sessions/$SESSION_ID/launch" \
  -H "Content-Type: application/json" \
  -d '{
    "script": "/Users/dev/myproject/main.py",
    "args": ["--input", "data.csv"],
    "cwd": "/Users/dev/myproject"
  }' | jq '.data'

# 4. Poll for breakpoint hit
echo "=== Waiting for breakpoint ==="
while true; do
  STATUS=$(curl -s "$BASE_URL/sessions/$SESSION_ID" | jq -r '.data.status')
  if [ "$STATUS" = "paused" ]; then
    echo "Paused!"
    break
  fi
  sleep 0.5
done

# 5. Get current location
echo "=== Current location ==="
curl -s "$BASE_URL/sessions/$SESSION_ID" | jq '.data.current_location'

# 6. Get stack trace
echo "=== Stack trace ==="
curl -s "$BASE_URL/sessions/$SESSION_ID/stacktrace" | jq '.data.frames'

# 7. Get local variables
echo "=== Getting scopes ==="
SCOPES=$(curl -s "$BASE_URL/sessions/$SESSION_ID/scopes?frame_id=0")
LOCALS_REF=$(echo $SCOPES | jq -r '.data.scopes[0].variables_reference')

echo "=== Local variables ==="
curl -s "$BASE_URL/sessions/$SESSION_ID/variables?variables_reference=$LOCALS_REF" | jq '.data.variables'

# 8. Evaluate an expression
echo "=== Evaluating expression ==="
curl -s -X POST "$BASE_URL/sessions/$SESSION_ID/evaluate" \
  -H "Content-Type: application/json" \
  -d '{"expression": "len(data)"}' | jq '.data'

# 9. Step over
echo "=== Step over ==="
curl -s -X POST "$BASE_URL/sessions/$SESSION_ID/step-over" | jq '.data.current_location'

# 10. Continue execution
echo "=== Continuing ==="
curl -s -X POST "$BASE_URL/sessions/$SESSION_ID/continue" | jq '.data'

# 11. Wait for completion
echo "=== Waiting for completion ==="
while true; do
  STATUS=$(curl -s "$BASE_URL/sessions/$SESSION_ID" | jq -r '.data.status')
  if [ "$STATUS" = "terminated" ]; then
    echo "Program terminated"
    break
  fi
  sleep 0.5
done

# 12. Get output
echo "=== Program output ==="
curl -s "$BASE_URL/sessions/$SESSION_ID/output" | jq '.data.entries'

# 13. Cleanup
echo "=== Cleaning up ==="
curl -s -X DELETE "$BASE_URL/sessions/$SESSION_ID" | jq '.data'
```

### 8.2 Conditional Breakpoint Debugging

Debug a loop that processes many items, but only stop when a specific condition is met.

```bash
#!/bin/bash
# Conditional breakpoint example

BASE_URL="http://localhost:5679/api/v1"

# Create session
SESSION_ID=$(curl -s -X POST "$BASE_URL/sessions" \
  -H "Content-Type: application/json" \
  -d '{"name": "loop-debug"}' | jq -r '.data.session_id')

# Set conditional breakpoint - only break when item count > 100
curl -s -X POST "$BASE_URL/sessions/$SESSION_ID/breakpoints" \
  -H "Content-Type: application/json" \
  -d '{
    "breakpoints": [
      {
        "source": {"path": "/Users/dev/myproject/processor.py"},
        "line": 42,
        "condition": "len(items) > 100"
      }
    ]
  }'

# Set a hit-count breakpoint - break on the 50th iteration
curl -s -X POST "$BASE_URL/sessions/$SESSION_ID/breakpoints" \
  -H "Content-Type: application/json" \
  -d '{
    "breakpoints": [
      {
        "source": {"path": "/Users/dev/myproject/processor.py"},
        "line": 45,
        "hit_condition": "== 50"
      }
    ]
  }'

# Set a logpoint - log without stopping
curl -s -X POST "$BASE_URL/sessions/$SESSION_ID/breakpoints" \
  -H "Content-Type: application/json" \
  -d '{
    "breakpoints": [
      {
        "source": {"path": "/Users/dev/myproject/processor.py"},
        "line": 48,
        "log_message": "Processing item {i}: {item.name}"
      }
    ]
  }'

# Launch
curl -s -X POST "$BASE_URL/sessions/$SESSION_ID/launch" \
  -H "Content-Type: application/json" \
  -d '{"script": "/Users/dev/myproject/processor.py"}'

# Poll and inspect when stopped
# ... (same polling pattern as basic example)
```

### 8.3 Exception Debugging

Debug a program that raises an exception.

```bash
#!/bin/bash
# Exception debugging example

BASE_URL="http://localhost:5679/api/v1"

# Create session
SESSION_ID=$(curl -s -X POST "$BASE_URL/sessions" \
  -H "Content-Type: application/json" \
  -d '{"name": "exception-debug"}' | jq -r '.data.session_id')

# Launch with stop_on_exception enabled
curl -s -X POST "$BASE_URL/sessions/$SESSION_ID/launch" \
  -H "Content-Type: application/json" \
  -d '{
    "script": "/Users/dev/myproject/buggy_script.py",
    "stop_on_exception": true
  }'

# Poll for exception stop
while true; do
  RESPONSE=$(curl -s "$BASE_URL/sessions/$SESSION_ID")
  STATUS=$(echo $RESPONSE | jq -r '.data.status')
  REASON=$(echo $RESPONSE | jq -r '.data.stop_reason')

  if [ "$STATUS" = "paused" ] && [ "$REASON" = "exception" ]; then
    echo "=== Exception caught! ==="
    echo $RESPONSE | jq '.data.exception'
    break
  elif [ "$STATUS" = "terminated" ]; then
    echo "Program terminated without catching exception"
    break
  fi
  sleep 0.5
done

# Get detailed stack trace at exception point
echo "=== Stack trace at exception ==="
curl -s "$BASE_URL/sessions/$SESSION_ID/stacktrace" | jq '.data.frames'

# Inspect variables at the crash site
SCOPES=$(curl -s "$BASE_URL/sessions/$SESSION_ID/scopes?frame_id=0")
LOCALS_REF=$(echo $SCOPES | jq -r '.data.scopes[0].variables_reference')

echo "=== Variables at crash ==="
curl -s "$BASE_URL/sessions/$SESSION_ID/variables?variables_reference=$LOCALS_REF" | jq '.data.variables'

# Evaluate what caused the exception
echo "=== Diagnosing cause ==="
curl -s -X POST "$BASE_URL/sessions/$SESSION_ID/evaluate" \
  -H "Content-Type: application/json" \
  -d '{"expression": "type(problematic_var)"}' | jq '.data'

curl -s -X POST "$BASE_URL/sessions/$SESSION_ID/evaluate" \
  -H "Content-Type: application/json" \
  -d '{"expression": "repr(problematic_var)"}' | jq '.data'

# Cleanup
curl -s -X DELETE "$BASE_URL/sessions/$SESSION_ID"
```

### 8.4 Multi-File Debugging

Debug across multiple files in a project.

```bash
#!/bin/bash
# Multi-file debugging example

BASE_URL="http://localhost:5679/api/v1"

# Create session with project root
SESSION_ID=$(curl -s -X POST "$BASE_URL/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "multifile-debug",
    "project_root": "/Users/dev/myproject"
  }' | jq -r '.data.session_id')

# Set breakpoints in multiple files
curl -s -X POST "$BASE_URL/sessions/$SESSION_ID/breakpoints" \
  -H "Content-Type: application/json" \
  -d '{
    "breakpoints": [
      {
        "source": {"path": "/Users/dev/myproject/main.py"},
        "line": 15
      },
      {
        "source": {"path": "/Users/dev/myproject/utils/helpers.py"},
        "line": 42
      },
      {
        "source": {"path": "/Users/dev/myproject/models/data.py"},
        "line": 78
      }
    ]
  }'

# Launch main entry point
curl -s -X POST "$BASE_URL/sessions/$SESSION_ID/launch" \
  -H "Content-Type: application/json" \
  -d '{
    "script": "/Users/dev/myproject/main.py",
    "cwd": "/Users/dev/myproject"
  }'

# When paused, stack trace will show frames from multiple files
echo "=== Multi-file stack trace ==="
curl -s "$BASE_URL/sessions/$SESSION_ID/stacktrace?levels=20" | jq '.data.frames[] | {name, file: .source.path, line}'

# Step into a function call (will go to different file)
curl -s -X POST "$BASE_URL/sessions/$SESSION_ID/step-into"

# Check new location (should be in different file)
curl -s "$BASE_URL/sessions/$SESSION_ID" | jq '.data.current_location'

# Continue to next breakpoint (in yet another file)
curl -s -X POST "$BASE_URL/sessions/$SESSION_ID/continue"
```

### 8.5 Python Script Client Example

A more robust Python client implementation:

```python
#!/usr/bin/env python3
"""
Example Python client for OpenCode Debug Relay Server
"""

import time
import requests
from typing import Optional, Dict, Any, List

class DebugClient:
    """Client for OpenCode Debug Relay Server API."""

    def __init__(self, base_url: str = "http://localhost:5679/api/v1"):
        self.base_url = base_url
        self.session_id: Optional[str] = None
        self._event_cursor: Optional[str] = None

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Make an API request and return the data."""
        url = f"{self.base_url}{path}"
        response = requests.request(method, url, **kwargs)
        result = response.json()

        if not result.get("success"):
            error = result.get("error", {})
            raise Exception(f"API Error: {error.get('code')} - {error.get('message')}")

        return result.get("data", {})

    def create_session(self, name: str = None, project_root: str = None) -> str:
        """Create a new debug session."""
        payload = {}
        if name:
            payload["name"] = name
        if project_root:
            payload["project_root"] = project_root

        data = self._request("POST", "/sessions", json=payload)
        self.session_id = data["session_id"]
        return self.session_id

    def get_session(self) -> Dict[str, Any]:
        """Get current session status."""
        return self._request("GET", f"/sessions/{self.session_id}")

    def set_breakpoints(self, breakpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Set breakpoints in the session."""
        data = self._request(
            "POST",
            f"/sessions/{self.session_id}/breakpoints",
            json={"breakpoints": breakpoints}
        )
        return data["breakpoints"]

    def launch(self, script: str, args: List[str] = None,
               cwd: str = None, stop_on_entry: bool = False,
               stop_on_exception: bool = True) -> Dict[str, Any]:
        """Launch a program for debugging."""
        payload = {
            "script": script,
            "stop_on_entry": stop_on_entry,
            "stop_on_exception": stop_on_exception
        }
        if args:
            payload["args"] = args
        if cwd:
            payload["cwd"] = cwd

        return self._request("POST", f"/sessions/{self.session_id}/launch", json=payload)

    def wait_for_pause(self, timeout: float = 30.0) -> Dict[str, Any]:
        """Wait until the program is paused."""
        start = time.time()
        while time.time() - start < timeout:
            session = self.get_session()
            if session["status"] == "paused":
                return session
            if session["status"] == "terminated":
                raise Exception("Program terminated")
            time.sleep(0.1)
        raise TimeoutError("Timeout waiting for pause")

    def continue_execution(self) -> Dict[str, Any]:
        """Resume program execution."""
        return self._request("POST", f"/sessions/{self.session_id}/continue")

    def step_over(self) -> Dict[str, Any]:
        """Step over to next line."""
        return self._request("POST", f"/sessions/{self.session_id}/step-over")

    def step_into(self) -> Dict[str, Any]:
        """Step into function call."""
        return self._request("POST", f"/sessions/{self.session_id}/step-into")

    def step_out(self) -> Dict[str, Any]:
        """Step out of current function."""
        return self._request("POST", f"/sessions/{self.session_id}/step-out")

    def get_stacktrace(self, thread_id: int = None) -> List[Dict[str, Any]]:
        """Get current stack trace."""
        params = {}
        if thread_id:
            params["thread_id"] = thread_id
        data = self._request("GET", f"/sessions/{self.session_id}/stacktrace", params=params)
        return data["frames"]

    def get_variables(self, variables_reference: int) -> List[Dict[str, Any]]:
        """Get variables for a scope or variable reference."""
        data = self._request(
            "GET",
            f"/sessions/{self.session_id}/variables",
            params={"variables_reference": variables_reference}
        )
        return data["variables"]

    def get_local_variables(self, frame_id: int = 0) -> List[Dict[str, Any]]:
        """Get local variables for a frame."""
        scopes = self._request(
            "GET",
            f"/sessions/{self.session_id}/scopes",
            params={"frame_id": frame_id}
        )

        for scope in scopes["scopes"]:
            if scope["name"] == "Locals":
                return self.get_variables(scope["variables_reference"])
        return []

    def evaluate(self, expression: str, frame_id: int = 0) -> Dict[str, Any]:
        """Evaluate an expression in the current context."""
        return self._request(
            "POST",
            f"/sessions/{self.session_id}/evaluate",
            json={"expression": expression, "frame_id": frame_id}
        )

    def get_output(self) -> List[Dict[str, Any]]:
        """Get program output."""
        data = self._request("GET", f"/sessions/{self.session_id}/output")
        return data["entries"]

    def poll_events(self, timeout: int = 0) -> List[Dict[str, Any]]:
        """Poll for debug events."""
        params = {"timeout": timeout}
        if self._event_cursor:
            params["cursor"] = self._event_cursor

        data = self._request("GET", f"/sessions/{self.session_id}/events", params=params)
        self._event_cursor = data.get("next_cursor")
        return data["events"]

    def delete_session(self) -> Dict[str, Any]:
        """Delete the current session."""
        result = self._request("DELETE", f"/sessions/{self.session_id}")
        self.session_id = None
        return result


# Example usage
if __name__ == "__main__":
    client = DebugClient()

    try:
        # Create session
        session_id = client.create_session(
            name="example-debug",
            project_root="/Users/dev/myproject"
        )
        print(f"Created session: {session_id}")

        # Set breakpoint
        breakpoints = client.set_breakpoints([
            {"source": {"path": "/Users/dev/myproject/main.py"}, "line": 25}
        ])
        print(f"Set {len(breakpoints)} breakpoint(s)")

        # Launch program
        client.launch(
            script="/Users/dev/myproject/main.py",
            args=["--verbose"],
            stop_on_exception=True
        )
        print("Program launched")

        # Wait for breakpoint
        session = client.wait_for_pause()
        print(f"Paused at: {session['current_location']}")

        # Get stack trace
        frames = client.get_stacktrace()
        print(f"Stack trace ({len(frames)} frames):")
        for frame in frames:
            print(f"  {frame['name']} at {frame['source']['path']}:{frame['line']}")

        # Get local variables
        variables = client.get_local_variables()
        print("Local variables:")
        for var in variables:
            print(f"  {var['name']} = {var['value']} ({var['type']})")

        # Evaluate expression
        result = client.evaluate("len(data) * 2")
        print(f"Evaluation result: {result['result']} ({result['type']})")

        # Continue and wait for completion
        client.continue_execution()

        while True:
            session = client.get_session()
            if session["status"] == "terminated":
                print("Program terminated")
                break
            time.sleep(0.5)

        # Get final output
        output = client.get_output()
        print(f"Program output ({len(output)} entries):")
        for entry in output[-5:]:  # Last 5 entries
            print(f"  [{entry['category']}] {entry['output'].strip()}")

    finally:
        # Cleanup
        if client.session_id:
            client.delete_session()
            print("Session cleaned up")
```

---

## Appendix A: HTTP Status Code Reference

| Status | Meaning | When Used |
|--------|---------|-----------|
| 200 | OK | Successful GET, POST, DELETE |
| 201 | Created | Session created successfully |
| 400 | Bad Request | Invalid request body, validation errors |
| 404 | Not Found | Session, breakpoint, or resource not found |
| 409 | Conflict | Invalid state for operation |
| 410 | Gone | Session expired |
| 429 | Too Many Requests | Session limit reached |
| 500 | Internal Server Error | Unexpected server error |
| 502 | Bad Gateway | debugpy connection refused |
| 504 | Gateway Timeout | debugpy operation timeout |

---

## Appendix B: Design Decisions

### B.1 Polling vs WebSockets

**Decision:** Polling-based event retrieval

**Rationale:**
- AI agents typically use HTTP-based tool interfaces
- WebSockets add complexity without significant benefit for CLI agents
- Long-polling provides reasonable latency when needed
- Simpler to implement and debug

### B.2 Response Envelope

**Decision:** Consistent envelope with `success`, `data`, `error`, `meta`

**Rationale:**
- Predictable response structure for all endpoints
- Clear separation of data and metadata
- Error handling is uniform across all endpoints
- Request tracking via request_id

### B.3 Variable References

**Decision:** Use integer references for expandable variables (DAP-style)

**Rationale:**
- Direct mapping to debugpy/DAP protocol
- Efficient for large data structures
- Supports lazy loading of complex objects
- Handles circular references gracefully

### B.4 Breakpoint Management

**Decision:** Batch breakpoint setting with individual IDs

**Rationale:**
- Efficient for setting multiple breakpoints at once
- Individual IDs allow targeted removal
- Verification status per breakpoint
- Matches debugpy capabilities

---

**Document Revision History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-13 | API Designer Agent | Initial comprehensive API specification |
