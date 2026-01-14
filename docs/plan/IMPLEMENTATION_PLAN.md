# OpenCode Debug Relay Server - Implementation Plan

**Version:** 1.0
**Date:** January 13, 2026
**Status:** Ready for Implementation

---

## Executive Summary

This document compiles the complete implementation plan for the **OpenCode Debug Relay Server** - an HTTP relay that enables AI coding agents to perform full interactive debugging of Python applications via the debugpy/DAP protocol.

### Quick Links

| Document | Description |
|----------|-------------|
| [USER_STORY.md](../USER_STORY.md) | Product requirements and acceptance criteria |
| [LLD_BACKEND.md](./LLD_BACKEND.md) | Backend implementation specification |
| [LLD_API.md](./LLD_API.md) | API contract specification |
| [LLD_REVIEW.md](./LLD_REVIEW.md) | Architecture review and alignment |
| [TEST_PLAN.md](./TEST_PLAN.md) | Test strategy and test cases |
| [TEST_AUTOMATION.md](./TEST_AUTOMATION.md) | Pytest implementations and CI/CD |

---

## 1. Feature Overview

### Problem
AI coding agents cannot use interactive debuggers like pdb because they require bidirectional stdin/stdout. Agents execute discrete commands, making traditional debugging impossible.

### Solution
An HTTP relay server that:
- Exposes debugpy functionality via REST API
- Manages debug sessions with state persistence
- Enables full debugging through polling-based interaction

### Key Capabilities
- Set breakpoints (conditional, hit count, logpoints)
- Step through code (over, into, out)
- Inspect variables and evaluate expressions
- Capture stdout/stderr output
- Debug multi-file Python projects

---

## 2. Architecture Summary

```
┌─────────────┐     HTTP/JSON      ┌─────────────────┐     DAP      ┌──────────┐
│  AI Agent   │ <----------------> │  Debug Relay    │ <----------> │  debugpy │
│  (Claude)   │                    │  Server         │              │          │
└─────────────┘                    └─────────────────┘              └──────────┘
                                          │                              │
                                          v                              v
                                   ┌──────────────┐              ┌──────────┐
                                   │  Persistence │              │  Target  │
                                   │  (JSON)      │              │  Script  │
                                   └──────────────┘              └──────────┘
```

### Core Components

| Component | Responsibility |
|-----------|---------------|
| **HTTP API Layer** | FastAPI routes, validation, responses |
| **Session Manager** | Lifecycle, max 10 concurrent, cleanup |
| **Debug Adapter** | debugpy/DAP integration |
| **Breakpoint Manager** | Per-project persistence |
| **Output Buffer** | 50MB ring buffer |
| **Persistence Layer** | Atomic JSON file operations |

### Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| HTTP Server | FastAPI | >=0.109.0 |
| ASGI Server | uvicorn | >=0.27.0 |
| Debug Backend | debugpy | >=1.8.0 |
| Validation | Pydantic | >=2.5.0 |
| Async Files | aiofiles | >=23.2.0 |
| Python | CPython | >=3.9 |

---

## 3. Implementation Phases

### Phase 1: Project Foundation (Days 1-2)

