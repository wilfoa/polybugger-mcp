# LLD Architecture Review

**Project:** OpenCode Debug Relay Server
**Review Date:** January 13, 2026
**Reviewer:** Architecture Review Agent
**Documents Reviewed:**
- LLD_BACKEND.md (Backend Implementation)
- LLD_API.md (API Specification)

---

## Executive Summary

Both Low-Level Design documents are **well-structured and comprehensive**, demonstrating excellent alignment with the HLD requirements. The documents show thoughtful design decisions, proper separation of concerns, and practical implementation guidance. However, there are several **minor inconsistencies** between the two documents that should be addressed before implementation.

| Document | Verdict | Summary |
|----------|---------|---------|
| **LLD_BACKEND.md** | :recycle: **Revision Required** | Minor inconsistencies in error codes and model fields |
| **LLD_API.md** | :recycle: **Revision Required** | Session ID format inconsistency, status enum mismatch |

---

## 1. Document Summaries

### 1.1 LLD_BACKEND.md Summary

The Backend LLD provides a comprehensive implementation specification including:

- **Project Structure**: Clean modular architecture with 7 main packages (api, core, adapters, persistence, models, utils)
- **Module Specifications**: Detailed Python code for all core components
- **Session Management**: Full lifecycle with state machine (CREATED -> LAUNCHING -> RUNNING -> PAUSED -> TERMINATED)
- **DAP Protocol Integration**: Complete debugpy adapter with DAP client implementation
- **Persistence Layer**: Atomic file operations with per-project breakpoint storage
- **Output Buffer**: Ring buffer implementation with 50MB limit
- **Error Hierarchy**: Well-structured exception classes with error codes
- **Implementation Order**: Prioritized task list with dependencies

**Strengths:**
- Comprehensive code examples with type hints
- Clear state transition diagram
- Proper async patterns with locks
- Good separation of DAP protocol handling

### 1.2 LLD_API.md Summary

The API LLD provides a complete REST API specification including:

- **20+ Endpoints**: Full coverage of sessions, breakpoints, execution, inspection, output
- **Request/Response Schemas**: JSON Schema definitions for all payloads
- **Error Codes**: Comprehensive catalog with HTTP status mappings
- **Event Types**: Complete event specification for polling-based model
- **OpenAPI Outline**: Structure for auto-generated documentation
- **Client Examples**: Bash and Python client implementations

**Strengths:**
- Excellent documentation with examples
- Consistent response envelope pattern
- Thorough error code catalog
- Practical client usage examples

---

## 2. Review Checklist Results

### 2.1 Alignment with HLD

| Requirement | Backend LLD | API LLD | Notes |
|-------------|:-----------:|:-------:|-------|
| FastAPI async HTTP server | :white_check_mark: | :white_check_mark: | Both specify FastAPI with uvicorn |
| debugpy subprocess per session | :white_check_mark: | :white_check_mark: | DebugpyAdapter spawns subprocess |
| Max 10 concurrent sessions | :white_check_mark: | :white_check_mark: | `max_sessions: int = 10` |
| 50MB output buffer per session | :white_check_mark: | :white_check_mark: | `output_buffer_max_bytes: int = 50 * 1024 * 1024` |
| Per-project breakpoint persistence | :white_check_mark: | :white_check_mark: | BreakpointStore with project_id_from_path |
| Session auto-recovery | :warning: | N/A | Backend has TODO placeholder |
| Polling-based event model | :white_check_mark: | :white_check_mark: | EventQueue with GET /events endpoint |
| localhost-only binding | :white_check_mark: | :white_check_mark: | `host: str = "127.0.0.1"` |

**Issue Found:** Session recovery is marked as TODO in backend (line 471: `# TODO: Implement session recovery from disk`). This is acceptable as P2 priority but should be tracked.

### 2.2 Cross-LLD Consistency

#### 2.2.1 Session Status Values

| Backend (`SessionState`) | API (`status`) | Match |
|--------------------------|----------------|:-----:|
| `CREATED` | `created` | :white_check_mark: |
| `LAUNCHING` | `launching` | :white_check_mark: |
| `RUNNING` | `running` | :white_check_mark: |
| `PAUSED` | `paused` | :white_check_mark: |
| `TERMINATED` | `terminated` | :white_check_mark: |
| `ERROR` | `failed` | :x: **MISMATCH** |

**Issue #1:** Backend uses `SessionState.ERROR` while API uses status `failed`. These should be aligned.

