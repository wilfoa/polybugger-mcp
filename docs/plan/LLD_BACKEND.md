# Low-Level Design: Backend Implementation

**Project:** OpenCode Debug Relay Server
**Version:** 1.0
**Date:** January 13, 2026

---

## 1. Project Structure

```
opencode_debugger/
├── src/
│   └── opencode_debugger/
│       ├── __init__.py
│       ├── main.py              # Entry point, FastAPI app
│       ├── config.py            # Settings management
│       ├── api/
│       │   ├── __init__.py
│       │   ├── router.py        # Main router aggregator
│       │   ├── sessions.py      # Session endpoints
│       │   ├── breakpoints.py   # Breakpoint endpoints
│       │   ├── execution.py     # Continue/step endpoints
│       │   ├── inspection.py    # Variables/stacktrace endpoints
│       │   ├── output.py        # Output/events endpoints
│       │   └── server.py        # Health/info endpoints
│       ├── core/
│       │   ├── __init__.py
│       │   ├── session.py       # Session, SessionManager
│       │   ├── events.py        # Event queue, event types
│       │   └── exceptions.py    # Custom exceptions
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── dap_client.py    # DAP protocol client
│       │   └── debugpy_adapter.py  # debugpy subprocess
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
│           └── output_buffer.py # Ring buffer implementation
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_session.py
│   ├── test_dap_client.py
│   ├── test_persistence.py
│   └── test_api/
│       ├── test_sessions.py
│       └── test_breakpoints.py
├── pyproject.toml
├── README.md
└── .env.example
```

---

## 2. Module Specifications

### 2.1 config.py - Configuration Management

```python
"""Application configuration using Pydantic Settings."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="OPENCODE_DEBUG_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Server settings
    host: str = "127.0.0.1"
    port: int = 5679
    debug: bool = False

    # Session limits
    max_sessions: int = 10
    session_timeout_seconds: int = 3600  # 1 hour
    session_max_lifetime_seconds: int = 14400  # 4 hours

    # Output buffer
    output_buffer_max_bytes: int = 50 * 1024 * 1024  # 50MB

    # Persistence
    data_dir: Path = Path.home() / ".opencode-debugger"

    # DAP settings
    dap_timeout_seconds: float = 30.0
    dap_launch_timeout_seconds: float = 60.0

    # Python settings
    default_python_path: str = "python3"

    @property
    def breakpoints_dir(self) -> Path:
        return self.data_dir / "breakpoints"

    @property
    def sessions_dir(self) -> Path:
        return self.data_dir / "sessions"


settings = Settings()
```

**Dependencies:** pydantic-settings

---

### 2.2 core/exceptions.py - Error Hierarchy

```python
"""Custom exception hierarchy for the debug relay."""

from typing import Any, Optional


class DebugRelayError(Exception):
    """Base exception for all debug relay errors."""

    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class SessionError(DebugRelayError):
    """Session-related errors."""
    pass


class SessionNotFoundError(SessionError):
    """Session with given ID does not exist."""

    def __init__(self, session_id: str):
        super().__init__(
            code="SESSION_NOT_FOUND",
            message=f"Session '{session_id}' not found",
            details={"session_id": session_id}
        )


class SessionLimitError(SessionError):
    """Maximum concurrent sessions reached."""

    def __init__(self, max_sessions: int):
        super().__init__(
            code="SESSION_LIMIT_REACHED",
            message=f"Maximum of {max_sessions} concurrent sessions reached",
            details={"max_sessions": max_sessions}
        )


class InvalidSessionStateError(SessionError):
    """Operation not valid in current session state."""

    def __init__(self, session_id: str, current_state: str, required_states: list[str]):
        super().__init__(
            code="INVALID_SESSION_STATE",
            message=f"Session '{session_id}' is in state '{current_state}', "
                    f"but operation requires: {required_states}",
            details={
                "session_id": session_id,
                "current_state": current_state,
                "required_states": required_states
            }
        )


class DAPError(DebugRelayError):
    """DAP protocol errors."""
    pass


class DAPTimeoutError(DAPError):
    """DAP request timed out."""

    def __init__(self, command: str, timeout: float):
        super().__init__(
            code="DEBUGPY_TIMEOUT",
            message=f"debugpy command '{command}' timed out after {timeout}s",
            details={"command": command, "timeout": timeout}
        )


class DAPConnectionError(DAPError):
    """Failed to connect to debugpy."""

    def __init__(self, reason: str):
        super().__init__(
            code="DEBUGPY_ERROR",
            message=f"Failed to connect to debugpy: {reason}",
            details={"reason": reason}
        )


class LaunchError(DAPError):
    """Failed to launch debug target."""

    def __init__(self, reason: str, details: Optional[dict] = None):
        super().__init__(
            code="LAUNCH_FAILED",
            message=f"Failed to launch debug target: {reason}",
            details=details or {}
        )


class PersistenceError(DebugRelayError):
    """Persistence layer errors."""
    pass


class BreakpointError(DebugRelayError):
    """Breakpoint-related errors."""
    pass


class SessionExpiredError(SessionError):
    """Session has expired due to inactivity."""

    def __init__(self, session_id: str):
        super().__init__(
            code="SESSION_EXPIRED",
            message=f"Session '{session_id}' has expired",
            details={"session_id": session_id}
        )


class BreakpointNotFoundError(BreakpointError):
    """Breakpoint with given ID does not exist."""

    def __init__(self, session_id: str, breakpoint_id: str):
        super().__init__(
            code="BREAKPOINT_NOT_FOUND",
            message=f"Breakpoint '{breakpoint_id}' not found in session '{session_id}'",
            details={"session_id": session_id, "breakpoint_id": breakpoint_id}
        )


class ThreadNotFoundError(DebugRelayError):
    """Thread with given ID does not exist."""

    def __init__(self, session_id: str, thread_id: int):
        super().__init__(
            code="THREAD_NOT_FOUND",
            message=f"Thread '{thread_id}' not found in session '{session_id}'",
            details={"session_id": session_id, "thread_id": thread_id}
        )


class FrameNotFoundError(DebugRelayError):
    """Stack frame with given ID does not exist."""

    def __init__(self, session_id: str, frame_id: int):
        super().__init__(
            code="FRAME_NOT_FOUND",
            message=f"Frame '{frame_id}' not found in session '{session_id}'",
            details={"session_id": session_id, "frame_id": frame_id}
        )


class VariableNotFoundError(DebugRelayError):
    """Variable reference does not exist."""

    def __init__(self, session_id: str, variable_ref: int):
        super().__init__(
            code="VARIABLE_NOT_FOUND",
            message=f"Variable reference '{variable_ref}' not found in session '{session_id}'",
            details={"session_id": session_id, "variable_ref": variable_ref}
        )
```

