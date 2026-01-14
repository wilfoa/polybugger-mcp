# Test Plan: OpenCode Debug Relay Server

**Project:** OpenCode Debug Relay Server
**Document Version:** 1.0
**Created:** January 13, 2026
**Status:** Design Complete
**Author:** QA Expert Agent

---

## Table of Contents

1. [Test Strategy](#1-test-strategy)
2. [Unit Test Specifications](#2-unit-test-specifications)
3. [Integration Test Specifications](#3-integration-test-specifications)
4. [End-to-End Test Scenarios](#4-end-to-end-test-scenarios)
5. [Edge Case Test Scenarios](#5-edge-case-test-scenarios)
6. [Performance Tests](#6-performance-tests)
7. [Error Handling Tests](#7-error-handling-tests)
8. [Test Fixtures](#8-test-fixtures)
9. [CI/CD Integration](#9-cicd-integration)

---

## 1. Test Strategy

### 1.1 Testing Approach

The OpenCode Debug Relay Server requires a comprehensive multi-layer testing strategy to ensure reliability, performance, and correctness when bridging AI agents with Python debugging capabilities.

#### Testing Pyramid

```
                    ┌─────────────────┐
                    │    E2E Tests    │  (~10% of tests)
                    │  Full Workflows │
                    └────────┬────────┘
                             │
                ┌────────────┴────────────┐
                │   Integration Tests     │  (~30% of tests)
                │ API + DAP + Persistence │
                └────────────┬────────────┘
                             │
        ┌────────────────────┴────────────────────┐
        │            Unit Tests                   │  (~60% of tests)
        │  Core Logic, Models, Utilities          │
        └─────────────────────────────────────────┘
```

#### Test Categories

| Category | Scope | Coverage Target | Execution Time |
|----------|-------|-----------------|----------------|
| Unit Tests | Individual functions, classes, modules | >90% line coverage | <30 seconds |
| Integration Tests | API endpoints, DAP protocol, persistence | 100% API contracts | <2 minutes |
| E2E Tests | Complete debug workflows | All user story flows | <5 minutes |
| Performance Tests | Latency, throughput, limits | All KPIs met | <3 minutes |
| Edge Case Tests | Error handling, boundary conditions | All documented edge cases | <2 minutes |

### 1.2 Test Environments

#### Local Development Environment

```yaml
environment: local
python_version: "3.11+"
dependencies:
  - pytest >= 8.0.0
  - pytest-asyncio >= 0.23.0
  - pytest-cov >= 4.1.0
  - pytest-timeout >= 2.2.0
  - httpx >= 0.25.0  # Async HTTP client
  - respx >= 0.20.0  # HTTP mocking
  - debugpy >= 1.8.0
  - factory-boy >= 3.3.0  # Test fixtures
  - faker >= 20.0.0  # Data generation

server_config:
  host: "127.0.0.1"
  port: 5679
  max_sessions: 10
  output_buffer_max_bytes: 52428800  # 50MB
  session_timeout_seconds: 3600
```

#### CI Environment

```yaml
environment: ci
os: ubuntu-latest
python_versions: ["3.10", "3.11", "3.12"]
services:
  - none (self-contained)
parallelism: 4
timeout_minutes: 15
coverage_threshold: 90
```

### 1.3 Test Data Management

#### Data Categories

| Category | Source | Refresh Strategy |
|----------|--------|------------------|
| Sample Scripts | `tests/fixtures/scripts/` | Static, version controlled |
| Mock DAP Responses | `tests/fixtures/dap/` | Static, version controlled |
| Test Project Structures | `tests/fixtures/projects/` | Static, version controlled |
| Generated Data | Factory classes | Runtime generation |

#### Data Isolation

- Each test creates isolated session data
- Temporary directories for persistence tests
- Automatic cleanup via pytest fixtures
- No shared state between tests

### 1.4 Test Coverage Targets

| Component | Line Coverage | Branch Coverage | Contract Coverage |
|-----------|---------------|-----------------|-------------------|
| `core/session.py` | >95% | >90% | 100% |
| `core/events.py` | >95% | >90% | 100% |
| `adapters/dap_client.py` | >90% | >85% | 100% |
| `adapters/debugpy_adapter.py` | >85% | >80% | 100% |
| `persistence/storage.py` | >95% | >90% | 100% |
| `persistence/breakpoints.py` | >95% | >90% | 100% |
| `utils/output_buffer.py` | >95% | >90% | 100% |
| `api/*` | >90% | >85% | 100% |
| **Overall** | **>90%** | **>85%** | **100%** |

---

## 2. Unit Test Specifications

### 2.1 core/session.py - Session Lifecycle

**Test File:** `tests/unit/test_session.py`

#### SessionState Tests

| Test Case ID | Test Name | Description | Expected Result |
|--------------|-----------|-------------|-----------------|
| SS-001 | `test_session_state_enum_values` | Verify all state values are lowercase strings | All states match API contract |
| SS-002 | `test_session_state_created_initial` | New session starts in CREATED state | `state == SessionState.CREATED` |
| SS-003 | `test_valid_state_transitions` | Test all valid state transitions | Transitions succeed |
| SS-004 | `test_invalid_state_transition_raises` | Invalid transitions raise error | `InvalidSessionStateError` raised |
| SS-005 | `test_state_transition_thread_safety` | Concurrent transitions are safe | No race conditions |

#### Session Class Tests

| Test Case ID | Test Name | Description | Expected Result |
|--------------|-----------|-------------|-----------------|
| S-001 | `test_session_creation_basic` | Create session with minimal params | Session created with defaults |
| S-002 | `test_session_creation_with_name` | Create session with custom name | Name set correctly |
| S-003 | `test_session_auto_generated_name` | Session without name gets auto-name | Name format: `session-{id[:8]}` |
| S-004 | `test_session_id_format` | Session ID follows format | Format: `sess_{uuid8}` |
| S-005 | `test_session_timestamps` | Created/last_activity timestamps set | Both timestamps are UTC |
| S-006 | `test_session_transition_to_valid` | Valid state transition succeeds | State updated |
| S-007 | `test_session_transition_updates_activity` | Transition updates last_activity | Timestamp updated |
| S-008 | `test_session_require_state_passes` | require_state with valid state passes | No exception |
| S-009 | `test_session_require_state_fails` | require_state with invalid state fails | `InvalidSessionStateError` raised |
| S-010 | `test_session_to_info_conversion` | Session converts to SessionInfo model | All fields mapped correctly |
| S-011 | `test_session_cleanup_releases_resources` | Cleanup releases adapter and buffers | Resources freed |
| S-012 | `test_session_output_buffer_initialized` | Output buffer created with correct size | Buffer has 50MB limit |
| S-013 | `test_session_event_queue_initialized` | Event queue created | Queue is empty initially |

#### SessionManager Tests

| Test Case ID | Test Name | Description | Expected Result |
|--------------|-----------|-------------|-----------------|
| SM-001 | `test_manager_create_session` | Create session via manager | Session returned with valid ID |
| SM-002 | `test_manager_create_session_limit` | Create more than max sessions | `SessionLimitError` raised at 10 |
| SM-003 | `test_manager_get_session_exists` | Get existing session | Session returned |
| SM-004 | `test_manager_get_session_not_found` | Get non-existent session | `SessionNotFoundError` raised |
| SM-005 | `test_manager_get_session_updates_activity` | Getting session updates activity | `last_activity` updated |
| SM-006 | `test_manager_list_sessions_empty` | List with no sessions | Empty list |
| SM-007 | `test_manager_list_sessions_multiple` | List with multiple sessions | All sessions returned |
| SM-008 | `test_manager_terminate_session` | Terminate existing session | Session removed and cleaned |
| SM-009 | `test_manager_terminate_not_found` | Terminate non-existent session | `SessionNotFoundError` raised |
| SM-010 | `test_manager_cleanup_stale_sessions` | Stale sessions are cleaned up | Expired sessions removed |
| SM-011 | `test_manager_cleanup_respects_activity` | Active sessions not cleaned | Recent sessions preserved |
| SM-012 | `test_manager_concurrent_create` | Concurrent session creation | Thread-safe, limit enforced |
| SM-013 | `test_manager_start_background_tasks` | Manager starts cleanup task | Task is running |
| SM-014 | `test_manager_stop_cleans_all` | Manager stop cleans all sessions | All sessions terminated |

**Mock Requirements:**
- `DebugpyAdapter` - Mock initialization and cleanup
- `BreakpointStore` - Mock load/save operations
- `asyncio.sleep` - Mock for time-sensitive tests

**Edge Cases:**
- Session timeout at exactly boundary
- Concurrent get/terminate on same session
- Manager stop during active operations

---

### 2.2 core/events.py - Event Queue

**Test File:** `tests/unit/test_events.py`

#### EventQueue Tests

| Test Case ID | Test Name | Description | Expected Result |
|--------------|-----------|-------------|-----------------|
| EQ-001 | `test_queue_put_adds_event` | Put event adds to queue | Event retrievable |
| EQ-002 | `test_queue_event_timestamp` | Event has UTC timestamp | Timestamp is timezone-aware |
| EQ-003 | `test_queue_get_returns_event` | Get retrieves event | Correct event returned |
| EQ-004 | `test_queue_get_with_timeout` | Get with timeout waits | Returns after timeout or event |
| EQ-005 | `test_queue_get_empty_no_timeout` | Get on empty queue, no timeout | Returns None immediately |
| EQ-006 | `test_queue_get_all_multiple` | Get all returns all events | All events returned in order |
| EQ-007 | `test_queue_get_all_empties_queue` | Get all removes events | Queue is empty after |
| EQ-008 | `test_queue_max_size_drops_oldest` | Full queue drops oldest | Oldest event dropped |
| EQ-009 | `test_queue_history_maintained` | History tracks recent events | History has events |
| EQ-010 | `test_queue_history_max_size` | History respects max size | Oldest history dropped |
| EQ-011 | `test_queue_clear_removes_all` | Clear empties queue and history | Both are empty |
| EQ-012 | `test_queue_concurrent_put_get` | Concurrent put/get is safe | No data corruption |

**Edge Cases:**
- Put on full queue with concurrent get
- Clear during active operations

---

### 2.3 adapters/dap_client.py - DAP Protocol Client

**Test File:** `tests/unit/test_dap_client.py`

#### DAPClient Tests

| Test Case ID | Test Name | Description | Expected Result |
|--------------|-----------|-------------|-----------------|
| DC-001 | `test_client_send_request_basic` | Send request and receive response | Response body returned |
| DC-002 | `test_client_request_sequence_increment` | Sequence numbers increment | Each request has unique seq |
| DC-003 | `test_client_request_timeout` | Request times out | `DAPTimeoutError` raised |
| DC-004 | `test_client_request_failure` | Request returns success=false | `DAPError` raised |
| DC-005 | `test_client_message_format` | Message has Content-Length header | Correct DAP format |
| DC-006 | `test_client_read_message_parses` | Read parses DAP message | Correct dict returned |
| DC-007 | `test_client_event_dispatch` | Events dispatched to callback | Callback invoked |
| DC-008 | `test_client_response_matches_request` | Response matched to pending request | Future resolved |
| DC-009 | `test_client_concurrent_requests` | Multiple concurrent requests | All get correct responses |
| DC-010 | `test_client_stop_cancels_pending` | Stop cancels pending requests | All futures cancelled |
| DC-011 | `test_client_closed_flag` | Client tracks closed state | No operations after close |

**Mock Requirements:**
- `asyncio.StreamReader` - Mock input stream
- `asyncio.StreamWriter` - Mock output stream

---

### 2.4 adapters/debugpy_adapter.py - debugpy Integration

**Test File:** `tests/unit/test_debugpy_adapter.py`

#### DebugpyAdapter Tests

| Test Case ID | Test Name | Description | Expected Result |
|--------------|-----------|-------------|-----------------|
| DA-001 | `test_adapter_initialize_starts_process` | Initialize spawns debugpy | Process running |
| DA-002 | `test_adapter_initialize_sends_init_request` | Initialize sends DAP init | Capabilities returned |
| DA-003 | `test_adapter_launch_sends_request` | Launch sends DAP launch | No error |
| DA-004 | `test_adapter_launch_config_mapping` | Launch config maps correctly | All fields present |
| DA-005 | `test_adapter_attach_by_pid` | Attach by PID | Request includes processId |
| DA-006 | `test_adapter_attach_by_port` | Attach by host/port | Request includes connect |
| DA-007 | `test_adapter_disconnect_terminates` | Disconnect terminates debuggee | terminateDebuggee=true |
| DA-008 | `test_adapter_set_breakpoints` | Set breakpoints request | Breakpoints returned |
| DA-009 | `test_adapter_continue_request` | Continue sends to correct thread | threadId included |
| DA-010 | `test_adapter_step_over` | Step over sends next request | DAP "next" sent |
| DA-011 | `test_adapter_step_into` | Step into sends stepIn request | DAP "stepIn" sent |
| DA-012 | `test_adapter_step_out` | Step out sends stepOut request | DAP "stepOut" sent |
| DA-013 | `test_adapter_threads` | Get threads | Thread list returned |
| DA-014 | `test_adapter_stack_trace` | Get stack trace | Frames returned |
| DA-015 | `test_adapter_scopes` | Get scopes | Scopes returned |
| DA-016 | `test_adapter_variables` | Get variables | Variables returned |
| DA-017 | `test_adapter_evaluate` | Evaluate expression | Result returned |
| DA-018 | `test_adapter_event_mapping` | DAP events map to EventType | Correct types |
| DA-019 | `test_adapter_output_callback` | Output events invoke callback | Callback receives output |
| DA-020 | `test_adapter_not_initialized_error` | Operations before init fail | `DAPConnectionError` raised |

**Mock Requirements:**
- `asyncio.create_subprocess_exec` - Mock process creation
- `DAPClient` - Mock DAP communication

---

### 2.5 persistence/storage.py - Atomic File Operations

**Test File:** `tests/unit/test_storage.py`

#### Storage Tests

| Test Case ID | Test Name | Description | Expected Result |
|--------------|-----------|-------------|-----------------|
| ST-001 | `test_project_id_from_path_consistent` | Same path gives same ID | IDs match |
| ST-002 | `test_project_id_from_path_unique` | Different paths give different IDs | IDs differ |
| ST-003 | `test_project_id_normalizes_path` | Path resolved before hashing | Symlinks handled |
| ST-004 | `test_atomic_write_creates_file` | Write creates new file | File exists |
| ST-005 | `test_atomic_write_creates_dirs` | Write creates parent directories | Dirs created |
| ST-006 | `test_atomic_write_json_format` | Data written as pretty JSON | Valid JSON with indent |
| ST-007 | `test_atomic_write_atomic` | Write is atomic (temp+rename) | No partial writes |
| ST-008 | `test_atomic_write_cleans_temp_on_error` | Error cleans up temp file | No .tmp files left |
| ST-009 | `test_safe_read_exists` | Read existing file | Data returned |
| ST-010 | `test_safe_read_not_found` | Read non-existent file | None returned |
| ST-011 | `test_safe_read_invalid_json` | Read invalid JSON file | `PersistenceError` raised |
| ST-012 | `test_safe_delete_exists` | Delete existing file | True returned |
| ST-013 | `test_safe_delete_not_found` | Delete non-existent file | False returned |
| ST-014 | `test_list_json_files` | List .json files only | Only .json files |
| ST-015 | `test_list_json_files_empty_dir` | List in empty directory | Empty list |
| ST-016 | `test_list_json_files_no_dir` | List in non-existent directory | Empty list |

**Edge Cases:**
- Disk full during write
- Permission denied
- Concurrent read/write

---

### 2.6 persistence/breakpoints.py - Breakpoint Storage

**Test File:** `tests/unit/test_breakpoints.py`

#### BreakpointStore Tests

| Test Case ID | Test Name | Description | Expected Result |
|--------------|-----------|-------------|-----------------|
| BP-001 | `test_store_load_empty` | Load from new project | Empty dict returned |
| BP-002 | `test_store_save_and_load` | Save then load breakpoints | Data matches |
| BP-003 | `test_store_save_multiple_files` | Save breakpoints for multiple files | All files saved |
| BP-004 | `test_store_update_file_adds` | Update adds breakpoints to file | Breakpoints added |
| BP-005 | `test_store_update_file_replaces` | Update replaces file breakpoints | Old ones removed |
| BP-006 | `test_store_update_file_removes` | Update with empty list removes file | File entry gone |
| BP-007 | `test_store_clear_removes_all` | Clear deletes file | File removed |
| BP-008 | `test_store_project_isolation` | Different projects have different files | No cross-contamination |
| BP-009 | `test_store_breakpoint_model_conversion` | SourceBreakpoint model roundtrip | All fields preserved |
| BP-010 | `test_store_conditional_breakpoint` | Conditional breakpoint stored | Condition preserved |
| BP-011 | `test_store_hit_count_breakpoint` | Hit count breakpoint stored | Hit condition preserved |
| BP-012 | `test_store_log_message_breakpoint` | Logpoint stored | Log message preserved |

---

### 2.7 utils/output_buffer.py - Ring Buffer

**Test File:** `tests/unit/test_output_buffer.py`

#### OutputBuffer Tests

| Test Case ID | Test Name | Description | Expected Result |
|--------------|-----------|-------------|-----------------|
| OB-001 | `test_buffer_append_stdout` | Append stdout content | Content stored |
| OB-002 | `test_buffer_append_stderr` | Append stderr content | Category preserved |
| OB-003 | `test_buffer_line_numbers` | Lines have sequential numbers | Numbers increment |
| OB-004 | `test_buffer_timestamps` | Lines have UTC timestamps | Timestamps present |
| OB-005 | `test_buffer_get_page_basic` | Get page returns lines | Lines returned |
| OB-006 | `test_buffer_get_page_offset` | Get page with offset | Correct lines returned |
| OB-007 | `test_buffer_get_page_limit` | Get page with limit | Respects limit |
| OB-008 | `test_buffer_get_page_has_more` | has_more flag correct | True when more exist |
| OB-009 | `test_buffer_filter_by_category` | Filter by stdout/stderr | Only matching category |
| OB-010 | `test_buffer_max_size_enforced` | Buffer respects max size | Oldest dropped |
| OB-011 | `test_buffer_truncated_flag` | Truncated flag set when dropping | Flag is true |
| OB-012 | `test_buffer_dropped_count` | Dropped lines counted | Count accurate |
| OB-013 | `test_buffer_clear_resets_all` | Clear resets counters | All zeros |
| OB-014 | `test_buffer_size_property` | Size property accurate | Matches actual bytes |
| OB-015 | `test_buffer_unicode_content` | Unicode content handled | No encoding errors |
| OB-016 | `test_buffer_50mb_limit` | 50MB default limit | Enforced correctly |

**Edge Cases:**
- Entry larger than max buffer size
- Rapid appends exceeding size
- Unicode with varying byte sizes

---

## 3. Integration Test Specifications

### 3.1 API Endpoint Integration Tests

**Test File:** `tests/integration/test_api_sessions.py`

#### Session API Tests

| Test Case ID | Test Name | Description | Expected Result |
|--------------|-----------|-------------|-----------------|
| API-S-001 | `test_create_session_201` | POST /sessions creates session | 201, session_id returned |
| API-S-002 | `test_create_session_with_config` | POST /sessions with all fields | All config applied |
| API-S-003 | `test_create_session_limit_429` | Exceed max sessions | 429, SESSION_LIMIT_REACHED |
| API-S-004 | `test_list_sessions_empty` | GET /sessions empty | 200, empty items |
| API-S-005 | `test_list_sessions_multiple` | GET /sessions with sessions | 200, all sessions listed |
| API-S-006 | `test_list_sessions_filter_status` | GET /sessions?status=paused | Only paused sessions |
| API-S-007 | `test_get_session_200` | GET /sessions/{id} exists | 200, full session data |
| API-S-008 | `test_get_session_404` | GET /sessions/{id} not found | 404, SESSION_NOT_FOUND |
| API-S-009 | `test_delete_session_200` | DELETE /sessions/{id} | 200, deleted=true |
| API-S-010 | `test_delete_session_404` | DELETE non-existent | 404, SESSION_NOT_FOUND |
| API-S-011 | `test_response_envelope_format` | All responses have envelope | success, data, error, meta |
| API-S-012 | `test_request_id_tracking` | X-Request-ID echoed | Header present in response |

**Test File:** `tests/integration/test_api_breakpoints.py`

#### Breakpoint API Tests

| Test Case ID | Test Name | Description | Expected Result |
|--------------|-----------|-------------|-----------------|
| API-BP-001 | `test_set_breakpoints_200` | POST /sessions/{id}/breakpoints | 200, breakpoints set |
| API-BP-002 | `test_set_breakpoint_verified` | Set on valid line | verified=true |
| API-BP-003 | `test_set_breakpoint_unverified` | Set on comment line | verified=false, message |
| API-BP-004 | `test_set_conditional_breakpoint` | Set with condition | Condition stored |
| API-BP-005 | `test_set_hit_count_breakpoint` | Set with hit_condition | Hit condition stored |
| API-BP-006 | `test_set_logpoint` | Set with log_message | Log message stored |
| API-BP-007 | `test_list_breakpoints` | GET /sessions/{id}/breakpoints | All breakpoints returned |
| API-BP-008 | `test_list_breakpoints_filter_file` | Filter by file path | Only matching file |
| API-BP-009 | `test_list_breakpoints_filter_verified` | Filter by verified | Only matching status |
| API-BP-010 | `test_delete_breakpoint_200` | DELETE breakpoint | 200, deleted=true |
| API-BP-011 | `test_delete_breakpoint_404` | DELETE non-existent | 404, BREAKPOINT_NOT_FOUND |
| API-BP-012 | `test_breakpoint_persistence` | Breakpoints persist across requests | Still present |

**Test File:** `tests/integration/test_api_execution.py`

#### Execution Control API Tests

| Test Case ID | Test Name | Description | Expected Result |
|--------------|-----------|-------------|-----------------|
| API-EX-001 | `test_launch_200` | POST /sessions/{id}/launch | 200, status=running |
| API-EX-002 | `test_launch_with_args` | Launch with arguments | Args passed to script |
| API-EX-003 | `test_launch_with_env` | Launch with env vars | Env vars set |
| API-EX-004 | `test_launch_with_cwd` | Launch with working dir | CWD applied |
| API-EX-005 | `test_launch_stop_on_entry` | Launch with stop_on_entry | Pauses at first line |
| API-EX-006 | `test_launch_module_mode` | Launch with module | Module executed |
| API-EX-007 | `test_launch_invalid_state_409` | Launch when not created | 409, INVALID_SESSION_STATE |
| API-EX-008 | `test_continue_200` | POST /sessions/{id}/continue | 200, status=running |
| API-EX-009 | `test_continue_invalid_state_409` | Continue when running | 409, INVALID_SESSION_STATE |
| API-EX-010 | `test_pause_200` | POST /sessions/{id}/pause | 200, status=paused |
| API-EX-011 | `test_step_over_200` | POST /sessions/{id}/step-over | 200, new location |
| API-EX-012 | `test_step_into_200` | POST /sessions/{id}/step-into | 200, enters function |
| API-EX-013 | `test_step_out_200` | POST /sessions/{id}/step-out | 200, returns to caller |

**Test File:** `tests/integration/test_api_inspection.py`

#### Inspection API Tests

| Test Case ID | Test Name | Description | Expected Result |
|--------------|-----------|-------------|-----------------|
| API-IN-001 | `test_get_threads_200` | GET /sessions/{id}/threads | 200, thread list |
| API-IN-002 | `test_get_stacktrace_200` | GET /sessions/{id}/stacktrace | 200, frame list |
| API-IN-003 | `test_get_stacktrace_with_levels` | Stacktrace with levels param | Respects limit |
| API-IN-004 | `test_get_scopes_200` | GET /sessions/{id}/scopes | 200, scope list |
| API-IN-005 | `test_get_variables_200` | GET /sessions/{id}/variables | 200, variable list |
| API-IN-006 | `test_get_variables_pagination` | Variables with start/count | Paginated correctly |
| API-IN-007 | `test_evaluate_200` | POST /sessions/{id}/evaluate | 200, result returned |
| API-IN-008 | `test_evaluate_error` | Evaluate invalid expression | Error in response |
| API-IN-009 | `test_evaluate_complex_result` | Evaluate returns object | variables_reference set |
| API-IN-010 | `test_inspection_invalid_state_409` | Inspect when running | 409, must be paused |

**Test File:** `tests/integration/test_api_output.py`

#### Output & Events API Tests

| Test Case ID | Test Name | Description | Expected Result |
|--------------|-----------|-------------|-----------------|
| API-OUT-001 | `test_get_output_200` | GET /sessions/{id}/output | 200, entries returned |
| API-OUT-002 | `test_get_output_pagination` | Output with cursor | Continues from cursor |
| API-OUT-003 | `test_get_output_filter_category` | Filter by stdout/stderr | Only matching category |
| API-OUT-004 | `test_get_events_200` | GET /sessions/{id}/events | 200, event list |
| API-OUT-005 | `test_get_events_cursor` | Events with cursor | Continues from cursor |
| API-OUT-006 | `test_get_events_long_poll` | Events with timeout | Waits for events |
| API-OUT-007 | `test_events_include_stopped` | Stopped event captured | Event has details |
| API-OUT-008 | `test_events_include_output` | Output events captured | Text present |
| API-OUT-009 | `test_events_include_terminated` | Terminated event captured | Exit code present |

---

### 3.2 DAP Protocol Integration Tests

**Test File:** `tests/integration/test_dap_integration.py`

#### DAP Communication Tests

| Test Case ID | Test Name | Description | Expected Result |
|--------------|-----------|-------------|-----------------|
| DAP-001 | `test_dap_initialize_handshake` | Full initialize sequence | Capabilities received |
| DAP-002 | `test_dap_launch_and_terminate` | Launch, run, terminate | Clean lifecycle |
| DAP-003 | `test_dap_breakpoint_hit` | Set breakpoint, run, hit | Stopped at breakpoint |
| DAP-004 | `test_dap_step_sequence` | Step over, into, out | All step types work |
| DAP-005 | `test_dap_variable_inspection` | Get scopes and variables | All data returned |
| DAP-006 | `test_dap_expression_evaluation` | Evaluate in context | Correct result |
| DAP-007 | `test_dap_conditional_breakpoint` | Conditional triggers only when true | Skips false conditions |
| DAP-008 | `test_dap_exception_handling` | Exception breakpoint | Stops on exception |
| DAP-009 | `test_dap_multiple_threads` | Multi-threaded debugging | All threads visible |
| DAP-010 | `test_dap_output_capture` | Stdout/stderr captured | Output events received |

---

### 3.3 Persistence Integration Tests

**Test File:** `tests/integration/test_persistence_integration.py`

#### Persistence Integration

| Test Case ID | Test Name | Description | Expected Result |
|--------------|-----------|-------------|-----------------|
| PERS-001 | `test_breakpoints_persist_across_restart` | Save, restart, load | Breakpoints restored |
| PERS-002 | `test_breakpoints_per_project_isolation` | Multiple projects | Each has own breakpoints |
| PERS-003 | `test_invalid_persistence_graceful` | Corrupted file | Starts fresh |
| PERS-004 | `test_concurrent_persistence_ops` | Multiple sessions saving | No conflicts |
| PERS-005 | `test_persistence_directory_creation` | Directory doesn't exist | Created automatically |

---

### 3.4 Session Lifecycle Integration Tests

**Test File:** `tests/integration/test_session_lifecycle.py`

#### Full Session Lifecycle

| Test Case ID | Test Name | Description | Expected Result |
|--------------|-----------|-------------|-----------------|
| SL-001 | `test_complete_session_lifecycle` | Create→Launch→Debug→Terminate→Delete | Clean workflow |
| SL-002 | `test_session_timeout_cleanup` | Session times out | Auto-terminated |
| SL-003 | `test_session_max_lifetime` | Session exceeds max lifetime | Auto-terminated |
| SL-004 | `test_session_activity_resets_timeout` | Activity resets idle timer | Session preserved |
| SL-005 | `test_multiple_sessions_concurrent` | 5 concurrent sessions | All work independently |
| SL-006 | `test_session_recovery_after_crash` | Session state preserved | Can resume |

---

## 4. End-to-End Test Scenarios

### 4.1 Basic Debug Session (User Story 3.1)

**Test File:** `tests/e2e/test_basic_debug_session.py`

```python
@pytest.mark.e2e
async def test_basic_debug_session_flow():
    """
    Test complete basic debug workflow from User Story 3.1:
    Start Session → Set Breakpoints → Launch Script → Hit Breakpoint →
    Inspect State → Step Through → Continue → Session Ends
    """
    # Steps from User Story Table 3.1
```

| Step | Action | Verification |
|------|--------|--------------|
| 1 | Create debug session | session_id returned, status=created |
| 2 | Set breakpoint | verified=true |
| 3 | Launch script | status=running |
| 4 | Poll for pause | status=paused, reason=breakpoint |
| 5 | Get stack trace | frames returned with location |
| 6 | Get variables | variables with values |
| 7 | Evaluate expression | result matches expected |
| 8 | Step over | new location (line +1) |
| 9 | Continue | status=running |
| 10 | Check completion | status=terminated, exit_code=0 |
| 11 | Clean up | deleted=true |

---

### 4.2 Conditional Breakpoint Debugging (User Story 3.5)

**Test File:** `tests/e2e/test_conditional_breakpoint.py`

```python
@pytest.mark.e2e
async def test_conditional_breakpoint_debugging():
    """
    Test conditional breakpoint workflow from User Story 3.5:
    Set breakpoint with condition i > 100 in a loop
    """
```

| Step | Action | Verification |
|------|--------|--------------|
| 1 | Create session | session_id returned |
| 2 | Set conditional breakpoint | condition stored |
| 3 | Launch script with loop | status=running |
| 4 | Wait for breakpoint | status=paused |
| 5 | Verify condition | variable i > 100 |
| 6 | Set hit count breakpoint | hit_condition stored |
| 7 | Continue and verify | Stops at correct iteration |

---

### 4.3 Exception Debugging (User Story 3.6)

**Test File:** `tests/e2e/test_exception_debugging.py`

```python
@pytest.mark.e2e
async def test_exception_debugging():
    """
    Test exception debugging from User Story 3.6:
    Launch → Script Raises Exception → Capture State → Inspect → Terminate
    """
```

| Step | Action | Verification |
|------|--------|--------------|
| 1 | Create session | session_id returned |
| 2 | Launch with stop_on_exception=true | status=running |
| 3 | Wait for exception | status=paused, reason=exception |
| 4 | Verify exception details | type, message, location present |
| 5 | Get stack trace | Shows exception location |
| 6 | Inspect variables | Values at crash point |
| 7 | Evaluate cause | Can inspect problematic values |
| 8 | Clean up | Session terminated |

---

### 4.4 Multi-File Debugging

**Test File:** `tests/e2e/test_multi_file_debugging.py`

```python
@pytest.mark.e2e
async def test_multi_file_debugging():
    """
    Test debugging across multiple files in a project
    """
```

| Step | Action | Verification |
|------|--------|--------------|
| 1 | Create session with project_root | Project configured |
| 2 | Set breakpoints in 3 files | All verified |
| 3 | Launch main.py | status=running |
| 4 | Hit breakpoint in main.py | Location correct |
| 5 | Step into imported module | Different file in stack |
| 6 | Continue to next breakpoint | In another file |
| 7 | Stack trace shows all files | Multiple sources |

---

### 4.5 Concurrent Sessions

**Test File:** `tests/e2e/test_concurrent_sessions.py`

```python
@pytest.mark.e2e
async def test_concurrent_sessions():
    """
    Test running up to 10 concurrent debug sessions
    """
```

| Step | Action | Verification |
|------|--------|--------------|
| 1 | Create 10 sessions | All created successfully |
| 2 | Set breakpoints in each | All verified |
| 3 | Launch all scripts | All running |
| 4 | Poll all for breakpoints | All pause independently |
| 5 | Operate on each | No cross-contamination |
| 6 | Try to create 11th | SESSION_LIMIT_REACHED |
| 7 | Delete one, create new | Works after deletion |
| 8 | Clean up all | All terminated |

---

## 5. Edge Case Test Scenarios

### 5.1 Syntax Errors in Target Script (User Story 4.1)

**Test File:** `tests/edge_cases/test_syntax_errors.py`

| Test Case ID | Scenario | Expected Behavior |
|--------------|----------|-------------------|
| EC-SYN-001 | Launch script with syntax error | LAUNCH_SYNTAX_ERROR with file, line, offset |
| EC-SYN-002 | Session state after syntax error | Remains in "created" state |
| EC-SYN-003 | Can retry launch after fix | Launches successfully |
| EC-SYN-004 | Syntax error in imported module | Error includes correct file |

---

### 5.2 Breakpoint in Non-Existent File (User Story 4.2)

**Test File:** `tests/edge_cases/test_missing_files.py`

| Test Case ID | Scenario | Expected Behavior |
|--------------|----------|-------------------|
| EC-MIS-001 | Set breakpoint in missing file | verified=false, message="Source file not found" |
| EC-MIS-002 | Breakpoint ID still assigned | bp_id returned |
| EC-MIS-003 | List shows unverified breakpoint | Status is unverified |
| EC-MIS-004 | Delete unverified breakpoint | Removes successfully |

---

### 5.3 Multiple Threads Hitting Breakpoints (User Story 4.3)

**Test File:** `tests/edge_cases/test_threading.py`

| Test Case ID | Scenario | Expected Behavior |
|--------------|----------|-------------------|
| EC-THR-001 | Two threads hit breakpoints | Both threads paused |
| EC-THR-002 | Get threads shows all stopped | All threads in paused state |
| EC-THR-003 | Stack trace per thread | Different stacks returned |
| EC-THR-004 | Continue one thread | Only that thread continues |
| EC-THR-005 | All threads stopped flag | all_threads_stopped=true |

---

### 5.4 Long-Running Scripts (User Story 4.4)

**Test File:** `tests/edge_cases/test_long_running.py`

| Test Case ID | Scenario | Expected Behavior |
|--------------|----------|-------------------|
| EC-LRS-001 | Script runs for extended period | Session stays active with activity |
| EC-LRS-002 | Breakpoint set while running | Breakpoint takes effect |
| EC-LRS-003 | Pause on running script | Pauses within 1 second |
| EC-LRS-004 | Output pagination works | Can retrieve incremental output |
| EC-LRS-005 | Activity resets timeout | Session not expired |

---

### 5.5 Large Variable Inspection (User Story 4.7)

**Test File:** `tests/edge_cases/test_large_variables.py`

| Test Case ID | Scenario | Expected Behavior |
|--------------|----------|-------------------|
| EC-LRG-001 | Inspect list with 1M items | Truncated display, expandable |
| EC-LRG-002 | Paginate large list | start/count work correctly |
| EC-LRG-003 | Large dict inspection | Keys are expandable |
| EC-LRG-004 | Deep nested object | Can traverse via references |
| EC-LRG-005 | Long string value | Value truncated with indicator |
| EC-LRG-006 | Large DataFrame | Summary view with shape |

---

### 5.6 Circular References (User Story 4.8)

**Test File:** `tests/edge_cases/test_circular_references.py`

| Test Case ID | Scenario | Expected Behavior |
|--------------|----------|-------------------|
| EC-CIR-001 | Object references itself | circular=true flag set |
| EC-CIR-002 | Parent-child circular | "<circular: parent>" displayed |
| EC-CIR-003 | Graph with cycles | Cycles detected and marked |
| EC-CIR-004 | Can still navigate | variable_reference allows traversal |
| EC-CIR-005 | No infinite loops | Response returns in reasonable time |

---

### 5.7 50MB Output Buffer Overflow

**Test File:** `tests/edge_cases/test_output_overflow.py`

| Test Case ID | Scenario | Expected Behavior |
|--------------|----------|-------------------|
| EC-OUT-001 | Output exceeds 50MB | Oldest output dropped |
| EC-OUT-002 | Truncated flag set | truncated=true in response |
| EC-OUT-003 | Most recent preserved | Latest output accessible |
| EC-OUT-004 | Line numbers continuous | No gaps in visible range |
| EC-OUT-005 | Dropped count accurate | Count matches actual drops |

---

### 5.8 Invalid Operations

**Test File:** `tests/edge_cases/test_invalid_operations.py`

| Test Case ID | Scenario | Expected Behavior |
|--------------|----------|-------------------|
| EC-INV-001 | Launch twice | INVALID_SESSION_STATE |
| EC-INV-002 | Step when running | INVALID_SESSION_STATE |
| EC-INV-003 | Continue when not paused | INVALID_SESSION_STATE |
| EC-INV-004 | Get variables when running | INVALID_SESSION_STATE |
| EC-INV-005 | Invalid frame_id | FRAME_NOT_FOUND |
| EC-INV-006 | Invalid variables_reference | VARIABLE_NOT_FOUND |
| EC-INV-007 | Invalid thread_id | THREAD_NOT_FOUND |

---

## 6. Performance Tests

### 6.1 Latency Tests

**Test File:** `tests/performance/test_latency.py`

| Test Case ID | Metric | Target | Test Description |
|--------------|--------|--------|------------------|
| PERF-LAT-001 | Session creation latency | <500ms | Time from POST to session ready |
| PERF-LAT-002 | Breakpoint set latency | <100ms | Time to set and verify breakpoint |
| PERF-LAT-003 | Step operation latency | <200ms | Time for step-over/into/out |
| PERF-LAT-004 | Variable inspection latency | <300ms | Time to retrieve scope variables |
| PERF-LAT-005 | Expression evaluation latency | <500ms | Time to evaluate simple expression |
| PERF-LAT-006 | Status polling latency | <50ms | Time for status endpoint response |
| PERF-LAT-007 | Output retrieval latency | <100ms | Time to get output page |
| PERF-LAT-008 | Event polling latency | <50ms | Time for events endpoint |

**Implementation:**

```python
@pytest.mark.performance
async def test_session_creation_latency(benchmark):
    """Session creation should complete within 500ms."""
    async def create_session():
        response = await client.post("/sessions", json={})
        return response

    result = await benchmark.pedantic(create_session, rounds=10)
    assert result.stats.mean < 0.5  # 500ms
```

---

### 6.2 Throughput Tests

**Test File:** `tests/performance/test_throughput.py`

| Test Case ID | Metric | Target | Test Description |
|--------------|--------|--------|------------------|
| PERF-THR-001 | Concurrent sessions | 10 | Support 10 simultaneous sessions |
| PERF-THR-002 | Breakpoints per session | 100 | Set 100 breakpoints |
| PERF-THR-003 | Steps per second | 10 | 10 step operations per second |
| PERF-THR-004 | Events per second | 100 | Handle 100 events/second |
| PERF-THR-005 | Output lines per second | 1000 | Buffer 1000 lines/second |

---

### 6.3 Stress Tests

**Test File:** `tests/performance/test_stress.py`

| Test Case ID | Scenario | Pass Criteria |
|--------------|----------|---------------|
| PERF-STR-001 | Max sessions at once | All 10 function correctly |
| PERF-STR-002 | Rapid session create/delete | No resource leaks |
| PERF-STR-003 | Output flood (1MB/s) | Buffer handles without crash |
| PERF-STR-004 | Rapid step operations | All complete successfully |
| PERF-STR-005 | Many breakpoints (500+) | All verified correctly |

---

### 6.4 Memory Tests

**Test File:** `tests/performance/test_memory.py`

| Test Case ID | Scenario | Pass Criteria |
|--------------|----------|---------------|
| PERF-MEM-001 | Output buffer 50MB limit | Stays at limit, no growth |
| PERF-MEM-002 | Session cleanup | Memory released after delete |
| PERF-MEM-003 | Long-running session | Memory stable over time |
| PERF-MEM-004 | Event queue limit | Queue doesn't grow unbounded |

---

## 7. Error Handling Tests

### 7.1 Session Error Codes

**Test File:** `tests/errors/test_session_errors.py`

| Error Code | HTTP Status | Test Case |
|------------|-------------|-----------|
| `SESSION_NOT_FOUND` | 404 | Get/delete non-existent session |
| `SESSION_LIMIT_REACHED` | 429 | Create 11th session |
| `SESSION_EXPIRED` | 410 | Access expired session |
| `INVALID_SESSION_STATE` | 409 | Invalid operation for state |

---

### 7.2 Breakpoint Error Codes

**Test File:** `tests/errors/test_breakpoint_errors.py`

| Error Code | HTTP Status | Test Case |
|------------|-------------|-----------|
| `BREAKPOINT_NOT_FOUND` | 404 | Delete non-existent breakpoint |
| `BREAKPOINT_INVALID_LINE` | 400 | Set on whitespace/comment |
| `BREAKPOINT_INVALID_CONDITION` | 400 | Syntax error in condition |
| `BREAKPOINT_FILE_NOT_FOUND` | 400 | Set in non-existent file |

---

### 7.3 DAP Error Codes

**Test File:** `tests/errors/test_dap_errors.py`

| Error Code | HTTP Status | Test Case |
|------------|-------------|-----------|
| `DEBUGPY_TIMEOUT` | 504 | debugpy operation times out |
| `DEBUGPY_ERROR` | 500 | Internal debugpy error |
| `LAUNCH_FAILED` | 500 | Failed to start debuggee |
| `LAUNCH_SCRIPT_NOT_FOUND` | 400 | Script file doesn't exist |
| `LAUNCH_SYNTAX_ERROR` | 400 | Python syntax error |
| `ATTACH_FAILED` | 500 | Failed to attach |
| `ATTACH_TIMEOUT` | 504 | Attach connection timeout |
| `ATTACH_REFUSED` | 502 | Target refused connection |

---

### 7.4 Reference Error Codes

**Test File:** `tests/errors/test_reference_errors.py`

| Error Code | HTTP Status | Test Case |
|------------|-------------|-----------|
| `THREAD_NOT_FOUND` | 404 | Invalid thread_id |
| `FRAME_NOT_FOUND` | 404 | Invalid frame_id |
| `VARIABLE_NOT_FOUND` | 404 | Invalid variables_reference |

---

### 7.5 Request Error Codes

**Test File:** `tests/errors/test_request_errors.py`

| Error Code | HTTP Status | Test Case |
|------------|-------------|-----------|
| `INVALID_REQUEST` | 400 | Malformed JSON body |
| `MISSING_PARAMETER` | 400 | Required field missing |
| `INVALID_PARAMETER` | 400 | Invalid field value |
| `EVALUATE_ERROR` | 400 | Expression evaluation failed |

---

### 7.6 Error Response Format Verification

**Test File:** `tests/errors/test_error_format.py`

```python
@pytest.mark.parametrize("error_scenario", ALL_ERROR_SCENARIOS)
async def test_error_response_format(error_scenario):
    """All errors follow standard format with code, message, details."""
    response = await trigger_error(error_scenario)

    assert response.json()["success"] == False
    assert response.json()["data"] is None
    assert "code" in response.json()["error"]
    assert "message" in response.json()["error"]
    assert "details" in response.json()["error"]
    assert "request_id" in response.json()["meta"]
    assert "timestamp" in response.json()["meta"]
```

---

## 8. Test Fixtures

### 8.1 Sample Python Scripts

**Location:** `tests/fixtures/scripts/`

#### simple_script.py
```python
"""Simple script for basic debugging tests."""

def main():
    x = 10
    y = 20
    result = x + y
    print(f"Result: {result}")
    return result

if __name__ == "__main__":
    main()
```

#### loop_script.py
```python
"""Script with loop for conditional breakpoint tests."""

def process_items():
    items = []
    for i in range(200):
        items.append(i * 2)
        print(f"Processing {i}")
    return items

if __name__ == "__main__":
    process_items()
```

#### exception_script.py
```python
"""Script that raises an exception."""

def problematic_function():
    data = "not_a_number"
    return int(data)  # Raises ValueError

def main():
    try:
        result = problematic_function()
    except ValueError:
        raise  # Re-raise for debugging

if __name__ == "__main__":
    main()
```

#### threading_script.py
```python
"""Multi-threaded script for threading tests."""
import threading
import time

def worker(name, delay):
    print(f"{name} starting")
    time.sleep(delay)
    x = 42  # Breakpoint target
    print(f"{name} done: {x}")

def main():
    threads = [
        threading.Thread(target=worker, args=("Worker-1", 0.1)),
        threading.Thread(target=worker, args=("Worker-2", 0.2)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
```

#### large_output_script.py
```python
"""Script that generates large output."""

def main():
    for i in range(100000):
        print(f"Line {i}: " + "x" * 100)

if __name__ == "__main__":
    main()
```

#### multi_file/main.py
```python
"""Main entry point for multi-file tests."""
from utils.helpers import helper_function
from models.data import DataModel

def main():
    data = DataModel(value=42)
    result = helper_function(data)
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
```

#### multi_file/utils/helpers.py
```python
"""Helper utilities."""

def helper_function(data):
    intermediate = data.value * 2
    return process(intermediate)

def process(value):
    return value + 10
```

#### multi_file/models/data.py
```python
"""Data models."""
from dataclasses import dataclass

@dataclass
class DataModel:
    value: int

    def double(self):
        return self.value * 2
```

#### circular_reference_script.py
```python
"""Script with circular references."""

class Node:
    def __init__(self, name):
        self.name = name
        self.parent = None
        self.children = []

    def add_child(self, child):
        self.children.append(child)
        child.parent = self

def main():
    root = Node("root")
    child1 = Node("child1")
    child2 = Node("child2")
    root.add_child(child1)
    root.add_child(child2)
    x = 1  # Breakpoint here to inspect

if __name__ == "__main__":
    main()
```

#### large_variable_script.py
```python
"""Script with large data structures."""

def main():
    large_list = list(range(1000000))
    large_dict = {f"key_{i}": i * 2 for i in range(10000)}
    nested = {"level1": {"level2": {"level3": {"data": large_list[:100]}}}}
    x = 1  # Breakpoint here

if __name__ == "__main__":
    main()
```

#### syntax_error_script.py
```python
"""Script with intentional syntax error."""

def main():
    x = 10
    if x == 10  # Missing colon
        print("ten")

if __name__ == "__main__":
    main()
```

---

### 8.2 Mock DAP Responses

**Location:** `tests/fixtures/dap/`

#### initialize_response.json
```json
{
  "seq": 1,
  "type": "response",
  "request_seq": 1,
  "success": true,
  "command": "initialize",
  "body": {
    "supportsConfigurationDoneRequest": true,
    "supportsConditionalBreakpoints": true,
    "supportsHitConditionalBreakpoints": true,
    "supportsLogPoints": true,
    "supportsSetVariable": false,
    "supportsStepInTargetsRequest": false,
    "supportsEvaluateForHovers": true,
    "exceptionBreakpointFilters": [
      {"filter": "raised", "label": "Raised Exceptions"},
      {"filter": "uncaught", "label": "Uncaught Exceptions"}
    ]
  }
}
```

#### stopped_breakpoint_event.json
```json
{
  "seq": 10,
  "type": "event",
  "event": "stopped",
  "body": {
    "reason": "breakpoint",
    "description": "Paused on breakpoint",
    "threadId": 1,
    "preserveFocusHint": false,
    "allThreadsStopped": true,
    "hitBreakpointIds": [1]
  }
}
```

#### stack_trace_response.json
```json
{
  "seq": 5,
  "type": "response",
  "request_seq": 5,
  "success": true,
  "command": "stackTrace",
  "body": {
    "stackFrames": [
      {
        "id": 0,
        "name": "main",
        "source": {"path": "/test/script.py", "name": "script.py"},
        "line": 10,
        "column": 0
      },
      {
        "id": 1,
        "name": "<module>",
        "source": {"path": "/test/script.py", "name": "script.py"},
        "line": 15,
        "column": 0
      }
    ],
    "totalFrames": 2
  }
}
```

#### variables_response.json
```json
{
  "seq": 7,
  "type": "response",
  "request_seq": 7,
  "success": true,
  "command": "variables",
  "body": {
    "variables": [
      {
        "name": "x",
        "value": "10",
        "type": "int",
        "variablesReference": 0
      },
      {
        "name": "y",
        "value": "20",
        "type": "int",
        "variablesReference": 0
      },
      {
        "name": "items",
        "value": "[1, 2, 3, ...]",
        "type": "list",
        "variablesReference": 1001,
        "indexedVariables": 100
      }
    ]
  }
}
```

---

### 8.3 Test Project Structures

**Location:** `tests/fixtures/projects/`

```
projects/
├── simple/
│   ├── main.py
│   └── README.md
├── multi_file/
│   ├── main.py
│   ├── utils/
│   │   ├── __init__.py
│   │   └── helpers.py
│   └── models/
│       ├── __init__.py
│       └── data.py
├── with_venv/
│   ├── main.py
│   └── requirements.txt
└── with_config/
    ├── main.py
    ├── config.json
    └── .env.example
```

---

### 8.4 Pytest Fixtures

**Location:** `tests/conftest.py`

```python
"""Shared pytest fixtures for all tests."""

import asyncio
import tempfile
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from opencode_debugger.main import create_app
from opencode_debugger.config import Settings
from opencode_debugger.core.session import SessionManager
from opencode_debugger.persistence.breakpoints import BreakpointStore


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_data_dir(tmp_path) -> Path:
    """Create temporary data directory."""
    return tmp_path / "opencode-debugger"


@pytest.fixture
def test_settings(temp_data_dir) -> Settings:
    """Create test settings with temp directory."""
    return Settings(
        host="127.0.0.1",
        port=5679,
        data_dir=temp_data_dir,
        max_sessions=10,
        session_timeout_seconds=60,
        output_buffer_max_bytes=1024 * 1024,  # 1MB for tests
    )


@pytest_asyncio.fixture
async def app(test_settings):
    """Create test application."""
    application = create_app(test_settings)
    yield application


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test/api/v1"
    ) as client:
        yield client


@pytest_asyncio.fixture
async def session_manager(test_settings) -> AsyncGenerator[SessionManager, None]:
    """Create session manager for unit tests."""
    store = BreakpointStore(base_dir=test_settings.breakpoints_dir)
    manager = SessionManager(breakpoint_store=store)
    await manager.start()
    yield manager
    await manager.stop()


@pytest.fixture
def sample_scripts_dir() -> Path:
    """Path to sample test scripts."""
    return Path(__file__).parent / "fixtures" / "scripts"


@pytest.fixture
def simple_script(sample_scripts_dir) -> Path:
    """Path to simple test script."""
    return sample_scripts_dir / "simple_script.py"


@pytest.fixture
def loop_script(sample_scripts_dir) -> Path:
    """Path to loop test script."""
    return sample_scripts_dir / "loop_script.py"


@pytest.fixture
def exception_script(sample_scripts_dir) -> Path:
    """Path to exception test script."""
    return sample_scripts_dir / "exception_script.py"


@pytest.fixture
def threading_script(sample_scripts_dir) -> Path:
    """Path to threading test script."""
    return sample_scripts_dir / "threading_script.py"


@pytest.fixture
def multi_file_project(sample_scripts_dir) -> Path:
    """Path to multi-file test project."""
    return sample_scripts_dir / "multi_file"


# Factory fixtures for test data generation
@pytest.fixture
def breakpoint_factory():
    """Factory for creating test breakpoints."""
    def _factory(file_path: str = "/test/script.py", line: int = 10, **kwargs):
        return {
            "source": {"path": file_path},
            "line": line,
            **kwargs
        }
    return _factory


@pytest.fixture
def session_config_factory():
    """Factory for creating session configs."""
    def _factory(name: str = None, project_root: str = "/test/project", **kwargs):
        config = {"project_root": project_root}
        if name:
            config["name"] = name
        config.update(kwargs)
        return config
    return _factory


@pytest.fixture
def launch_config_factory():
    """Factory for creating launch configs."""
    def _factory(script: str = "/test/script.py", **kwargs):
        return {"script": script, **kwargs}
    return _factory
```

---

## 9. CI/CD Integration

### 9.1 pytest Configuration

**File:** `pyproject.toml`

```toml
[tool.pytest.ini_options]
minversion = "8.0"
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

# Markers
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "performance: Performance tests",
    "slow: Slow tests (>10s)",
]

# Async configuration
asyncio_default_fixture_loop_scope = "function"

# Timeout
timeout = 60
timeout_method = "thread"

# Coverage
addopts = [
    "--strict-markers",
    "-ra",
    "--cov=src/opencode_debugger",
    "--cov-report=term-missing",
    "--cov-report=xml",
    "--cov-report=html:htmlcov",
    "--cov-fail-under=90",
]

# Filter warnings
filterwarnings = [
    "error",
    "ignore::DeprecationWarning",
]
```

### 9.2 Coverage Configuration

**File:** `.coveragerc`

```ini
[run]
source = src/opencode_debugger
branch = True
parallel = True
omit =
    */tests/*
    */__pycache__/*
    */migrations/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
    @abstractmethod

fail_under = 90
show_missing = True
precision = 2

[html]
directory = htmlcov
title = OpenCode Debug Relay Coverage Report
```

### 9.3 GitHub Actions Workflow

**File:** `.github/workflows/test.yml`

```yaml
name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

env:
  PYTHON_VERSION: "3.11"

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          pip install ruff mypy
          pip install -e ".[dev]"

      - name: Run ruff
        run: ruff check src tests

      - name: Run mypy
        run: mypy src

  unit-tests:
    name: Unit Tests
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install -e ".[dev,test]"

      - name: Run unit tests
        run: |
          pytest tests/unit -v --cov --cov-report=xml -m "not slow"

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: coverage.xml
          flags: unit
          fail_ci_if_error: true

  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: unit-tests

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          pip install -e ".[dev,test]"

      - name: Run integration tests
        run: |
          pytest tests/integration -v --cov --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: coverage.xml
          flags: integration

  e2e-tests:
    name: E2E Tests
    runs-on: ubuntu-latest
    needs: integration-tests

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          pip install -e ".[dev,test]"

      - name: Run E2E tests
        run: |
          pytest tests/e2e -v --timeout=300
        timeout-minutes: 10

  performance-tests:
    name: Performance Tests
    runs-on: ubuntu-latest
    needs: integration-tests

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          pip install -e ".[dev,test]"
          pip install pytest-benchmark

      - name: Run performance tests
        run: |
          pytest tests/performance -v --benchmark-json=benchmark.json

      - name: Upload benchmark results
        uses: actions/upload-artifact@v3
        with:
          name: benchmark-results
          path: benchmark.json

  edge-case-tests:
    name: Edge Case Tests
    runs-on: ubuntu-latest
    needs: unit-tests

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          pip install -e ".[dev,test]"

      - name: Run edge case tests
        run: |
          pytest tests/edge_cases -v

  error-handling-tests:
    name: Error Handling Tests
    runs-on: ubuntu-latest
    needs: unit-tests

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          pip install -e ".[dev,test]"

      - name: Run error handling tests
        run: |
          pytest tests/errors -v

  coverage-report:
    name: Coverage Report
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          pip install -e ".[dev,test]"

      - name: Run all tests with coverage
        run: |
          pytest tests --cov --cov-report=xml --cov-report=html

      - name: Check coverage threshold
        run: |
          coverage report --fail-under=90

      - name: Upload coverage report
        uses: actions/upload-artifact@v3
        with:
          name: coverage-report
          path: htmlcov/
```

### 9.4 Test Commands

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit -v

# Run integration tests only
pytest tests/integration -v

# Run E2E tests only
pytest tests/e2e -v

# Run with coverage report
pytest --cov --cov-report=html

# Run specific test file
pytest tests/unit/test_session.py -v

# Run specific test case
pytest tests/unit/test_session.py::test_session_creation_basic -v

# Run tests matching pattern
pytest -k "breakpoint" -v

# Run tests with markers
pytest -m "unit and not slow" -v

# Run performance tests with benchmarking
pytest tests/performance --benchmark-only

# Run with parallel execution
pytest -n auto

# Run with verbose output and print
pytest -v -s

# Generate coverage XML for CI
pytest --cov --cov-report=xml

# Check coverage threshold
pytest --cov --cov-fail-under=90
```

### 9.5 Pre-commit Hooks

**File:** `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, fastapi]
        args: [--ignore-missing-imports]

  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: pytest tests/unit -x -q --no-cov
        language: system
        pass_filenames: false
        always_run: true
```

---

## Appendix A: Test Naming Conventions

### Test File Naming
- Unit tests: `test_{module_name}.py`
- Integration tests: `test_{feature}_integration.py`
- E2E tests: `test_{scenario}.py`
- Performance tests: `test_{metric}.py`

### Test Function Naming
- Format: `test_{what}_{condition}_{expected}`
- Examples:
  - `test_session_creation_basic`
  - `test_breakpoint_set_verified_true`
  - `test_launch_invalid_state_raises_409`

### Test Class Naming
- Format: `Test{Component}`
- Examples:
  - `TestSession`
  - `TestBreakpointAPI`
  - `TestDAPClient`

---

## Appendix B: Test Priority Matrix

| Priority | Test Category | CI Stage | Blocking |
|----------|---------------|----------|----------|
| P0 | Unit tests | Every commit | Yes |
| P0 | API contract tests | Every commit | Yes |
| P1 | Integration tests | Every PR | Yes |
| P1 | Error handling tests | Every PR | Yes |
| P2 | E2E tests | Merge to main | No |
| P2 | Performance tests | Nightly | No |
| P3 | Stress tests | Weekly | No |

---

## Appendix C: Test Data Requirements

| Data Type | Size | Location | Refresh |
|-----------|------|----------|---------|
| Sample scripts | <1KB each | `fixtures/scripts/` | Version controlled |
| Mock DAP responses | <5KB each | `fixtures/dap/` | Version controlled |
| Test projects | <100KB | `fixtures/projects/` | Version controlled |
| Generated data | Runtime | In-memory | Per test |
| Coverage data | ~10MB | `.coverage`, `htmlcov/` | Per run |

---

**Document Revision History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-13 | QA Expert Agent | Initial comprehensive test plan |
