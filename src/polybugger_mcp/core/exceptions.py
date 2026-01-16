"""Custom exception hierarchy for the debug relay."""

from typing import Any


class DebugRelayError(Exception):
    """Base exception for all debug relay errors."""

    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
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
            details={"session_id": session_id},
        )


class SessionLimitError(SessionError):
    """Maximum concurrent sessions reached."""

    def __init__(self, max_sessions: int):
        super().__init__(
            code="SESSION_LIMIT_REACHED",
            message=f"Maximum of {max_sessions} concurrent sessions reached",
            details={"max_sessions": max_sessions},
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
                "required_states": required_states,
            },
        )


class SessionExpiredError(SessionError):
    """Session has expired due to inactivity."""

    def __init__(self, session_id: str):
        super().__init__(
            code="SESSION_EXPIRED",
            message=f"Session '{session_id}' has expired",
            details={"session_id": session_id},
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
            details={"command": command, "timeout": timeout},
        )


class DAPConnectionError(DAPError):
    """Failed to connect to debugpy."""

    def __init__(self, reason: str):
        super().__init__(
            code="DEBUGPY_ERROR",
            message=f"Failed to connect to debugpy: {reason}",
            details={"reason": reason},
        )


class LaunchError(DAPError):
    """Failed to launch debug target."""

    def __init__(self, reason: str, details: dict[str, Any] | None = None):
        super().__init__(
            code="LAUNCH_FAILED",
            message=f"Failed to launch debug target: {reason}",
            details=details or {},
        )


class PersistenceError(DebugRelayError):
    """Persistence layer errors."""

    pass


class BreakpointError(DebugRelayError):
    """Breakpoint-related errors."""

    pass


class BreakpointNotFoundError(BreakpointError):
    """Breakpoint with given ID does not exist."""

    def __init__(self, session_id: str, breakpoint_id: str):
        super().__init__(
            code="BREAKPOINT_NOT_FOUND",
            message=f"Breakpoint '{breakpoint_id}' not found in session '{session_id}'",
            details={"session_id": session_id, "breakpoint_id": breakpoint_id},
        )


class ThreadNotFoundError(DebugRelayError):
    """Thread with given ID does not exist."""

    def __init__(self, session_id: str, thread_id: int):
        super().__init__(
            code="THREAD_NOT_FOUND",
            message=f"Thread '{thread_id}' not found in session '{session_id}'",
            details={"session_id": session_id, "thread_id": thread_id},
        )


class FrameNotFoundError(DebugRelayError):
    """Stack frame with given ID does not exist."""

    def __init__(self, session_id: str, frame_id: int):
        super().__init__(
            code="FRAME_NOT_FOUND",
            message=f"Frame '{frame_id}' not found in session '{session_id}'",
            details={"session_id": session_id, "frame_id": frame_id},
        )


class VariableNotFoundError(DebugRelayError):
    """Variable reference does not exist."""

    def __init__(self, session_id: str, variable_ref: int):
        super().__init__(
            code="VARIABLE_NOT_FOUND",
            message=f"Variable reference '{variable_ref}' not found in session '{session_id}'",
            details={"session_id": session_id, "variable_ref": variable_ref},
        )


class EvaluateError(DebugRelayError):
    """Expression evaluation failed."""

    def __init__(self, expression: str, reason: str):
        super().__init__(
            code="EVALUATE_ERROR",
            message=f"Failed to evaluate '{expression}': {reason}",
            details={"expression": expression, "reason": reason},
        )