---

### 2.3 core/session.py - Session Management

```python
"""Session lifecycle management."""

import asyncio
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

from opencode_debugger.adapters.debugpy_adapter import DebugpyAdapter
from opencode_debugger.config import settings
from opencode_debugger.core.events import EventQueue
from opencode_debugger.core.exceptions import (
    InvalidSessionStateError,
    SessionLimitError,
    SessionNotFoundError,
)
from opencode_debugger.models.session import SessionConfig, SessionInfo
from opencode_debugger.persistence.breakpoints import BreakpointStore
from opencode_debugger.utils.output_buffer import OutputBuffer


class SessionState(str, Enum):
    """Possible session states.

    Note: Values are lowercase strings to match API contract.
    """

    CREATED = "created"
    LAUNCHING = "launching"
    RUNNING = "running"
    PAUSED = "paused"
    TERMINATED = "terminated"
    FAILED = "failed"  # Session encountered an error


class Session:
    """Represents a single debug session."""

    def __init__(
        self,
        session_id: str,
        project_root: Path,
        name: Optional[str] = None,
    ):
        self.id = session_id
        self.project_root = project_root
        self.name = name or f"session-{session_id[:8]}"

        self._state = SessionState.CREATED
        self._state_lock = asyncio.Lock()

        self.created_at = datetime.now(timezone.utc)
        self.last_activity = self.created_at

        # Components
        self.adapter: Optional[DebugpyAdapter] = None
        self.output_buffer = OutputBuffer(max_size=settings.output_buffer_max_bytes)
        self.event_queue = EventQueue()

        # Debug state
        self.current_thread_id: Optional[int] = None
        self.stop_reason: Optional[str] = None

    @property
    def state(self) -> SessionState:
        return self._state

    async def transition_to(self, new_state: SessionState) -> None:
        """Thread-safe state transition."""
        async with self._state_lock:
            valid_transitions = {
                SessionState.CREATED: {SessionState.LAUNCHING, SessionState.ERROR},
                SessionState.LAUNCHING: {SessionState.RUNNING, SessionState.PAUSED, SessionState.ERROR, SessionState.TERMINATED},
                SessionState.RUNNING: {SessionState.PAUSED, SessionState.TERMINATED, SessionState.ERROR},
                SessionState.PAUSED: {SessionState.RUNNING, SessionState.TERMINATED, SessionState.ERROR},
            }

            if self._state in valid_transitions:
                if new_state not in valid_transitions[self._state]:
                    raise InvalidSessionStateError(
                        self.id,
                        self._state.value,
                        [s.value for s in valid_transitions[self._state]]
                    )

            self._state = new_state
            self.last_activity = datetime.now(timezone.utc)

    def require_state(self, *states: SessionState) -> None:
        """Raise if not in one of the required states."""
        if self._state not in states:
            raise InvalidSessionStateError(
                self.id,
                self._state.value,
                [s.value for s in states]
            )

    async def initialize_adapter(self) -> None:
        """Create and initialize the debugpy adapter."""
        self.adapter = DebugpyAdapter(
            session_id=self.id,
            output_callback=self.output_buffer.append,
            event_callback=self.event_queue.put,
        )
        await self.adapter.initialize()

    async def cleanup(self) -> None:
        """Clean up session resources."""
        if self.adapter:
            await self.adapter.disconnect()
            self.adapter = None

        self.output_buffer.clear()
        self.event_queue.clear()

    def to_info(self) -> SessionInfo:
        """Convert to API response model."""
        return SessionInfo(
            id=self.id,
            name=self.name,
            project_root=str(self.project_root),
            state=self._state.value,
            created_at=self.created_at,
            last_activity=self.last_activity,
            current_thread_id=self.current_thread_id,
            stop_reason=self.stop_reason,
        )


class SessionManager:
    """Manages all debug sessions."""

    def __init__(self, breakpoint_store: BreakpointStore):
        self._sessions: dict[str, Session] = {}
        self._lock = asyncio.Lock()
        self._breakpoint_store = breakpoint_store
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the session manager and background tasks."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        await self._recover_sessions()

    async def stop(self) -> None:
        """Stop the session manager and cleanup all sessions."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Terminate all sessions
        async with self._lock:
            for session in list(self._sessions.values()):
                await session.cleanup()
            self._sessions.clear()

    async def create_session(self, config: SessionConfig) -> Session:
        """Create a new debug session."""
        async with self._lock:
            if len(self._sessions) >= settings.max_sessions:
                raise SessionLimitError(settings.max_sessions)

            session_id = f"sess_{uuid.uuid4().hex[:8]}"
            session = Session(
                session_id=session_id,
                project_root=Path(config.project_root),
                name=config.name,
            )

            # Initialize adapter
            await session.initialize_adapter()

            # Load existing breakpoints for this project
            breakpoints = await self._breakpoint_store.load(session.project_root)
            # Note: breakpoints will be set when launch() is called

            self._sessions[session_id] = session
            return session

    async def get_session(self, session_id: str) -> Session:
        """Get a session by ID."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise SessionNotFoundError(session_id)
            session.last_activity = datetime.now(timezone.utc)
            return session

    async def list_sessions(self) -> list[Session]:
        """List all active sessions."""
        async with self._lock:
            return list(self._sessions.values())

    async def terminate_session(self, session_id: str) -> None:
        """Terminate and remove a session."""
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            if not session:
                raise SessionNotFoundError(session_id)

            await session.cleanup()

    async def _cleanup_loop(self) -> None:
        """Background task to cleanup stale sessions."""
        while True:
            await asyncio.sleep(60)  # Check every minute
            await self._cleanup_stale_sessions()

    async def _cleanup_stale_sessions(self) -> None:
        """Remove sessions that have exceeded timeout."""
        now = datetime.now(timezone.utc)
        async with self._lock:
            stale_ids = []
            for session_id, session in self._sessions.items():
                idle_seconds = (now - session.last_activity).total_seconds()
                lifetime_seconds = (now - session.created_at).total_seconds()

                if (idle_seconds > settings.session_timeout_seconds or
                    lifetime_seconds > settings.session_max_lifetime_seconds):
                    stale_ids.append(session_id)

            for session_id in stale_ids:
                session = self._sessions.pop(session_id)
                await session.cleanup()

    async def _recover_sessions(self) -> None:
        """Recover sessions from persistence on startup."""
        # TODO: Implement session recovery from disk
        pass
```