| Task | Priority | Effort |
|------|----------|--------|
| Create project structure | P0 | 2h |
| Setup pyproject.toml with dependencies | P0 | 1h |
| Implement config.py (Settings) | P0 | 1h |
| Implement core/exceptions.py | P0 | 2h |
| Implement all models (models/*.py) | P0 | 4h |
| Setup pytest with conftest.py | P0 | 2h |

**Deliverable:** Project skeleton with all models and exceptions defined.

### Phase 2: Core Infrastructure (Days 3-5)

| Task | Priority | Effort |
|------|----------|--------|
| Implement utils/output_buffer.py | P0 | 2h |
| Implement persistence/storage.py | P0 | 3h |
| Implement persistence/breakpoints.py | P0 | 2h |
| Implement adapters/dap_client.py | P0 | 6h |
| Implement adapters/debugpy_adapter.py | P0 | 6h |
| Unit tests for all infrastructure | P0 | 4h |

**Deliverable:** Working DAP client that can communicate with debugpy.

### Phase 3: Session Management (Days 6-7)

| Task | Priority | Effort |
|------|----------|--------|
| Implement core/events.py | P0 | 2h |
| Implement core/session.py (Session class) | P0 | 4h |
| Implement core/session.py (SessionManager) | P0 | 4h |
| Unit tests for session management | P0 | 3h |
| Integration tests for session lifecycle | P1 | 3h |

**Deliverable:** Complete session management with lifecycle handling.

### Phase 4: API Layer (Days 8-10)

| Task | Priority | Effort |
|------|----------|--------|
| Implement api/server.py (health/info) | P0 | 1h |
| Implement api/sessions.py | P0 | 4h |
| Implement api/breakpoints.py | P0 | 3h |
| Implement api/execution.py | P0 | 3h |
| Implement api/inspection.py | P0 | 4h |
| Implement api/output.py | P0 | 2h |
| Implement api/router.py | P0 | 1h |
| Implement main.py | P0 | 2h |
| API integration tests | P0 | 6h |

**Deliverable:** Complete working API with all endpoints.

### Phase 5: End-to-End Testing (Days 11-12)

| Task | Priority | Effort |
|------|----------|--------|
| E2E test: Basic debug session | P0 | 4h |
| E2E test: Conditional breakpoints | P0 | 3h |
| E2E test: Exception debugging | P0 | 2h |
| E2E test: Multi-file debugging | P0 | 3h |
| E2E test: Concurrent sessions | P1 | 3h |
| Edge case testing | P1 | 4h |
| Performance testing | P2 | 3h |

**Deliverable:** Fully tested system with >90% coverage.

### Phase 6: Polish & Documentation (Days 13-14)

| Task | Priority | Effort |
|------|----------|--------|
| Session recovery implementation | P1 | 6h |
| Error message improvements | P1 | 2h |
| Logging and observability | P1 | 3h |
| README.md | P1 | 2h |
| OpenAPI spec generation | P2 | 1h |
| Example client scripts | P2 | 2h |

**Deliverable:** Production-ready release.

---

## 4. Project Structure

```
opencode_debugger/
├── src/
│   └── opencode_debugger/
│       ├── __init__.py
│       ├── main.py              # FastAPI app entry point
│       ├── config.py            # Pydantic settings
│       ├── api/
│       │   ├── __init__.py
│       │   ├── router.py        # Router aggregation
│       │   ├── sessions.py      # Session endpoints
│       │   ├── breakpoints.py   # Breakpoint endpoints
│       │   ├── execution.py     # Step/continue endpoints
│       │   ├── inspection.py    # Variables/stack endpoints
│       │   ├── output.py        # Output/events endpoints
│       │   └── server.py        # Health/info endpoints
│       ├── core/
│       │   ├── __init__.py
│       │   ├── session.py       # Session, SessionManager
│       │   ├── events.py        # EventQueue
│       │   └── exceptions.py    # Error hierarchy
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── dap_client.py    # DAP protocol client
│       │   └── debugpy_adapter.py  # debugpy integration
│       ├── persistence/
│       │   ├── __init__.py
│       │   ├── storage.py       # Atomic file operations
│       │   └── breakpoints.py   # Breakpoint persistence
│       ├── models/
│       │   ├── __init__.py
│       │   ├── requests.py      # API request models
│       │   ├── responses.py     # API response models
│       │   ├── session.py       # Session models
│       │   ├── dap.py           # DAP message models
│       │   └── events.py        # Event models
│       └── utils/
│           ├── __init__.py
│           └── output_buffer.py # Ring buffer
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Global fixtures
│   ├── unit/
│   │   ├── test_session.py
│   │   ├── test_output_buffer.py
│   │   ├── test_dap_client.py
│   │   └── test_persistence.py
│   ├── integration/
│   │   ├── test_api_sessions.py
│   │   ├── test_api_breakpoints.py
│   │   └── test_api_execution.py
│   ├── e2e/
│   │   ├── test_basic_debug.py
│   │   └── test_breakpoints.py
│   └── fixtures/
│       ├── scripts/
│       │   ├── simple_script.py
│       │   ├── error_script.py
│       │   └── loop_script.py
│       └── projects/
│           └── multifile/
├── docs/
│   ├── USER_STORY.md
│   └── plan/
│       ├── LLD_BACKEND.md
│       ├── LLD_API.md
│       ├── LLD_REVIEW.md
│       ├── TEST_PLAN.md
│       ├── TEST_AUTOMATION.md
│       └── IMPLEMENTATION_PLAN.md
├── pyproject.toml
├── README.md
└── .github/
    └── workflows/
        └── test.yml
```

---

## 5. API Endpoints Summary

### Session Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/sessions | Create debug session |
| GET | /api/v1/sessions | List all sessions |
| GET | /api/v1/sessions/{id} | Get session details |
| DELETE | /api/v1/sessions/{id} | Terminate session |

### Program Control
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/sessions/{id}/launch | Launch debuggee |
| POST | /api/v1/sessions/{id}/attach | Attach to process |

### Breakpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/sessions/{id}/breakpoints | Set breakpoints |
| GET | /api/v1/sessions/{id}/breakpoints | List breakpoints |
| DELETE | /api/v1/sessions/{id}/breakpoints/{bp_id} | Remove breakpoint |

### Execution Control
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/sessions/{id}/continue | Continue execution |
| POST | /api/v1/sessions/{id}/pause | Pause execution |
| POST | /api/v1/sessions/{id}/step-over | Step to next line |
| POST | /api/v1/sessions/{id}/step-into | Step into function |
| POST | /api/v1/sessions/{id}/step-out | Step out of function |

### State Inspection
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/sessions/{id}/threads | List threads |
| GET | /api/v1/sessions/{id}/stacktrace | Get stack trace |
| GET | /api/v1/sessions/{id}/scopes | Get variable scopes |
| GET | /api/v1/sessions/{id}/variables | Get variables |
| POST | /api/v1/sessions/{id}/evaluate | Evaluate expression |

### Output & Events
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/sessions/{id}/output | Get captured output |
| GET | /api/v1/sessions/{id}/events | Poll for events |

### Server
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/health | Health check |
| GET | /api/v1/info | Server info |

---

## 6. Success Criteria

### Functional Requirements
- [ ] Create and manage up to 10 concurrent debug sessions
- [ ] Set breakpoints (simple, conditional, hit count, logpoints)
- [ ] Control execution (continue, pause, step over/into/out)
- [ ] Inspect runtime state (variables, stack, threads)
- [ ] Evaluate expressions in current context
- [ ] Capture and retrieve stdout/stderr output
- [ ] Persist breakpoints per project
- [ ] Recover sessions after server restart

### Performance Requirements
| Metric | Target |
|--------|--------|
| Session creation | <500ms |
| Breakpoint set | <100ms |
| Step operations | <200ms |
| Variable inspection | <300ms |
| Status polling | <50ms |

### Quality Requirements
| Metric | Target |
|--------|--------|
| Unit test coverage | >90% |
| API contract coverage | 100% |
| All error codes tested | 100% |
| Documentation coverage | 100% |

---

## 7. Dependencies

### Runtime Dependencies
```toml
[project.dependencies]
fastapi = ">=0.109.0"
uvicorn = { version = ">=0.27.0", extras = ["standard"] }
debugpy = ">=1.8.0"
pydantic = ">=2.5.0"
pydantic-settings = ">=2.1.0"
aiofiles = ">=23.2.0"
```

### Development Dependencies
```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "pytest-timeout>=2.2.0",
    "httpx>=0.26.0",
    "ruff>=0.1.0",
    "mypy>=1.8.0",
]
```

---

## 8. Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| debugpy API changes | Low | High | Pin version, integration tests |
| Performance issues | Medium | Medium | Early performance testing |
| Memory leaks | Medium | High | Ring buffer limits, session cleanup |
| Race conditions | Medium | High | Comprehensive async locking |
| Persistence corruption | Low | Medium | Atomic writes, validation |

---

## 9. Out of Scope (v1)

The following are explicitly NOT included in v1:

- WebSocket/real-time event streaming
- GUI/web dashboard
- Remote debugging (non-localhost)
- Multi-language support (Python only)
- Subprocess debugging
- Hot code reloading
- Authentication/authorization
- Rate limiting

---

## 10. Getting Started

### Prerequisites
- Python 3.9+
- pip or uv package manager

### Installation
```bash
# Clone repository
cd /Users/amir/Development/opencode_debugger

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Start server
uvicorn opencode_debugger.main:app --reload
```

### Quick Test
```bash
# Create session
curl -X POST http://localhost:5679/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"project_root": "/path/to/project"}'

# Check health
curl http://localhost:5679/api/v1/health
```

---

## 11. Next Steps

1. **Create project scaffold** - pyproject.toml, directory structure
2. **Implement Phase 1** - Models, exceptions, config
3. **Implement Phase 2** - Infrastructure (DAP client, persistence)
4. **Implement Phase 3** - Session management
5. **Implement Phase 4** - API layer
6. **Run test suite** - Ensure >90% coverage
7. **Documentation** - README, examples
8. **Release** - Tag v0.1.0

---

**Document Compiled:** January 13, 2026
**Ready for Implementation:** Yes

---

## Appendix: Document Inventory

| Document | Lines | Description |
|----------|-------|-------------|
| USER_STORY.md | 1,026 | Complete product requirements |
| LLD_BACKEND.md | 1,800+ | Backend implementation spec |
| LLD_API.md | 3,000+ | API contract specification |
| LLD_REVIEW.md | 452 | Architecture alignment review |
| TEST_PLAN.md | 1,844 | Test strategy and cases |
| TEST_AUTOMATION.md | 2,000+ | Pytest implementations |
| IMPLEMENTATION_PLAN.md | 500+ | This document |

**Total Documentation:** ~10,000+ lines of detailed specifications.
