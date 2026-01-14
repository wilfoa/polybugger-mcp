# OpenCode Debug Relay Server - Engineering Task Backlog

**Project:** OpenCode Debug Relay Server
**Version:** 1.0
**Created:** January 13, 2026
**Last Updated:** January 13, 2026
**Status:** Ready for Development

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total Tasks** | 127 |
| **P0 (Critical)** | 48 tasks |
| **P1 (High)** | 42 tasks |
| **P2 (Medium)** | 27 tasks |
| **P3 (Low)** | 10 tasks |
| **Total Estimated Hours** | ~248h |
| **Estimated Duration** | 14 days (2 weeks) |

### Priority Breakdown

```
P0 Critical  ████████████████░░░░░░░░  48 tasks (38%)
P1 High      █████████████░░░░░░░░░░░  42 tasks (33%)
P2 Medium    ████████░░░░░░░░░░░░░░░░  27 tasks (19%)
P3 Low       ███░░░░░░░░░░░░░░░░░░░░░  10 tasks (8%)
```

### Sprint Breakdown (2-Week Sprint)

| Sprint | Focus Area | Tasks | Hours | Deliverable |
|--------|------------|-------|-------|-------------|
| **Sprint 1** (Days 1-7) | Foundation + Infrastructure | TASK-001 to TASK-050 | ~110h | Working DAP client, session management |
| **Sprint 2** (Days 8-14) | API + Testing + Polish | TASK-051 to TASK-127 | ~138h | Complete API, tests, documentation |

### Critical Path

```
TASK-001 (Setup)
    └─> TASK-011 (Models)
        └─> TASK-021 (Config)
            └─> TASK-025 (Output Buffer)
                └─> TASK-031 (DAP Client)
                    └─> TASK-035 (debugpy Adapter)
                        └─> TASK-041 (Session)
                            └─> TASK-045 (SessionManager)
                                └─> TASK-051 (Health API)
                                    └─> TASK-055 (Sessions API)
                                        └─> TASK-081 (Unit Tests)
                                            └─> TASK-101 (Integration Tests)
                                                └─> TASK-111 (E2E Tests)
```

---

## Task Categories