---

### 2.4 core/events.py - Event Queue

```python
"""Event queue for debug events."""

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

from opencode_debugger.models.events import DebugEvent, EventType


class EventQueue:
    """Thread-safe event queue for a session."""

    def __init__(self, max_size: int = 1000):
        self._queue: asyncio.Queue[DebugEvent] = asyncio.Queue(maxsize=max_size)
        self._history: list[DebugEvent] = []
        self._max_history = 100

    async def put(self, event_type: EventType, data: dict[str, Any]) -> None:
        """Add an event to the queue."""
        event = DebugEvent(
            type=event_type,
            timestamp=datetime.now(timezone.utc),
            data=data,
        )

        # Try to put in queue, drop oldest if full
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            self._queue.put_nowait(event)

        # Add to history
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

    async def get(self, timeout: Optional[float] = None) -> Optional[DebugEvent]:
        """Get next event, optionally with timeout."""
        try:
            if timeout:
                return await asyncio.wait_for(self._queue.get(), timeout=timeout)
            return self._queue.get_nowait()
        except (asyncio.TimeoutError, asyncio.QueueEmpty):
            return None

    async def get_all(self) -> list[DebugEvent]:
        """Get all pending events."""
        events = []
        while True:
            try:
                events.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return events

    def clear(self) -> None:
        """Clear all pending events."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        self._history.clear()
```

---

### 2.5 adapters/dap_client.py - DAP Protocol Client