#### 2.2.2 Session ID Format

| Document | Format | Example |
|----------|--------|---------|
| Backend | UUID v4 | `a1b2c3d4-e5f6-7890-abcd-ef1234567890` |
| API | `sess_{uuid8}` | `sess_a1b2c3d4` |

**Issue #2:** Backend generates full UUID (`str(uuid.uuid4())`), but API specifies prefixed 8-character format (`sess_{uuid8}`). This needs alignment.

#### 2.2.3 Error Codes Comparison

| Error Scenario | Backend Code | API Code | Match |
|----------------|--------------|----------|:-----:|
| Session not found | `SESSION_NOT_FOUND` | `SESSION_NOT_FOUND` | :white_check_mark: |
| Session limit | `SESSION_LIMIT_REACHED` | `SESSION_LIMIT_REACHED` | :white_check_mark: |
| Invalid state | `INVALID_SESSION_STATE` | `INVALID_SESSION_STATE` | :white_check_mark: |
| DAP timeout | `DAP_TIMEOUT` | `DEBUGPY_TIMEOUT` | :x: **MISMATCH** |
| DAP connection | `DAP_CONNECTION_ERROR` | `DEBUGPY_ERROR` | :x: **MISMATCH** |
| Launch error | `LAUNCH_ERROR` | `LAUNCH_FAILED` | :x: **MISMATCH** |
| Session expired | N/A | `SESSION_EXPIRED` | :warning: Missing in backend |
| Breakpoint not found | N/A | `BREAKPOINT_NOT_FOUND` | :warning: Missing in backend |
| Thread not found | N/A | `THREAD_NOT_FOUND` | :warning: Missing in backend |
| Frame not found | N/A | `FRAME_NOT_FOUND` | :warning: Missing in backend |
| Variable not found | N/A | `VARIABLE_NOT_FOUND` | :warning: Missing in backend |

**Issue #3:** Several error code naming inconsistencies and missing backend exceptions for API-defined errors.

#### 2.2.4 Endpoint Paths vs Router Definitions

| API Endpoint | Backend Router File | Notes |
|--------------|---------------------|-------|
| `GET /health` | `api/server.py` | :white_check_mark: |
| `GET /info` | `api/server.py` | :white_check_mark: |
| `POST /sessions` | `api/sessions.py` | :white_check_mark: |
| `GET /sessions` | `api/sessions.py` | :white_check_mark: |
| `GET /sessions/{id}` | `api/sessions.py` | :white_check_mark: |
| `DELETE /sessions/{id}` | `api/sessions.py` | :white_check_mark: |
| `POST /sessions/{id}/launch` | `api/sessions.py` | :white_check_mark: |
| `POST /sessions/{id}/attach` | `api/sessions.py` | :white_check_mark: |
| `POST /sessions/{id}/breakpoints` | `api/breakpoints.py` | :white_check_mark: |
| `GET /sessions/{id}/breakpoints` | `api/breakpoints.py` | :white_check_mark: |
| `DELETE /sessions/{id}/breakpoints/{bp_id}` | `api/breakpoints.py` | :white_check_mark: |
| `POST /sessions/{id}/continue` | `api/execution.py` | :white_check_mark: |
| `POST /sessions/{id}/pause` | `api/execution.py` | :white_check_mark: |
| `POST /sessions/{id}/step-over` | `api/execution.py` | :white_check_mark: |
| `POST /sessions/{id}/step-into` | `api/execution.py` | :white_check_mark: |
| `POST /sessions/{id}/step-out` | `api/execution.py` | :white_check_mark: |
| `GET /sessions/{id}/threads` | `api/inspection.py` | :white_check_mark: |
| `GET /sessions/{id}/stacktrace` | `api/inspection.py` | :white_check_mark: |
| `GET /sessions/{id}/scopes` | `api/inspection.py` | :white_check_mark: |
| `GET /sessions/{id}/variables` | `api/inspection.py` | :white_check_mark: |
| `POST /sessions/{id}/evaluate` | `api/inspection.py` | :white_check_mark: |
| `GET /sessions/{id}/output` | `api/output.py` | :white_check_mark: |
| `GET /sessions/{id}/events` | `api/output.py` | :white_check_mark: |

All endpoints have corresponding router files defined.

#### 2.2.5 Request/Response Model Alignment

