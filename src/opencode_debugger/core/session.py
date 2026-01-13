"""Session lifecycle management."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from opencode_debugger.adapters.debugpy_adapter import DebugpyAdapter
from opencode_debugger.config import settings
from opencode_debugger.core.events import EventQueue
from opencode_debugger.core.exceptions import (
    InvalidSessionStateError,
    SessionLimitError,
    SessionNotFoundError,
)
from opencode_debugger.models.dap import (
    AttachConfig,
    Breakpoint,
    LaunchConfig,
    Scope,
    SourceBreakpoint,
    StackFrame,
    Thread,
    Variable,
)
from opencode_debugger.models.events import EventType
from opencode_debugger.models.session import SessionConfig, SessionInfo
from opencode_debugger.persistence.breakpoints import BreakpointStore
from opencode_debugger.persistence.sessions import PersistedSession, SessionStore
from opencode_debugger.utils.output_buffer import OutputBuffer

logger = logging.getLogger(__name__)


class SessionState(str, Enum):
    """Possible session states."""

    CREATED = "created"
    LAUNCHING = "launching"
    RUNNING = "running"
    PAUSED = "paused"
    TERMINATED = "terminated"
    FAILED = "failed"


class Session:
    """Represents a single debug session."""

    def __init__(
        self,
        session_id: str,
        project_root: Path,
        name: Optional[str] = None,
        timeout_minutes: int = 60,
    ):
        self.id = session_id
        self.project_root = project_root
        self.name = name or f"session-{session_id[:8]}"
        self.timeout_minutes = timeout_minutes

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
        self.stop_location: Optional[dict[str, Any]] = None

        # Breakpoints (file path -> list of breakpoints)
        self._breakpoints: dict[str, list[SourceBreakpoint]] = {}

        # Watch expressions (evaluated on each stop)
        self._watch_expressions: list[str] = []

    @property
    def state(self) -> SessionState:
        return self._state

    async def transition_to(self, new_state: SessionState) -> None:
        """Thread-safe state transition."""
        async with self._state_lock:
            valid_transitions: dict[SessionState, set[SessionState]] = {
                SessionState.CREATED: {SessionState.LAUNCHING, SessionState.FAILED},
                SessionState.LAUNCHING: {
                    SessionState.RUNNING,
                    SessionState.PAUSED,
                    SessionState.FAILED,
                    SessionState.TERMINATED,
                },
                SessionState.RUNNING: {
                    SessionState.PAUSED,
                    SessionState.TERMINATED,
                    SessionState.FAILED,
                },
                SessionState.PAUSED: {
                    SessionState.RUNNING,
                    SessionState.TERMINATED,
                    SessionState.FAILED,
                },
            }

            if self._state in valid_transitions:
                if new_state not in valid_transitions[self._state]:
                    raise InvalidSessionStateError(
                        self.id,
                        self._state.value,
                        [s.value for s in valid_transitions[self._state]],
                    )

            self._state = new_state
            self.last_activity = datetime.now(timezone.utc)
            logger.info(f"Session {self.id}: state -> {new_state.value}")

    def require_state(self, *states: SessionState) -> None:
        """Raise if not in one of the required states."""
        if self._state not in states:
            raise InvalidSessionStateError(
                self.id,
                self._state.value,
                [s.value for s in states],
            )

    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)

    async def initialize_adapter(self) -> None:
        """Create and initialize the debugpy adapter."""
        self.adapter = DebugpyAdapter(
            session_id=self.id,
            output_callback=self._handle_output,
            event_callback=self._handle_event,
        )
        await self.adapter.initialize()

    async def launch(self, config: LaunchConfig) -> None:
        """Launch the debug target."""
        self.require_state(SessionState.CREATED)
        await self.transition_to(SessionState.LAUNCHING)

        try:
            if self.adapter is None:
                raise InvalidSessionStateError(self.id, "no adapter", ["initialized"])

            async def configure_breakpoints() -> None:
                """Configure breakpoints during DAP configuration phase."""
                # Set source breakpoints
                for file_path, breakpoints in self._breakpoints.items():
                    await self.adapter.set_breakpoints(file_path, breakpoints)  # type: ignore

                # Set exception breakpoints if configured
                if config.stop_on_exception:
                    await self.adapter.set_exception_breakpoints(["uncaught"])  # type: ignore

            await self.adapter.launch(config, configure_callback=configure_breakpoints)
            await self.transition_to(SessionState.RUNNING)
        except Exception as e:
            await self.transition_to(SessionState.FAILED)
            raise

    async def attach(self, config: AttachConfig) -> None:
        """Attach to a running process."""
        self.require_state(SessionState.CREATED)
        await self.transition_to(SessionState.LAUNCHING)

        try:
            if self.adapter is None:
                raise InvalidSessionStateError(self.id, "no adapter", ["initialized"])

            async def configure_breakpoints() -> None:
                """Configure breakpoints during DAP configuration phase."""
                for file_path, breakpoints in self._breakpoints.items():
                    await self.adapter.set_breakpoints(file_path, breakpoints)  # type: ignore

            await self.adapter.attach(config, configure_callback=configure_breakpoints)
            await self.transition_to(SessionState.RUNNING)
        except Exception as e:
            await self.transition_to(SessionState.FAILED)
            raise

    async def set_breakpoints(
        self,
        file_path: str,
        breakpoints: list[SourceBreakpoint],
    ) -> list[Breakpoint]:
        """Set breakpoints for a file."""
        self.touch()
        self._breakpoints[file_path] = breakpoints

        # If already launched, set them immediately
        if self.adapter and self.adapter.is_launched:
            return await self.adapter.set_breakpoints(file_path, breakpoints)

        # Otherwise, return unverified breakpoints
        return [
            Breakpoint(verified=False, line=bp.line, message="Pending launch")
            for bp in breakpoints
        ]

    async def continue_(self, thread_id: Optional[int] = None) -> None:
        """Continue execution."""
        self.require_state(SessionState.PAUSED)
        if self.adapter is None:
            raise InvalidSessionStateError(self.id, "no adapter", ["initialized"])

        tid = thread_id or self.current_thread_id or 1
        await self.adapter.continue_(tid)
        await self.transition_to(SessionState.RUNNING)
        self.stop_reason = None
        self.stop_location = None

    async def pause(self, thread_id: Optional[int] = None) -> None:
        """Pause execution."""
        self.require_state(SessionState.RUNNING)
        if self.adapter is None:
            raise InvalidSessionStateError(self.id, "no adapter", ["initialized"])

        tid = thread_id or self.current_thread_id or 1
        await self.adapter.pause(tid)

    async def step_over(self, thread_id: Optional[int] = None) -> None:
        """Step over (next line)."""
        self.require_state(SessionState.PAUSED)
        if self.adapter is None:
            raise InvalidSessionStateError(self.id, "no adapter", ["initialized"])

        tid = thread_id or self.current_thread_id or 1
        await self.adapter.step_over(tid)
        await self.transition_to(SessionState.RUNNING)

    async def step_into(self, thread_id: Optional[int] = None) -> None:
        """Step into function."""
        self.require_state(SessionState.PAUSED)
        if self.adapter is None:
            raise InvalidSessionStateError(self.id, "no adapter", ["initialized"])

        tid = thread_id or self.current_thread_id or 1
        await self.adapter.step_into(tid)
        await self.transition_to(SessionState.RUNNING)

    async def step_out(self, thread_id: Optional[int] = None) -> None:
        """Step out of function."""
        self.require_state(SessionState.PAUSED)
        if self.adapter is None:
            raise InvalidSessionStateError(self.id, "no adapter", ["initialized"])

        tid = thread_id or self.current_thread_id or 1
        await self.adapter.step_out(tid)
        await self.transition_to(SessionState.RUNNING)

    async def get_threads(self) -> list[Thread]:
        """Get all threads."""
        if self.adapter is None:
            return []
        return await self.adapter.threads()

    async def get_stack_trace(
        self,
        thread_id: Optional[int] = None,
        start_frame: int = 0,
        levels: int = 20,
    ) -> list[StackFrame]:
        """Get stack trace for a thread."""
        if self.adapter is None:
            return []

        tid = thread_id or self.current_thread_id or 1
        return await self.adapter.stack_trace(tid, start_frame, levels)

    async def get_scopes(self, frame_id: int) -> list[Scope]:
        """Get scopes for a frame."""
        if self.adapter is None:
            return []
        return await self.adapter.scopes(frame_id)

    async def get_variables(
        self,
        variables_ref: int,
        start: int = 0,
        count: int = 100,
    ) -> list[Variable]:
        """Get variables for a scope."""
        if self.adapter is None:
            return []
        return await self.adapter.variables(variables_ref, start, count)

    async def evaluate(
        self,
        expression: str,
        frame_id: Optional[int] = None,
        context: str = "watch",
    ) -> dict[str, Any]:
        """Evaluate an expression."""
        if self.adapter is None:
            raise InvalidSessionStateError(self.id, "no adapter", ["initialized"])
        return await self.adapter.evaluate(expression, frame_id, context)

    async def cleanup(self) -> None:
        """Clean up session resources."""
        if self.adapter:
            await self.adapter.disconnect()
            self.adapter = None

        self.output_buffer.clear()
        self.event_queue.clear()
        logger.info(f"Session {self.id}: cleaned up")

    # Watch expression methods

    def add_watch(self, expression: str) -> list[str]:
        """Add a watch expression.

        Args:
            expression: Expression to watch

        Returns:
            Current list of watch expressions
        """
        self.touch()
        if expression not in self._watch_expressions:
            self._watch_expressions.append(expression)
        return self._watch_expressions.copy()

    def remove_watch(self, expression: str) -> list[str]:
        """Remove a watch expression.

        Args:
            expression: Expression to remove

        Returns:
            Current list of watch expressions
        """
        self.touch()
        if expression in self._watch_expressions:
            self._watch_expressions.remove(expression)
        return self._watch_expressions.copy()

    def list_watches(self) -> list[str]:
        """Get all watch expressions.

        Returns:
            List of watch expressions
        """
        return self._watch_expressions.copy()

    def clear_watches(self) -> None:
        """Clear all watch expressions."""
        self.touch()
        self._watch_expressions.clear()

    async def evaluate_watches(
        self,
        frame_id: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """Evaluate all watch expressions.

        Args:
            frame_id: Frame to evaluate in (uses current frame if None)

        Returns:
            List of evaluation results with expression, result, type, and error
        """
        if not self.adapter or self._state != SessionState.PAUSED:
            return []

        results: list[dict[str, Any]] = []
        for expr in self._watch_expressions:
            try:
                result = await self.adapter.evaluate(expr, frame_id, "watch")
                results.append({
                    "expression": expr,
                    "result": result.get("result", ""),
                    "type": result.get("type"),
                    "variables_reference": result.get("variablesReference", 0),
                    "error": None,
                })
            except Exception as e:
                results.append({
                    "expression": expr,
                    "result": None,
                    "type": None,
                    "variables_reference": 0,
                    "error": str(e),
                })
        return results

    # Persistence methods

    def to_persisted(self, server_shutdown: bool = False) -> PersistedSession:
        """Convert to persistable format for recovery.

        Args:
            server_shutdown: Whether this is during graceful shutdown

        Returns:
            PersistedSession for storage
        """
        from datetime import datetime, timezone

        return PersistedSession(
            id=self.id,
            name=self.name,
            project_root=str(self.project_root),
            state=self._state.value,
            created_at=self.created_at,
            last_activity=self.last_activity,
            breakpoints={
                path: [bp.model_dump() for bp in bps]
                for path, bps in self._breakpoints.items()
            },
            watch_expressions=self._watch_expressions.copy(),
            saved_at=datetime.now(timezone.utc),
            server_shutdown=server_shutdown,
        )

    @classmethod
    def from_persisted(cls, data: PersistedSession) -> "Session":
        """Create a new session initialized from persisted data.

        Note: This creates a NEW session with the same settings,
        not a restored connection to the old debug process.

        Args:
            data: Persisted session data

        Returns:
            New Session with settings from persisted data
        """
        session = cls(
            session_id=data.id,
            project_root=Path(data.project_root),
            name=data.name,
        )

        # Restore breakpoints
        for path, bps in data.breakpoints.items():
            session._breakpoints[path] = [
                SourceBreakpoint(**bp) for bp in bps
            ]

        # Restore watch expressions
        session._watch_expressions = data.watch_expressions.copy()

        return session

    def _handle_output(self, category: str, content: str) -> None:
        """Handle output from debugpy."""
        self.output_buffer.append(category, content)

    async def _handle_event(self, event_type: EventType, data: dict[str, Any]) -> None:
        """Handle debug events from debugpy."""
        await self.event_queue.put(event_type, data)

        if event_type == EventType.STOPPED:
            self.current_thread_id = data.get("threadId")
            self.stop_reason = data.get("reason")
            # Update state to paused
            try:
                await self.transition_to(SessionState.PAUSED)
            except InvalidSessionStateError:
                pass  # May already be paused or terminated

        elif event_type == EventType.CONTINUED:
            try:
                await self.transition_to(SessionState.RUNNING)
            except InvalidSessionStateError:
                pass

        elif event_type in (EventType.TERMINATED, EventType.EXITED):
            try:
                await self.transition_to(SessionState.TERMINATED)
            except InvalidSessionStateError:
                pass

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
            stop_location=self.stop_location,
        )


class SessionManager:
    """Manages all debug sessions."""

    def __init__(
        self,
        breakpoint_store: Optional[BreakpointStore] = None,
        session_store: Optional[SessionStore] = None,
    ):
        self._sessions: dict[str, Session] = {}
        self._lock = asyncio.Lock()
        self._breakpoint_store = breakpoint_store or BreakpointStore()
        self._session_store = session_store or SessionStore()
        self._cleanup_task: Optional[asyncio.Task[None]] = None
        self._persist_task: Optional[asyncio.Task[None]] = None
        self._recoverable_sessions: dict[str, PersistedSession] = {}

    async def start(self) -> None:
        """Start the session manager and background tasks."""
        settings.ensure_directories()

        # Load recoverable sessions from previous run
        await self._load_recoverable_sessions()

        # Start background tasks
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._persist_task = asyncio.create_task(self._persist_loop())
        logger.info("SessionManager started")

    async def stop(self) -> None:
        """Stop the session manager and cleanup all sessions."""
        # Cancel background tasks
        for task in [self._cleanup_task, self._persist_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Persist and terminate all sessions
        async with self._lock:
            for session in list(self._sessions.values()):
                # Save session state for recovery
                try:
                    persisted = session.to_persisted(server_shutdown=True)
                    await self._session_store.save(persisted)
                except Exception as e:
                    logger.warning(f"Failed to persist session {session.id}: {e}")

                # Save breakpoints
                await self._breakpoint_store.save(session.project_root, session._breakpoints)
                await session.cleanup()
            self._sessions.clear()

        logger.info("SessionManager stopped (sessions persisted for recovery)")

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
                timeout_minutes=config.timeout_minutes,
            )

            # Initialize adapter
            await session.initialize_adapter()

            # Load existing breakpoints for this project
            breakpoints = await self._breakpoint_store.load(session.project_root)
            session._breakpoints = breakpoints

            self._sessions[session_id] = session
            logger.info(f"Created session {session_id} for {config.project_root}")
            return session

    async def get_session(self, session_id: str) -> Session:
        """Get a session by ID."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise SessionNotFoundError(session_id)
            session.touch()
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

            # Save breakpoints before cleanup
            await self._breakpoint_store.save(session.project_root, session._breakpoints)
            await session.cleanup()
            logger.info(f"Terminated session {session_id}")

    async def save_breakpoints(self, session: Session) -> None:
        """Save session breakpoints to persistence."""
        await self._breakpoint_store.save(session.project_root, session._breakpoints)

    async def _cleanup_loop(self) -> None:
        """Background task to cleanup stale sessions."""
        while True:
            await asyncio.sleep(60)  # Check every minute
            await self._cleanup_stale_sessions()

    async def _cleanup_stale_sessions(self) -> None:
        """Remove sessions that have exceeded timeout."""
        now = datetime.now(timezone.utc)
        async with self._lock:
            stale_ids: list[str] = []
            for session_id, session in self._sessions.items():
                idle_seconds = (now - session.last_activity).total_seconds()
                timeout_seconds = session.timeout_minutes * 60

                if idle_seconds > timeout_seconds:
                    stale_ids.append(session_id)
                    logger.info(f"Session {session_id} expired (idle {idle_seconds:.0f}s)")

            for session_id in stale_ids:
                session = self._sessions.pop(session_id)
                await self._breakpoint_store.save(session.project_root, session._breakpoints)
                await session.cleanup()

    @property
    def active_count(self) -> int:
        """Number of active sessions."""
        return len(self._sessions)

    # Recovery methods

    async def _load_recoverable_sessions(self) -> None:
        """Load sessions from previous server run for recovery."""
        try:
            # Clean up very old sessions first
            await self._session_store.cleanup_old(max_age_hours=24)

            # Load remaining sessions
            persisted = await self._session_store.list_all()
            for session_data in persisted:
                self._recoverable_sessions[session_data.id] = session_data
                logger.info(
                    f"Loaded recoverable session {session_data.id} "
                    f"(project: {session_data.project_root})"
                )

            if self._recoverable_sessions:
                logger.info(
                    f"Found {len(self._recoverable_sessions)} recoverable sessions"
                )
        except Exception as e:
            logger.warning(f"Failed to load recoverable sessions: {e}")

    async def _persist_loop(self) -> None:
        """Background task to periodically persist active sessions."""
        while True:
            await asyncio.sleep(300)  # Every 5 minutes
            await self._persist_active_sessions()

    async def _persist_active_sessions(self) -> None:
        """Persist all active sessions for crash recovery."""
        async with self._lock:
            for session in self._sessions.values():
                try:
                    persisted = session.to_persisted(server_shutdown=False)
                    await self._session_store.save(persisted)
                except Exception as e:
                    logger.warning(f"Failed to persist session {session.id}: {e}")

    async def list_recoverable_sessions(self) -> list[PersistedSession]:
        """List sessions available for recovery.

        Returns:
            List of persisted sessions that can be recovered
        """
        return list(self._recoverable_sessions.values())

    async def get_recoverable_session(self, session_id: str) -> Optional[PersistedSession]:
        """Get a specific recoverable session.

        Args:
            session_id: Session ID to get

        Returns:
            PersistedSession if found, None otherwise
        """
        return self._recoverable_sessions.get(session_id)

    async def recover_session(self, session_id: str) -> Session:
        """Create a new session from recoverable session data.

        This creates a NEW debug session initialized with the settings
        (breakpoints, watch expressions) from the previous session.
        The debug process itself cannot be restored.

        Args:
            session_id: ID of the recoverable session

        Returns:
            New Session with recovered settings

        Raises:
            SessionNotFoundError: If session not found in recoverable list
            SessionLimitError: If max sessions reached
        """
        async with self._lock:
            if len(self._sessions) >= settings.max_sessions:
                raise SessionLimitError(settings.max_sessions)

            persisted = self._recoverable_sessions.get(session_id)
            if not persisted:
                raise SessionNotFoundError(session_id)

            # Create new session with recovered settings
            session = Session.from_persisted(persisted)

            # Initialize adapter
            await session.initialize_adapter()

            # Remove from recoverable list and delete persisted file
            del self._recoverable_sessions[session_id]
            await self._session_store.delete(session_id)

            self._sessions[session_id] = session
            logger.info(f"Recovered session {session_id} for {persisted.project_root}")
            return session

    async def dismiss_recoverable_session(self, session_id: str) -> bool:
        """Dismiss a recoverable session without recovering it.

        Args:
            session_id: Session ID to dismiss

        Returns:
            True if dismissed, False if not found
        """
        if session_id in self._recoverable_sessions:
            del self._recoverable_sessions[session_id]
            await self._session_store.delete(session_id)
            logger.info(f"Dismissed recoverable session {session_id}")
            return True
        return False