```python
"""Debug Adapter Protocol (DAP) client implementation."""

import asyncio
import json
from typing import Any, Callable, Optional

from opencode_debugger.core.exceptions import DAPError, DAPTimeoutError
from opencode_debugger.models.dap import (
    DAPMessage,
    DAPRequest,
    DAPResponse,
    DAPEvent,
)


class DAPClient:
    """Client for communicating via Debug Adapter Protocol."""

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        event_callback: Optional[Callable[[str, dict], Any]] = None,
        timeout: float = 30.0,
    ):
        self._reader = reader
        self._writer = writer
        self._event_callback = event_callback
        self._timeout = timeout

        self._seq = 0
        self._pending: dict[int, asyncio.Future] = {}
        self._lock = asyncio.Lock()
        self._reader_task: Optional[asyncio.Task] = None
        self._closed = False

    async def start(self) -> None:
        """Start the message reader loop."""
        self._reader_task = asyncio.create_task(self._read_loop())

    async def stop(self) -> None:
        """Stop the client and cleanup."""
        self._closed = True

        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

        # Cancel all pending requests
        for future in self._pending.values():
            future.cancel()
        self._pending.clear()

        self._writer.close()
        await self._writer.wait_closed()

    async def send_request(
        self,
        command: str,
        arguments: Optional[dict] = None,
        timeout: Optional[float] = None,
    ) -> dict:
        """Send a DAP request and wait for response."""
        async with self._lock:
            self._seq += 1
            seq = self._seq

        request = DAPRequest(
            seq=seq,
            command=command,
            arguments=arguments or {},
        )

        future: asyncio.Future = asyncio.Future()
        self._pending[seq] = future

        try:
            await self._send_message(request.model_dump())
            response = await asyncio.wait_for(
                future,
                timeout=timeout or self._timeout
            )

            if not response.get("success", False):
                raise DAPError(
                    code="DAP_REQUEST_FAILED",
                    message=response.get("message", "Unknown error"),
                    details=response,
                )

            return response.get("body", {})

        except asyncio.TimeoutError:
            raise DAPTimeoutError(command, timeout or self._timeout)

        finally:
            self._pending.pop(seq, None)

    async def _send_message(self, message: dict) -> None:
        """Send a DAP message with Content-Length header."""
        content = json.dumps(message)
        header = f"Content-Length: {len(content)}\r\n\r\n"

        self._writer.write(header.encode("utf-8"))
        self._writer.write(content.encode("utf-8"))
        await self._writer.drain()

    async def _read_loop(self) -> None:
        """Read and dispatch incoming DAP messages."""
        while not self._closed:
            try:
                message = await self._read_message()
                if message is None:
                    break

                await self._handle_message(message)

            except asyncio.CancelledError:
                break
            except Exception as e:
                if not self._closed:
                    # Log error but continue
                    print(f"DAP read error: {e}")

    async def _read_message(self) -> Optional[dict]:
        """Read a single DAP message."""
        # Read headers
        headers = {}
        while True:
            line = await self._reader.readline()
            if not line:
                return None

            line = line.decode("utf-8").strip()
            if not line:
                break

            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()

        # Read content
        content_length = int(headers.get("Content-Length", 0))
        if content_length == 0:
            return None

        content = await self._reader.readexactly(content_length)
        return json.loads(content.decode("utf-8"))

    async def _handle_message(self, message: dict) -> None:
        """Handle an incoming DAP message."""
        msg_type = message.get("type")

        if msg_type == "response":
            # Match response to pending request
            seq = message.get("request_seq")
            future = self._pending.get(seq)
            if future and not future.done():
                future.set_result(message)

        elif msg_type == "event":
            # Dispatch event to callback
            if self._event_callback:
                event_type = message.get("event")
                body = message.get("body", {})
                await self._event_callback(event_type, body)
```

---

### 2.6 adapters/debugpy_adapter.py - debugpy Integration