| API Model | Backend Model | Match | Notes |
|-----------|---------------|:-----:|-------|
| `CreateSessionRequest` | `SessionConfig` | :warning: | API has more fields (timeout_minutes) |
| `LaunchRequest` | `LaunchConfig` | :warning: | API has module, console, python_args |
| `AttachRequest` | `AttachConfig` | :white_check_mark: | Aligned |
| `SetBreakpointsRequest` | `SourceBreakpoint` | :warning: | API has enabled field, backend doesn't |
| `StackFrame` | `StackFrame` | :white_check_mark: | Aligned |
| `Variable` | `Variable` | :white_check_mark: | Aligned |
| `Thread` | `Thread` | :white_check_mark: | Aligned |

**Issue #4:** Model field mismatches between API and backend:
- API `LaunchRequest` has `module`, `console`, `python_args` not in backend `LaunchConfig`
- API breakpoint has `enabled` field not in backend `SourceBreakpoint`
- API `CreateSessionRequest` has `timeout_minutes` not directly mapped in backend

### 2.3 Completeness

#### Backend LLD Completeness

| Aspect | Status | Notes |
|--------|:------:|-------|
| Core session lifecycle | :white_check_mark: | Complete state machine |
| DAP protocol handling | :white_check_mark: | Full initialize/launch/attach/step/continue |
| Breakpoint management | :white_check_mark: | Set, persist, load |
| Variable inspection | :white_check_mark: | Scopes, variables, evaluate |
| Output capture | :white_check_mark: | Ring buffer with pagination |
| Event queue | :white_check_mark: | Async queue with history |
| Error handling | :white_check_mark: | Exception hierarchy |
| Session recovery | :warning: | TODO placeholder |
| Graceful shutdown | :white_check_mark: | Cleanup on stop |

#### API LLD Completeness

| Aspect | Status | Notes |
|--------|:------:|-------|
| All CRUD operations | :white_check_mark: | Sessions, breakpoints |
| Execution control | :white_check_mark: | continue, pause, step operations |
| Inspection endpoints | :white_check_mark: | threads, stack, scopes, variables |
| Event polling | :white_check_mark: | With cursor and long-poll |
| Error responses | :white_check_mark: | Comprehensive catalog |
| Request validation | :white_check_mark: | JSON Schema definitions |
| Pagination | :white_check_mark: | Both offset and cursor based |
| Client examples | :white_check_mark: | Bash and Python |

### 2.4 Technical Correctness

#### Async Patterns Assessment

| Pattern | Status | Notes |
|---------|:------:|-------|
| `asyncio.Lock` usage | :white_check_mark: | Used for state transitions and session registry |
| `asyncio.Queue` usage | :white_check_mark: | EventQueue implementation |
| Background tasks | :white_check_mark: | Cleanup loop with `create_task` |
| Stream reader/writer | :white_check_mark: | DAP client uses subprocess PIPE |
| Proper cancellation | :white_check_mark: | Tasks cancelled in stop() |
| `await` on I/O | :white_check_mark: | aiofiles for persistence |

#### DAP Protocol Handling

| Aspect | Status | Notes |
|--------|:------:|-------|
| Content-Length header | :white_check_mark: | Properly implemented |
| JSON message parsing | :white_check_mark: | Correct encoding |
| Request/response matching | :white_check_mark: | Using seq numbers |
| Event dispatching | :white_check_mark: | Callback-based |
| Timeout handling | :white_check_mark: | asyncio.wait_for |
| Error propagation | :white_check_mark: | DAPError exceptions |

#### Persistence Design

| Aspect | Status | Notes |
|--------|:------:|-------|
| Atomic writes | :white_check_mark: | Temp file + rename |
| Project ID hashing | :white_check_mark: | SHA256 of path |
| JSON serialization | :white_check_mark: | With default=str |
| Error recovery | :white_check_mark: | Temp file cleanup |
| Directory creation | :white_check_mark: | parents=True |

### 2.5 Implementation Feasibility

#### Dependencies Assessment

| Dependency | Version | Availability | Risk |
|------------|---------|:------------:|:----:|
| FastAPI | >=0.109.0 | :white_check_mark: | Low |
| uvicorn | >=0.27.0 | :white_check_mark: | Low |
| debugpy | >=1.8.0 | :white_check_mark: | Low |
| pydantic | >=2.5.0 | :white_check_mark: | Low |
| pydantic-settings | >=2.1.0 | :white_check_mark: | Low |
| aiofiles | >=23.2.0 | :white_check_mark: | Low |

All dependencies are well-maintained and widely used.

