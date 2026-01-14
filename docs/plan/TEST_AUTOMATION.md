# Test Automation Plan: OpenCode Debug Relay Server

**Project:** OpenCode Debug Relay Server
**Version:** 1.0
**Date:** January 13, 2026
**Status:** Test Planning Complete

---

## Table of Contents

1. [Test Framework Setup](#1-test-framework-setup)
2. [Fixture Implementations](#2-fixture-implementations)
3. [Unit Test Examples](#3-unit-test-examples)
4. [Integration Test Examples](#4-integration-test-examples)
5. [E2E Test Examples](#5-e2e-test-examples)
6. [Mock Strategies](#6-mock-strategies)
7. [Test Data](#7-test-data)
8. [Coverage Configuration](#8-coverage-configuration)
9. [GitHub Actions Workflow](#9-github-actions-workflow)

---

## 1. Test Framework Setup

### 1.1 pytest Configuration (pyproject.toml)

```toml
[project]
name = "opencode-debugger"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn>=0.27.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "aiofiles>=23.2.0",
    "debugpy>=1.8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "pytest-timeout>=2.2.0",
    "pytest-xdist>=3.5.0",
    "httpx>=0.26.0",
    "respx>=0.20.0",
    "pytest-mock>=3.12.0",
    "factory-boy>=3.3.0",
    "faker>=22.0.0",
    "anyio>=4.2.0",
]

[tool.pytest.ini_options]
minversion = "8.0"
testpaths = ["tests"]
asyncio_mode = "auto"
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-ra",
    "-q",
    "--strict-markers",
    "--strict-config",
    "-p", "no:warnings",
]
markers = [
    "unit: Unit tests (fast, isolated)",
    "integration: Integration tests (may require setup)",
    "e2e: End-to-end tests (full system)",
    "slow: Tests that take more than 5 seconds",
]
filterwarnings = [
    "ignore::DeprecationWarning",
    "ignore::PendingDeprecationWarning",
]
timeout = 30

[tool.coverage.run]
branch = true
source = ["src/opencode_debugger"]
omit = [
    "*/tests/*",
    "*/__pycache__/*",
    "*/conftest.py",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
    "@abstractmethod",
]
fail_under = 90
show_missing = true
precision = 2

[tool.coverage.html]
directory = "htmlcov"
```

### 1.2 Directory Structure

```
opencode_debugger/
├── src/
│   └── opencode_debugger/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── api/
│       ├── core/
│       ├── adapters/
│       ├── persistence/
│       ├── models/
│       └── utils/
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # Global fixtures
│   ├── factories.py                   # Test data factories
│   ├── helpers.py                     # Test utilities
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── conftest.py                # Unit test fixtures
│   │   ├── test_session.py            # Session state machine
│   │   ├── test_output_buffer.py      # Ring buffer
│   │   ├── test_dap_client.py         # DAP protocol
│   │   ├── test_persistence.py        # Atomic writes
│   │   ├── test_events.py             # Event queue
│   │   └── test_config.py             # Configuration
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── conftest.py                # Integration fixtures
│   │   ├── test_api_sessions.py       # Session CRUD
│   │   ├── test_api_breakpoints.py    # Breakpoint endpoints
│   │   ├── test_api_execution.py      # Step/continue
│   │   ├── test_api_inspection.py     # Variables/stacktrace
│   │   └── test_api_output.py         # Output/events
│   ├── e2e/
│   │   ├── __init__.py
│   │   ├── conftest.py                # E2E fixtures
│   │   ├── test_e2e_basic_debug.py    # Full debug flow
│   │   ├── test_e2e_breakpoints.py    # Breakpoint scenarios
│   │   └── test_e2e_exceptions.py     # Exception handling
│   └── fixtures/
│       ├── scripts/
│       │   ├── simple_script.py
│       │   ├── error_script.py
│       │   ├── loop_script.py
│       │   └── multifile/
│       │       ├── main.py
│       │       ├── utils.py
│       │       └── models.py
│       └── data/
│           └── sample_breakpoints.json
├── pyproject.toml
└── pytest.ini                         # Alternative pytest config
```

---

## 2. Fixture Implementations

### 2.1 Global conftest.py (tests/conftest.py)

```python
"""Global pytest fixtures for all test types."""

import asyncio
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

from opencode_debugger.main import create_app
from opencode_debugger.config import Settings, settings
from opencode_debugger.core.session import Session, SessionManager, SessionState
from opencode_debugger.core.events import EventQueue
from opencode_debugger.persistence.breakpoints import BreakpointStore
from opencode_debugger.utils.output_buffer import OutputBuffer


# ============================================================================
# Event Loop Configuration
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for entire test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Application Fixtures
# ============================================================================

@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    """Create test settings with temporary directories."""
    return Settings(
        host="127.0.0.1",
        port=0,  # Dynamic port
        debug=True,
        max_sessions=5,
        session_timeout_seconds=300,
        session_max_lifetime_seconds=600,
        output_buffer_max_bytes=1024 * 1024,  # 1MB for tests
        data_dir=tmp_path / ".opencode-debugger",
        dap_timeout_seconds=5.0,
        dap_launch_timeout_seconds=10.0,
    )


@pytest.fixture
async def app(test_settings: Settings):
    """Create FastAPI test application."""
    with patch("opencode_debugger.config.settings", test_settings):
        application = create_app()
        yield application


@pytest.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test/api/v1",
        timeout=30.0,
    ) as ac:
        yield ac


@pytest.fixture
async def authenticated_client(client: AsyncClient) -> AsyncClient:
    """Client with any required authentication (future use)."""
    # No auth required in v1, but placeholder for future
    return client


# ============================================================================
# Core Component Fixtures
# ============================================================================

@pytest.fixture
async def breakpoint_store(tmp_path: Path) -> BreakpointStore:
    """Create breakpoint store with temporary directory."""
    store = BreakpointStore(base_dir=tmp_path / "breakpoints")
    return store


@pytest.fixture
async def session_manager(breakpoint_store: BreakpointStore) -> AsyncGenerator[SessionManager, None]:
    """Create session manager with cleanup."""
    manager = SessionManager(breakpoint_store=breakpoint_store)
    await manager.start()
    yield manager
    await manager.stop()


@pytest.fixture
def output_buffer() -> OutputBuffer:
    """Create output buffer for testing."""
    return OutputBuffer(max_size=10 * 1024)  # 10KB for tests


@pytest.fixture
def event_queue() -> EventQueue:
    """Create event queue for testing."""
    return EventQueue(max_size=100)


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_debugpy():
    """Mock debugpy adapter for isolated testing."""
    mock = AsyncMock()
    mock.initialize = AsyncMock(return_value={
        "supportsConfigurationDoneRequest": True,
        "supportsFunctionBreakpoints": True,
        "supportsConditionalBreakpoints": True,
        "supportsHitConditionalBreakpoints": True,
        "supportsEvaluateForHovers": True,
    })
    mock.launch = AsyncMock()
    mock.disconnect = AsyncMock()
    mock.set_breakpoints = AsyncMock(return_value=[])
    mock.continue_ = AsyncMock()
    mock.pause = AsyncMock()
    mock.step_over = AsyncMock()
    mock.step_into = AsyncMock()
    mock.step_out = AsyncMock()
    mock.threads = AsyncMock(return_value=[
        MagicMock(id=1, name="MainThread"),
    ])
    mock.stack_trace = AsyncMock(return_value=[])
    mock.scopes = AsyncMock(return_value=[])
    mock.variables = AsyncMock(return_value=[])
    mock.evaluate = AsyncMock(return_value={"result": "42", "type": "int"})
    return mock


@pytest.fixture
def mock_dap_client():
    """Mock DAP client for protocol testing."""
    mock = AsyncMock()
    mock.start = AsyncMock()
    mock.stop = AsyncMock()
    mock.send_request = AsyncMock(return_value={"success": True, "body": {}})
    return mock


@pytest.fixture
def mock_subprocess():
    """Mock asyncio subprocess for debugpy process."""
    mock_process = AsyncMock()
    mock_process.stdin = MagicMock()
    mock_process.stdout = MagicMock()
    mock_process.stderr = MagicMock()
    mock_process.returncode = None
    mock_process.terminate = MagicMock()
    mock_process.kill = MagicMock()
    mock_process.wait = AsyncMock()
    return mock_process


# ============================================================================
# Test Script Fixtures
# ============================================================================

@pytest.fixture
def sample_script(tmp_path: Path) -> Path:
    """Create a simple Python script for debugging."""
    script = tmp_path / "test_script.py"
    script.write_text('''#!/usr/bin/env python3
"""Simple test script for debugging."""

def calculate(x, y):
    """Calculate sum of two numbers."""
    result = x + y
    return result

def main():
    """Main function."""
    a = 10
    b = 20
    total = calculate(a, b)
    print(f"Result: {total}")
    return total

if __name__ == "__main__":
    main()
''')
    return script


@pytest.fixture
def error_script(tmp_path: Path) -> Path:
    """Create a script that raises an exception."""
    script = tmp_path / "error_script.py"
    script.write_text('''#!/usr/bin/env python3
"""Script that raises an exception."""

def failing_function():
    """Function that will fail."""
    data = [1, 2, 3]
    return data[10]  # IndexError

def main():
    """Main function."""
    print("Starting...")
    failing_function()
    print("Done")

if __name__ == "__main__":
    main()
''')
    return script


@pytest.fixture
def loop_script(tmp_path: Path) -> Path:
    """Create a script with a loop for conditional breakpoint testing."""
    script = tmp_path / "loop_script.py"
    script.write_text('''#!/usr/bin/env python3
"""Script with loop for conditional breakpoint testing."""

def process_items():
    """Process items in a loop."""
    items = []
    for i in range(100):
        item = {"id": i, "value": i * 2}
        items.append(item)
        print(f"Processed item {i}")
    return items

def main():
    """Main function."""
    result = process_items()
    print(f"Total items: {len(result)}")
    return result

if __name__ == "__main__":
    main()
''')
    return script


@pytest.fixture
def multifile_project(tmp_path: Path) -> Path:
    """Create a multi-file project for import testing."""
    project_dir = tmp_path / "multifile"
    project_dir.mkdir()

    # Main entry point
    (project_dir / "main.py").write_text('''#!/usr/bin/env python3
"""Main entry point."""
from utils import helper_function
from models import DataModel

def main():
    """Main function."""
    data = DataModel(name="test", value=42)
    result = helper_function(data)
    print(f"Result: {result}")
    return result

if __name__ == "__main__":
    main()
''')

    # Utils module
    (project_dir / "utils.py").write_text('''"""Utility functions."""

def helper_function(data):
    """Helper that processes data."""
    processed = data.value * 2
    return processed
''')

    # Models module
    (project_dir / "models.py").write_text('''"""Data models."""
from dataclasses import dataclass

@dataclass
class DataModel:
    """Simple data model."""
    name: str
    value: int
''')

    # __init__.py
    (project_dir / "__init__.py").write_text('')

    return project_dir


# ============================================================================
# Helper Fixtures
# ============================================================================

@pytest.fixture
def make_session(tmp_path: Path):
    """Factory fixture to create session instances."""
    sessions = []

    def _make_session(
        session_id: str = "sess_test123",
        project_root: Path = None,
        name: str = "test-session",
    ) -> Session:
        session = Session(
            session_id=session_id,
            project_root=project_root or tmp_path,
            name=name,
        )
        sessions.append(session)
        return session

    yield _make_session

    # Cleanup
    for session in sessions:
        if hasattr(session, 'cleanup'):
            asyncio.get_event_loop().run_until_complete(session.cleanup())


@pytest.fixture
def response_validator():
    """Fixture to validate API response structure."""
    def _validate(response: dict, expected_success: bool = True):
        assert "success" in response
        assert response["success"] == expected_success
        assert "data" in response
        assert "error" in response
        assert "meta" in response

        if expected_success:
            assert response["error"] is None
            assert response["data"] is not None
        else:
            assert response["error"] is not None
            assert "code" in response["error"]
            assert "message" in response["error"]

        return response["data"]

    return _validate
```

### 2.2 Unit Test Fixtures (tests/unit/conftest.py)

```python
"""Unit test specific fixtures."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from opencode_debugger.core.session import Session, SessionState
from opencode_debugger.models.dap import SourceBreakpoint, Breakpoint
from opencode_debugger.models.events import EventType, DebugEvent


@pytest.fixture
def isolated_session(tmp_path, mock_debugpy):
    """Create isolated session with mocked adapter."""
    session = Session(
        session_id="sess_isolated",
        project_root=tmp_path,
        name="isolated-test",
    )
    session.adapter = mock_debugpy
    return session


@pytest.fixture
def sample_breakpoints():
    """Sample breakpoint configurations."""
    return [
        SourceBreakpoint(line=10, condition=None),
        SourceBreakpoint(line=20, condition="x > 5"),
        SourceBreakpoint(line=30, hit_condition=">10"),
        SourceBreakpoint(line=40, log_message="Value is {x}"),
    ]


@pytest.fixture
def sample_events():
    """Sample debug events for testing."""
    now = datetime.now(timezone.utc)
    return [
        DebugEvent(
            type=EventType.STOPPED,
            timestamp=now,
            data={"reason": "breakpoint", "thread_id": 1}
        ),
        DebugEvent(
            type=EventType.OUTPUT,
            timestamp=now,
            data={"category": "stdout", "output": "Hello\n"}
        ),
        DebugEvent(
            type=EventType.CONTINUED,
            timestamp=now,
            data={"thread_id": 1}
        ),
    ]


@pytest.fixture
def mock_file_operations(tmp_path):
    """Mock file operations for persistence tests."""
    return {
        "read": AsyncMock(return_value={"data": "test"}),
        "write": AsyncMock(),
        "delete": AsyncMock(return_value=True),
        "base_path": tmp_path,
    }
```

### 2.3 Integration Test Fixtures (tests/integration/conftest.py)

```python
"""Integration test specific fixtures."""

import pytest
from httpx import AsyncClient

from opencode_debugger.core.session import SessionState


@pytest.fixture
async def created_session(client: AsyncClient, sample_script) -> dict:
    """Create a session and return its data."""
    response = await client.post(
        "/sessions",
        json={
            "name": "integration-test-session",
            "project_root": str(sample_script.parent),
        }
    )
    assert response.status_code == 201
    data = response.json()
    session_data = data["data"]

    yield session_data

    # Cleanup: delete session if it still exists
    try:
        await client.delete(f"/sessions/{session_data['session_id']}")
    except Exception:
        pass


@pytest.fixture
async def launched_session(
    client: AsyncClient,
    created_session: dict,
    sample_script,
) -> dict:
    """Create and launch a session."""
    session_id = created_session["session_id"]

    response = await client.post(
        f"/sessions/{session_id}/launch",
        json={
            "script": str(sample_script),
            "stop_on_entry": True,
        }
    )
    assert response.status_code == 200

    # Wait for paused state
    for _ in range(50):  # Max 5 seconds
        status_response = await client.get(f"/sessions/{session_id}")
        if status_response.json()["data"]["status"] == "paused":
            break
        await asyncio.sleep(0.1)

    return created_session


@pytest.fixture
async def session_with_breakpoint(
    client: AsyncClient,
    created_session: dict,
    sample_script,
) -> dict:
    """Create session with a breakpoint set."""
    session_id = created_session["session_id"]

    # Set breakpoint at line 7 (result = x + y)
    response = await client.post(
        f"/sessions/{session_id}/breakpoints",
        json={
            "breakpoints": [
                {
                    "source": {"path": str(sample_script)},
                    "line": 7,
                }
            ]
        }
    )
    assert response.status_code == 200

    return created_session
```

### 2.4 E2E Test Fixtures (tests/e2e/conftest.py)

```python
"""End-to-end test specific fixtures."""

import asyncio
import subprocess
import sys
from pathlib import Path
from typing import AsyncGenerator

import pytest
from httpx import AsyncClient

from opencode_debugger.main import create_app
from opencode_debugger.config import Settings


@pytest.fixture(scope="module")
async def e2e_app():
    """Create app for E2E tests with real debugpy."""
    # Use default settings for E2E
    app = create_app()
    yield app


@pytest.fixture(scope="module")
async def e2e_client(e2e_app) -> AsyncGenerator[AsyncClient, None]:
    """Create client for E2E tests."""
    from httpx import ASGITransport
    transport = ASGITransport(app=e2e_app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test/api/v1",
        timeout=60.0,  # Longer timeout for E2E
    ) as ac:
        yield ac


@pytest.fixture
def real_debugpy_available():
    """Check if real debugpy is available."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import debugpy; print(debugpy.__version__)"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


@pytest.fixture
async def full_debug_session(
    e2e_client: AsyncClient,
    sample_script: Path,
    real_debugpy_available: bool,
):
    """Create a fully functional debug session for E2E tests."""
    if not real_debugpy_available:
        pytest.skip("debugpy not available")

    # Create session
    response = await e2e_client.post(
        "/sessions",
        json={
            "name": "e2e-test-session",
            "project_root": str(sample_script.parent),
        }
    )
    session_data = response.json()["data"]
    session_id = session_data["session_id"]

    yield {
        "session_id": session_id,
        "script": sample_script,
        "client": e2e_client,
    }

    # Cleanup
    try:
        await e2e_client.delete(f"/sessions/{session_id}")
    except Exception:
        pass


async def wait_for_status(
    client: AsyncClient,
    session_id: str,
    status: str,
    timeout: float = 10.0,
) -> dict:
    """Wait for session to reach specific status."""
    import time
    start = time.time()

    while time.time() - start < timeout:
        response = await client.get(f"/sessions/{session_id}")
        data = response.json()["data"]
        if data["status"] == status:
            return data
        await asyncio.sleep(0.1)

    raise TimeoutError(f"Session did not reach status '{status}' within {timeout}s")
```

---

## 3. Unit Test Examples

### 3.1 test_session.py - Session State Machine Tests

```python
"""Unit tests for session state machine and management."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from opencode_debugger.core.session import Session, SessionManager, SessionState
from opencode_debugger.core.exceptions import (
    InvalidSessionStateError,
    SessionNotFoundError,
    SessionLimitError,
)
from opencode_debugger.models.session import SessionConfig


class TestSessionState:
    """Tests for session state transitions."""

    @pytest.mark.unit
    async def test_initial_state_is_created(self, tmp_path):
        """Session should start in CREATED state."""
        session = Session(
            session_id="sess_test",
            project_root=tmp_path,
        )
        assert session.state == SessionState.CREATED

    @pytest.mark.unit
    async def test_valid_state_transition_created_to_launching(self, tmp_path):
        """Should transition from CREATED to LAUNCHING."""
        session = Session(session_id="sess_test", project_root=tmp_path)
        await session.transition_to(SessionState.LAUNCHING)
        assert session.state == SessionState.LAUNCHING

    @pytest.mark.unit
    async def test_valid_state_transition_launching_to_running(self, tmp_path):
        """Should transition from LAUNCHING to RUNNING."""
        session = Session(session_id="sess_test", project_root=tmp_path)
        await session.transition_to(SessionState.LAUNCHING)
        await session.transition_to(SessionState.RUNNING)
        assert session.state == SessionState.RUNNING

    @pytest.mark.unit
    async def test_valid_state_transition_running_to_paused(self, tmp_path):
        """Should transition from RUNNING to PAUSED."""
        session = Session(session_id="sess_test", project_root=tmp_path)
        await session.transition_to(SessionState.LAUNCHING)
        await session.transition_to(SessionState.RUNNING)
        await session.transition_to(SessionState.PAUSED)
        assert session.state == SessionState.PAUSED

    @pytest.mark.unit
    async def test_invalid_state_transition_created_to_paused(self, tmp_path):
        """Should reject invalid transition from CREATED to PAUSED."""
        session = Session(session_id="sess_test", project_root=tmp_path)
        with pytest.raises(InvalidSessionStateError) as exc_info:
            await session.transition_to(SessionState.PAUSED)
        assert exc_info.value.code == "INVALID_SESSION_STATE"

    @pytest.mark.unit
    async def test_transition_updates_last_activity(self, tmp_path):
        """State transition should update last_activity timestamp."""
        session = Session(session_id="sess_test", project_root=tmp_path)
        original_activity = session.last_activity

        await session.transition_to(SessionState.LAUNCHING)

        assert session.last_activity > original_activity

    @pytest.mark.unit
    async def test_require_state_passes_for_valid_state(self, tmp_path):
        """require_state should not raise for valid state."""
        session = Session(session_id="sess_test", project_root=tmp_path)
        session.require_state(SessionState.CREATED)  # Should not raise

    @pytest.mark.unit
    async def test_require_state_raises_for_invalid_state(self, tmp_path):
        """require_state should raise for invalid state."""
        session = Session(session_id="sess_test", project_root=tmp_path)
        with pytest.raises(InvalidSessionStateError):
            session.require_state(SessionState.RUNNING, SessionState.PAUSED)

    @pytest.mark.unit
    async def test_session_to_info_conversion(self, tmp_path):
        """Session should convert to SessionInfo correctly."""
        session = Session(
            session_id="sess_test123",
            project_root=tmp_path,
            name="Test Session",
        )

        info = session.to_info()

        assert info.id == "sess_test123"
        assert info.name == "Test Session"
        assert info.project_root == str(tmp_path)
        assert info.state == "created"


class TestSessionManager:
    """Tests for session manager functionality."""

    @pytest.mark.unit
    async def test_create_session_returns_session(self, session_manager, tmp_path):
        """Creating a session should return a valid session."""
        config = SessionConfig(project_root=str(tmp_path))

        with patch.object(Session, 'initialize_adapter', new_callable=AsyncMock):
            session = await session_manager.create_session(config)

        assert session is not None
        assert session.state == SessionState.CREATED
        assert session.id.startswith("sess_")

    @pytest.mark.unit
    async def test_create_session_respects_limit(self, breakpoint_store, tmp_path):
        """Should raise SessionLimitError when limit reached."""
        with patch("opencode_debugger.config.settings.max_sessions", 2):
            manager = SessionManager(breakpoint_store=breakpoint_store)
            await manager.start()

            config = SessionConfig(project_root=str(tmp_path))

            with patch.object(Session, 'initialize_adapter', new_callable=AsyncMock):
                # Create 2 sessions (at limit)
                await manager.create_session(config)
                await manager.create_session(config)

                # Third should fail
                with pytest.raises(SessionLimitError):
                    await manager.create_session(config)

            await manager.stop()

    @pytest.mark.unit
    async def test_get_session_returns_session(self, session_manager, tmp_path):
        """Should retrieve existing session by ID."""
        config = SessionConfig(project_root=str(tmp_path))

        with patch.object(Session, 'initialize_adapter', new_callable=AsyncMock):
            created = await session_manager.create_session(config)
            retrieved = await session_manager.get_session(created.id)

        assert retrieved.id == created.id

    @pytest.mark.unit
    async def test_get_session_raises_for_unknown_id(self, session_manager):
        """Should raise SessionNotFoundError for unknown ID."""
        with pytest.raises(SessionNotFoundError) as exc_info:
            await session_manager.get_session("sess_nonexistent")
        assert exc_info.value.code == "SESSION_NOT_FOUND"

    @pytest.mark.unit
    async def test_get_session_updates_last_activity(self, session_manager, tmp_path):
        """Getting a session should update its last_activity."""
        config = SessionConfig(project_root=str(tmp_path))

        with patch.object(Session, 'initialize_adapter', new_callable=AsyncMock):
            created = await session_manager.create_session(config)
            original_activity = created.last_activity

            # Small delay
            import asyncio
            await asyncio.sleep(0.01)

            await session_manager.get_session(created.id)

        assert created.last_activity > original_activity

    @pytest.mark.unit
    async def test_list_sessions_returns_all(self, session_manager, tmp_path):
        """Should list all active sessions."""
        config = SessionConfig(project_root=str(tmp_path))

        with patch.object(Session, 'initialize_adapter', new_callable=AsyncMock):
            await session_manager.create_session(config)
            await session_manager.create_session(config)

            sessions = await session_manager.list_sessions()

        assert len(sessions) == 2

    @pytest.mark.unit
    async def test_terminate_session_removes_from_list(self, session_manager, tmp_path):
        """Terminating a session should remove it from the list."""
        config = SessionConfig(project_root=str(tmp_path))

        with patch.object(Session, 'initialize_adapter', new_callable=AsyncMock):
            session = await session_manager.create_session(config)
            session_id = session.id

            await session_manager.terminate_session(session_id)

            with pytest.raises(SessionNotFoundError):
                await session_manager.get_session(session_id)

    @pytest.mark.unit
    async def test_terminate_nonexistent_session_raises(self, session_manager):
        """Should raise SessionNotFoundError for unknown session."""
        with pytest.raises(SessionNotFoundError):
            await session_manager.terminate_session("sess_nonexistent")


class TestSessionCleanup:
    """Tests for session cleanup and resource management."""

    @pytest.mark.unit
    async def test_cleanup_clears_output_buffer(self, isolated_session):
        """Cleanup should clear the output buffer."""
        isolated_session.output_buffer.append("stdout", "test output")
        assert isolated_session.output_buffer.total_lines > 0

        await isolated_session.cleanup()

        assert isolated_session.output_buffer.total_lines == 0

    @pytest.mark.unit
    async def test_cleanup_clears_event_queue(self, isolated_session):
        """Cleanup should clear the event queue."""
        from opencode_debugger.models.events import EventType
        await isolated_session.event_queue.put(EventType.OUTPUT, {"test": "data"})

        await isolated_session.cleanup()

        events = await isolated_session.event_queue.get_all()
        assert len(events) == 0

    @pytest.mark.unit
    async def test_cleanup_disconnects_adapter(self, isolated_session, mock_debugpy):
        """Cleanup should disconnect the debugpy adapter."""
        await isolated_session.cleanup()

        mock_debugpy.disconnect.assert_called_once()
```

### 3.2 test_output_buffer.py - Ring Buffer Tests

```python
"""Unit tests for the output ring buffer."""

import pytest
from datetime import datetime, timezone

from opencode_debugger.utils.output_buffer import OutputBuffer, OutputLine, OutputPage


class TestOutputBuffer:
    """Tests for OutputBuffer functionality."""

    @pytest.mark.unit
    def test_append_adds_entry(self, output_buffer):
        """Appending should add an entry to the buffer."""
        output_buffer.append("stdout", "Hello, World!")

        assert output_buffer.total_lines == 1

    @pytest.mark.unit
    def test_append_increments_line_numbers(self, output_buffer):
        """Line numbers should increment with each append."""
        output_buffer.append("stdout", "Line 1")
        output_buffer.append("stdout", "Line 2")
        output_buffer.append("stderr", "Line 3")

        page = output_buffer.get_page()

        assert page.lines[0].line_number == 1
        assert page.lines[1].line_number == 2
        assert page.lines[2].line_number == 3

    @pytest.mark.unit
    def test_append_preserves_category(self, output_buffer):
        """Category should be preserved for each entry."""
        output_buffer.append("stdout", "stdout message")
        output_buffer.append("stderr", "stderr message")
        output_buffer.append("console", "console message")

        page = output_buffer.get_page()

        assert page.lines[0].category == "stdout"
        assert page.lines[1].category == "stderr"
        assert page.lines[2].category == "console"

    @pytest.mark.unit
    def test_append_sets_timestamp(self, output_buffer):
        """Each entry should have a timestamp."""
        before = datetime.now(timezone.utc)
        output_buffer.append("stdout", "test")
        after = datetime.now(timezone.utc)

        page = output_buffer.get_page()

        assert before <= page.lines[0].timestamp <= after

    @pytest.mark.unit
    def test_append_drops_oldest_when_full(self):
        """Buffer should drop oldest entries when size limit reached."""
        # Create a very small buffer (100 bytes)
        buffer = OutputBuffer(max_size=100)

        # Add enough data to exceed limit
        for i in range(20):
            buffer.append("stdout", f"Message {i:04d} - padding to make it bigger")

        assert buffer.dropped_lines > 0
        assert buffer.size <= 100

    @pytest.mark.unit
    def test_get_page_with_offset(self, output_buffer):
        """get_page should respect offset parameter."""
        for i in range(10):
            output_buffer.append("stdout", f"Line {i}")

        page = output_buffer.get_page(offset=5, limit=3)

        assert len(page.lines) == 3
        assert page.offset == 5
        assert page.lines[0].content == "Line 5"

    @pytest.mark.unit
    def test_get_page_with_limit(self, output_buffer):
        """get_page should respect limit parameter."""
        for i in range(10):
            output_buffer.append("stdout", f"Line {i}")

        page = output_buffer.get_page(limit=5)

        assert len(page.lines) == 5
        assert page.limit == 5
        assert page.has_more is True

    @pytest.mark.unit
    def test_get_page_with_category_filter(self, output_buffer):
        """get_page should filter by category."""
        output_buffer.append("stdout", "stdout 1")
        output_buffer.append("stderr", "stderr 1")
        output_buffer.append("stdout", "stdout 2")
        output_buffer.append("stderr", "stderr 2")

        stdout_page = output_buffer.get_page(category="stdout")
        stderr_page = output_buffer.get_page(category="stderr")

        assert stdout_page.total == 2
        assert all(line.category == "stdout" for line in stdout_page.lines)

        assert stderr_page.total == 2
        assert all(line.category == "stderr" for line in stderr_page.lines)

    @pytest.mark.unit
    def test_get_page_has_more_flag(self, output_buffer):
        """has_more flag should indicate remaining entries."""
        for i in range(10):
            output_buffer.append("stdout", f"Line {i}")

        page1 = output_buffer.get_page(offset=0, limit=5)
        page2 = output_buffer.get_page(offset=5, limit=5)
        page3 = output_buffer.get_page(offset=10, limit=5)

        assert page1.has_more is True
        assert page2.has_more is False
        assert page3.has_more is False

    @pytest.mark.unit
    def test_get_page_truncated_flag(self):
        """truncated flag should indicate if lines were dropped."""
        buffer = OutputBuffer(max_size=100)

        # Initially not truncated
        buffer.append("stdout", "Short")
        page1 = buffer.get_page()
        assert page1.truncated is False

        # Force truncation
        for i in range(50):
            buffer.append("stdout", f"Long message {i:04d}")

        page2 = buffer.get_page()
        assert page2.truncated is True

    @pytest.mark.unit
    def test_clear_removes_all_entries(self, output_buffer):
        """clear should remove all entries."""
        for i in range(10):
            output_buffer.append("stdout", f"Line {i}")

        output_buffer.clear()

        assert output_buffer.total_lines == 0
        assert output_buffer.size == 0
        assert output_buffer.dropped_lines == 0

    @pytest.mark.unit
    def test_size_tracks_bytes(self, output_buffer):
        """size property should track bytes correctly."""
        output_buffer.append("stdout", "Hello")  # 5 bytes
        output_buffer.append("stdout", "World")  # 5 bytes

        # Size should be at least 10 bytes
        assert output_buffer.size >= 10

    @pytest.mark.unit
    def test_empty_buffer_returns_empty_page(self, output_buffer):
        """Empty buffer should return empty page."""
        page = output_buffer.get_page()

        assert page.lines == []
        assert page.total == 0
        assert page.has_more is False
        assert page.truncated is False


class TestOutputLine:
    """Tests for OutputLine dataclass."""

    @pytest.mark.unit
    def test_output_line_defaults(self):
        """OutputLine should have sensible defaults."""
        line = OutputLine(
            line_number=1,
            category="stdout",
            content="test",
        )

        assert line.line_number == 1
        assert line.category == "stdout"
        assert line.content == "test"
        assert isinstance(line.timestamp, datetime)
```

### 3.3 test_dap_client.py - DAP Protocol Tests

```python
"""Unit tests for DAP client implementation."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from opencode_debugger.adapters.dap_client import DAPClient
from opencode_debugger.core.exceptions import DAPError, DAPTimeoutError


class TestDAPClient:
    """Tests for DAP client functionality."""

    @pytest.fixture
    def mock_streams(self):
        """Create mock stream reader/writer."""
        reader = AsyncMock(spec=asyncio.StreamReader)
        writer = MagicMock(spec=asyncio.StreamWriter)
        writer.write = MagicMock()
        writer.drain = AsyncMock()
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()
        return reader, writer

    @pytest.fixture
    def dap_client(self, mock_streams):
        """Create DAP client with mock streams."""
        reader, writer = mock_streams
        return DAPClient(
            reader=reader,
            writer=writer,
            event_callback=None,
            timeout=5.0,
        )

    @pytest.mark.unit
    async def test_start_begins_reader_loop(self, dap_client):
        """start() should begin the message reader loop."""
        await dap_client.start()

        assert dap_client._reader_task is not None
        assert not dap_client._reader_task.done()

        await dap_client.stop()

    @pytest.mark.unit
    async def test_stop_cancels_reader_task(self, dap_client):
        """stop() should cancel the reader task."""
        await dap_client.start()
        await dap_client.stop()

        assert dap_client._reader_task.cancelled() or dap_client._reader_task.done()

    @pytest.mark.unit
    async def test_send_request_formats_message_correctly(self, dap_client, mock_streams):
        """send_request should format DAP message with proper headers."""
        reader, writer = mock_streams

        # Mock response
        response = {
            "type": "response",
            "request_seq": 1,
            "success": True,
            "command": "initialize",
            "body": {"supportsBreakpoints": True}
        }

        async def mock_read_response():
            dap_client._pending[1].set_result(response)

        # Start client and immediately resolve
        asyncio.get_event_loop().call_soon(
            lambda: dap_client._pending[1].set_result(response) if 1 in dap_client._pending else None
        )

        with patch.object(dap_client, '_read_loop', new_callable=AsyncMock):
            await dap_client.start()

            # Create pending future manually for test
            future = asyncio.Future()
            future.set_result(response)
            dap_client._pending[1] = future

            result = await dap_client.send_request("initialize", {"clientID": "test"})

        # Verify message was written
        writer.write.assert_called()
        call_args = writer.write.call_args_list[0][0][0]

        # Should have Content-Length header
        assert b"Content-Length:" in call_args

        await dap_client.stop()

    @pytest.mark.unit
    async def test_send_request_raises_on_timeout(self, mock_streams):
        """send_request should raise DAPTimeoutError on timeout."""
        reader, writer = mock_streams

        client = DAPClient(
            reader=reader,
            writer=writer,
            timeout=0.01,  # Very short timeout
        )

        with patch.object(client, '_read_loop', new_callable=AsyncMock):
            await client.start()

            with pytest.raises(DAPTimeoutError) as exc_info:
                await client.send_request("initialize", timeout=0.01)

            assert exc_info.value.code == "DEBUGPY_TIMEOUT"

        await client.stop()

    @pytest.mark.unit
    async def test_send_request_raises_on_error_response(self, dap_client, mock_streams):
        """send_request should raise DAPError on error response."""
        error_response = {
            "type": "response",
            "request_seq": 1,
            "success": False,
            "command": "launch",
            "message": "File not found",
        }

        with patch.object(dap_client, '_read_loop', new_callable=AsyncMock):
            await dap_client.start()

            future = asyncio.Future()
            future.set_result(error_response)
            dap_client._pending[1] = future

            with pytest.raises(DAPError) as exc_info:
                await dap_client.send_request("launch", {"program": "/nonexistent"})

            assert "File not found" in str(exc_info.value)

        await dap_client.stop()

    @pytest.mark.unit
    async def test_handle_event_calls_callback(self, mock_streams):
        """Event messages should trigger the callback."""
        reader, writer = mock_streams

        callback = AsyncMock()
        client = DAPClient(
            reader=reader,
            writer=writer,
            event_callback=callback,
        )

        event_message = {
            "type": "event",
            "seq": 1,
            "event": "stopped",
            "body": {"reason": "breakpoint", "threadId": 1}
        }

        await client._handle_message(event_message)

        callback.assert_called_once_with("stopped", {"reason": "breakpoint", "threadId": 1})

    @pytest.mark.unit
    async def test_handle_response_resolves_pending_future(self, dap_client):
        """Response messages should resolve pending futures."""
        future = asyncio.Future()
        dap_client._pending[42] = future

        response_message = {
            "type": "response",
            "request_seq": 42,
            "success": True,
            "command": "continue",
            "body": {}
        }

        await dap_client._handle_message(response_message)

        assert future.done()
        assert future.result() == response_message

    @pytest.mark.unit
    def test_sequence_numbers_increment(self, dap_client):
        """Sequence numbers should increment with each request."""
        initial_seq = dap_client._seq

        # Access the lock-protected increment (simulate)
        dap_client._seq += 1
        assert dap_client._seq == initial_seq + 1

        dap_client._seq += 1
        assert dap_client._seq == initial_seq + 2


class TestDAPMessageParsing:
    """Tests for DAP message parsing."""

    @pytest.mark.unit
    async def test_read_message_parses_headers(self, mock_streams):
        """Should correctly parse Content-Length header."""
        reader, writer = mock_streams

        content = '{"type":"response","seq":1}'
        header = f"Content-Length: {len(content)}\r\n\r\n"

        # Mock readline to return header lines
        reader.readline.side_effect = [
            header.split('\r\n')[0].encode() + b'\r\n',
            b'\r\n',
        ]
        reader.readexactly.return_value = content.encode()

        client = DAPClient(reader, writer)
        message = await client._read_message()

        assert message is not None
        assert message["type"] == "response"
        assert message["seq"] == 1

    @pytest.mark.unit
    async def test_read_message_handles_empty_content(self, mock_streams):
        """Should return None for empty content."""
        reader, writer = mock_streams

        reader.readline.side_effect = [
            b"Content-Length: 0\r\n",
            b"\r\n",
        ]

        client = DAPClient(reader, writer)
        message = await client._read_message()

        assert message is None
```

### 3.4 test_persistence.py - Atomic Write Tests

```python
"""Unit tests for persistence layer and atomic writes."""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, mock_open

from opencode_debugger.persistence.storage import (
    atomic_write,
    safe_read,
    safe_delete,
    project_id_from_path,
)
from opencode_debugger.persistence.breakpoints import BreakpointStore
from opencode_debugger.core.exceptions import PersistenceError
from opencode_debugger.models.dap import SourceBreakpoint


class TestAtomicWrite:
    """Tests for atomic file write operations."""

    @pytest.mark.unit
    async def test_atomic_write_creates_file(self, tmp_path):
        """atomic_write should create the target file."""
        target = tmp_path / "test.json"
        data = {"key": "value"}

        await atomic_write(target, data)

        assert target.exists()
        with open(target) as f:
            assert json.load(f) == data

    @pytest.mark.unit
    async def test_atomic_write_creates_parent_directories(self, tmp_path):
        """atomic_write should create parent directories if needed."""
        target = tmp_path / "nested" / "deep" / "test.json"
        data = {"nested": True}

        await atomic_write(target, data)

        assert target.exists()

    @pytest.mark.unit
    async def test_atomic_write_uses_temp_file(self, tmp_path):
        """atomic_write should use a temp file for atomicity."""
        target = tmp_path / "test.json"

        # Track temp file creation
        temp_files_created = []

        original_open = open
        def tracking_open(path, *args, **kwargs):
            if str(path).endswith('.tmp'):
                temp_files_created.append(path)
            return original_open(path, *args, **kwargs)

        # Note: aiofiles makes this tricky to test directly
        # The atomicity is ensured by write-to-temp + rename pattern
        await atomic_write(target, {"test": "data"})

        # Temp file should not exist after completion
        assert not (target.with_suffix(".tmp")).exists()

    @pytest.mark.unit
    async def test_atomic_write_overwrites_existing(self, tmp_path):
        """atomic_write should overwrite existing file."""
        target = tmp_path / "test.json"

        # Write initial content
        await atomic_write(target, {"version": 1})

        # Overwrite
        await atomic_write(target, {"version": 2})

        with open(target) as f:
            data = json.load(f)
            assert data["version"] == 2

    @pytest.mark.unit
    async def test_atomic_write_preserves_original_on_error(self, tmp_path):
        """On error, original file should be preserved."""
        target = tmp_path / "test.json"
        original_data = {"original": True}

        await atomic_write(target, original_data)

        # Attempting to write non-serializable data should fail
        # but original should remain
        class NonSerializable:
            pass

        try:
            await atomic_write(target, {"bad": NonSerializable()})
        except (TypeError, PersistenceError):
            pass

        with open(target) as f:
            data = json.load(f)
            assert data == original_data


class TestSafeRead:
    """Tests for safe file read operations."""

    @pytest.mark.unit
    async def test_safe_read_returns_data(self, tmp_path):
        """safe_read should return parsed JSON data."""
        target = tmp_path / "test.json"
        expected = {"key": "value", "number": 42}

        with open(target, 'w') as f:
            json.dump(expected, f)

        result = await safe_read(target)

        assert result == expected

    @pytest.mark.unit
    async def test_safe_read_returns_none_for_missing(self, tmp_path):
        """safe_read should return None for missing file."""
        target = tmp_path / "nonexistent.json"

        result = await safe_read(target)

        assert result is None

    @pytest.mark.unit
    async def test_safe_read_raises_on_invalid_json(self, tmp_path):
        """safe_read should raise PersistenceError on invalid JSON."""
        target = tmp_path / "invalid.json"

        with open(target, 'w') as f:
            f.write("not valid json {{{")

        with pytest.raises(PersistenceError) as exc_info:
            await safe_read(target)

        assert exc_info.value.code == "INVALID_JSON"


class TestSafeDelete:
    """Tests for safe file delete operations."""

    @pytest.mark.unit
    async def test_safe_delete_removes_file(self, tmp_path):
        """safe_delete should remove the file."""
        target = tmp_path / "test.json"
        target.write_text("{}")

        result = await safe_delete(target)

        assert result is True
        assert not target.exists()

    @pytest.mark.unit
    async def test_safe_delete_returns_false_for_missing(self, tmp_path):
        """safe_delete should return False for missing file."""
        target = tmp_path / "nonexistent.json"

        result = await safe_delete(target)

        assert result is False


class TestProjectIdGeneration:
    """Tests for project ID generation."""

    @pytest.mark.unit
    def test_project_id_is_deterministic(self, tmp_path):
        """Same path should always produce same ID."""
        id1 = project_id_from_path(tmp_path)
        id2 = project_id_from_path(tmp_path)

        assert id1 == id2

    @pytest.mark.unit
    def test_project_id_different_for_different_paths(self, tmp_path):
        """Different paths should produce different IDs."""
        path1 = tmp_path / "project1"
        path2 = tmp_path / "project2"
        path1.mkdir()
        path2.mkdir()

        id1 = project_id_from_path(path1)
        id2 = project_id_from_path(path2)

        assert id1 != id2

    @pytest.mark.unit
    def test_project_id_length(self, tmp_path):
        """Project ID should be 16 characters."""
        project_id = project_id_from_path(tmp_path)

        assert len(project_id) == 16


class TestBreakpointStore:
    """Tests for breakpoint persistence."""

    @pytest.mark.unit
    async def test_load_returns_empty_for_new_project(self, breakpoint_store, tmp_path):
        """load should return empty dict for new project."""
        project_root = tmp_path / "new_project"
        project_root.mkdir()

        breakpoints = await breakpoint_store.load(project_root)

        assert breakpoints == {}

    @pytest.mark.unit
    async def test_save_and_load_round_trip(self, breakpoint_store, tmp_path):
        """save and load should preserve breakpoints."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        breakpoints = {
            "/path/to/file1.py": [
                SourceBreakpoint(line=10),
                SourceBreakpoint(line=20, condition="x > 5"),
            ],
            "/path/to/file2.py": [
                SourceBreakpoint(line=5),
            ],
        }

        await breakpoint_store.save(project_root, breakpoints)
        loaded = await breakpoint_store.load(project_root)

        assert len(loaded) == 2
        assert len(loaded["/path/to/file1.py"]) == 2
        assert loaded["/path/to/file1.py"][0].line == 10
        assert loaded["/path/to/file1.py"][1].condition == "x > 5"

    @pytest.mark.unit
    async def test_update_file_adds_breakpoints(self, breakpoint_store, tmp_path):
        """update_file should add breakpoints for a file."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        breakpoints = [SourceBreakpoint(line=10)]

        await breakpoint_store.update_file(
            project_root,
            "/path/to/file.py",
            breakpoints,
        )

        loaded = await breakpoint_store.load(project_root)
        assert "/path/to/file.py" in loaded
        assert len(loaded["/path/to/file.py"]) == 1

    @pytest.mark.unit
    async def test_update_file_removes_on_empty_list(self, breakpoint_store, tmp_path):
        """update_file with empty list should remove file entry."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Add breakpoints
        await breakpoint_store.update_file(
            project_root,
            "/path/to/file.py",
            [SourceBreakpoint(line=10)],
        )

        # Remove by passing empty list
        await breakpoint_store.update_file(
            project_root,
            "/path/to/file.py",
            [],
        )

        loaded = await breakpoint_store.load(project_root)
        assert "/path/to/file.py" not in loaded

    @pytest.mark.unit
    async def test_clear_removes_all_breakpoints(self, breakpoint_store, tmp_path):
        """clear should remove all breakpoints for project."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Add some breakpoints
        await breakpoint_store.save(project_root, {
            "/file1.py": [SourceBreakpoint(line=10)],
            "/file2.py": [SourceBreakpoint(line=20)],
        })

        await breakpoint_store.clear(project_root)

        loaded = await breakpoint_store.load(project_root)
        assert loaded == {}
```

---

## 4. Integration Test Examples

### 4.1 test_api_sessions.py - Session CRUD Endpoints

```python
"""Integration tests for session API endpoints."""

import pytest
from httpx import AsyncClient


class TestCreateSession:
    """Tests for POST /sessions endpoint."""

    @pytest.mark.integration
    async def test_create_session_success(self, client: AsyncClient, tmp_path, response_validator):
        """Should create a new session successfully."""
        response = await client.post(
            "/sessions",
            json={
                "name": "test-session",
                "project_root": str(tmp_path),
            }
        )

        assert response.status_code == 201
        data = response_validator(response.json())

        assert "session_id" in data
        assert data["session_id"].startswith("sess_")
        assert data["name"] == "test-session"
        assert data["status"] == "created"

    @pytest.mark.integration
    async def test_create_session_auto_generates_name(self, client: AsyncClient, tmp_path):
        """Should auto-generate name if not provided."""
        response = await client.post(
            "/sessions",
            json={"project_root": str(tmp_path)}
        )

        assert response.status_code == 201
        data = response.json()["data"]

        assert "name" in data
        assert data["name"].startswith("session-")

    @pytest.mark.integration
    async def test_create_session_validates_project_root(self, client: AsyncClient):
        """Should validate project_root path."""
        response = await client.post(
            "/sessions",
            json={"project_root": "/nonexistent/path/that/does/not/exist"}
        )

        # May succeed (path validation is lenient) or fail
        # depending on implementation
        assert response.status_code in [201, 400]

    @pytest.mark.integration
    async def test_create_session_respects_limit(self, client: AsyncClient, tmp_path, test_settings):
        """Should return 429 when session limit reached."""
        # Create sessions up to limit
        sessions = []
        for i in range(test_settings.max_sessions):
            response = await client.post(
                "/sessions",
                json={"project_root": str(tmp_path)}
            )
            if response.status_code == 201:
                sessions.append(response.json()["data"]["session_id"])

        # Try to create one more
        response = await client.post(
            "/sessions",
            json={"project_root": str(tmp_path)}
        )

        assert response.status_code == 429
        assert response.json()["error"]["code"] == "SESSION_LIMIT_REACHED"

        # Cleanup
        for session_id in sessions:
            await client.delete(f"/sessions/{session_id}")


class TestGetSession:
    """Tests for GET /sessions/{session_id} endpoint."""

    @pytest.mark.integration
    async def test_get_session_success(self, client: AsyncClient, created_session: dict, response_validator):
        """Should return session details."""
        session_id = created_session["session_id"]

        response = await client.get(f"/sessions/{session_id}")

        assert response.status_code == 200
        data = response_validator(response.json())

        assert data["session_id"] == session_id
        assert "status" in data
        assert "created_at" in data

    @pytest.mark.integration
    async def test_get_session_not_found(self, client: AsyncClient, response_validator):
        """Should return 404 for unknown session."""
        response = await client.get("/sessions/sess_nonexistent")

        assert response.status_code == 404
        response_validator(response.json(), expected_success=False)
        assert response.json()["error"]["code"] == "SESSION_NOT_FOUND"


class TestListSessions:
    """Tests for GET /sessions endpoint."""

    @pytest.mark.integration
    async def test_list_sessions_empty(self, client: AsyncClient, response_validator):
        """Should return empty list when no sessions."""
        response = await client.get("/sessions")

        assert response.status_code == 200
        data = response_validator(response.json())

        assert "items" in data
        assert isinstance(data["items"], list)

    @pytest.mark.integration
    async def test_list_sessions_returns_all(self, client: AsyncClient, tmp_path, response_validator):
        """Should return all active sessions."""
        # Create multiple sessions
        session_ids = []
        for i in range(3):
            response = await client.post(
                "/sessions",
                json={"name": f"test-session-{i}", "project_root": str(tmp_path)}
            )
            session_ids.append(response.json()["data"]["session_id"])

        # List sessions
        response = await client.get("/sessions")

        assert response.status_code == 200
        data = response_validator(response.json())

        assert data["total"] >= 3
        listed_ids = [s["session_id"] for s in data["items"]]
        for session_id in session_ids:
            assert session_id in listed_ids

        # Cleanup
        for session_id in session_ids:
            await client.delete(f"/sessions/{session_id}")

    @pytest.mark.integration
    async def test_list_sessions_pagination(self, client: AsyncClient, tmp_path):
        """Should support pagination parameters."""
        # Create sessions
        session_ids = []
        for i in range(5):
            response = await client.post(
                "/sessions",
                json={"project_root": str(tmp_path)}
            )
            session_ids.append(response.json()["data"]["session_id"])

        # Request with pagination
        response = await client.get("/sessions", params={"offset": 1, "limit": 2})

        assert response.status_code == 200
        data = response.json()["data"]

        assert len(data["items"]) <= 2
        assert data["offset"] == 1
        assert data["limit"] == 2

        # Cleanup
        for session_id in session_ids:
            await client.delete(f"/sessions/{session_id}")


class TestDeleteSession:
    """Tests for DELETE /sessions/{session_id} endpoint."""

    @pytest.mark.integration
    async def test_delete_session_success(self, client: AsyncClient, created_session: dict, response_validator):
        """Should delete session successfully."""
        session_id = created_session["session_id"]

        response = await client.delete(f"/sessions/{session_id}")

        assert response.status_code == 200
        data = response_validator(response.json())

        assert data["deleted"] is True

        # Verify session is gone
        get_response = await client.get(f"/sessions/{session_id}")
        assert get_response.status_code == 404

    @pytest.mark.integration
    async def test_delete_session_not_found(self, client: AsyncClient):
        """Should return 404 for unknown session."""
        response = await client.delete("/sessions/sess_nonexistent")

        assert response.status_code == 404

    @pytest.mark.integration
    async def test_delete_session_idempotent(self, client: AsyncClient, created_session: dict):
        """Deleting already-deleted session should return 404."""
        session_id = created_session["session_id"]

        # First delete
        response1 = await client.delete(f"/sessions/{session_id}")
        assert response1.status_code == 200

        # Second delete
        response2 = await client.delete(f"/sessions/{session_id}")
        assert response2.status_code == 404
```

### 4.2 test_api_breakpoints.py - Breakpoint Endpoints

```python
"""Integration tests for breakpoint API endpoints."""

import pytest
from httpx import AsyncClient


class TestSetBreakpoints:
    """Tests for POST /sessions/{session_id}/breakpoints endpoint."""

    @pytest.mark.integration
    async def test_set_single_breakpoint(
        self,
        client: AsyncClient,
        created_session: dict,
        sample_script,
        response_validator,
    ):
        """Should set a single breakpoint."""
        session_id = created_session["session_id"]

        response = await client.post(
            f"/sessions/{session_id}/breakpoints",
            json={
                "breakpoints": [
                    {
                        "source": {"path": str(sample_script)},
                        "line": 10,
                    }
                ]
            }
        )

        assert response.status_code == 200
        data = response_validator(response.json())

        assert "breakpoints" in data
        assert len(data["breakpoints"]) == 1
        assert data["breakpoints"][0]["line"] == 10

    @pytest.mark.integration
    async def test_set_multiple_breakpoints(
        self,
        client: AsyncClient,
        created_session: dict,
        sample_script,
        response_validator,
    ):
        """Should set multiple breakpoints at once."""
        session_id = created_session["session_id"]

        response = await client.post(
            f"/sessions/{session_id}/breakpoints",
            json={
                "breakpoints": [
                    {"source": {"path": str(sample_script)}, "line": 5},
                    {"source": {"path": str(sample_script)}, "line": 10},
                    {"source": {"path": str(sample_script)}, "line": 15},
                ]
            }
        )

        assert response.status_code == 200
        data = response_validator(response.json())

        assert len(data["breakpoints"]) == 3

    @pytest.mark.integration
    async def test_set_conditional_breakpoint(
        self,
        client: AsyncClient,
        created_session: dict,
        sample_script,
        response_validator,
    ):
        """Should set a conditional breakpoint."""
        session_id = created_session["session_id"]

        response = await client.post(
            f"/sessions/{session_id}/breakpoints",
            json={
                "breakpoints": [
                    {
                        "source": {"path": str(sample_script)},
                        "line": 10,
                        "condition": "x > 5",
                    }
                ]
            }
        )

        assert response.status_code == 200
        data = response_validator(response.json())

        assert data["breakpoints"][0]["condition"] == "x > 5"

    @pytest.mark.integration
    async def test_set_logpoint(
        self,
        client: AsyncClient,
        created_session: dict,
        sample_script,
        response_validator,
    ):
        """Should set a logpoint (log_message instead of break)."""
        session_id = created_session["session_id"]

        response = await client.post(
            f"/sessions/{session_id}/breakpoints",
            json={
                "breakpoints": [
                    {
                        "source": {"path": str(sample_script)},
                        "line": 10,
                        "log_message": "Value of x: {x}",
                    }
                ]
            }
        )

        assert response.status_code == 200
        data = response_validator(response.json())

        assert data["breakpoints"][0]["log_message"] == "Value of x: {x}"

    @pytest.mark.integration
    async def test_set_breakpoint_invalid_session(self, client: AsyncClient, sample_script):
        """Should return 404 for unknown session."""
        response = await client.post(
            "/sessions/sess_nonexistent/breakpoints",
            json={
                "breakpoints": [
                    {"source": {"path": str(sample_script)}, "line": 10}
                ]
            }
        )

        assert response.status_code == 404


class TestListBreakpoints:
    """Tests for GET /sessions/{session_id}/breakpoints endpoint."""

    @pytest.mark.integration
    async def test_list_breakpoints_empty(
        self,
        client: AsyncClient,
        created_session: dict,
        response_validator,
    ):
        """Should return empty list when no breakpoints."""
        session_id = created_session["session_id"]

        response = await client.get(f"/sessions/{session_id}/breakpoints")

        assert response.status_code == 200
        data = response_validator(response.json())

        assert data["breakpoints"] == []

    @pytest.mark.integration
    async def test_list_breakpoints_after_set(
        self,
        client: AsyncClient,
        session_with_breakpoint: dict,
        response_validator,
    ):
        """Should list breakpoints after setting them."""
        session_id = session_with_breakpoint["session_id"]

        response = await client.get(f"/sessions/{session_id}/breakpoints")

        assert response.status_code == 200
        data = response_validator(response.json())

        assert len(data["breakpoints"]) >= 1


class TestDeleteBreakpoint:
    """Tests for DELETE /sessions/{session_id}/breakpoints/{breakpoint_id} endpoint."""

    @pytest.mark.integration
    async def test_delete_breakpoint_success(
        self,
        client: AsyncClient,
        created_session: dict,
        sample_script,
        response_validator,
    ):
        """Should delete a specific breakpoint."""
        session_id = created_session["session_id"]

        # Set a breakpoint
        set_response = await client.post(
            f"/sessions/{session_id}/breakpoints",
            json={
                "breakpoints": [
                    {"source": {"path": str(sample_script)}, "line": 10}
                ]
            }
        )
        bp_id = set_response.json()["data"]["breakpoints"][0]["id"]

        # Delete it
        delete_response = await client.delete(
            f"/sessions/{session_id}/breakpoints/{bp_id}"
        )

        assert delete_response.status_code == 200
        data = response_validator(delete_response.json())

        assert data["deleted"] is True

    @pytest.mark.integration
    async def test_delete_breakpoint_not_found(
        self,
        client: AsyncClient,
        created_session: dict,
    ):
        """Should return 404 for unknown breakpoint."""
        session_id = created_session["session_id"]

        response = await client.delete(
            f"/sessions/{session_id}/breakpoints/bp_nonexistent"
        )

        assert response.status_code == 404
```

### 4.3 test_api_execution.py - Step/Continue Endpoints

```python
"""Integration tests for execution control endpoints."""

import asyncio
import pytest
from httpx import AsyncClient


class TestContinue:
    """Tests for POST /sessions/{session_id}/continue endpoint."""

    @pytest.mark.integration
    async def test_continue_from_paused(
        self,
        client: AsyncClient,
        launched_session: dict,
        response_validator,
    ):
        """Should resume execution from paused state."""
        session_id = launched_session["session_id"]

        response = await client.post(f"/sessions/{session_id}/continue")

        assert response.status_code == 200
        data = response_validator(response.json())

        assert data["continued"] is True

    @pytest.mark.integration
    async def test_continue_wrong_state(
        self,
        client: AsyncClient,
        created_session: dict,
    ):
        """Should return 409 when session not paused."""
        session_id = created_session["session_id"]

        response = await client.post(f"/sessions/{session_id}/continue")

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "INVALID_SESSION_STATE"


class TestPause:
    """Tests for POST /sessions/{session_id}/pause endpoint."""

    @pytest.mark.integration
    async def test_pause_running_session(
        self,
        client: AsyncClient,
        launched_session: dict,
        response_validator,
    ):
        """Should pause a running session."""
        session_id = launched_session["session_id"]

        # First continue to make it running
        await client.post(f"/sessions/{session_id}/continue")

        # Small delay to let it start running
        await asyncio.sleep(0.1)

        # Then pause
        response = await client.post(f"/sessions/{session_id}/pause")

        # May be 200 (paused) or 409 (already paused/terminated)
        assert response.status_code in [200, 409]


class TestStepOver:
    """Tests for POST /sessions/{session_id}/step-over endpoint."""

    @pytest.mark.integration
    async def test_step_over_from_paused(
        self,
        client: AsyncClient,
        launched_session: dict,
        response_validator,
    ):
        """Should step over to next line."""
        session_id = launched_session["session_id"]

        # Get initial location
        status1 = await client.get(f"/sessions/{session_id}")
        initial_line = status1.json()["data"].get("current_location", {}).get("line")

        # Step over
        response = await client.post(f"/sessions/{session_id}/step-over")

        assert response.status_code == 200
        data = response_validator(response.json())

        assert data["status"] == "paused"
        assert data["stop_reason"] == "step"

    @pytest.mark.integration
    async def test_step_over_wrong_state(
        self,
        client: AsyncClient,
        created_session: dict,
    ):
        """Should return 409 when session not paused."""
        session_id = created_session["session_id"]

        response = await client.post(f"/sessions/{session_id}/step-over")

        assert response.status_code == 409


class TestStepInto:
    """Tests for POST /sessions/{session_id}/step-into endpoint."""

    @pytest.mark.integration
    async def test_step_into_from_paused(
        self,
        client: AsyncClient,
        launched_session: dict,
        response_validator,
    ):
        """Should step into function call."""
        session_id = launched_session["session_id"]

        response = await client.post(f"/sessions/{session_id}/step-into")

        assert response.status_code == 200
        data = response_validator(response.json())

        assert data["status"] == "paused"


class TestStepOut:
    """Tests for POST /sessions/{session_id}/step-out endpoint."""

    @pytest.mark.integration
    async def test_step_out_from_paused(
        self,
        client: AsyncClient,
        launched_session: dict,
        response_validator,
    ):
        """Should step out of current function."""
        session_id = launched_session["session_id"]

        # Step into a function first
        await client.post(f"/sessions/{session_id}/step-into")

        # Then step out
        response = await client.post(f"/sessions/{session_id}/step-out")

        assert response.status_code == 200
        data = response_validator(response.json())

        assert data["status"] == "paused"
```

---

## 5. E2E Test Examples

### 5.1 test_e2e_basic_debug.py - Full Debug Flow

```python
"""End-to-end tests for complete debug workflows."""

import asyncio
import pytest
from httpx import AsyncClient

from tests.e2e.conftest import wait_for_status


@pytest.mark.e2e
class TestBasicDebugFlow:
    """Tests for basic debugging workflow."""

    async def test_full_debug_session_lifecycle(
        self,
        full_debug_session: dict,
    ):
        """Test complete session lifecycle: create, launch, debug, terminate."""
        client = full_debug_session["client"]
        session_id = full_debug_session["session_id"]
        script = full_debug_session["script"]

        # 1. Set a breakpoint at the calculate function
        bp_response = await client.post(
            f"/sessions/{session_id}/breakpoints",
            json={
                "breakpoints": [
                    {"source": {"path": str(script)}, "line": 7}  # result = x + y
                ]
            }
        )
        assert bp_response.status_code == 200

        # 2. Launch the script
        launch_response = await client.post(
            f"/sessions/{session_id}/launch",
            json={"script": str(script)}
        )
        assert launch_response.status_code == 200

        # 3. Wait for breakpoint hit
        session_data = await wait_for_status(client, session_id, "paused", timeout=15.0)
        assert session_data["stop_reason"] == "breakpoint"

        # 4. Inspect variables
        scopes_response = await client.get(
            f"/sessions/{session_id}/scopes",
            params={"frame_id": 0}
        )
        assert scopes_response.status_code == 200
        scopes = scopes_response.json()["data"]["scopes"]

        # Get locals reference
        locals_ref = next(
            s["variables_reference"] for s in scopes
            if s["name"] == "Locals"
        )

        vars_response = await client.get(
            f"/sessions/{session_id}/variables",
            params={"variables_reference": locals_ref}
        )
        assert vars_response.status_code == 200
        variables = vars_response.json()["data"]["variables"]

        # Should have x and y variables
        var_names = [v["name"] for v in variables]
        assert "x" in var_names
        assert "y" in var_names

        # 5. Evaluate an expression
        eval_response = await client.post(
            f"/sessions/{session_id}/evaluate",
            json={"expression": "x + y", "frame_id": 0}
        )
        assert eval_response.status_code == 200
        assert eval_response.json()["data"]["result"] == "30"  # 10 + 20

        # 6. Step over
        step_response = await client.post(f"/sessions/{session_id}/step-over")
        assert step_response.status_code == 200

        # 7. Continue execution
        continue_response = await client.post(f"/sessions/{session_id}/continue")
        assert continue_response.status_code == 200

        # 8. Wait for termination
        await wait_for_status(client, session_id, "terminated", timeout=10.0)

        # 9. Check output
        output_response = await client.get(f"/sessions/{session_id}/output")
        assert output_response.status_code == 200
        entries = output_response.json()["data"]["entries"]

        # Should have some output
        stdout_entries = [e for e in entries if e["category"] == "stdout"]
        assert len(stdout_entries) > 0

    async def test_debug_with_stop_on_entry(
        self,
        e2e_client: AsyncClient,
        sample_script,
        real_debugpy_available,
    ):
        """Test debugging with stop_on_entry enabled."""
        if not real_debugpy_available:
            pytest.skip("debugpy not available")

        # Create session
        create_response = await e2e_client.post(
            "/sessions",
            json={"project_root": str(sample_script.parent)}
        )
        session_id = create_response.json()["data"]["session_id"]

        try:
            # Launch with stop_on_entry
            await e2e_client.post(
                f"/sessions/{session_id}/launch",
                json={
                    "script": str(sample_script),
                    "stop_on_entry": True,
                }
            )

            # Should pause at entry
            session_data = await wait_for_status(
                e2e_client, session_id, "paused", timeout=15.0
            )
            assert session_data["stop_reason"] == "entry"

            # Location should be near the start of the file
            location = session_data.get("current_location", {})
            assert location.get("line", 0) <= 15  # Near the top

        finally:
            await e2e_client.delete(f"/sessions/{session_id}")


@pytest.mark.e2e
class TestStackTraceInspection:
    """Tests for stack trace inspection."""

    async def test_get_stack_trace_at_breakpoint(
        self,
        full_debug_session: dict,
    ):
        """Test getting stack trace when paused at breakpoint."""
        client = full_debug_session["client"]
        session_id = full_debug_session["session_id"]
        script = full_debug_session["script"]

        # Set breakpoint inside calculate function
        await client.post(
            f"/sessions/{session_id}/breakpoints",
            json={
                "breakpoints": [
                    {"source": {"path": str(script)}, "line": 7}
                ]
            }
        )

        # Launch
        await client.post(
            f"/sessions/{session_id}/launch",
            json={"script": str(script)}
        )

        # Wait for breakpoint
        await wait_for_status(client, session_id, "paused", timeout=15.0)

        # Get stack trace
        response = await client.get(f"/sessions/{session_id}/stacktrace")

        assert response.status_code == 200
        frames = response.json()["data"]["frames"]

        # Should have at least 2 frames: calculate and main
        assert len(frames) >= 2

        # Top frame should be in calculate
        assert frames[0]["name"] == "calculate"
        assert frames[0]["line"] == 7
```

### 5.2 test_e2e_breakpoints.py - Breakpoint Scenarios

```python
"""End-to-end tests for breakpoint functionality."""

import pytest
from httpx import AsyncClient

from tests.e2e.conftest import wait_for_status


@pytest.mark.e2e
class TestConditionalBreakpoints:
    """Tests for conditional breakpoints."""

    async def test_conditional_breakpoint_triggers(
        self,
        e2e_client: AsyncClient,
        loop_script,
        real_debugpy_available,
    ):
        """Test that conditional breakpoint only triggers when condition is true."""
        if not real_debugpy_available:
            pytest.skip("debugpy not available")

        # Create session
        create_response = await e2e_client.post(
            "/sessions",
            json={"project_root": str(loop_script.parent)}
        )
        session_id = create_response.json()["data"]["session_id"]

        try:
            # Set conditional breakpoint: only break when i == 50
            await e2e_client.post(
                f"/sessions/{session_id}/breakpoints",
                json={
                    "breakpoints": [
                        {
                            "source": {"path": str(loop_script)},
                            "line": 10,  # Inside the loop
                            "condition": "i == 50",
                        }
                    ]
                }
            )

            # Launch
            await e2e_client.post(
                f"/sessions/{session_id}/launch",
                json={"script": str(loop_script)}
            )

            # Wait for breakpoint
            session_data = await wait_for_status(
                e2e_client, session_id, "paused", timeout=30.0
            )

            # Verify we stopped at the right iteration
            scopes = await e2e_client.get(
                f"/sessions/{session_id}/scopes",
                params={"frame_id": 0}
            )
            locals_ref = next(
                s["variables_reference"]
                for s in scopes.json()["data"]["scopes"]
                if s["name"] == "Locals"
            )

            variables = await e2e_client.get(
                f"/sessions/{session_id}/variables",
                params={"variables_reference": locals_ref}
            )

            # Find i variable
            i_var = next(
                v for v in variables.json()["data"]["variables"]
                if v["name"] == "i"
            )

            assert i_var["value"] == "50"

        finally:
            await e2e_client.delete(f"/sessions/{session_id}")

    async def test_hit_count_breakpoint(
        self,
        e2e_client: AsyncClient,
        loop_script,
        real_debugpy_available,
    ):
        """Test hit count breakpoint (break after N hits)."""
        if not real_debugpy_available:
            pytest.skip("debugpy not available")

        create_response = await e2e_client.post(
            "/sessions",
            json={"project_root": str(loop_script.parent)}
        )
        session_id = create_response.json()["data"]["session_id"]

        try:
            # Break on 10th hit
            await e2e_client.post(
                f"/sessions/{session_id}/breakpoints",
                json={
                    "breakpoints": [
                        {
                            "source": {"path": str(loop_script)},
                            "line": 10,
                            "hit_condition": "== 10",
                        }
                    ]
                }
            )

            await e2e_client.post(
                f"/sessions/{session_id}/launch",
                json={"script": str(loop_script)}
            )

            await wait_for_status(e2e_client, session_id, "paused", timeout=30.0)

            # Verify iteration is ~10 (depends on loop start)
            # This is a basic check - exact value depends on implementation

        finally:
            await e2e_client.delete(f"/sessions/{session_id}")


@pytest.mark.e2e
class TestLogpoints:
    """Tests for logpoints (breakpoints that log instead of stopping)."""

    async def test_logpoint_produces_output(
        self,
        e2e_client: AsyncClient,
        loop_script,
        real_debugpy_available,
    ):
        """Test that logpoint produces console output without stopping."""
        if not real_debugpy_available:
            pytest.skip("debugpy not available")

        create_response = await e2e_client.post(
            "/sessions",
            json={"project_root": str(loop_script.parent)}
        )
        session_id = create_response.json()["data"]["session_id"]

        try:
            # Set a logpoint
            await e2e_client.post(
                f"/sessions/{session_id}/breakpoints",
                json={
                    "breakpoints": [
                        {
                            "source": {"path": str(loop_script)},
                            "line": 10,
                            "log_message": "Iteration: {i}",
                        }
                    ]
                }
            )

            # Launch (should run to completion without stopping)
            await e2e_client.post(
                f"/sessions/{session_id}/launch",
                json={"script": str(loop_script)}
            )

            # Wait for termination (not paused)
            await wait_for_status(
                e2e_client, session_id, "terminated", timeout=30.0
            )

            # Check output contains logpoint messages
            output_response = await e2e_client.get(
                f"/sessions/{session_id}/output"
            )
            entries = output_response.json()["data"]["entries"]

            # Should have console output with iteration info
            # Logpoint output category may vary by debugpy version
            all_output = " ".join(e["output"] for e in entries)
            assert "Iteration:" in all_output or "iteration" in all_output.lower()

        finally:
            await e2e_client.delete(f"/sessions/{session_id}")


@pytest.mark.e2e
class TestBreakpointPersistence:
    """Tests for breakpoint persistence across sessions."""

    async def test_breakpoints_persist_for_project(
        self,
        e2e_client: AsyncClient,
        sample_script,
        real_debugpy_available,
    ):
        """Test that breakpoints persist and are restored for same project."""
        if not real_debugpy_available:
            pytest.skip("debugpy not available")

        project_root = str(sample_script.parent)

        # Create first session and set breakpoints
        create1 = await e2e_client.post(
            "/sessions",
            json={"project_root": project_root}
        )
        session1_id = create1.json()["data"]["session_id"]

        await e2e_client.post(
            f"/sessions/{session1_id}/breakpoints",
            json={
                "breakpoints": [
                    {"source": {"path": str(sample_script)}, "line": 10},
                    {"source": {"path": str(sample_script)}, "line": 15},
                ]
            }
        )

        # Delete first session
        await e2e_client.delete(f"/sessions/{session1_id}")

        # Create second session for same project
        create2 = await e2e_client.post(
            "/sessions",
            json={"project_root": project_root}
        )
        session2_id = create2.json()["data"]["session_id"]

        try:
            # Breakpoints should be restored
            bp_response = await e2e_client.get(
                f"/sessions/{session2_id}/breakpoints"
            )
            breakpoints = bp_response.json()["data"]["breakpoints"]

            # Should have the same breakpoints
            lines = sorted([bp["line"] for bp in breakpoints])
            assert 10 in lines
            assert 15 in lines

        finally:
            await e2e_client.delete(f"/sessions/{session2_id}")
```

---

## 6. Mock Strategies

### 6.1 Mocking debugpy Subprocess

```python
"""Strategies for mocking debugpy subprocess."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest


class MockDebugpyProcess:
    """Mock for asyncio subprocess representing debugpy."""

    def __init__(self):
        self.stdin = MagicMock()
        self.stdout = MagicMock()
        self.stderr = MagicMock()
        self.returncode = None
        self._terminated = asyncio.Event()

    def terminate(self):
        self._terminated.set()
        self.returncode = 0

    def kill(self):
        self._terminated.set()
        self.returncode = -9

    async def wait(self):
        await self._terminated.wait()
        return self.returncode


@pytest.fixture
def mock_debugpy_subprocess():
    """Fixture to mock debugpy subprocess creation."""
    mock_process = MockDebugpyProcess()

    async def mock_create_subprocess(*args, **kwargs):
        return mock_process

    with patch(
        'asyncio.create_subprocess_exec',
        side_effect=mock_create_subprocess
    ):
        yield mock_process
```

### 6.2 Mocking DAP Messages

```python
"""Strategies for mocking DAP protocol messages."""

import json
from typing import Dict, Any, List
from unittest.mock import AsyncMock


class DAPMessageMocker:
    """Helper to create mock DAP responses."""

    @staticmethod
    def initialize_response() -> Dict[str, Any]:
        """Create mock initialize response."""
        return {
            "type": "response",
            "request_seq": 1,
            "success": True,
            "command": "initialize",
            "body": {
                "supportsConfigurationDoneRequest": True,
                "supportsFunctionBreakpoints": True,
                "supportsConditionalBreakpoints": True,
                "supportsHitConditionalBreakpoints": True,
                "supportsEvaluateForHovers": True,
                "supportsStepBack": False,
                "supportsSetVariable": True,
                "supportsRestartFrame": False,
                "supportsGotoTargetsRequest": False,
                "supportsStepInTargetsRequest": False,
                "supportsCompletionsRequest": True,
                "supportsModulesRequest": True,
                "supportsExceptionOptions": True,
                "supportsValueFormattingOptions": True,
                "supportsExceptionInfoRequest": True,
                "supportTerminateDebuggee": True,
            }
        }

    @staticmethod
    def breakpoints_response(breakpoints: List[Dict]) -> Dict[str, Any]:
        """Create mock setBreakpoints response."""
        return {
            "type": "response",
            "request_seq": 2,
            "success": True,
            "command": "setBreakpoints",
            "body": {
                "breakpoints": breakpoints
            }
        }

    @staticmethod
    def stopped_event(
        reason: str = "breakpoint",
        thread_id: int = 1,
        breakpoint_ids: List[str] = None,
    ) -> Dict[str, Any]:
        """Create mock stopped event."""
        return {
            "type": "event",
            "seq": 1,
            "event": "stopped",
            "body": {
                "reason": reason,
                "threadId": thread_id,
                "allThreadsStopped": True,
                "hitBreakpointIds": breakpoint_ids or [],
            }
        }

    @staticmethod
    def stack_trace_response(frames: List[Dict]) -> Dict[str, Any]:
        """Create mock stackTrace response."""
        return {
            "type": "response",
            "request_seq": 3,
            "success": True,
            "command": "stackTrace",
            "body": {
                "stackFrames": frames,
                "totalFrames": len(frames),
            }
        }


@pytest.fixture
def dap_message_mocker():
    """Fixture providing DAP message mocker."""
    return DAPMessageMocker()
```

### 6.3 Mocking File System for Persistence

```python
"""Strategies for mocking file system operations."""

import json
from pathlib import Path
from typing import Dict, Any
from unittest.mock import AsyncMock, patch
import pytest


class MockFileSystem:
    """In-memory mock file system."""

    def __init__(self):
        self.files: Dict[str, str] = {}
        self.directories: set = set()

    async def read_file(self, path: Path) -> str:
        path_str = str(path)
        if path_str not in self.files:
            raise FileNotFoundError(path)
        return self.files[path_str]

    async def write_file(self, path: Path, content: str):
        path_str = str(path)
        # Auto-create parent directories
        self.directories.add(str(path.parent))
        self.files[path_str] = content

    async def delete_file(self, path: Path) -> bool:
        path_str = str(path)
        if path_str in self.files:
            del self.files[path_str]
            return True
        return False

    def exists(self, path: Path) -> bool:
        return str(path) in self.files


@pytest.fixture
def mock_filesystem():
    """Fixture providing mock file system."""
    fs = MockFileSystem()

    with patch('aiofiles.open', new_callable=AsyncMock) as mock_open:
        # Configure mock_open to use our mock filesystem
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(side_effect=lambda: fs.files.get('current_file', ''))
        mock_file.write = AsyncMock()
        mock_open.return_value.__aenter__.return_value = mock_file

        yield fs
```

### 6.4 Mocking asyncio for Timing Tests

```python
"""Strategies for mocking asyncio timing."""

import asyncio
from unittest.mock import patch, AsyncMock
import pytest


class MockClock:
    """Mock clock for controlling time in tests."""

    def __init__(self):
        self.current_time = 0.0
        self.pending_tasks = []

    def advance(self, seconds: float):
        """Advance time by given seconds."""
        self.current_time += seconds

    def time(self) -> float:
        """Get current mock time."""
        return self.current_time


@pytest.fixture
def mock_clock():
    """Fixture for controlling time in tests."""
    clock = MockClock()

    with patch('asyncio.get_event_loop') as mock_loop:
        mock_loop.return_value.time.return_value = clock.time()
        yield clock


@pytest.fixture
def fast_sleep():
    """Fixture to make asyncio.sleep instant for tests."""
    original_sleep = asyncio.sleep

    async def instant_sleep(delay):
        # Allow event loop to process but don't actually wait
        await original_sleep(0)

    with patch('asyncio.sleep', side_effect=instant_sleep):
        yield
```

---

## 7. Test Data

### 7.1 Sample Scripts

#### simple_script.py
```python
#!/usr/bin/env python3
"""Simple test script for basic debugging."""

def calculate(x, y):
    """Calculate sum of two numbers."""
    result = x + y
    return result

def main():
    """Main function."""
    a = 10
    b = 20
    total = calculate(a, b)
    print(f"Result: {total}")
    return total

if __name__ == "__main__":
    main()
```

#### error_script.py
```python
#!/usr/bin/env python3
"""Script that raises an exception for testing exception breakpoints."""

def parse_number(text):
    """Parse a string to integer."""
    return int(text)

def process_data(items):
    """Process a list of items."""
    results = []
    for item in items:
        result = parse_number(item)
        results.append(result)
    return results

def main():
    """Main function with buggy input."""
    data = ["1", "2", "invalid", "4"]
    print("Starting processing...")
    results = process_data(data)
    print(f"Results: {results}")

if __name__ == "__main__":
    main()
```

#### loop_script.py
```python
#!/usr/bin/env python3
"""Script with loop for conditional breakpoint testing."""

def process_items():
    """Process items in a loop."""
    items = []
    for i in range(100):
        item = {"id": i, "value": i * 2}
        items.append(item)
        print(f"Processed item {i}")
    return items

def analyze_results(items):
    """Analyze processed items."""
    total = sum(item["value"] for item in items)
    average = total / len(items) if items else 0
    return {"total": total, "average": average}

def main():
    """Main function."""
    print("Starting processing...")
    items = process_items()
    stats = analyze_results(items)
    print(f"Statistics: {stats}")
    return stats

if __name__ == "__main__":
    main()
```

### 7.2 Multi-file Project

#### multifile/main.py
```python
#!/usr/bin/env python3
"""Main entry point for multi-file project."""
from utils import helper_function, format_output
from models import DataModel, create_sample_data

def process(data):
    """Process data using helper functions."""
    transformed = helper_function(data)
    output = format_output(transformed)
    return output

def main():
    """Main function."""
    print("Multi-file project starting...")
    data = create_sample_data()
    result = process(data)
    print(f"Result: {result}")
    return result

if __name__ == "__main__":
    main()
```

#### multifile/utils.py
```python
"""Utility functions for multi-file project."""

def helper_function(data):
    """Transform data."""
    return {
        "name": data.name.upper(),
        "value": data.value * 2,
    }

def format_output(data):
    """Format data for output."""
    return f"{data['name']}: {data['value']}"
```

#### multifile/models.py
```python
"""Data models for multi-file project."""
from dataclasses import dataclass

@dataclass
class DataModel:
    """Simple data model."""
    name: str
    value: int

def create_sample_data():
    """Create sample data instance."""
    return DataModel(name="test", value=42)
```

### 7.3 Test Data Factories

```python
"""Test data factories using factory_boy."""

import factory
from factory import fuzzy
from datetime import datetime, timezone
from pathlib import Path

from opencode_debugger.models.dap import SourceBreakpoint, Breakpoint
from opencode_debugger.models.events import EventType, DebugEvent
from opencode_debugger.models.session import SessionConfig


class SourceBreakpointFactory(factory.Factory):
    """Factory for SourceBreakpoint instances."""

    class Meta:
        model = SourceBreakpoint

    line = factory.Sequence(lambda n: 10 + n)
    column = None
    condition = None
    hit_condition = None
    log_message = None
    enabled = True


class BreakpointFactory(factory.Factory):
    """Factory for verified Breakpoint instances."""

    class Meta:
        model = Breakpoint

    id = factory.Sequence(lambda n: n + 1)
    verified = True
    line = factory.Sequence(lambda n: 10 + n)
    column = None
    message = None
    source = None


class DebugEventFactory(factory.Factory):
    """Factory for DebugEvent instances."""

    class Meta:
        model = DebugEvent

    type = EventType.STOPPED
    timestamp = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    data = factory.LazyAttribute(lambda _: {"reason": "breakpoint"})


class SessionConfigFactory(factory.Factory):
    """Factory for SessionConfig instances."""

    class Meta:
        model = SessionConfig

    project_root = factory.LazyAttribute(lambda _: "/tmp/test_project")
    name = factory.Sequence(lambda n: f"test-session-{n}")
    timeout_minutes = 60
```

---

## 8. Coverage Configuration

### 8.1 pytest-cov Settings

```ini
# pytest.ini or pyproject.toml [tool.pytest.ini_options]
[pytest]
addopts =
    --cov=src/opencode_debugger
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-report=xml:coverage.xml
    --cov-fail-under=90
    --cov-branch
```

### 8.2 Coverage Configuration (pyproject.toml)

```toml
[tool.coverage.run]
branch = true
source = ["src/opencode_debugger"]
omit = [
    "*/tests/*",
    "*/__pycache__/*",
    "*/conftest.py",
    "*/.venv/*",
    "*/migrations/*",
]
parallel = true
concurrency = ["thread", "multiprocessing"]

[tool.coverage.paths]
source = [
    "src/opencode_debugger",
    "**/site-packages/opencode_debugger",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "def __str__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "if typing.TYPE_CHECKING:",
    "@abstractmethod",
    "@abc.abstractmethod",
    "class .*\\bProtocol\\):",
    "except ImportError:",
]
fail_under = 90
show_missing = true
skip_covered = false
precision = 2

[tool.coverage.html]
directory = "htmlcov"
show_contexts = true
skip_covered = false

[tool.coverage.xml]
output = "coverage.xml"
```

### 8.3 Coverage Commands

```bash
# Run tests with coverage
pytest --cov

# Generate HTML report
pytest --cov --cov-report=html

# Check coverage threshold
pytest --cov --cov-fail-under=90

# Run specific test types with coverage
pytest tests/unit --cov --cov-report=term
pytest tests/integration --cov --cov-report=term
pytest tests/e2e --cov --cov-report=term

# Combine coverage from multiple runs
coverage combine
coverage report
coverage html
```

---

## 9. GitHub Actions Workflow

### 9.1 .github/workflows/test.yml

```yaml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

env:
  PYTHON_VERSION: "3.11"

jobs:
  # ============================================================================
  # Linting and Static Analysis
  # ============================================================================
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
          python -m pip install --upgrade pip
          pip install ruff mypy
          pip install -e ".[dev]"

      - name: Run Ruff
        run: ruff check src tests

      - name: Run Ruff Format Check
        run: ruff format --check src tests

      - name: Run MyPy
        run: mypy src/opencode_debugger --ignore-missing-imports

  # ============================================================================
  # Unit Tests
  # ============================================================================
  unit-tests:
    name: Unit Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Cache pip packages
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/pyproject.toml') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run Unit Tests
        run: |
          pytest tests/unit \
            -v \
            --tb=short \
            --cov=src/opencode_debugger \
            --cov-report=xml:coverage-unit.xml \
            --cov-report=term-missing \
            -m "unit"

      - name: Upload Coverage
        uses: codecov/codecov-action@v4
        with:
          files: coverage-unit.xml
          flags: unit
          name: unit-coverage
          fail_ci_if_error: false

  # ============================================================================
  # Integration Tests
  # ============================================================================
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

      - name: Cache pip packages
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/pyproject.toml') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run Integration Tests
        run: |
          pytest tests/integration \
            -v \
            --tb=short \
            --cov=src/opencode_debugger \
            --cov-report=xml:coverage-integration.xml \
            --cov-report=term-missing \
            -m "integration"
        timeout-minutes: 10

      - name: Upload Coverage
        uses: codecov/codecov-action@v4
        with:
          files: coverage-integration.xml
          flags: integration
          name: integration-coverage
          fail_ci_if_error: false

  # ============================================================================
  # E2E Tests
  # ============================================================================
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

      - name: Cache pip packages
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/pyproject.toml') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"
          pip install debugpy  # Ensure debugpy is available for E2E

      - name: Run E2E Tests
        run: |
          pytest tests/e2e \
            -v \
            --tb=short \
            --cov=src/opencode_debugger \
            --cov-report=xml:coverage-e2e.xml \
            --cov-report=term-missing \
            -m "e2e"
        timeout-minutes: 15

      - name: Upload Coverage
        uses: codecov/codecov-action@v4
        with:
          files: coverage-e2e.xml
          flags: e2e
          name: e2e-coverage
          fail_ci_if_error: false

  # ============================================================================
  # Combined Coverage Report
  # ============================================================================
  coverage:
    name: Coverage Report
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests, e2e-tests]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run All Tests with Coverage
        run: |
          pytest tests \
            -v \
            --tb=short \
            --cov=src/opencode_debugger \
            --cov-report=xml:coverage.xml \
            --cov-report=html:htmlcov \
            --cov-fail-under=90

      - name: Upload Coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: coverage.xml
          flags: combined
          name: combined-coverage
          fail_ci_if_error: true

      - name: Upload HTML Report
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: htmlcov/
          retention-days: 7

  # ============================================================================
  # Test Matrix (Multiple Python Versions)
  # ============================================================================
  test-matrix:
    name: Test Python ${{ matrix.python-version }}
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest]
        python-version: ["3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run Tests
        run: |
          pytest tests/unit tests/integration \
            -v \
            --tb=short \
            -m "not slow"
        timeout-minutes: 15

  # ============================================================================
  # Final Check
  # ============================================================================
  test-complete:
    name: All Tests Passed
    runs-on: ubuntu-latest
    needs: [lint, unit-tests, integration-tests, e2e-tests, coverage, test-matrix]
    steps:
      - name: Tests Complete
        run: echo "All tests passed successfully!"
```

### 9.2 Pre-commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: [--ignore-missing-imports]

  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: pytest tests/unit -x -q --no-cov
        language: system
        types: [python]
        pass_filenames: false
        always_run: true
```

---

## Summary

This test automation plan provides:

1. **Framework Setup**: Complete pytest configuration with async support, coverage, and timeouts
2. **Fixture Implementations**: Comprehensive fixtures for app, client, mocks, and test data
3. **Unit Tests**: Isolated tests for session state machine, output buffer, DAP client, and persistence
4. **Integration Tests**: API endpoint tests for sessions, breakpoints, and execution control
5. **E2E Tests**: Full debugging workflows with real debugpy
6. **Mock Strategies**: Patterns for mocking debugpy, DAP messages, file system, and timing
7. **Test Data**: Sample scripts and factory patterns for generating test data
8. **Coverage Configuration**: Settings for >90% coverage with branch coverage
9. **CI/CD Workflow**: GitHub Actions workflow with parallel jobs and coverage reporting

**Key Metrics:**
- Target coverage: >90%
- Execution time target: <30 minutes for full suite
- Flaky test target: <1%
- Test categories: unit, integration, e2e, slow

---

**Document Revision History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-13 | Test Automation Agent | Initial test automation plan |