```python
"""debugpy subprocess adapter."""

import asyncio
import sys
from pathlib import Path
from typing import Any, Callable, Optional

from opencode_debugger.adapters.dap_client import DAPClient
from opencode_debugger.config import settings
from opencode_debugger.core.exceptions import DAPConnectionError, LaunchError
from opencode_debugger.models.dap import (
    LaunchConfig,
    AttachConfig,
    SourceBreakpoint,
    Breakpoint,
    StackFrame,
    Scope,
    Variable,
    Thread,
)
from opencode_debugger.models.events import EventType


class DebugpyAdapter:
    """Adapter for communicating with debugpy via DAP."""

    def __init__(
        self,
        session_id: str,
        output_callback: Optional[Callable[[str, str], Any]] = None,
        event_callback: Optional[Callable[[EventType, dict], Any]] = None,
    ):
        self.session_id = session_id
        self._output_callback = output_callback
        self._event_callback = event_callback

        self._process: Optional[asyncio.subprocess.Process] = None
        self._client: Optional[DAPClient] = None
        self._initialized = False
        self._capabilities: dict = {}

    async def initialize(self) -> dict:
        """Start debugpy and initialize DAP connection."""
        # Start debugpy adapter process
        self._process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m", "debugpy.adapter",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        if not self._process.stdin or not self._process.stdout:
            raise DAPConnectionError("Failed to create debugpy process pipes")

        # Create DAP client
        self._client = DAPClient(
            reader=self._process.stdout,
            writer=self._process.stdin,
            event_callback=self._handle_event,
            timeout=settings.dap_timeout_seconds,
        )
        await self._client.start()

        # Send initialize request
        self._capabilities = await self._client.send_request(
            "initialize",
            {
                "clientID": "opencode-debugger",
                "clientName": "OpenCode Debug Relay",
                "adapterID": "python",
                "pathFormat": "path",
                "linesStartAt1": True,
                "columnsStartAt1": True,
                "supportsVariableType": True,
                "supportsVariablePaging": True,
                "supportsRunInTerminalRequest": False,
            }
        )

        self._initialized = True
        return self._capabilities

    async def launch(self, config: LaunchConfig) -> None:
        """Launch the debug target."""
        self._require_initialized()

        args = {
            "program": str(config.program),
            "args": config.args,
            "cwd": str(config.cwd),
            "env": config.env,
            "stopOnEntry": config.stop_on_entry,
            "justMyCode": False,  # Always debug all code
            "console": "internalConsole",
            "redirectOutput": True,
        }

        if config.python_path:
            args["python"] = str(config.python_path)

        try:
            await self._client.send_request(
                "launch",
                args,
                timeout=settings.dap_launch_timeout_seconds,
            )
        except Exception as e:
            raise LaunchError(str(e))

    async def attach(self, config: AttachConfig) -> None:
        """Attach to a running process."""
        self._require_initialized()

        args = {
            "justMyCode": False,
            "redirectOutput": True,
        }

        if config.process_id:
            args["processId"] = config.process_id
        else:
            args["connect"] = {
                "host": config.host,
                "port": config.port,
            }

        await self._client.send_request("attach", args)

    async def disconnect(self) -> None:
        """Disconnect and cleanup."""
        if self._client:
            try:
                await self._client.send_request(
                    "disconnect",
                    {"terminateDebuggee": True},
                    timeout=5.0,
                )
            except Exception:
                pass

            await self._client.stop()
            self._client = None

        if self._process:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
            self._process = None

        self._initialized = False

    async def set_breakpoints(
        self,
        source_path: str,
        breakpoints: list[SourceBreakpoint],
    ) -> list[Breakpoint]:
        """Set breakpoints for a source file."""
        self._require_initialized()

        response = await self._client.send_request(
            "setBreakpoints",
            {
                "source": {"path": source_path},
                "breakpoints": [bp.model_dump() for bp in breakpoints],
            }
        )

        return [Breakpoint(**bp) for bp in response.get("breakpoints", [])]

    async def set_exception_breakpoints(self, filters: list[str]) -> None:
        """Set exception breakpoints."""
        self._require_initialized()

        await self._client.send_request(
            "setExceptionBreakpoints",
            {"filters": filters}
        )

    async def continue_(self, thread_id: int) -> None:
        """Continue execution."""
        self._require_initialized()
        await self._client.send_request("continue", {"threadId": thread_id})

    async def pause(self, thread_id: int) -> None:
        """Pause execution."""
        self._require_initialized()
        await self._client.send_request("pause", {"threadId": thread_id})

    async def step_over(self, thread_id: int) -> None:
        """Step over (next line)."""
        self._require_initialized()
        await self._client.send_request("next", {"threadId": thread_id})

    async def step_into(self, thread_id: int) -> None:
        """Step into function."""
        self._require_initialized()
        await self._client.send_request("stepIn", {"threadId": thread_id})

    async def step_out(self, thread_id: int) -> None:
        """Step out of function."""
        self._require_initialized()
        await self._client.send_request("stepOut", {"threadId": thread_id})

    async def threads(self) -> list[Thread]:
        """Get all threads."""
        self._require_initialized()
        response = await self._client.send_request("threads")
        return [Thread(**t) for t in response.get("threads", [])]

    async def stack_trace(
        self,
        thread_id: int,
        start_frame: int = 0,
        levels: int = 20,
    ) -> list[StackFrame]:
        """Get stack trace for a thread."""
        self._require_initialized()

        response = await self._client.send_request(
            "stackTrace",
            {
                "threadId": thread_id,
                "startFrame": start_frame,
                "levels": levels,
            }
        )

        return [StackFrame(**f) for f in response.get("stackFrames", [])]

    async def scopes(self, frame_id: int) -> list[Scope]:
        """Get scopes for a stack frame."""
        self._require_initialized()

        response = await self._client.send_request(
            "scopes",
            {"frameId": frame_id}
        )

        return [Scope(**s) for s in response.get("scopes", [])]

    async def variables(
        self,
        variables_ref: int,
        start: int = 0,
        count: int = 100,
    ) -> list[Variable]:
        """Get variables for a scope or variable reference."""
        self._require_initialized()

        response = await self._client.send_request(
            "variables",
            {
                "variablesReference": variables_ref,
                "start": start,
                "count": count,
            }
        )

        return [Variable(**v) for v in response.get("variables", [])]

    async def evaluate(
        self,
        expression: str,
        frame_id: Optional[int] = None,
        context: str = "watch",
    ) -> dict:
        """Evaluate an expression."""
        self._require_initialized()

        args = {
            "expression": expression,
            "context": context,
        }
        if frame_id is not None:
            args["frameId"] = frame_id

        return await self._client.send_request("evaluate", args)

    async def _handle_event(self, event_type: str, body: dict) -> None:
        """Handle DAP events from debugpy."""
        # Map DAP events to our event types
        event_mapping = {
            "stopped": EventType.STOPPED,
            "continued": EventType.CONTINUED,
            "terminated": EventType.TERMINATED,
            "output": EventType.OUTPUT,
            "breakpoint": EventType.BREAKPOINT,
            "thread": EventType.THREAD,
        }

        if event_type == "output" and self._output_callback:
            category = body.get("category", "stdout")
            output = body.get("output", "")
            await self._output_callback(category, output)

        if self._event_callback and event_type in event_mapping:
            await self._event_callback(event_mapping[event_type], body)

    def _require_initialized(self) -> None:
        """Raise if not initialized."""
        if not self._initialized:
            raise DAPConnectionError("Adapter not initialized")
```

---

### 2.7 persistence/storage.py - Atomic File Operations