#### Implementation Order Analysis

The backend LLD provides a clear implementation order with dependencies:

```
1. Project scaffolding
2. config.py (depends on: 1)
3. exceptions.py (depends on: 1)
4. models/*.py (depends on: 1)
5. output_buffer.py (depends on: 4)
6. persistence/storage.py (depends on: 3)
7. persistence/breakpoints.py (depends on: 6)
8. dap_client.py (depends on: 3, 4)
9. debugpy_adapter.py (depends on: 8)
10. events.py (depends on: 4)
11. session.py (depends on: 5, 7, 9, 10)
12-19. API layer (depends on: 11)
```

**Assessment:** Implementation order is logical with no circular dependencies.

---

## 3. Issues Found

### Critical Issues (Must Fix)

None identified. Both documents are fundamentally sound.

### Major Issues (Should Fix Before Implementation)

#### Issue #1: Session Status Enum Mismatch
- **Location:** Backend `SessionState.ERROR` vs API status `failed`
- **Impact:** API consumers will receive inconsistent status values
- **Recommendation:** Change backend to use `FAILED` or API to use `error`
- **Suggested Fix:** Align on `error` in both (more descriptive than `failed`)

#### Issue #2: Session ID Format Mismatch
- **Location:** Backend `uuid.uuid4()` vs API `sess_{uuid8}`
- **Impact:** Session IDs won't match documented format
- **Recommendation:** Update backend to generate prefixed IDs
- **Suggested Fix:**
  ```python
  session_id = f"sess_{uuid.uuid4().hex[:8]}"
  ```

#### Issue #3: Error Code Inconsistencies
- **Location:** Multiple error codes differ between documents
- **Impact:** Error handling code will be inconsistent
- **Recommendation:** Standardize error codes
- **Suggested Fixes:**
  - `DAP_TIMEOUT` -> `DEBUGPY_TIMEOUT` (use API version)
  - `DAP_CONNECTION_ERROR` -> `DEBUGPY_ERROR` (use API version)
  - `LAUNCH_ERROR` -> `LAUNCH_FAILED` (use API version)
  - Add missing backend exceptions: `SessionExpiredError`, `BreakpointNotFoundError`, `ThreadNotFoundError`, `FrameNotFoundError`, `VariableNotFoundError`

#### Issue #4: Model Field Mismatches
- **Location:** LaunchConfig, SourceBreakpoint, SessionConfig
- **Impact:** API features won't be implementable
- **Recommendation:** Add missing fields to backend models
- **Suggested Fixes:**
  - Add to `LaunchConfig`: `module`, `console`, `python_args`
  - Add to `SourceBreakpoint`: `enabled`
  - Add to `SessionConfig`: `timeout_minutes`

### Minor Issues (Nice to Fix)

#### Issue #5: Event Type Enum
- **Location:** Backend `EventType` vs API event types
- **Status:** Aligned, but API has additional event body details not in backend
- **Recommendation:** Ensure backend event data matches API schema

#### Issue #6: Output Entry Format
- **Location:** Backend `OutputLine` vs API output entry
- **Difference:** API has `source` and `line` fields not in backend
- **Recommendation:** Add source tracking to `OutputLine`

---

## 4. Architectural Recommendations

### 4.1 Strengths to Preserve

1. **Clean Separation of Concerns**: The modular structure with adapters, core, and persistence layers is well-designed
2. **Async-First Design**: Proper use of asyncio primitives throughout
3. **DAP Protocol Abstraction**: Clean adapter pattern isolates protocol details
4. **Consistent API Envelope**: Uniform response structure aids client development
5. **Comprehensive Error Handling**: Both documents have thorough error catalogs

### 4.2 Suggested Improvements

1. **Add Health Check Details**: Include debugpy process health in health endpoint
2. **Consider Rate Limiting**: Even for localhost, protect against runaway clients
3. **Add Request Logging**: Structured logging for debugging the debugger
4. **Session Recovery Priority**: Move from P2 to P1 given crash scenario importance
5. **Add Metrics Endpoint**: Expose session/request metrics for monitoring

### 4.3 Security Considerations

Both documents correctly specify localhost-only binding. Additional recommendations:

1. **Input Validation**: Ensure all file paths are validated and sandboxed
2. **Expression Evaluation Safety**: Document security implications of `evaluate` endpoint
3. **Resource Limits**: Add per-session memory limits beyond output buffer
4. **Timeout Enforcement**: Ensure all DAP operations have timeouts