1. [Project Setup](#1-project-setup-task-001-to-task-010) (TASK-001 to TASK-010)
2. [Core Models](#2-core-models-task-011-to-task-020) (TASK-011 to TASK-020)
3. [Infrastructure](#3-infrastructure-task-021-to-task-040) (TASK-021 to TASK-040)
4. [Session Management](#4-session-management-task-041-to-task-050) (TASK-041 to TASK-050)
5. [API Endpoints](#5-api-endpoints-task-051-to-task-080) (TASK-051 to TASK-080)
6. [Unit Tests](#6-unit-tests-task-081-to-task-100) (TASK-081 to TASK-100)
7. [Integration Tests](#7-integration-tests-task-101-to-task-110) (TASK-101 to TASK-110)
8. [E2E Tests](#8-e2e-tests-task-111-to-task-120) (TASK-111 to TASK-120)
9. [Documentation & Polish](#9-documentation--polish-task-121-to-task-127) (TASK-121 to TASK-127)

---

## 1. Project Setup (TASK-001 to TASK-010)

### TASK-001: Initialize Project Repository Structure

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 2h
**Dependencies:** None
**Assignee:** Unassigned

**Description:**
Create the initial project directory structure following the layout specified in LLD_BACKEND.md. This includes all directories for source code, tests, fixtures, and documentation.

**Acceptance Criteria:**
- [ ] Create `src/opencode_debugger/` directory with all subdirectories (api/, core/, adapters/, persistence/, models/, utils/)
- [ ] Create `tests/` directory with subdirectories (unit/, integration/, e2e/, fixtures/, errors/, performance/)
- [ ] Create `tests/fixtures/scripts/` and `tests/fixtures/projects/` directories
- [ ] Create empty `__init__.py` files in all Python packages
- [ ] Verify structure matches LLD_BACKEND.md Section 1

**Files to Create/Modify:**
- src/opencode_debugger/__init__.py
- src/opencode_debugger/api/__init__.py
- src/opencode_debugger/core/__init__.py
- src/opencode_debugger/adapters/__init__.py
- src/opencode_debugger/persistence/__init__.py
- src/opencode_debugger/models/__init__.py
- src/opencode_debugger/utils/__init__.py
- tests/__init__.py
- tests/conftest.py (empty)

**Reference:**
- LLD_BACKEND.md Section 1 (Project Structure)

---

### TASK-002: Create pyproject.toml with Dependencies

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 1h
**Dependencies:** TASK-001
**Assignee:** Unassigned

**Description:**
Create the `pyproject.toml` file with all runtime and development dependencies, build configuration, and tool settings.

**Acceptance Criteria:**
- [ ] Define project metadata (name, version, description, authors)
- [ ] Add runtime dependencies: fastapi>=0.109.0, uvicorn>=0.27.0, debugpy>=1.8.0, pydantic>=2.5.0, pydantic-settings>=2.1.0, aiofiles>=23.2.0
- [ ] Add dev dependencies: pytest>=8.0.0, pytest-asyncio>=0.23.0, pytest-cov>=4.1.0, pytest-timeout>=2.2.0, httpx>=0.26.0, ruff>=0.1.0, mypy>=1.8.0
- [ ] Configure pytest settings per TEST_PLAN.md Section 9.1
- [ ] Configure ruff and mypy settings
- [ ] Set Python version requirement >=3.9

**Files to Create/Modify:**
- pyproject.toml

**Reference:**
- IMPLEMENTATION_PLAN.md Section 7 (Dependencies)
- TEST_PLAN.md Section 9.1 (pytest Configuration)

---

### TASK-003: Setup Development Tooling Configuration

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 1h
**Dependencies:** TASK-002
**Assignee:** Unassigned

**Description:**
Configure development tools including ruff linting, mypy type checking, and coverage reporting.

**Acceptance Criteria:**
- [ ] Create `.coveragerc` with coverage settings from TEST_PLAN.md
- [ ] Verify ruff configuration in pyproject.toml
- [ ] Verify mypy configuration in pyproject.toml
- [ ] Create `.env.example` with sample environment variables

**Files to Create/Modify:**
- .coveragerc
- .env.example

**Reference:**
- TEST_PLAN.md Section 9.2 (Coverage Configuration)
- LLD_BACKEND.md Section 2.1 (config.py)

---

### TASK-004: Create Pre-commit Hooks Configuration

**Status:** TODO
**Priority:** P2 (Medium)
**Estimate:** 0.5h
**Dependencies:** TASK-003
**Assignee:** Unassigned

**Description:**
Set up pre-commit hooks for code quality enforcement.

**Acceptance Criteria:**
- [ ] Create `.pre-commit-config.yaml` with ruff, mypy, and pytest hooks
- [ ] Document pre-commit setup in README

**Files to Create/Modify:**
- .pre-commit-config.yaml

**Reference:**
- TEST_PLAN.md Section 9.5 (Pre-commit Hooks)

---

### TASK-005: Setup pytest Fixtures and conftest.py

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 2h
**Dependencies:** TASK-002
**Assignee:** Unassigned

**Description:**
Create the global pytest configuration and shared fixtures for all tests.

**Acceptance Criteria:**
- [ ] Implement `event_loop` fixture for async tests
- [ ] Implement `temp_data_dir` fixture for test isolation
- [ ] Implement `test_settings` fixture with test configuration
- [ ] Implement `app` and `client` fixtures for API testing
- [ ] Implement `session_manager` fixture for unit tests
- [ ] Implement `sample_scripts_dir` and script path fixtures
- [ ] Implement factory fixtures (breakpoint_factory, session_config_factory, launch_config_factory)

**Files to Create/Modify:**
- tests/conftest.py

**Reference:**
- TEST_PLAN.md Section 8.4 (Pytest Fixtures)

---

### TASK-006: Create Sample Test Scripts

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 2h
**Dependencies:** TASK-001
**Assignee:** Unassigned

**Description:**
Create the sample Python scripts used as test fixtures for debugging tests.

**Acceptance Criteria:**
- [ ] Create `simple_script.py` - basic arithmetic script
- [ ] Create `loop_script.py` - script with loops for conditional breakpoint testing
- [ ] Create `exception_script.py` - script that raises exceptions
- [ ] Create `threading_script.py` - multi-threaded script
- [ ] Create `large_output_script.py` - script generating large output
- [ ] Create `circular_reference_script.py` - script with circular references
- [ ] Create `large_variable_script.py` - script with large data structures
- [ ] Create `syntax_error_script.py` - script with intentional syntax error

**Files to Create/Modify:**
- tests/fixtures/scripts/simple_script.py
- tests/fixtures/scripts/loop_script.py
- tests/fixtures/scripts/exception_script.py
- tests/fixtures/scripts/threading_script.py
- tests/fixtures/scripts/large_output_script.py
- tests/fixtures/scripts/circular_reference_script.py
- tests/fixtures/scripts/large_variable_script.py
- tests/fixtures/scripts/syntax_error_script.py

**Reference:**
- TEST_PLAN.md Section 8.1 (Sample Python Scripts)

---

### TASK-007: Create Multi-File Test Project

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 1h
**Dependencies:** TASK-001
**Assignee:** Unassigned

**Description:**
Create the multi-file test project structure for cross-file debugging tests.

**Acceptance Criteria:**
- [ ] Create `multi_file/main.py` - entry point
- [ ] Create `multi_file/utils/__init__.py` and `helpers.py`
- [ ] Create `multi_file/models/__init__.py` and `data.py`
- [ ] Ensure imports work correctly

**Files to Create/Modify:**
- tests/fixtures/scripts/multi_file/main.py
- tests/fixtures/scripts/multi_file/utils/__init__.py
- tests/fixtures/scripts/multi_file/utils/helpers.py
- tests/fixtures/scripts/multi_file/models/__init__.py
- tests/fixtures/scripts/multi_file/models/data.py

**Reference:**
- TEST_PLAN.md Section 8.1 (multi_file scripts)

---

### TASK-008: Create Mock DAP Response Fixtures

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 1h
**Dependencies:** TASK-001
**Assignee:** Unassigned

**Description:**
Create JSON fixtures for mocking DAP protocol responses in tests.

**Acceptance Criteria:**
- [ ] Create `initialize_response.json`
- [ ] Create `stopped_breakpoint_event.json`
- [ ] Create `stack_trace_response.json`
- [ ] Create `variables_response.json`
- [ ] Create additional DAP response fixtures as needed

**Files to Create/Modify:**
- tests/fixtures/dap/initialize_response.json
- tests/fixtures/dap/stopped_breakpoint_event.json
- tests/fixtures/dap/stack_trace_response.json
- tests/fixtures/dap/variables_response.json

**Reference:**
- TEST_PLAN.md Section 8.2 (Mock DAP Responses)

---

### TASK-009: Create GitHub Actions CI Workflow

**Status:** TODO
**Priority:** P2 (Medium)
**Estimate:** 2h
**Dependencies:** TASK-002, TASK-005
**Assignee:** Unassigned

**Description:**
Set up GitHub Actions workflow for continuous integration testing.

**Acceptance Criteria:**
- [ ] Create `test.yml` workflow with lint, unit, integration, e2e, and performance jobs
- [ ] Configure matrix testing for Python 3.10, 3.11, 3.12
- [ ] Configure coverage reporting with Codecov
- [ ] Set up artifact uploading for coverage reports

**Files to Create/Modify:**
- .github/workflows/test.yml

**Reference:**
- TEST_PLAN.md Section 9.3 (GitHub Actions Workflow)

---

### TASK-010: Create .gitignore File

**Status:** TODO
**Priority:** P3 (Low)
**Estimate:** 0.5h
**Dependencies:** None
**Assignee:** Unassigned

**Description:**
Create a comprehensive .gitignore file for the Python project.

**Acceptance Criteria:**
- [ ] Ignore Python cache files (__pycache__, *.pyc)
- [ ] Ignore virtual environments (.venv, venv)
- [ ] Ignore IDE files (.idea, .vscode)
- [ ] Ignore coverage and test artifacts
- [ ] Ignore .env files (but not .env.example)
- [ ] Ignore build artifacts (dist, *.egg-info)

**Files to Create/Modify:**
- .gitignore

**Reference:**
- Standard Python .gitignore patterns

---

## 2. Core Models (TASK-011 to TASK-020)

### TASK-011: Implement DAP Protocol Models (models/dap.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 3h
**Dependencies:** TASK-002
**Assignee:** Unassigned

**Description:**
Implement all Pydantic models for DAP (Debug Adapter Protocol) messages and data structures.

**Acceptance Criteria:**
- [ ] Implement `DAPMessage` base model
- [ ] Implement `DAPRequest` model with seq, command, arguments
- [ ] Implement `DAPResponse` model with request_seq, success, body
- [ ] Implement `DAPEvent` model with event, body
- [ ] Implement `LaunchConfig` model with all launch parameters
- [ ] Implement `AttachConfig` model with process_id, host, port
- [ ] Implement `SourceBreakpoint` model with line, condition, hit_condition, log_message
- [ ] Implement `Breakpoint` model (verified breakpoint from debugpy)
- [ ] Implement `StackFrame` model
- [ ] Implement `Scope` model with variables_reference
- [ ] Implement `Variable` model with type, value, variables_reference
- [ ] Implement `Thread` model

**Files to Create/Modify:**
- src/opencode_debugger/models/dap.py

**Reference:**
- LLD_BACKEND.md Section 3.1 (models/dap.py)

---

### TASK-012: Implement Session Models (models/session.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 1h
**Dependencies:** TASK-002
**Assignee:** Unassigned

**Description:**
Implement Pydantic models for session configuration and information.

**Acceptance Criteria:**
- [ ] Implement `SessionConfig` model with project_root, name, timeout_minutes
- [ ] Implement `SessionInfo` model with id, name, state, timestamps, location, etc.
- [ ] Add field validators as needed
- [ ] Import datetime from correct module

**Files to Create/Modify:**
- src/opencode_debugger/models/session.py

**Reference:**
- LLD_BACKEND.md Section 3.1 (models/dap.py - contains SessionConfig/SessionInfo)

---

### TASK-013: Implement Event Models (models/events.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 1h
**Dependencies:** TASK-002
**Assignee:** Unassigned

**Description:**
Implement Pydantic models for debug events.

**Acceptance Criteria:**
- [ ] Implement `EventType` enum with STOPPED, CONTINUED, TERMINATED, OUTPUT, BREAKPOINT, THREAD, MODULE
- [ ] Implement `DebugEvent` model with type, timestamp, data

**Files to Create/Modify:**
- src/opencode_debugger/models/events.py

**Reference:**
- LLD_BACKEND.md Section 3.2 (models/events.py)

---

### TASK-014: Implement API Request Models (models/requests.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 2h
**Dependencies:** TASK-011, TASK-012
**Assignee:** Unassigned

**Description:**
Implement Pydantic models for all API request bodies.

**Acceptance Criteria:**
- [ ] Implement `CreateSessionRequest` model
- [ ] Implement `LaunchRequest` model with script/module, args, cwd, env, stop_on_entry, stop_on_exception
- [ ] Implement `AttachRequest` model with pid, host, port
- [ ] Implement `SetBreakpointsRequest` model with breakpoints array
- [ ] Implement `EvaluateRequest` model with expression, frame_id, context
- [ ] Implement `ContinueRequest`, `PauseRequest`, step requests
- [ ] Add validation for mutually exclusive fields (script vs module)

**Files to Create/Modify:**
- src/opencode_debugger/models/requests.py

**Reference:**
- LLD_API.md Section 4.1 (Request Schemas)

---

### TASK-015: Implement API Response Models (models/responses.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 2h
**Dependencies:** TASK-011, TASK-012, TASK-013
**Assignee:** Unassigned

**Description:**
Implement Pydantic models for all API response bodies including the response envelope.

**Acceptance Criteria:**
- [ ] Implement `ResponseMeta` model with request_id, timestamp
- [ ] Implement `ApiError` model with code, message, details
- [ ] Implement `ApiResponse` generic envelope model
- [ ] Implement `SessionResponse`, `SessionListResponse` models
- [ ] Implement `BreakpointResponse` model
- [ ] Implement `StackTraceResponse`, `ScopesResponse`, `VariablesResponse` models
- [ ] Implement `EvaluateResponse` model
- [ ] Implement `OutputResponse`, `EventsResponse` models
- [ ] Implement `HealthResponse`, `InfoResponse` models

**Files to Create/Modify:**
- src/opencode_debugger/models/responses.py

**Reference:**
- LLD_API.md Section 4.2 (Response Schemas)
- LLD_API.md Section 2.1 (Response Envelope)

---

### TASK-016: Implement Exception Hierarchy (core/exceptions.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 2h
**Dependencies:** TASK-002
**Assignee:** Unassigned

**Description:**
Implement the complete custom exception hierarchy for the debug relay server.

**Acceptance Criteria:**
- [ ] Implement `DebugRelayError` base exception with code, message, details
- [ ] Implement `SessionError` and subclasses: SessionNotFoundError, SessionLimitError, InvalidSessionStateError, SessionExpiredError
- [ ] Implement `DAPError` and subclasses: DAPTimeoutError, DAPConnectionError, LaunchError
- [ ] Implement `PersistenceError`
- [ ] Implement `BreakpointError` and BreakpointNotFoundError
- [ ] Implement `ThreadNotFoundError`, `FrameNotFoundError`, `VariableNotFoundError`
- [ ] Ensure error codes match LLD_API.md Section 5

**Files to Create/Modify:**
- src/opencode_debugger/core/exceptions.py

**Reference:**
- LLD_BACKEND.md Section 2.2 (core/exceptions.py)
- LLD_API.md Section 5 (Error Codes)

---

### TASK-017: Create Models Package Exports

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 0.5h
**Dependencies:** TASK-011, TASK-012, TASK-013, TASK-014, TASK-015
**Assignee:** Unassigned

**Description:**
Update models/__init__.py to export all model classes for convenient importing.

**Acceptance Criteria:**
- [ ] Export all models from dap.py
- [ ] Export all models from session.py
- [ ] Export all models from events.py
- [ ] Export all models from requests.py
- [ ] Export all models from responses.py

**Files to Create/Modify:**
- src/opencode_debugger/models/__init__.py

**Reference:**
- LLD_BACKEND.md Section 1 (Project Structure)

---

### TASK-018: Unit Tests for DAP Models

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 2h
**Dependencies:** TASK-011, TASK-005
**Assignee:** Unassigned

**Description:**
Write unit tests for DAP protocol models.

**Acceptance Criteria:**
- [ ] Test model creation with valid data
- [ ] Test model validation for required fields
- [ ] Test field aliases (variablesReference -> variables_reference)
- [ ] Test model serialization/deserialization
- [ ] Test LaunchConfig with script and module variants

**Files to Create/Modify:**
- tests/unit/test_models_dap.py

**Reference:**
- TEST_PLAN.md Section 2 (Unit Test Specifications)

---

### TASK-019: Unit Tests for Request/Response Models

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 2h
**Dependencies:** TASK-014, TASK-015, TASK-005
**Assignee:** Unassigned

**Description:**
Write unit tests for API request and response models.

**Acceptance Criteria:**
- [ ] Test request model validation
- [ ] Test response envelope format
- [ ] Test error response structure
- [ ] Test pagination fields
- [ ] Test optional vs required fields

**Files to Create/Modify:**
- tests/unit/test_models_requests.py
- tests/unit/test_models_responses.py

**Reference:**
- TEST_PLAN.md Section 2 (Unit Test Specifications)

---

### TASK-020: Unit Tests for Exceptions

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 1h
**Dependencies:** TASK-016, TASK-005
**Assignee:** Unassigned

**Description:**
Write unit tests for the exception hierarchy.

**Acceptance Criteria:**
- [ ] Test exception creation with code, message, details
- [ ] Test inheritance hierarchy
- [ ] Test exception string representation
- [ ] Verify error codes match specification

**Files to Create/Modify:**
- tests/unit/test_exceptions.py

**Reference:**
- TEST_PLAN.md Section 7 (Error Handling Tests)

---

## 3. Infrastructure (TASK-021 to TASK-040)

### TASK-021: Implement Configuration Management (config.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 1h
**Dependencies:** TASK-002
**Assignee:** Unassigned

**Description:**
Implement the Settings class using pydantic-settings for configuration management.

**Acceptance Criteria:**
- [ ] Implement `Settings` class extending BaseSettings
- [ ] Configure env_prefix="OPENCODE_DEBUG_"
- [ ] Add server settings (host, port, debug)
- [ ] Add session limits (max_sessions, timeout, max_lifetime)
- [ ] Add output buffer settings (max_bytes = 50MB)
- [ ] Add persistence settings (data_dir)
- [ ] Add DAP settings (timeout, launch_timeout)
- [ ] Add default_python_path setting
- [ ] Implement breakpoints_dir and sessions_dir properties
- [ ] Create singleton `settings` instance

**Files to Create/Modify:**
- src/opencode_debugger/config.py

**Reference:**
- LLD_BACKEND.md Section 2.1 (config.py)

---

### TASK-022: Unit Tests for Configuration

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 1h
**Dependencies:** TASK-021, TASK-005
**Assignee:** Unassigned

**Description:**
Write unit tests for configuration management.

**Acceptance Criteria:**
- [ ] Test default values
- [ ] Test environment variable override
- [ ] Test computed properties (breakpoints_dir, sessions_dir)
- [ ] Test validation constraints

**Files to Create/Modify:**
- tests/unit/test_config.py

**Reference:**
- TEST_PLAN.md Section 2 (Unit Test Specifications)

---

### TASK-023: Implement Output Buffer (utils/output_buffer.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 2h
**Dependencies:** TASK-002
**Assignee:** Unassigned

**Description:**
Implement the ring buffer for capturing program output with size limits.

**Acceptance Criteria:**
- [ ] Implement `OutputLine` dataclass with line_number, category, content, timestamp
- [ ] Implement `OutputPage` dataclass with lines, offset, limit, total, has_more, truncated
- [ ] Implement `OutputBuffer` class with max_size parameter (default 50MB)
- [ ] Implement `append(category, content)` method
- [ ] Implement `get_page(offset, limit, category)` method
- [ ] Implement `clear()` method
- [ ] Implement size, total_lines, dropped_lines properties
- [ ] Ensure oldest entries are dropped when max size exceeded
- [ ] Track dropped count for truncated flag

**Files to Create/Modify:**
- src/opencode_debugger/utils/output_buffer.py

**Reference:**
- LLD_BACKEND.md Section 2.9 (utils/output_buffer.py)

---

### TASK-024: Unit Tests for Output Buffer

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 2h
**Dependencies:** TASK-023, TASK-005
**Assignee:** Unassigned

**Description:**
Write comprehensive unit tests for the output buffer.

**Acceptance Criteria:**
- [ ] Test OB-001 through OB-016 from TEST_PLAN.md
- [ ] Test append for stdout/stderr
- [ ] Test line numbering and timestamps
- [ ] Test pagination with offset/limit
- [ ] Test category filtering
- [ ] Test 50MB size limit enforcement
- [ ] Test truncated flag and dropped count
- [ ] Test clear() functionality
- [ ] Test Unicode content handling

**Files to Create/Modify:**
- tests/unit/test_output_buffer.py

**Reference:**
- TEST_PLAN.md Section 2.7 (utils/output_buffer.py)

---

### TASK-025: Implement Atomic Storage Operations (persistence/storage.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 3h
**Dependencies:** TASK-002
**Assignee:** Unassigned

**Description:**
Implement atomic file operations for JSON persistence using aiofiles.

**Acceptance Criteria:**
- [ ] Implement `project_id_from_path(project_root)` - SHA256 hash of normalized path
- [ ] Implement `atomic_write(path, data)` - write using temp file + rename
- [ ] Implement `safe_read(path)` - read JSON, return None if not found
- [ ] Implement `safe_delete(path)` - delete if exists
- [ ] Implement `list_json_files(directory)` - list .json files
- [ ] Ensure atomic_write creates parent directories
- [ ] Ensure proper error handling with PersistenceError

**Files to Create/Modify:**
- src/opencode_debugger/persistence/storage.py

**Reference:**
- LLD_BACKEND.md Section 2.7 (persistence/storage.py)

---

### TASK-026: Unit Tests for Storage Operations

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 2h
**Dependencies:** TASK-025, TASK-005
**Assignee:** Unassigned

**Description:**
Write unit tests for atomic storage operations.

**Acceptance Criteria:**
- [ ] Test ST-001 through ST-016 from TEST_PLAN.md
- [ ] Test project_id consistency and uniqueness
- [ ] Test atomic_write creates file and directories
- [ ] Test atomic_write is atomic (no partial writes)
- [ ] Test safe_read for existing and non-existent files
- [ ] Test safe_read for invalid JSON
- [ ] Test safe_delete behavior
- [ ] Test list_json_files filtering

**Files to Create/Modify:**
- tests/unit/test_storage.py

**Reference:**
- TEST_PLAN.md Section 2.5 (persistence/storage.py)

---

### TASK-027: Implement Breakpoint Storage (persistence/breakpoints.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 2h
**Dependencies:** TASK-025, TASK-011
**Assignee:** Unassigned

**Description:**
Implement per-project breakpoint persistence using the storage layer.

**Acceptance Criteria:**
- [ ] Implement `BreakpointStore` class
- [ ] Implement `_get_path(project_root)` method
- [ ] Implement `load(project_root)` - returns dict[file_path, list[SourceBreakpoint]]
- [ ] Implement `save(project_root, breakpoints)` method
- [ ] Implement `update_file(project_root, file_path, breakpoints)` method
- [ ] Implement `clear(project_root)` method
- [ ] Ensure proper model serialization/deserialization

**Files to Create/Modify:**
- src/opencode_debugger/persistence/breakpoints.py

**Reference:**
- LLD_BACKEND.md Section 2.8 (persistence/breakpoints.py)

---

### TASK-028: Unit Tests for Breakpoint Storage

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 2h
**Dependencies:** TASK-027, TASK-005
**Assignee:** Unassigned

**Description:**
Write unit tests for breakpoint storage.

**Acceptance Criteria:**
- [ ] Test BP-001 through BP-012 from TEST_PLAN.md
- [ ] Test load from empty/new project
- [ ] Test save and load roundtrip
- [ ] Test multiple files in one save
- [ ] Test update_file add/replace/remove
- [ ] Test clear functionality
- [ ] Test project isolation
- [ ] Test conditional, hit count, and logpoint breakpoints

**Files to Create/Modify:**
- tests/unit/test_breakpoints.py

**Reference:**
- TEST_PLAN.md Section 2.6 (persistence/breakpoints.py)

---

### TASK-029: Create Persistence Package Exports

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 0.5h
**Dependencies:** TASK-025, TASK-027
**Assignee:** Unassigned

**Description:**
Update persistence/__init__.py to export storage functions and BreakpointStore.

**Acceptance Criteria:**
- [ ] Export atomic_write, safe_read, safe_delete, list_json_files, project_id_from_path
- [ ] Export BreakpointStore class

**Files to Create/Modify:**
- src/opencode_debugger/persistence/__init__.py

**Reference:**
- LLD_BACKEND.md Section 1 (Project Structure)

---

### TASK-030: Implement DAP Protocol Client (adapters/dap_client.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 6h
**Dependencies:** TASK-011, TASK-016
**Assignee:** Unassigned

**Description:**
Implement the DAP protocol client for communicating with debugpy over stdin/stdout.

**Acceptance Criteria:**
- [ ] Implement `DAPClient` class with reader, writer, event_callback, timeout
- [ ] Implement sequence number management with lock
- [ ] Implement pending requests tracking with futures
- [ ] Implement `start()` method to begin reader loop
- [ ] Implement `stop()` method to cleanup and cancel pending
- [ ] Implement `send_request(command, arguments, timeout)` method
- [ ] Implement `_send_message(message)` with Content-Length header
- [ ] Implement `_read_loop()` for continuous message reading
- [ ] Implement `_read_message()` to parse DAP format
- [ ] Implement `_handle_message(message)` to dispatch responses/events
- [ ] Handle DAPError and DAPTimeoutError appropriately

**Files to Create/Modify:**
- src/opencode_debugger/adapters/dap_client.py

**Reference:**
- LLD_BACKEND.md Section 2.5 (adapters/dap_client.py)

---

### TASK-031: Unit Tests for DAP Client

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 4h
**Dependencies:** TASK-030, TASK-005, TASK-008
**Assignee:** Unassigned

**Description:**
Write unit tests for the DAP protocol client with mocked streams.

**Acceptance Criteria:**
- [ ] Test DC-001 through DC-011 from TEST_PLAN.md
- [ ] Test send_request with successful response
- [ ] Test sequence number incrementing
- [ ] Test request timeout
- [ ] Test request failure (success=false)
- [ ] Test message format with Content-Length
- [ ] Test event dispatch to callback
- [ ] Test response matching to pending request
- [ ] Test concurrent requests
- [ ] Test stop cancels pending

**Files to Create/Modify:**
- tests/unit/test_dap_client.py

**Reference:**
- TEST_PLAN.md Section 2.3 (adapters/dap_client.py)

---

### TASK-032: Implement debugpy Adapter (adapters/debugpy_adapter.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 6h
**Dependencies:** TASK-030, TASK-011, TASK-013, TASK-021
**Assignee:** Unassigned

**Description:**
Implement the debugpy adapter that manages debugpy subprocess and DAP communication.

**Acceptance Criteria:**
- [ ] Implement `DebugpyAdapter` class with session_id, output_callback, event_callback
- [ ] Implement `initialize()` - spawn debugpy.adapter, create DAPClient, send init request
- [ ] Implement `launch(config: LaunchConfig)` - send launch request
- [ ] Implement `attach(config: AttachConfig)` - send attach request
- [ ] Implement `disconnect()` - send disconnect, stop client, terminate process
- [ ] Implement `set_breakpoints(source_path, breakpoints)` - send setBreakpoints
- [ ] Implement `set_exception_breakpoints(filters)` method
- [ ] Implement `continue_(thread_id)`, `pause(thread_id)` methods
- [ ] Implement `step_over(thread_id)`, `step_into(thread_id)`, `step_out(thread_id)` methods
- [ ] Implement `threads()`, `stack_trace(thread_id)`, `scopes(frame_id)`, `variables(ref)` methods
- [ ] Implement `evaluate(expression, frame_id, context)` method
- [ ] Implement `_handle_event(event_type, body)` for event mapping
- [ ] Implement `_require_initialized()` check

**Files to Create/Modify:**
- src/opencode_debugger/adapters/debugpy_adapter.py

**Reference:**
- LLD_BACKEND.md Section 2.6 (adapters/debugpy_adapter.py)

---

### TASK-033: Unit Tests for debugpy Adapter

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 4h
**Dependencies:** TASK-032, TASK-005
**Assignee:** Unassigned

**Description:**
Write unit tests for the debugpy adapter with mocked DAPClient.

**Acceptance Criteria:**
- [ ] Test DA-001 through DA-020 from TEST_PLAN.md
- [ ] Test initialize starts process and sends init request
- [ ] Test launch with various configurations
- [ ] Test attach by PID and by host/port
- [ ] Test disconnect and cleanup
- [ ] Test all breakpoint operations
- [ ] Test all execution control methods
- [ ] Test all inspection methods
- [ ] Test event mapping
- [ ] Test not initialized error

**Files to Create/Modify:**
- tests/unit/test_debugpy_adapter.py

**Reference:**
- TEST_PLAN.md Section 2.4 (adapters/debugpy_adapter.py)

---

### TASK-034: Create Adapters Package Exports

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 0.5h
**Dependencies:** TASK-030, TASK-032
**Assignee:** Unassigned

**Description:**
Update adapters/__init__.py to export DAPClient and DebugpyAdapter.

**Acceptance Criteria:**
- [ ] Export DAPClient class
- [ ] Export DebugpyAdapter class

**Files to Create/Modify:**
- src/opencode_debugger/adapters/__init__.py

**Reference:**
- LLD_BACKEND.md Section 1 (Project Structure)

---

### TASK-035: Implement Event Queue (core/events.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 2h
**Dependencies:** TASK-013
**Assignee:** Unassigned

**Description:**
Implement the thread-safe event queue for debug events.

**Acceptance Criteria:**
- [ ] Implement `EventQueue` class with max_size parameter
- [ ] Implement `put(event_type, data)` - create event and add to queue
- [ ] Implement `get(timeout)` - get next event with optional wait
- [ ] Implement `get_all()` - drain all pending events
- [ ] Implement `clear()` - clear queue and history
- [ ] Maintain event history (max 100 entries)
- [ ] Handle queue full by dropping oldest

**Files to Create/Modify:**
- src/opencode_debugger/core/events.py

**Reference:**
- LLD_BACKEND.md Section 2.4 (core/events.py)

---

### TASK-036: Unit Tests for Event Queue

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 2h
**Dependencies:** TASK-035, TASK-005
**Assignee:** Unassigned

**Description:**
Write unit tests for the event queue.

**Acceptance Criteria:**
- [ ] Test EQ-001 through EQ-012 from TEST_PLAN.md
- [ ] Test put adds event with timestamp
- [ ] Test get with and without timeout
- [ ] Test get_all drains queue
- [ ] Test max_size enforcement
- [ ] Test history maintenance
- [ ] Test clear functionality
- [ ] Test concurrent put/get safety

**Files to Create/Modify:**
- tests/unit/test_events.py

**Reference:**
- TEST_PLAN.md Section 2.2 (core/events.py)

---

### TASK-037: Create Utils Package Exports

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 0.5h
**Dependencies:** TASK-023
**Assignee:** Unassigned

**Description:**
Update utils/__init__.py to export OutputBuffer and related classes.

**Acceptance Criteria:**
- [ ] Export OutputBuffer, OutputLine, OutputPage classes

**Files to Create/Modify:**
- src/opencode_debugger/utils/__init__.py

**Reference:**
- LLD_BACKEND.md Section 1 (Project Structure)

---

### TASK-038: DAP Integration Tests

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 4h
**Dependencies:** TASK-032, TASK-006
**Assignee:** Unassigned

**Description:**
Write integration tests for DAP protocol communication with real debugpy.

**Acceptance Criteria:**
- [ ] Test DAP-001 through DAP-010 from TEST_PLAN.md
- [ ] Test initialize handshake
- [ ] Test launch and terminate
- [ ] Test breakpoint hit
- [ ] Test step sequence
- [ ] Test variable inspection
- [ ] Test expression evaluation
- [ ] Test conditional breakpoint
- [ ] Test exception handling
- [ ] Test output capture

**Files to Create/Modify:**
- tests/integration/test_dap_integration.py

**Reference:**
- TEST_PLAN.md Section 3.2 (DAP Protocol Integration Tests)

---

### TASK-039: Persistence Integration Tests

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 2h
**Dependencies:** TASK-027, TASK-005
**Assignee:** Unassigned

**Description:**
Write integration tests for persistence layer.

**Acceptance Criteria:**
- [ ] Test PERS-001 through PERS-005 from TEST_PLAN.md
- [ ] Test breakpoints persist across restart
- [ ] Test per-project isolation
- [ ] Test graceful handling of corrupted files
- [ ] Test concurrent persistence operations
- [ ] Test directory creation

**Files to Create/Modify:**
- tests/integration/test_persistence_integration.py

**Reference:**
- TEST_PLAN.md Section 3.3 (Persistence Integration Tests)

---

### TASK-040: Create Core Package Exports

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 0.5h
**Dependencies:** TASK-035, TASK-016
**Assignee:** Unassigned

**Description:**
Update core/__init__.py to export exceptions and EventQueue.

**Acceptance Criteria:**
- [ ] Export all exception classes
- [ ] Export EventQueue class

**Files to Create/Modify:**
- src/opencode_debugger/core/__init__.py

**Reference:**
- LLD_BACKEND.md Section 1 (Project Structure)

---

## 4. Session Management (TASK-041 to TASK-050)

### TASK-041: Implement SessionState Enum and Session Class

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 4h
**Dependencies:** TASK-032, TASK-023, TASK-035, TASK-012
**Assignee:** Unassigned

**Description:**
Implement the Session class that represents a single debug session.

**Acceptance Criteria:**
- [ ] Implement `SessionState` enum with CREATED, LAUNCHING, RUNNING, PAUSED, TERMINATED, FAILED
- [ ] Implement `Session` class with id, project_root, name, state, timestamps
- [ ] Implement state transition validation with _state_lock
- [ ] Implement `transition_to(new_state)` with valid transition checking
- [ ] Implement `require_state(*states)` method
- [ ] Implement `initialize_adapter()` method
- [ ] Implement `cleanup()` method
- [ ] Implement `to_info()` conversion method
- [ ] Initialize OutputBuffer and EventQueue in constructor

**Files to Create/Modify:**
- src/opencode_debugger/core/session.py

**Reference:**
- LLD_BACKEND.md Section 2.3 (core/session.py)

---

### TASK-042: Implement SessionManager Class

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 4h
**Dependencies:** TASK-041, TASK-027, TASK-021
**Assignee:** Unassigned

**Description:**
Implement the SessionManager that manages all debug sessions.

**Acceptance Criteria:**
- [ ] Implement `SessionManager` class with breakpoint_store
- [ ] Implement `start()` method to initialize and start cleanup task
- [ ] Implement `stop()` method to cleanup all sessions
- [ ] Implement `create_session(config)` with limit checking
- [ ] Implement `get_session(session_id)` with activity update
- [ ] Implement `list_sessions()` method
- [ ] Implement `terminate_session(session_id)` method
- [ ] Implement `_cleanup_loop()` background task
- [ ] Implement `_cleanup_stale_sessions()` with timeout logic
- [ ] Implement `_recover_sessions()` stub for future implementation

**Files to Create/Modify:**
- src/opencode_debugger/core/session.py (add SessionManager)

**Reference:**
- LLD_BACKEND.md Section 2.3 (core/session.py)

---

### TASK-043: Unit Tests for Session Class

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 3h
**Dependencies:** TASK-041, TASK-005
**Assignee:** Unassigned

**Description:**
Write unit tests for the Session class.

**Acceptance Criteria:**
- [ ] Test SS-001 through SS-005 (SessionState tests)
- [ ] Test S-001 through S-013 (Session class tests)
- [ ] Test state transitions valid and invalid
- [ ] Test timestamps (created_at, last_activity)
- [ ] Test require_state passes and fails
- [ ] Test to_info conversion
- [ ] Test cleanup releases resources

**Files to Create/Modify:**
- tests/unit/test_session.py

**Reference:**
- TEST_PLAN.md Section 2.1 (core/session.py)

---

### TASK-044: Unit Tests for SessionManager

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 3h
**Dependencies:** TASK-042, TASK-005
**Assignee:** Unassigned

**Description:**
Write unit tests for the SessionManager class.

**Acceptance Criteria:**
- [ ] Test SM-001 through SM-014 from TEST_PLAN.md
- [ ] Test create_session success and limit
- [ ] Test get_session found, not found, and activity update
- [ ] Test list_sessions empty and multiple
- [ ] Test terminate_session success and not found
- [ ] Test stale session cleanup
- [ ] Test concurrent create operations
- [ ] Test start/stop lifecycle

**Files to Create/Modify:**
- tests/unit/test_session_manager.py

**Reference:**
- TEST_PLAN.md Section 2.1 (SessionManager Tests)

---

### TASK-045: Session Lifecycle Integration Tests

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 3h
**Dependencies:** TASK-042, TASK-006
**Assignee:** Unassigned

**Description:**
Write integration tests for complete session lifecycle.

**Acceptance Criteria:**
- [ ] Test SL-001 through SL-006 from TEST_PLAN.md
- [ ] Test complete session lifecycle (create->launch->debug->terminate->delete)
- [ ] Test session timeout cleanup
- [ ] Test session max lifetime
- [ ] Test activity resets timeout
- [ ] Test multiple concurrent sessions
- [ ] Test session recovery (stub for now)

**Files to Create/Modify:**
- tests/integration/test_session_lifecycle.py

**Reference:**
- TEST_PLAN.md Section 3.4 (Session Lifecycle Integration Tests)

---

### TASK-046: Update Core Package Exports for Session

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 0.5h
**Dependencies:** TASK-041, TASK-042
**Assignee:** Unassigned

**Description:**
Update core/__init__.py to export Session, SessionState, and SessionManager.

**Acceptance Criteria:**
- [ ] Export Session class
- [ ] Export SessionState enum
- [ ] Export SessionManager class

**Files to Create/Modify:**
- src/opencode_debugger/core/__init__.py

**Reference:**
- LLD_BACKEND.md Section 1 (Project Structure)

---

### TASK-047: Implement Exception Handler Middleware

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 2h
**Dependencies:** TASK-016, TASK-015
**Assignee:** Unassigned

**Description:**
Implement FastAPI exception handlers to convert exceptions to proper API responses.

**Acceptance Criteria:**
- [ ] Create exception handler for DebugRelayError
- [ ] Create exception handler for SessionNotFoundError (404)
- [ ] Create exception handler for SessionLimitError (429)
- [ ] Create exception handler for InvalidSessionStateError (409)
- [ ] Create exception handler for DAPTimeoutError (504)
- [ ] Create handler for generic exceptions (500)
- [ ] Ensure all responses follow envelope format

**Files to Create/Modify:**
- src/opencode_debugger/api/middleware.py

**Reference:**
- LLD_API.md Section 5 (Error Codes)

---

### TASK-048: Implement Request ID Middleware

**Status:** TODO
**Priority:** P2 (Medium)
**Estimate:** 1h
**Dependencies:** TASK-015
**Assignee:** Unassigned

**Description:**
Implement middleware to handle X-Request-ID header tracking.

**Acceptance Criteria:**
- [ ] Extract X-Request-ID from request headers
- [ ] Generate UUID if not provided
- [ ] Include request_id in response meta
- [ ] Add X-Request-ID to response headers

**Files to Create/Modify:**
- src/opencode_debugger/api/middleware.py

**Reference:**
- LLD_API.md Section 2.4 (Common Headers)

---

### TASK-049: Unit Tests for Middleware

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 2h
**Dependencies:** TASK-047, TASK-048, TASK-005
**Assignee:** Unassigned

**Description:**
Write unit tests for exception handler and request ID middleware.

**Acceptance Criteria:**
- [ ] Test exception to HTTP status mapping
- [ ] Test error response format
- [ ] Test request ID generation and echo
- [ ] Test all error code scenarios

**Files to Create/Modify:**
- tests/unit/test_middleware.py

**Reference:**
- TEST_PLAN.md Section 7 (Error Handling Tests)

---

### TASK-050: Create API Package Structure

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 1h
**Dependencies:** TASK-047, TASK-048
**Assignee:** Unassigned

**Description:**
Set up the API package with dependencies and common utilities.

**Acceptance Criteria:**
- [ ] Create api/dependencies.py for FastAPI dependencies
- [ ] Implement get_session_manager dependency
- [ ] Implement get_session dependency with path parameter extraction
- [ ] Create api/__init__.py with exports

**Files to Create/Modify:**
- src/opencode_debugger/api/dependencies.py
- src/opencode_debugger/api/__init__.py

**Reference:**
- LLD_BACKEND.md Section 1 (Project Structure)

---

## 5. API Endpoints (TASK-051 to TASK-080)

### TASK-051: Implement Health Endpoint (api/server.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 1h
**Dependencies:** TASK-050, TASK-015
**Assignee:** Unassigned

**Description:**
Implement GET /health endpoint for health checks.

**Acceptance Criteria:**
- [ ] Create FastAPI router for server endpoints
- [ ] Implement GET /health returning HealthResponse
- [ ] Include status, version, uptime_seconds, active_sessions, debugpy_available
- [ ] Return 200 for healthy, 503 for unhealthy

**Files to Create/Modify:**
- src/opencode_debugger/api/server.py

**Reference:**
- LLD_API.md Section 3.1 (GET /health)

---

### TASK-052: Implement Info Endpoint (api/server.py)

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 1h
**Dependencies:** TASK-051
**Assignee:** Unassigned

**Description:**
Implement GET /info endpoint for server information.

**Acceptance Criteria:**
- [ ] Implement GET /info returning InfoResponse
- [ ] Include name, version, api_version, python_version, debugpy_version
- [ ] Include capabilities object with feature flags
- [ ] Include endpoints list

**Files to Create/Modify:**
- src/opencode_debugger/api/server.py

**Reference:**
- LLD_API.md Section 3.1 (GET /info)

---

### TASK-053: Implement Create Session Endpoint (api/sessions.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 2h
**Dependencies:** TASK-050, TASK-042, TASK-014, TASK-015
**Assignee:** Unassigned

**Description:**
Implement POST /sessions endpoint to create debug sessions.

**Acceptance Criteria:**
- [ ] Create FastAPI router for session endpoints
- [ ] Implement POST /sessions with CreateSessionRequest body
- [ ] Use SessionManager dependency
- [ ] Return 201 with SessionResponse on success
- [ ] Return 429 for session limit reached
- [ ] Return 400 for validation errors

**Files to Create/Modify:**
- src/opencode_debugger/api/sessions.py

**Reference:**
- LLD_API.md Section 3.2 (POST /sessions)

---

### TASK-054: Implement List Sessions Endpoint (api/sessions.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 1h
**Dependencies:** TASK-053
**Assignee:** Unassigned

**Description:**
Implement GET /sessions endpoint to list all sessions.

**Acceptance Criteria:**
- [ ] Implement GET /sessions with pagination (offset, limit)
- [ ] Support status filter query parameter
- [ ] Return SessionListResponse with items, total, has_more

**Files to Create/Modify:**
- src/opencode_debugger/api/sessions.py

**Reference:**
- LLD_API.md Section 3.2 (GET /sessions)

---

### TASK-055: Implement Get Session Endpoint (api/sessions.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 1h
**Dependencies:** TASK-053
**Assignee:** Unassigned

**Description:**
Implement GET /sessions/{session_id} endpoint.

**Acceptance Criteria:**
- [ ] Implement GET /sessions/{session_id}
- [ ] Return full SessionResponse with current_location, stop_reason
- [ ] Return 404 for session not found

**Files to Create/Modify:**
- src/opencode_debugger/api/sessions.py

**Reference:**
- LLD_API.md Section 3.2 (GET /sessions/{session_id})

---

### TASK-056: Implement Delete Session Endpoint (api/sessions.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 1h
**Dependencies:** TASK-053
**Assignee:** Unassigned

**Description:**
Implement DELETE /sessions/{session_id} endpoint.

**Acceptance Criteria:**
- [ ] Implement DELETE /sessions/{session_id}
- [ ] Support force query parameter
- [ ] Terminate debuggee and cleanup resources
- [ ] Return deletion confirmation with final_status, exit_code, runtime_seconds

**Files to Create/Modify:**
- src/opencode_debugger/api/sessions.py

**Reference:**
- LLD_API.md Section 3.2 (DELETE /sessions/{session_id})

---

### TASK-057: Implement Launch Endpoint (api/sessions.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 2h
**Dependencies:** TASK-053, TASK-032
**Assignee:** Unassigned

**Description:**
Implement POST /sessions/{session_id}/launch endpoint.

**Acceptance Criteria:**
- [ ] Implement POST /sessions/{session_id}/launch with LaunchRequest
- [ ] Support script and module launch modes
- [ ] Support args, cwd, env, stop_on_entry, stop_on_exception
- [ ] Validate session is in CREATED state
- [ ] Return 409 for invalid state
- [ ] Return 400 for launch failures

**Files to Create/Modify:**
- src/opencode_debugger/api/sessions.py

**Reference:**
- LLD_API.md Section 3.3 (POST /sessions/{session_id}/launch)

---

### TASK-058: Implement Attach Endpoint (api/sessions.py)

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 2h
**Dependencies:** TASK-053, TASK-032
**Assignee:** Unassigned

**Description:**
Implement POST /sessions/{session_id}/attach endpoint.

**Acceptance Criteria:**
- [ ] Implement POST /sessions/{session_id}/attach with AttachRequest
- [ ] Support attach by PID or by host/port
- [ ] Return 504 for connection timeout
- [ ] Return 502 for connection refused

**Files to Create/Modify:**
- src/opencode_debugger/api/sessions.py

**Reference:**
- LLD_API.md Section 3.3 (POST /sessions/{session_id}/attach)

---

### TASK-059: Implement Set Breakpoints Endpoint (api/breakpoints.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 3h
**Dependencies:** TASK-050, TASK-032, TASK-027
**Assignee:** Unassigned

**Description:**
Implement POST /sessions/{session_id}/breakpoints endpoint.

**Acceptance Criteria:**
- [ ] Create FastAPI router for breakpoint endpoints
- [ ] Implement POST /sessions/{session_id}/breakpoints with SetBreakpointsRequest
- [ ] Support condition, hit_condition, log_message
- [ ] Return verified status per breakpoint
- [ ] Persist breakpoints using BreakpointStore
- [ ] Generate breakpoint IDs (bp_1, bp_2, etc.)

**Files to Create/Modify:**
- src/opencode_debugger/api/breakpoints.py

**Reference:**
- LLD_API.md Section 3.4 (POST /sessions/{session_id}/breakpoints)

---

### TASK-060: Implement List Breakpoints Endpoint (api/breakpoints.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 1h
**Dependencies:** TASK-059
**Assignee:** Unassigned

**Description:**
Implement GET /sessions/{session_id}/breakpoints endpoint.

**Acceptance Criteria:**
- [ ] Implement GET /sessions/{session_id}/breakpoints
- [ ] Support file filter query parameter
- [ ] Support verified filter query parameter
- [ ] Return all breakpoints with hit_count

**Files to Create/Modify:**
- src/opencode_debugger/api/breakpoints.py

**Reference:**
- LLD_API.md Section 3.4 (GET /sessions/{session_id}/breakpoints)

---

### TASK-061: Implement Delete Breakpoint Endpoint (api/breakpoints.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 1h
**Dependencies:** TASK-059
**Assignee:** Unassigned

**Description:**
Implement DELETE /sessions/{session_id}/breakpoints/{breakpoint_id} endpoint.

**Acceptance Criteria:**
- [ ] Implement DELETE /sessions/{session_id}/breakpoints/{breakpoint_id}
- [ ] Return 404 for breakpoint not found
- [ ] Update persistence after deletion

**Files to Create/Modify:**
- src/opencode_debugger/api/breakpoints.py

**Reference:**
- LLD_API.md Section 3.4 (DELETE breakpoint)

---

### TASK-062: Implement Continue Endpoint (api/execution.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 1h
**Dependencies:** TASK-050, TASK-032
**Assignee:** Unassigned

**Description:**
Implement POST /sessions/{session_id}/continue endpoint.

**Acceptance Criteria:**
- [ ] Create FastAPI router for execution endpoints
- [ ] Implement POST /sessions/{session_id}/continue
- [ ] Support optional thread_id parameter
- [ ] Validate session is in PAUSED state
- [ ] Return 409 for invalid state

**Files to Create/Modify:**
- src/opencode_debugger/api/execution.py

**Reference:**
- LLD_API.md Section 3.5 (POST /sessions/{session_id}/continue)

---

### TASK-063: Implement Pause Endpoint (api/execution.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 1h
**Dependencies:** TASK-062
**Assignee:** Unassigned

**Description:**
Implement POST /sessions/{session_id}/pause endpoint.

**Acceptance Criteria:**
- [ ] Implement POST /sessions/{session_id}/pause
- [ ] Support optional thread_id parameter
- [ ] Validate session is in RUNNING state
- [ ] Return current_location after pause

**Files to Create/Modify:**
- src/opencode_debugger/api/execution.py

**Reference:**
- LLD_API.md Section 3.5 (POST /sessions/{session_id}/pause)

---

### TASK-064: Implement Step Over Endpoint (api/execution.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 1h
**Dependencies:** TASK-062
**Assignee:** Unassigned

**Description:**
Implement POST /sessions/{session_id}/step-over endpoint.

**Acceptance Criteria:**
- [ ] Implement POST /sessions/{session_id}/step-over
- [ ] Support optional thread_id and granularity parameters
- [ ] Validate session is in PAUSED state
- [ ] Return new current_location after step

**Files to Create/Modify:**
- src/opencode_debugger/api/execution.py

**Reference:**
- LLD_API.md Section 3.5 (POST /sessions/{session_id}/step-over)

---

### TASK-065: Implement Step Into Endpoint (api/execution.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 1h
**Dependencies:** TASK-062
**Assignee:** Unassigned

**Description:**
Implement POST /sessions/{session_id}/step-into endpoint.

**Acceptance Criteria:**
- [ ] Implement POST /sessions/{session_id}/step-into
- [ ] Support optional thread_id and granularity parameters
- [ ] Return new current_location (may be in different file)

**Files to Create/Modify:**
- src/opencode_debugger/api/execution.py

**Reference:**
- LLD_API.md Section 3.5 (POST /sessions/{session_id}/step-into)

---

### TASK-066: Implement Step Out Endpoint (api/execution.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 1h
**Dependencies:** TASK-062
**Assignee:** Unassigned

**Description:**
Implement POST /sessions/{session_id}/step-out endpoint.

**Acceptance Criteria:**
- [ ] Implement POST /sessions/{session_id}/step-out
- [ ] Support optional thread_id parameter
- [ ] Return new current_location and optional return_value

**Files to Create/Modify:**
- src/opencode_debugger/api/execution.py

**Reference:**
- LLD_API.md Section 3.5 (POST /sessions/{session_id}/step-out)

---

### TASK-067: Implement Get Threads Endpoint (api/inspection.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 1h
**Dependencies:** TASK-050, TASK-032
**Assignee:** Unassigned

**Description:**
Implement GET /sessions/{session_id}/threads endpoint.

**Acceptance Criteria:**
- [ ] Create FastAPI router for inspection endpoints
- [ ] Implement GET /sessions/{session_id}/threads
- [ ] Return thread list with id, name, status, is_current
- [ ] Return stopped_thread_id

**Files to Create/Modify:**
- src/opencode_debugger/api/inspection.py

**Reference:**
- LLD_API.md Section 3.6 (GET /sessions/{session_id}/threads)

---

### TASK-068: Implement Get Stack Trace Endpoint (api/inspection.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 2h
**Dependencies:** TASK-067
**Assignee:** Unassigned

**Description:**
Implement GET /sessions/{session_id}/stacktrace endpoint.

**Acceptance Criteria:**
- [ ] Implement GET /sessions/{session_id}/stacktrace
- [ ] Support thread_id, start_frame, levels query parameters
- [ ] Return frames with id, name, source, line, column
- [ ] Validate session is paused

**Files to Create/Modify:**
- src/opencode_debugger/api/inspection.py

**Reference:**
- LLD_API.md Section 3.6 (GET /sessions/{session_id}/stacktrace)

---

### TASK-069: Implement Get Scopes Endpoint (api/inspection.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 1h
**Dependencies:** TASK-067
**Assignee:** Unassigned

**Description:**
Implement GET /sessions/{session_id}/scopes endpoint.

**Acceptance Criteria:**
- [ ] Implement GET /sessions/{session_id}/scopes
- [ ] Support frame_id query parameter (default: 0)
- [ ] Return scopes with name, variables_reference, presentation_hint

**Files to Create/Modify:**
- src/opencode_debugger/api/inspection.py

**Reference:**
- LLD_API.md Section 3.6 (GET /sessions/{session_id}/scopes)

---

### TASK-070: Implement Get Variables Endpoint (api/inspection.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 2h
**Dependencies:** TASK-067
**Assignee:** Unassigned

**Description:**
Implement GET /sessions/{session_id}/variables endpoint.

**Acceptance Criteria:**
- [ ] Implement GET /sessions/{session_id}/variables
- [ ] Require variables_reference query parameter
- [ ] Support start, count, filter query parameters
- [ ] Return variables with name, value, type, variables_reference

**Files to Create/Modify:**
- src/opencode_debugger/api/inspection.py

**Reference:**
- LLD_API.md Section 3.6 (GET /sessions/{session_id}/variables)

---

### TASK-071: Implement Evaluate Endpoint (api/inspection.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 2h
**Dependencies:** TASK-067
**Assignee:** Unassigned

**Description:**
Implement POST /sessions/{session_id}/evaluate endpoint.

**Acceptance Criteria:**
- [ ] Implement POST /sessions/{session_id}/evaluate with EvaluateRequest
- [ ] Support expression, frame_id, context parameters
- [ ] Return result, type, variables_reference for complex results
- [ ] Return error field for evaluation errors (not HTTP error)

**Files to Create/Modify:**
- src/opencode_debugger/api/inspection.py

**Reference:**
- LLD_API.md Section 3.6 (POST /sessions/{session_id}/evaluate)

---

### TASK-072: Implement Get Output Endpoint (api/output.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 2h
**Dependencies:** TASK-050, TASK-023
**Assignee:** Unassigned

**Description:**
Implement GET /sessions/{session_id}/output endpoint.

**Acceptance Criteria:**
- [ ] Create FastAPI router for output endpoints
- [ ] Implement GET /sessions/{session_id}/output
- [ ] Support cursor, limit, category query parameters
- [ ] Return entries with category, output, timestamp
- [ ] Return next_cursor and has_more for pagination

**Files to Create/Modify:**
- src/opencode_debugger/api/output.py

**Reference:**
- LLD_API.md Section 3.7 (GET /sessions/{session_id}/output)

---

### TASK-073: Implement Get Events Endpoint (api/output.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 2h
**Dependencies:** TASK-072, TASK-035
**Assignee:** Unassigned

**Description:**
Implement GET /sessions/{session_id}/events endpoint.

**Acceptance Criteria:**
- [ ] Implement GET /sessions/{session_id}/events
- [ ] Support cursor, limit, timeout query parameters
- [ ] Implement long-polling when timeout > 0
- [ ] Return events with seq, type, timestamp, body
- [ ] Return session_status in response

**Files to Create/Modify:**
- src/opencode_debugger/api/output.py

**Reference:**
- LLD_API.md Section 3.7 (GET /sessions/{session_id}/events)

---

### TASK-074: Implement Router Aggregation (api/router.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 1h
**Dependencies:** TASK-051-TASK-073
**Assignee:** Unassigned

**Description:**
Create the main router that aggregates all endpoint routers.

**Acceptance Criteria:**
- [ ] Create api/router.py with main router
- [ ] Include server router with prefix
- [ ] Include sessions router with prefix
- [ ] Include breakpoints router with prefix
- [ ] Include execution router with prefix
- [ ] Include inspection router with prefix
- [ ] Include output router with prefix
- [ ] Configure all routers under /api/v1

**Files to Create/Modify:**
- src/opencode_debugger/api/router.py

**Reference:**
- LLD_BACKEND.md Section 1 (Project Structure)

---

### TASK-075: Implement Main Application Entry Point (main.py)

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 2h
**Dependencies:** TASK-074, TASK-047, TASK-048, TASK-042
**Assignee:** Unassigned

**Description:**
Implement the FastAPI application entry point with startup/shutdown lifecycle.

**Acceptance Criteria:**
- [ ] Create `create_app(settings)` factory function
- [ ] Configure FastAPI with title, version, description
- [ ] Register exception handlers
- [ ] Register middleware
- [ ] Include main router
- [ ] Implement startup event to initialize SessionManager
- [ ] Implement shutdown event to cleanup SessionManager
- [ ] Create uvicorn entry point for CLI

**Files to Create/Modify:**
- src/opencode_debugger/main.py

**Reference:**
- LLD_BACKEND.md Section 1 (main.py)
- IMPLEMENTATION_PLAN.md Section 10 (Getting Started)

---

### TASK-076: API Integration Tests - Sessions

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 4h
**Dependencies:** TASK-053-TASK-058, TASK-005
**Assignee:** Unassigned

**Description:**
Write integration tests for session API endpoints.

**Acceptance Criteria:**
- [ ] Test API-S-001 through API-S-012 from TEST_PLAN.md
- [ ] Test create session with various configs
- [ ] Test session limit (429)
- [ ] Test list sessions with filters
- [ ] Test get/delete session
- [ ] Test launch and attach
- [ ] Test response envelope format

**Files to Create/Modify:**
- tests/integration/test_api_sessions.py

**Reference:**
- TEST_PLAN.md Section 3.1 (Session API Tests)

---

### TASK-077: API Integration Tests - Breakpoints

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 3h
**Dependencies:** TASK-059-TASK-061, TASK-005
**Assignee:** Unassigned

**Description:**
Write integration tests for breakpoint API endpoints.

**Acceptance Criteria:**
- [ ] Test API-BP-001 through API-BP-012 from TEST_PLAN.md
- [ ] Test set breakpoints verified/unverified
- [ ] Test conditional, hit count, logpoint breakpoints
- [ ] Test list with filters
- [ ] Test delete breakpoint
- [ ] Test persistence across requests

**Files to Create/Modify:**
- tests/integration/test_api_breakpoints.py

**Reference:**
- TEST_PLAN.md Section 3.1 (Breakpoint API Tests)

---

### TASK-078: API Integration Tests - Execution

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 3h
**Dependencies:** TASK-062-TASK-066, TASK-005
**Assignee:** Unassigned

**Description:**
Write integration tests for execution control API endpoints.

**Acceptance Criteria:**
- [ ] Test API-EX-001 through API-EX-013 from TEST_PLAN.md
- [ ] Test launch with args, env, cwd
- [ ] Test stop_on_entry
- [ ] Test continue/pause
- [ ] Test step over/into/out
- [ ] Test invalid state errors (409)

**Files to Create/Modify:**
- tests/integration/test_api_execution.py

**Reference:**
- TEST_PLAN.md Section 3.1 (Execution Control API Tests)

---

### TASK-079: API Integration Tests - Inspection

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 3h
**Dependencies:** TASK-067-TASK-071, TASK-005
**Assignee:** Unassigned

**Description:**
Write integration tests for inspection API endpoints.

**Acceptance Criteria:**
- [ ] Test API-IN-001 through API-IN-010 from TEST_PLAN.md
- [ ] Test get threads
- [ ] Test get stacktrace with levels
- [ ] Test get scopes
- [ ] Test get variables with pagination
- [ ] Test evaluate success and error

**Files to Create/Modify:**
- tests/integration/test_api_inspection.py

**Reference:**
- TEST_PLAN.md Section 3.1 (Inspection API Tests)

---

### TASK-080: API Integration Tests - Output

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 2h
**Dependencies:** TASK-072-TASK-073, TASK-005
**Assignee:** Unassigned

**Description:**
Write integration tests for output API endpoints.

**Acceptance Criteria:**
- [ ] Test API-OUT-001 through API-OUT-009 from TEST_PLAN.md
- [ ] Test get output with pagination
- [ ] Test category filtering
- [ ] Test get events with cursor
- [ ] Test long-poll timeout
- [ ] Test event types (stopped, output, terminated)

**Files to Create/Modify:**
- tests/integration/test_api_output.py

**Reference:**
- TEST_PLAN.md Section 3.1 (Output & Events API Tests)

---

## 6. Unit Tests (TASK-081 to TASK-100)

### TASK-081: Error Handling Tests - Session Errors

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 2h
**Dependencies:** TASK-076
**Assignee:** Unassigned

**Description:**
Write tests for session-related error codes.

**Acceptance Criteria:**
- [ ] Test SESSION_NOT_FOUND (404)
- [ ] Test SESSION_LIMIT_REACHED (429)
- [ ] Test SESSION_EXPIRED (410)
- [ ] Test INVALID_SESSION_STATE (409)

**Files to Create/Modify:**
- tests/errors/test_session_errors.py

**Reference:**
- TEST_PLAN.md Section 7.1 (Session Error Codes)

---

### TASK-082: Error Handling Tests - Breakpoint Errors

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 2h
**Dependencies:** TASK-077
**Assignee:** Unassigned

**Description:**
Write tests for breakpoint-related error codes.

**Acceptance Criteria:**
- [ ] Test BREAKPOINT_NOT_FOUND (404)
- [ ] Test BREAKPOINT_INVALID_LINE (400)
- [ ] Test BREAKPOINT_INVALID_CONDITION (400)
- [ ] Test BREAKPOINT_FILE_NOT_FOUND (400)

**Files to Create/Modify:**
- tests/errors/test_breakpoint_errors.py

**Reference:**
- TEST_PLAN.md Section 7.2 (Breakpoint Error Codes)

---

### TASK-083: Error Handling Tests - DAP Errors

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 2h
**Dependencies:** TASK-078
**Assignee:** Unassigned

**Description:**
Write tests for DAP-related error codes.

**Acceptance Criteria:**
- [ ] Test DEBUGPY_TIMEOUT (504)
- [ ] Test DEBUGPY_ERROR (500)
- [ ] Test LAUNCH_FAILED (500)
- [ ] Test LAUNCH_SCRIPT_NOT_FOUND (400)
- [ ] Test LAUNCH_SYNTAX_ERROR (400)
- [ ] Test ATTACH_FAILED (500)
- [ ] Test ATTACH_TIMEOUT (504)
- [ ] Test ATTACH_REFUSED (502)

**Files to Create/Modify:**
- tests/errors/test_dap_errors.py

**Reference:**
- TEST_PLAN.md Section 7.3 (DAP Error Codes)

---

### TASK-084: Error Handling Tests - Reference Errors

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 1h
**Dependencies:** TASK-079
**Assignee:** Unassigned

**Description:**
Write tests for reference-related error codes.

**Acceptance Criteria:**
- [ ] Test THREAD_NOT_FOUND (404)
- [ ] Test FRAME_NOT_FOUND (404)
- [ ] Test VARIABLE_NOT_FOUND (404)

**Files to Create/Modify:**
- tests/errors/test_reference_errors.py

**Reference:**
- TEST_PLAN.md Section 7.4 (Reference Error Codes)

---

### TASK-085: Error Handling Tests - Request Errors

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 1h
**Dependencies:** TASK-076
**Assignee:** Unassigned

**Description:**
Write tests for request-related error codes.

**Acceptance Criteria:**
- [ ] Test INVALID_REQUEST (400)
- [ ] Test MISSING_PARAMETER (400)
- [ ] Test INVALID_PARAMETER (400)
- [ ] Test EVALUATE_ERROR (400)

**Files to Create/Modify:**
- tests/errors/test_request_errors.py

**Reference:**
- TEST_PLAN.md Section 7.5 (Request Error Codes)

---

### TASK-086: Error Response Format Verification Tests

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 2h
**Dependencies:** TASK-081-TASK-085
**Assignee:** Unassigned

**Description:**
Write tests to verify all error responses follow standard format.

**Acceptance Criteria:**
- [ ] Test all errors have success=false
- [ ] Test all errors have data=null
- [ ] Test all errors have code, message, details
- [ ] Test all responses have request_id and timestamp

**Files to Create/Modify:**
- tests/errors/test_error_format.py

**Reference:**
- TEST_PLAN.md Section 7.6 (Error Response Format Verification)

---

### TASK-087: Edge Case Tests - Syntax Errors

**Status:** TODO
**Priority:** P2 (Medium)
**Estimate:** 2h
**Dependencies:** TASK-078, TASK-006
**Assignee:** Unassigned

**Description:**
Write tests for syntax error edge cases.

**Acceptance Criteria:**
- [ ] Test EC-SYN-001 through EC-SYN-004 from TEST_PLAN.md
- [ ] Test launch with syntax error
- [ ] Test session state after syntax error
- [ ] Test retry after fix
- [ ] Test syntax error in imported module

**Files to Create/Modify:**
- tests/edge_cases/test_syntax_errors.py

**Reference:**
- TEST_PLAN.md Section 5.1 (Syntax Errors)

---

### TASK-088: Edge Case Tests - Missing Files

**Status:** TODO
**Priority:** P2 (Medium)
**Estimate:** 1h
**Dependencies:** TASK-077
**Assignee:** Unassigned

**Description:**
Write tests for missing file edge cases.

**Acceptance Criteria:**
- [ ] Test EC-MIS-001 through EC-MIS-004 from TEST_PLAN.md
- [ ] Test breakpoint in missing file (verified=false)
- [ ] Test breakpoint ID assignment
- [ ] Test list shows unverified
- [ ] Test delete unverified

**Files to Create/Modify:**
- tests/edge_cases/test_missing_files.py

**Reference:**
- TEST_PLAN.md Section 5.2 (Missing Files)

---

### TASK-089: Edge Case Tests - Threading

**Status:** TODO
**Priority:** P2 (Medium)
**Estimate:** 3h
**Dependencies:** TASK-079, TASK-006
**Assignee:** Unassigned

**Description:**
Write tests for multi-threading edge cases.

**Acceptance Criteria:**
- [ ] Test EC-THR-001 through EC-THR-005 from TEST_PLAN.md
- [ ] Test two threads hitting breakpoints
- [ ] Test get threads shows all stopped
- [ ] Test stack trace per thread
- [ ] Test continue one thread

**Files to Create/Modify:**
- tests/edge_cases/test_threading.py

**Reference:**
- TEST_PLAN.md Section 5.3 (Threading)

---

### TASK-090: Edge Case Tests - Long Running Scripts

**Status:** TODO
**Priority:** P2 (Medium)
**Estimate:** 2h
**Dependencies:** TASK-078, TASK-006
**Assignee:** Unassigned

**Description:**
Write tests for long-running script edge cases.

**Acceptance Criteria:**
- [ ] Test EC-LRS-001 through EC-LRS-005 from TEST_PLAN.md
- [ ] Test session stays active with activity
- [ ] Test breakpoint set while running
- [ ] Test pause timing
- [ ] Test output pagination
- [ ] Test activity resets timeout

**Files to Create/Modify:**
- tests/edge_cases/test_long_running.py

**Reference:**
- TEST_PLAN.md Section 5.4 (Long Running Scripts)

---

### TASK-091: Edge Case Tests - Large Variables

**Status:** TODO
**Priority:** P2 (Medium)
**Estimate:** 2h
**Dependencies:** TASK-079, TASK-006
**Assignee:** Unassigned

**Description:**
Write tests for large variable edge cases.

**Acceptance Criteria:**
- [ ] Test EC-LRG-001 through EC-LRG-006 from TEST_PLAN.md
- [ ] Test list with 1M items
- [ ] Test paginate large list
- [ ] Test large dict
- [ ] Test deep nested object
- [ ] Test long string truncation

**Files to Create/Modify:**
- tests/edge_cases/test_large_variables.py

**Reference:**
- TEST_PLAN.md Section 5.5 (Large Variables)

---

### TASK-092: Edge Case Tests - Circular References

**Status:** TODO
**Priority:** P2 (Medium)
**Estimate:** 2h
**Dependencies:** TASK-079, TASK-006
**Assignee:** Unassigned

**Description:**
Write tests for circular reference edge cases.

**Acceptance Criteria:**
- [ ] Test EC-CIR-001 through EC-CIR-005 from TEST_PLAN.md
- [ ] Test self-referencing object
- [ ] Test parent-child circular
- [ ] Test graph with cycles
- [ ] Test navigation still works
- [ ] Test no infinite loops

**Files to Create/Modify:**
- tests/edge_cases/test_circular_references.py

**Reference:**
- TEST_PLAN.md Section 5.6 (Circular References)

---

### TASK-093: Edge Case Tests - Output Buffer Overflow

**Status:** TODO
**Priority:** P2 (Medium)
**Estimate:** 2h
**Dependencies:** TASK-080, TASK-006
**Assignee:** Unassigned

**Description:**
Write tests for output buffer overflow edge cases.

**Acceptance Criteria:**
- [ ] Test EC-OUT-001 through EC-OUT-005 from TEST_PLAN.md
- [ ] Test output exceeds 50MB
- [ ] Test truncated flag
- [ ] Test most recent preserved
- [ ] Test line numbers continuous
- [ ] Test dropped count accuracy

**Files to Create/Modify:**
- tests/edge_cases/test_output_overflow.py

**Reference:**
- TEST_PLAN.md Section 5.7 (Output Buffer Overflow)

---

### TASK-094: Edge Case Tests - Invalid Operations

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 2h
**Dependencies:** TASK-076-TASK-079
**Assignee:** Unassigned

**Description:**
Write tests for invalid operation edge cases.

**Acceptance Criteria:**
- [ ] Test EC-INV-001 through EC-INV-007 from TEST_PLAN.md
- [ ] Test launch twice
- [ ] Test step when running
- [ ] Test continue when not paused
- [ ] Test get variables when running
- [ ] Test invalid frame_id, variables_reference, thread_id

**Files to Create/Modify:**
- tests/edge_cases/test_invalid_operations.py

**Reference:**
- TEST_PLAN.md Section 5.8 (Invalid Operations)

---

### TASK-095: Performance Tests - Latency

**Status:** TODO
**Priority:** P2 (Medium)
**Estimate:** 3h
**Dependencies:** TASK-075, TASK-005
**Assignee:** Unassigned

**Description:**
Write performance tests for API latency.

**Acceptance Criteria:**
- [ ] Test PERF-LAT-001 through PERF-LAT-008 from TEST_PLAN.md
- [ ] Session creation <500ms
- [ ] Breakpoint set <100ms
- [ ] Step operations <200ms
- [ ] Variable inspection <300ms
- [ ] Status polling <50ms

**Files to Create/Modify:**
- tests/performance/test_latency.py

**Reference:**
- TEST_PLAN.md Section 6.1 (Latency Tests)

---

### TASK-096: Performance Tests - Throughput

**Status:** TODO
**Priority:** P2 (Medium)
**Estimate:** 2h
**Dependencies:** TASK-095
**Assignee:** Unassigned

**Description:**
Write performance tests for throughput.

**Acceptance Criteria:**
- [ ] Test PERF-THR-001 through PERF-THR-005 from TEST_PLAN.md
- [ ] 10 concurrent sessions
- [ ] 100 breakpoints per session
- [ ] 10 steps per second
- [ ] 100 events per second

**Files to Create/Modify:**
- tests/performance/test_throughput.py

**Reference:**
- TEST_PLAN.md Section 6.2 (Throughput Tests)

---

### TASK-097: Performance Tests - Stress

**Status:** TODO
**Priority:** P3 (Low)
**Estimate:** 3h
**Dependencies:** TASK-096
**Assignee:** Unassigned

**Description:**
Write stress tests for system limits.

**Acceptance Criteria:**
- [ ] Test PERF-STR-001 through PERF-STR-005 from TEST_PLAN.md
- [ ] Max sessions at once
- [ ] Rapid session create/delete
- [ ] Output flood handling
- [ ] Rapid step operations
- [ ] Many breakpoints (500+)

**Files to Create/Modify:**
- tests/performance/test_stress.py

**Reference:**
- TEST_PLAN.md Section 6.3 (Stress Tests)

---

### TASK-098: Performance Tests - Memory

**Status:** TODO
**Priority:** P2 (Medium)
**Estimate:** 2h
**Dependencies:** TASK-096
**Assignee:** Unassigned

**Description:**
Write memory tests for resource limits.

**Acceptance Criteria:**
- [ ] Test PERF-MEM-001 through PERF-MEM-004 from TEST_PLAN.md
- [ ] Output buffer 50MB limit
- [ ] Session cleanup releases memory
- [ ] Long-running session memory stability
- [ ] Event queue bounded

**Files to Create/Modify:**
- tests/performance/test_memory.py

**Reference:**
- TEST_PLAN.md Section 6.4 (Memory Tests)

---

### TASK-099: API Contract Test Coverage

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 2h
**Dependencies:** TASK-076-TASK-080
**Assignee:** Unassigned

**Description:**
Ensure 100% API contract coverage with additional tests.

**Acceptance Criteria:**
- [ ] Verify all endpoints have at least one test
- [ ] Verify all response codes are tested
- [ ] Verify all query parameters are tested
- [ ] Document any coverage gaps

**Files to Create/Modify:**
- tests/integration/test_api_contracts.py

**Reference:**
- TEST_PLAN.md Section 1.4 (Test Coverage Targets)

---

### TASK-100: Test Suite Coverage Report

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 1h
**Dependencies:** TASK-081-TASK-099
**Assignee:** Unassigned

**Description:**
Generate and verify test coverage meets 90% target.

**Acceptance Criteria:**
- [ ] Run full test suite with coverage
- [ ] Verify >90% line coverage
- [ ] Verify >85% branch coverage
- [ ] Document uncovered code with justification

**Files to Create/Modify:**
- (Coverage reports only)

**Reference:**
- TEST_PLAN.md Section 1.4 (Test Coverage Targets)

---

## 7. Integration Tests (TASK-101 to TASK-110)

### TASK-101: E2E Test - Basic Debug Session

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 4h
**Dependencies:** TASK-075, TASK-006
**Assignee:** Unassigned

**Description:**
Implement end-to-end test for basic debug session workflow.

**Acceptance Criteria:**
- [ ] Test complete workflow from User Story 3.1
- [ ] Create session
- [ ] Set breakpoint
- [ ] Launch script
- [ ] Wait for breakpoint hit
- [ ] Get stack trace
- [ ] Get variables
- [ ] Evaluate expression
- [ ] Step over
- [ ] Continue to completion
- [ ] Verify output
- [ ] Cleanup

**Files to Create/Modify:**
- tests/e2e/test_basic_debug_session.py

**Reference:**
- TEST_PLAN.md Section 4.1 (Basic Debug Session)

---

### TASK-102: E2E Test - Conditional Breakpoint Debugging

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 3h
**Dependencies:** TASK-101, TASK-006
**Assignee:** Unassigned

**Description:**
Implement end-to-end test for conditional breakpoint debugging.

**Acceptance Criteria:**
- [ ] Test conditional breakpoint workflow from User Story 3.5
- [ ] Set breakpoint with condition i > 100
- [ ] Verify stops only when condition true
- [ ] Test hit count breakpoint
- [ ] Verify correct iteration

**Files to Create/Modify:**
- tests/e2e/test_conditional_breakpoint.py

**Reference:**
- TEST_PLAN.md Section 4.2 (Conditional Breakpoint)

---

### TASK-103: E2E Test - Exception Debugging

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 2h
**Dependencies:** TASK-101, TASK-006
**Assignee:** Unassigned

**Description:**
Implement end-to-end test for exception debugging.

**Acceptance Criteria:**
- [ ] Test exception debugging workflow from User Story 3.6
- [ ] Launch with stop_on_exception=true
- [ ] Wait for exception
- [ ] Verify exception details (type, message, location)
- [ ] Get stack trace at exception
- [ ] Inspect variables at crash

**Files to Create/Modify:**
- tests/e2e/test_exception_debugging.py

**Reference:**
- TEST_PLAN.md Section 4.3 (Exception Debugging)

---

### TASK-104: E2E Test - Multi-File Debugging

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 3h
**Dependencies:** TASK-101, TASK-007
**Assignee:** Unassigned

**Description:**
Implement end-to-end test for multi-file debugging.

**Acceptance Criteria:**
- [ ] Test debugging across multiple files
- [ ] Set breakpoints in 3 files
- [ ] Step into imported module
- [ ] Verify stack trace shows multiple files
- [ ] Continue to breakpoints in different files

**Files to Create/Modify:**
- tests/e2e/test_multi_file_debugging.py

**Reference:**
- TEST_PLAN.md Section 4.4 (Multi-File Debugging)

---

### TASK-105: E2E Test - Concurrent Sessions

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 3h
**Dependencies:** TASK-101
**Assignee:** Unassigned

**Description:**
Implement end-to-end test for concurrent sessions.

**Acceptance Criteria:**
- [ ] Test running up to 10 concurrent sessions
- [ ] Create 10 sessions
- [ ] Set breakpoints in each
- [ ] Launch all scripts
- [ ] Verify all pause independently
- [ ] Operate on each without cross-contamination
- [ ] Test 11th session returns 429
- [ ] Delete one, create new succeeds

**Files to Create/Modify:**
- tests/e2e/test_concurrent_sessions.py

**Reference:**
- TEST_PLAN.md Section 4.5 (Concurrent Sessions)

---

### TASK-106: E2E Test - Logpoints

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 2h
**Dependencies:** TASK-101, TASK-006
**Assignee:** Unassigned

**Description:**
Implement end-to-end test for logpoint debugging.

**Acceptance Criteria:**
- [ ] Set breakpoint with log_message
- [ ] Verify program continues (doesn't pause)
- [ ] Verify log message appears in output
- [ ] Test variable interpolation in log message

**Files to Create/Modify:**
- tests/e2e/test_logpoints.py

**Reference:**
- LLD_API.md Section 3.4 (Breakpoints)

---

### TASK-107: E2E Test - Module Launch Mode

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 2h
**Dependencies:** TASK-101
**Assignee:** Unassigned

**Description:**
Implement end-to-end test for module launch mode.

**Acceptance Criteria:**
- [ ] Test launch with module instead of script
- [ ] Launch pytest module
- [ ] Verify breakpoints work in test code
- [ ] Verify module args passed correctly

**Files to Create/Modify:**
- tests/e2e/test_module_launch.py

**Reference:**
- LLD_API.md Section 3.3 (Launch with module)

---

### TASK-108: E2E Test - Attach Mode

**Status:** TODO
**Priority:** P2 (Medium)
**Estimate:** 3h
**Dependencies:** TASK-101
**Assignee:** Unassigned

**Description:**
Implement end-to-end test for attach mode debugging.

**Acceptance Criteria:**
- [ ] Start script with debugpy enabled
- [ ] Create session
- [ ] Attach to running process
- [ ] Set breakpoint
- [ ] Verify breakpoint hit
- [ ] Debug normally after attach

**Files to Create/Modify:**
- tests/e2e/test_attach_mode.py

**Reference:**
- LLD_API.md Section 3.3 (Attach)

---

### TASK-109: E2E Test - Session Recovery

**Status:** TODO
**Priority:** P2 (Medium)
**Estimate:** 3h
**Dependencies:** TASK-101
**Assignee:** Unassigned

**Description:**
Implement end-to-end test for session recovery after server restart.

**Acceptance Criteria:**
- [ ] Create session and set breakpoints
- [ ] Restart server
- [ ] Verify breakpoints persist
- [ ] Verify session can be recreated
- [ ] Note: Full session recovery is future work

**Files to Create/Modify:**
- tests/e2e/test_session_recovery.py

**Reference:**
- IMPLEMENTATION_PLAN.md Section 6 (Success Criteria)

---

### TASK-110: E2E Test - Full Workflow Validation

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 4h
**Dependencies:** TASK-101-TASK-109
**Assignee:** Unassigned

**Description:**
Implement comprehensive E2E test validating all user story workflows.

**Acceptance Criteria:**
- [ ] Run through all major user story scenarios
- [ ] Verify API contract compliance
- [ ] Verify event sequences
- [ ] Verify timing requirements
- [ ] Document any deviations

**Files to Create/Modify:**
- tests/e2e/test_full_workflow.py

**Reference:**
- IMPLEMENTATION_PLAN.md Section 6 (Success Criteria)

---

## 8. E2E Tests (TASK-111 to TASK-120)

### TASK-111: Create README.md

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 2h
**Dependencies:** TASK-075
**Assignee:** Unassigned

**Description:**
Create comprehensive README with installation and usage instructions.

**Acceptance Criteria:**
- [ ] Add project description and features
- [ ] Add installation instructions
- [ ] Add quick start guide
- [ ] Add API overview with examples
- [ ] Add configuration documentation
- [ ] Add development setup instructions
- [ ] Add testing instructions
- [ ] Add license information

**Files to Create/Modify:**
- README.md

**Reference:**
- IMPLEMENTATION_PLAN.md Section 10 (Getting Started)

---

### TASK-112: Create Example Client Scripts

**Status:** TODO
**Priority:** P2 (Medium)
**Estimate:** 2h
**Dependencies:** TASK-075
**Assignee:** Unassigned

**Description:**
Create example client scripts demonstrating API usage.

**Acceptance Criteria:**
- [ ] Create bash example for basic debug session
- [ ] Create Python client class example
- [ ] Add conditional breakpoint example
- [ ] Add exception debugging example
- [ ] Add multi-file debugging example

**Files to Create/Modify:**
- examples/basic_debug.sh
- examples/debug_client.py
- examples/conditional_breakpoint.sh
- examples/exception_debug.sh

**Reference:**
- LLD_API.md Section 8 (Client Usage Examples)

---

### TASK-113: Generate OpenAPI Specification

**Status:** TODO
**Priority:** P2 (Medium)
**Estimate:** 1h
**Dependencies:** TASK-075
**Assignee:** Unassigned

**Description:**
Generate OpenAPI specification from FastAPI routes.

**Acceptance Criteria:**
- [ ] Verify FastAPI auto-generates OpenAPI spec
- [ ] Export openapi.json and openapi.yaml
- [ ] Verify spec matches LLD_API.md

**Files to Create/Modify:**
- docs/openapi.json
- docs/openapi.yaml

**Reference:**
- LLD_API.md Section 7 (OpenAPI Spec)

---

### TASK-114: Add Logging and Observability

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 3h
**Dependencies:** TASK-075
**Assignee:** Unassigned

**Description:**
Add structured logging throughout the application.

**Acceptance Criteria:**
- [ ] Configure logging with structlog or standard logging
- [ ] Add request/response logging
- [ ] Add DAP message logging (debug level)
- [ ] Add session lifecycle logging
- [ ] Add error logging with context
- [ ] Make log level configurable

**Files to Create/Modify:**
- src/opencode_debugger/logging.py
- (Various files for log statements)

**Reference:**
- IMPLEMENTATION_PLAN.md Phase 6 (Logging and observability)

---

### TASK-115: Improve Error Messages

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 2h
**Dependencies:** TASK-075
**Assignee:** Unassigned

**Description:**
Improve error messages with helpful suggestions.

**Acceptance Criteria:**
- [ ] Add suggestions to all error responses
- [ ] Include context in error details
- [ ] Add hints for common mistakes
- [ ] Verify error messages are user-friendly

**Files to Create/Modify:**
- src/opencode_debugger/core/exceptions.py
- (Various API error handlers)

**Reference:**
- LLD_API.md Section 5.2 (Error Response Examples)

---

### TASK-116: Implement Session Recovery (Stub)

**Status:** TODO
**Priority:** P2 (Medium)
**Estimate:** 4h
**Dependencies:** TASK-042
**Assignee:** Unassigned

**Description:**
Implement basic session recovery functionality.

**Acceptance Criteria:**
- [ ] Save session state to persistence
- [ ] Load session state on startup
- [ ] Handle recovery gracefully when debuggee is gone
- [ ] Document limitations

**Files to Create/Modify:**
- src/opencode_debugger/persistence/sessions.py
- src/opencode_debugger/core/session.py

**Reference:**
- IMPLEMENTATION_PLAN.md Phase 6 (Session recovery)

---

### TASK-117: Code Cleanup and Documentation

**Status:** TODO
**Priority:** P2 (Medium)
**Estimate:** 2h
**Dependencies:** All previous tasks
**Assignee:** Unassigned

**Description:**
Final code cleanup, docstrings, and inline documentation.

**Acceptance Criteria:**
- [ ] Add docstrings to all public functions/classes
- [ ] Remove any TODO comments
- [ ] Ensure consistent code style
- [ ] Run ruff and mypy, fix any issues

**Files to Create/Modify:**
- (All source files)

**Reference:**
- Standard Python documentation practices

---

### TASK-118: Final Test Suite Run and Coverage

**Status:** TODO
**Priority:** P0 (Critical)
**Estimate:** 2h
**Dependencies:** TASK-100, TASK-110
**Assignee:** Unassigned

**Description:**
Run complete test suite and verify coverage targets.

**Acceptance Criteria:**
- [ ] All tests pass
- [ ] Coverage >90%
- [ ] No flaky tests
- [ ] Performance tests meet targets

**Files to Create/Modify:**
- (Test reports only)

**Reference:**
- IMPLEMENTATION_PLAN.md Section 6 (Success Criteria)

---

### TASK-119: Release Preparation

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 1h
**Dependencies:** TASK-118
**Assignee:** Unassigned

**Description:**
Prepare for v0.1.0 release.

**Acceptance Criteria:**
- [ ] Update version in pyproject.toml
- [ ] Create CHANGELOG.md
- [ ] Tag release
- [ ] Build package

**Files to Create/Modify:**
- pyproject.toml
- CHANGELOG.md

**Reference:**
- IMPLEMENTATION_PLAN.md Section 11 (Next Steps)

---

### TASK-120: Post-Release Validation

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 2h
**Dependencies:** TASK-119
**Assignee:** Unassigned

**Description:**
Validate release package works correctly.

**Acceptance Criteria:**
- [ ] Install package from build
- [ ] Run server successfully
- [ ] Complete basic debug session
- [ ] Verify all documented features work

**Files to Create/Modify:**
- (Validation only)

**Reference:**
- IMPLEMENTATION_PLAN.md Section 10 (Quick Test)

---

## 9. Documentation & Polish (TASK-121 to TASK-127)

### TASK-121: API Documentation

**Status:** TODO
**Priority:** P2 (Medium)
**Estimate:** 2h
**Dependencies:** TASK-113
**Assignee:** Unassigned

**Description:**
Create API documentation beyond OpenAPI spec.

**Acceptance Criteria:**
- [ ] Document authentication (none for v1)
- [ ] Document rate limits (none for v1)
- [ ] Document versioning strategy
- [ ] Document deprecation policy

**Files to Create/Modify:**
- docs/API.md

**Reference:**
- LLD_API.md (entire document)

---

### TASK-122: Architecture Documentation

**Status:** TODO
**Priority:** P3 (Low)
**Estimate:** 2h
**Dependencies:** TASK-075
**Assignee:** Unassigned

**Description:**
Create architecture documentation for developers.

**Acceptance Criteria:**
- [ ] Document component architecture
- [ ] Document data flow
- [ ] Document DAP protocol integration
- [ ] Include diagrams

**Files to Create/Modify:**
- docs/ARCHITECTURE.md

**Reference:**
- LLD_BACKEND.md (entire document)

---

### TASK-123: Contributing Guide

**Status:** TODO
**Priority:** P3 (Low)
**Estimate:** 1h
**Dependencies:** TASK-111
**Assignee:** Unassigned

**Description:**
Create contributing guidelines.

**Acceptance Criteria:**
- [ ] Document development setup
- [ ] Document testing requirements
- [ ] Document code style
- [ ] Document PR process

**Files to Create/Modify:**
- CONTRIBUTING.md

**Reference:**
- Standard open source practices

---

### TASK-124: Security Considerations Documentation

**Status:** TODO
**Priority:** P2 (Medium)
**Estimate:** 1h
**Dependencies:** TASK-111
**Assignee:** Unassigned

**Description:**
Document security considerations and limitations.

**Acceptance Criteria:**
- [ ] Document localhost-only design
- [ ] Document no authentication (v1)
- [ ] Document code execution risks
- [ ] Recommend deployment practices

**Files to Create/Modify:**
- docs/SECURITY.md

**Reference:**
- LLD_API.md Section 1.1 (Base Configuration)

---

### TASK-125: Performance Tuning Documentation

**Status:** TODO
**Priority:** P3 (Low)
**Estimate:** 1h
**Dependencies:** TASK-095-TASK-098
**Assignee:** Unassigned

**Description:**
Document performance characteristics and tuning.

**Acceptance Criteria:**
- [ ] Document performance targets
- [ ] Document configuration options
- [ ] Document scaling limitations
- [ ] Include benchmark results

**Files to Create/Modify:**
- docs/PERFORMANCE.md

**Reference:**
- IMPLEMENTATION_PLAN.md Section 6 (Performance Requirements)

---

### TASK-126: Troubleshooting Guide

**Status:** TODO
**Priority:** P2 (Medium)
**Estimate:** 1h
**Dependencies:** TASK-111
**Assignee:** Unassigned

**Description:**
Create troubleshooting guide for common issues.

**Acceptance Criteria:**
- [ ] Document common error codes and solutions
- [ ] Document debugpy issues
- [ ] Document session timeout issues
- [ ] Document performance issues

**Files to Create/Modify:**
- docs/TROUBLESHOOTING.md

**Reference:**
- LLD_API.md Section 5 (Error Codes)

---

### TASK-127: Final Documentation Review

**Status:** TODO
**Priority:** P1 (High)
**Estimate:** 2h
**Dependencies:** TASK-121-TASK-126
**Assignee:** Unassigned

**Description:**
Final review of all documentation for completeness and accuracy.

**Acceptance Criteria:**
- [ ] All documentation is accurate
- [ ] All links work
- [ ] Examples are tested
- [ ] No outdated information

**Files to Create/Modify:**
- (All documentation files)

**Reference:**
- IMPLEMENTATION_PLAN.md Section 6 (Documentation coverage)

---

## Appendix: Task Dependencies Graph

```
Phase 1: Project Setup (Parallel: TASK-001 to TASK-010)
    │
    ▼
Phase 2: Core Models (TASK-011 to TASK-020)
    │
    ├──> TASK-011 (DAP Models) ──> TASK-012, TASK-014, TASK-015
    │
    └──> TASK-016 (Exceptions)
    │
    ▼
Phase 3: Infrastructure (TASK-021 to TASK-040)
    │
    ├──> TASK-021 (Config)
    │
    ├──> TASK-023 (Output Buffer)
    │
    ├──> TASK-025, TASK-027 (Persistence)
    │
    ├──> TASK-030 (DAP Client) ──> TASK-032 (debugpy Adapter)
    │
    └──> TASK-035 (Event Queue)
    │
    ▼
Phase 4: Session Management (TASK-041 to TASK-050)
    │
    ├──> TASK-041 (Session) ──> TASK-042 (SessionManager)
    │
    └──> TASK-047, TASK-048 (Middleware)
    │
    ▼
Phase 5: API Layer (TASK-051 to TASK-080)
    │
    ├──> TASK-051-052 (Server)
    │
    ├──> TASK-053-058 (Sessions)
    │
    ├──> TASK-059-061 (Breakpoints)
    │
    ├──> TASK-062-066 (Execution)
    │
    ├──> TASK-067-071 (Inspection)
    │
    └──> TASK-072-073 (Output)
         │
         └──> TASK-074-075 (Router + Main)
    │
    ▼
Phase 6: Testing (TASK-081 to TASK-120)
    │
    ├──> Unit Tests (TASK-081-100)
    │
    ├──> Integration Tests (TASK-101-110)
    │
    └──> E2E Tests (TASK-111-120)
    │
    ▼
Phase 7: Documentation (TASK-121 to TASK-127)
```

---

## Quick Reference: Tasks That Can Run in Parallel

### Wave 1 (No Dependencies):
- TASK-001, TASK-010

### Wave 2 (After TASK-001):
- TASK-002, TASK-006, TASK-007, TASK-008

### Wave 3 (After TASK-002):
- TASK-003, TASK-005, TASK-011, TASK-012, TASK-013, TASK-016, TASK-021

### Wave 4 (After Models):
- TASK-014, TASK-015, TASK-023, TASK-025, TASK-027, TASK-030, TASK-035

### Wave 5 (After Infrastructure):
- TASK-032, TASK-041

### Wave 6 (After Session):
- TASK-042, TASK-047, TASK-048, TASK-050

### Wave 7 (After API Dependencies):
- TASK-051-073 (many can run in parallel)

### Wave 8 (After All APIs):
- TASK-074, TASK-075

### Wave 9 (After Main App):
- All tests (TASK-076-120 can run in parallel by category)

### Wave 10 (After Tests):
- All documentation (TASK-121-127)

---

**Document End**

*Total Tasks: 127*
*Estimated Hours: ~248h*
*Target Completion: 14 days*