```python
"""Atomic file storage operations."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Optional

import aiofiles
import aiofiles.os

from opencode_debugger.config import settings
from opencode_debugger.core.exceptions import PersistenceError


def project_id_from_path(project_root: Path) -> str:
    """Generate stable ID from project path."""
    normalized = str(project_root.resolve())
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


async def atomic_write(path: Path, data: dict[str, Any]) -> None:
    """Write JSON data atomically using temp file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = path.with_suffix(".tmp")

    try:
        content = json.dumps(data, indent=2, default=str)

        async with aiofiles.open(temp_path, "w") as f:
            await f.write(content)
            await f.flush()
            os.fsync(f.fileno())

        # Atomic rename
        await aiofiles.os.rename(temp_path, path)

    except Exception as e:
        # Cleanup temp file on error
        try:
            await aiofiles.os.remove(temp_path)
        except FileNotFoundError:
            pass

        raise PersistenceError(
            code="WRITE_FAILED",
            message=f"Failed to write {path}: {e}",
            details={"path": str(path), "error": str(e)}
        )


async def safe_read(path: Path) -> Optional[dict[str, Any]]:
    """Read JSON data, returning None if file doesn't exist."""
    try:
        async with aiofiles.open(path, "r") as f:
            content = await f.read()
            return json.loads(content)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        raise PersistenceError(
            code="INVALID_JSON",
            message=f"Invalid JSON in {path}: {e}",
            details={"path": str(path), "error": str(e)}
        )


async def safe_delete(path: Path) -> bool:
    """Delete a file if it exists. Returns True if deleted."""
    try:
        await aiofiles.os.remove(path)
        return True
    except FileNotFoundError:
        return False


async def list_json_files(directory: Path) -> list[Path]:
    """List all .json files in a directory."""
    if not directory.exists():
        return []

    return [
        directory / name
        for name in os.listdir(directory)
        if name.endswith(".json")
    ]
```

---

### 2.8 persistence/breakpoints.py - Breakpoint Storage

```python
"""Per-project breakpoint persistence."""

from pathlib import Path
from typing import Optional

from opencode_debugger.config import settings
from opencode_debugger.models.dap import SourceBreakpoint
from opencode_debugger.persistence.storage import (
    atomic_write,
    project_id_from_path,
    safe_delete,
    safe_read,
)


class BreakpointStore:
    """Manages per-project breakpoint persistence."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or settings.breakpoints_dir

    def _get_path(self, project_root: Path) -> Path:
        """Get storage path for a project's breakpoints."""
        project_id = project_id_from_path(project_root)
        return self.base_dir / f"{project_id}.json"

    async def load(
        self,
        project_root: Path,
    ) -> dict[str, list[SourceBreakpoint]]:
        """Load all breakpoints for a project.

        Returns:
            Dict mapping file paths to breakpoint lists.
        """
        path = self._get_path(project_root)
        data = await safe_read(path)

        if not data:
            return {}

        result = {}
        for file_path, breakpoints in data.get("breakpoints", {}).items():
            result[file_path] = [
                SourceBreakpoint(**bp) for bp in breakpoints
            ]

        return result

    async def save(
        self,
        project_root: Path,
        breakpoints: dict[str, list[SourceBreakpoint]],
    ) -> None:
        """Save all breakpoints for a project.

        Args:
            project_root: Path to project root
            breakpoints: Dict mapping file paths to breakpoint lists
        """
        path = self._get_path(project_root)

        data = {
            "project_root": str(project_root),
            "breakpoints": {
                file_path: [bp.model_dump() for bp in bps]
                for file_path, bps in breakpoints.items()
            }
        }

        await atomic_write(path, data)

    async def update_file(
        self,
        project_root: Path,
        file_path: str,
        breakpoints: list[SourceBreakpoint],
    ) -> None:
        """Update breakpoints for a single file."""
        all_breakpoints = await self.load(project_root)

        if breakpoints:
            all_breakpoints[file_path] = breakpoints
        else:
            all_breakpoints.pop(file_path, None)

        await self.save(project_root, all_breakpoints)

    async def clear(self, project_root: Path) -> None:
        """Clear all breakpoints for a project."""
        path = self._get_path(project_root)
        await safe_delete(path)
```

---

### 2.9 utils/output_buffer.py - Ring Buffer

```python
"""Ring buffer for output capture with size limits."""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class OutputLine:
    """Single line of output."""

    line_number: int
    category: str  # "stdout", "stderr", "console"
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class OutputPage:
    """Paginated output response."""

    lines: list[OutputLine]
    offset: int
    limit: int
    total: int
    has_more: bool
    truncated: bool  # True if buffer limit was reached


class OutputBuffer:
    """Ring buffer for capturing debug output with size limits."""

    def __init__(self, max_size: int = 50 * 1024 * 1024):
        self.max_size = max_size
        self._entries: deque[OutputLine] = deque()
        self._current_size: int = 0
        self._total_dropped: int = 0
        self._line_counter: int = 0

    def append(self, category: str, content: str) -> None:
        """Add output to the buffer."""
        entry_size = len(content.encode("utf-8"))

        # Drop oldest entries if needed to make room
        while (self._current_size + entry_size > self.max_size
               and self._entries):
            dropped = self._entries.popleft()
            self._current_size -= len(dropped.content.encode("utf-8"))
            self._total_dropped += 1

        self._line_counter += 1
        entry = OutputLine(
            line_number=self._line_counter,
            category=category,
            content=content,
        )

        self._entries.append(entry)
        self._current_size += entry_size

    def get_page(
        self,
        offset: int = 0,
        limit: int = 1000,
        category: Optional[str] = None,
    ) -> OutputPage:
        """Get a page of output."""
        # Filter by category if specified
        if category:
            entries = [e for e in self._entries if e.category == category]
        else:
            entries = list(self._entries)

        total = len(entries)
        page_entries = entries[offset:offset + limit]

        return OutputPage(
            lines=page_entries,
            offset=offset,
            limit=limit,
            total=total,
            has_more=(offset + limit) < total,
            truncated=self._total_dropped > 0,
        )

    def clear(self) -> None:
        """Clear all output."""
        self._entries.clear()
        self._current_size = 0
        self._total_dropped = 0
        self._line_counter = 0

    @property
    def size(self) -> int:
        """Current buffer size in bytes."""
        return self._current_size

    @property
    def total_lines(self) -> int:
        """Total lines in buffer."""
        return len(self._entries)

    @property
    def dropped_lines(self) -> int:
        """Number of lines dropped due to size limit."""
        return self._total_dropped
```