---

## 5. Verdict

### LLD_BACKEND.md

:recycle: **Revision Required**

**Required Changes:**
1. Change `SessionState.ERROR` to `SessionState.FAILED` (or align with API)
2. Update session ID generation to use `sess_` prefix format
3. Rename error codes to match API specification
4. Add missing exception classes
5. Add missing model fields (`module`, `console`, `python_args`, `enabled`, `timeout_minutes`)

**Estimated Effort:** 2-4 hours

### LLD_API.md

:recycle: **Revision Required**

**Required Changes:**
1. Verify session status enum uses consistent value (`error` vs `failed`)
2. Confirm session ID format matches implementation choice

**Estimated Effort:** 30 minutes

---

## 6. Alignment Matrix

| HLD Requirement | Backend Implementation | API Contract | Status |
|-----------------|------------------------|--------------|:------:|
| FastAPI server | `main.py` with FastAPI app | `/api/v1/` base URL | :white_check_mark: |
| debugpy subprocess | `DebugpyAdapter.initialize()` | `POST /sessions/{id}/launch` | :white_check_mark: |
| Max 10 sessions | `settings.max_sessions = 10` | 429 `SESSION_LIMIT_REACHED` | :white_check_mark: |
| 50MB output buffer | `OutputBuffer(max_size=50*1024*1024)` | `GET /sessions/{id}/output` | :white_check_mark: |
| Breakpoint persistence | `BreakpointStore` + JSON files | `POST/GET /sessions/{id}/breakpoints` | :white_check_mark: |
| Session recovery | TODO in `_recover_sessions()` | N/A | :warning: |
| Polling events | `EventQueue.get_all()` | `GET /sessions/{id}/events?timeout=` | :white_check_mark: |
| Localhost only | `host: str = "127.0.0.1"` | `http://localhost:5679` | :white_check_mark: |

---

## 7. Next Steps

After revisions are complete:

1. **Test Plan Development**: Create comprehensive test plan based on both LLDs
2. **Integration Contract Tests**: Define tests that verify API-Backend alignment
3. **Implementation Sprint**: Follow backend implementation order
4. **API Documentation**: Generate OpenAPI spec from FastAPI routes
5. **Client SDK**: Consider generating clients from OpenAPI spec

---

**Review Completed:** January 13, 2026
**Reviewer Signature:** Architecture Review Agent

---

## Appendix: Cross-Reference Quick Guide

### Error Code Mapping (Proposed Alignment)

| Scenario | Backend Exception | API Error Code | HTTP Status |
|----------|-------------------|----------------|:-----------:|
| Session not found | `SessionNotFoundError` | `SESSION_NOT_FOUND` | 404 |
| Session limit | `SessionLimitError` | `SESSION_LIMIT_REACHED` | 429 |
| Invalid state | `InvalidSessionStateError` | `INVALID_SESSION_STATE` | 409 |
| Session expired | `SessionExpiredError` (NEW) | `SESSION_EXPIRED` | 410 |
| DAP timeout | `DAPTimeoutError` | `DEBUGPY_TIMEOUT` | 504 |
| DAP connection | `DAPConnectionError` | `DEBUGPY_ERROR` | 502 |
| Launch failed | `LaunchError` | `LAUNCH_FAILED` | 500 |
| Breakpoint not found | `BreakpointNotFoundError` (NEW) | `BREAKPOINT_NOT_FOUND` | 404 |
| Thread not found | `ThreadNotFoundError` (NEW) | `THREAD_NOT_FOUND` | 404 |
| Frame not found | `FrameNotFoundError` (NEW) | `FRAME_NOT_FOUND` | 404 |
| Variable not found | `VariableNotFoundError` (NEW) | `VARIABLE_NOT_FOUND` | 404 |
| Persistence error | `PersistenceError` | `INTERNAL_ERROR` | 500 |
| Validation error | Pydantic `ValidationError` | `INVALID_REQUEST` | 400 |

### Model Field Alignment Checklist

```
Backend LaunchConfig needs:
  [ ] module: Optional[str]
  [ ] console: str = "internalConsole"
  [ ] python_args: list[str] = []

Backend SourceBreakpoint needs:
  [ ] enabled: bool = True

Backend SessionConfig needs:
  [ ] timeout_minutes: int = 60

Backend Session needs:
  [ ] Generate ID as f"sess_{uuid.uuid4().hex[:8]}"
  [ ] Use FAILED instead of ERROR state
```