---

## 3. Models

### 3.1 models/dap.py - DAP Models

```python
"""DAP protocol models."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class DAPMessage(BaseModel):
    """Base DAP message."""
    seq: int
    type: str


class DAPRequest(DAPMessage):
    """DAP request message."""
    type: str = "request"
    command: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class DAPResponse(DAPMessage):
    """DAP response message."""
    type: str = "response"
    request_seq: int
    success: bool
    command: str
    message: Optional[str] = None
    body: dict[str, Any] = Field(default_factory=dict)


class DAPEvent(DAPMessage):
    """DAP event message."""
    type: str = "event"
    event: str
    body: dict[str, Any] = Field(default_factory=dict)


class LaunchConfig(BaseModel):
    """Configuration for launching a debug target."""
    program: Optional[str] = None
    module: Optional[str] = None  # Alternative to program (e.g., "pytest")
    args: list[str] = Field(default_factory=list)
    python_args: list[str] = Field(default_factory=list)  # Args to Python interpreter
    cwd: str = "."
    env: dict[str, str] = Field(default_factory=dict)
    python_path: Optional[str] = None
    stop_on_entry: bool = False
    console: str = "internalConsole"  # internalConsole, integratedTerminal, externalTerminal


class AttachConfig(BaseModel):
    """Configuration for attaching to a process."""
    process_id: Optional[int] = None
    host: str = "localhost"
    port: int = 5678


class SourceBreakpoint(BaseModel):
    """Breakpoint definition for a source file."""
    line: int
    column: Optional[int] = None
    condition: Optional[str] = None
    hit_condition: Optional[str] = None
    log_message: Optional[str] = None
    enabled: bool = True


class Breakpoint(BaseModel):
    """Verified breakpoint from debugpy."""
    id: Optional[int] = None
    verified: bool
    line: Optional[int] = None
    column: Optional[int] = None
    message: Optional[str] = None
    source: Optional[dict] = None


class StackFrame(BaseModel):
    """Stack frame information."""
    id: int
    name: str
    source: Optional[dict] = None
    line: int
    column: int = 0
    end_line: Optional[int] = None
    end_column: Optional[int] = None


class Scope(BaseModel):
    """Variable scope."""
    name: str
    presentation_hint: Optional[str] = None
    variables_reference: int = Field(alias="variablesReference")
    named_variables: Optional[int] = Field(None, alias="namedVariables")
    indexed_variables: Optional[int] = Field(None, alias="indexedVariables")
    expensive: bool = False

    class Config:
        populate_by_name = True


class Variable(BaseModel):
    """Variable information."""
    name: str
    value: str
    type: Optional[str] = None
    variables_reference: int = Field(0, alias="variablesReference")
    named_variables: Optional[int] = Field(None, alias="namedVariables")
    indexed_variables: Optional[int] = Field(None, alias="indexedVariables")

    class Config:
        populate_by_name = True


class Thread(BaseModel):
    """Thread information."""
    id: int
    name: str


# models/session.py - Session Models

class SessionConfig(BaseModel):
    """Configuration for creating a new session."""
    project_root: str
    name: Optional[str] = None
    timeout_minutes: int = 60  # Session idle timeout


class SessionInfo(BaseModel):
    """Session information for API responses."""
    id: str
    name: str
    project_root: str
    state: str
    created_at: datetime
    last_activity: datetime
    current_thread_id: Optional[int] = None
    stop_reason: Optional[str] = None
```

---

### 3.2 models/events.py - Event Models

```python
"""Debug event models."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of debug events."""

    STOPPED = "stopped"
    CONTINUED = "continued"
    TERMINATED = "terminated"
    OUTPUT = "output"
    BREAKPOINT = "breakpoint"
    THREAD = "thread"
    MODULE = "module"


class DebugEvent(BaseModel):
    """Debug event from debugpy."""

    type: EventType
    timestamp: datetime
    data: dict[str, Any] = Field(default_factory=dict)
```

---

## 4. DAP Protocol Integration

### 4.1 Initialize Sequence

```
Client                    Relay                     debugpy
  |                         |                          |
  | POST /sessions          |                          |
  |------------------------>|                          |
  |                         | spawn debugpy.adapter    |
  |                         |------------------------->|
  |                         |                          |
  |                         | initialize request       |
  |                         |------------------------->|
  |                         |        {                 |
  |                         |          "command": "initialize",
  |                         |          "arguments": {  |
  |                         |            "clientID": "opencode-debugger",
  |                         |            "adapterID": "python"
  |                         |          }               |
  |                         |        }                 |
  |                         |                          |
  |                         |<-------------------------|
  |                         |  initialize response     |
  |                         |  (capabilities)          |
  |<------------------------|                          |
  | {session_id, state}     |                          |
```

### 4.2 Launch Sequence

```
Client                    Relay                     debugpy
  |                         |                          |
  | POST /sessions/{id}/launch                         |
  | {program, args, cwd}    |                          |
  |------------------------>|                          |
  |                         | launch request           |
  |                         |------------------------->|
  |                         |        {                 |
  |                         |          "command": "launch",
  |                         |          "arguments": {  |
  |                         |            "program": "/path/to/script.py",
  |                         |            "args": ["--verbose"],
  |                         |            "cwd": "/project",
  |                         |            "justMyCode": false
  |                         |          }               |
  |                         |        }                 |
  |                         |                          |
  |                         |<-------------------------|
  |                         |  launch response         |
  |                         |                          |
  |                         |<-------------------------|
  |                         |  initialized event       |
  |                         |  (target ready)          |
  |<------------------------|                          |
  | {status: running}       |                          |
```

### 4.3 Breakpoint Hit Flow

```
Client                    Relay                     debugpy                Target
  |                         |                          |                      |
  |                         |                          | [executing...]       |
  |                         |                          |<---------------------|
  |                         |                          |  hit breakpoint      |
  |                         |<-------------------------|                      |
  |                         |  stopped event           |                      |
  |                         |  {reason: "breakpoint",  |                      |
  |                         |   threadId: 1}           |                      |
  |                         |                          |                      |
  | GET /sessions/{id}/events                          |                      |
  |------------------------>|                          |                      |
  |<------------------------|                          |                      |
  | [{type: stopped, ...}]  |                          |                      |
  |                         |                          |                      |
  | GET /sessions/{id}/stacktrace                      |                      |
  |------------------------>|                          |                      |
  |                         | stackTrace request       |                      |
  |                         |------------------------->|                      |
  |                         |<-------------------------|                      |
  |<------------------------|                          |                      |
  | {frames: [...]}         |                          |                      |
```

---

## 5. Error Handling

### Error to HTTP Status Mapping

| Exception | HTTP Status | Error Code |
|-----------|-------------|------------|
| SessionNotFoundError | 404 | SESSION_NOT_FOUND |
| SessionLimitError | 429 | SESSION_LIMIT_REACHED |
| InvalidSessionStateError | 409 | INVALID_SESSION_STATE |
| SessionExpiredError | 410 | SESSION_EXPIRED |
| DAPTimeoutError | 504 | DEBUGPY_TIMEOUT |
| DAPConnectionError | 502 | DEBUGPY_ERROR |
| LaunchError | 500 | LAUNCH_FAILED |
| BreakpointNotFoundError | 404 | BREAKPOINT_NOT_FOUND |
| ThreadNotFoundError | 404 | THREAD_NOT_FOUND |
| FrameNotFoundError | 404 | FRAME_NOT_FOUND |
| VariableNotFoundError | 404 | VARIABLE_NOT_FOUND |
| PersistenceError | 500 | INTERNAL_ERROR |
| ValidationError (Pydantic) | 422 | INVALID_REQUEST |

---

## 6. Concurrency Design

### Async Patterns

1. **One event loop** - FastAPI/uvicorn manages the event loop
2. **Per-session locks** - `asyncio.Lock()` for state transitions
3. **Global session lock** - For session registry operations
4. **Background tasks** - Cleanup loop via `asyncio.create_task()`

### Task Management

```python
# On startup
@app.on_event("startup")
async def startup():
    await session_manager.start()

# On shutdown
@app.on_event("shutdown")
async def shutdown():
    await session_manager.stop()
```

---

## 7. Implementation Order

| # | Task | Dependencies | Priority |
|---|------|--------------|----------|
| 1 | Project scaffolding (pyproject.toml, structure) | None | P0 |
| 2 | config.py - Settings | 1 | P0 |
| 3 | core/exceptions.py - Errors | 1 | P0 |
| 4 | models/*.py - All models | 1 | P0 |
| 5 | utils/output_buffer.py | 4 | P0 |
| 6 | persistence/storage.py | 3 | P0 |
| 7 | persistence/breakpoints.py | 6 | P0 |
| 8 | adapters/dap_client.py | 3, 4 | P0 |
| 9 | adapters/debugpy_adapter.py | 8 | P0 |
| 10 | core/events.py | 4 | P0 |
| 11 | core/session.py | 5, 7, 9, 10 | P0 |
| 12 | api/server.py - Health endpoints | 2 | P0 |
| 13 | api/sessions.py | 11 | P0 |
| 14 | api/breakpoints.py | 11, 7 | P0 |
| 15 | api/execution.py | 11 | P0 |
| 16 | api/inspection.py | 11 | P0 |
| 17 | api/output.py | 11 | P0 |
| 18 | api/router.py - Aggregate | 12-17 | P0 |
| 19 | main.py - App entry | 18 | P0 |
| 20 | Tests - Unit | All | P1 |
| 21 | Tests - Integration | 20 | P1 |
| 22 | Session recovery | 11, 6 | P2 |

---

## 8. Dependencies

```toml
[project]
name = "opencode-debugger"
version = "0.1.0"
requires-python = ">=3.9"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "debugpy>=1.8.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "aiofiles>=23.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "httpx>=0.26.0",
    "ruff>=0.1.0",
    "mypy>=1.8.0",
]
```
