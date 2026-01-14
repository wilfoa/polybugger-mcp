"""API response models."""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseMeta(BaseModel):
    """Response metadata."""

    request_id: str
    timestamp: datetime


class ApiError(BaseModel):
    """API error details."""

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response envelope."""

    success: bool
    data: T | None = None
    error: ApiError | None = None
    meta: ResponseMeta


# Session responses


class SessionResponse(BaseModel):
    """Session information response."""

    id: str
    name: str
    project_root: str
    state: str
    created_at: datetime
    last_activity: datetime
    current_thread_id: int | None = None
    stop_reason: str | None = None
    stop_location: dict[str, Any] | None = None


class SessionListResponse(BaseModel):
    """List of sessions response."""

    sessions: list[SessionResponse]
    total: int


# Breakpoint responses


class BreakpointResponse(BaseModel):
    """Breakpoint information."""

    id: int | None = None
    verified: bool
    line: int | None = None
    column: int | None = None
    message: str | None = None
    source: str | None = None


class SetBreakpointsResponse(BaseModel):
    """Response for set breakpoints."""

    breakpoints: list[BreakpointResponse]


class BreakpointListResponse(BaseModel):
    """List of breakpoints for a session."""

    files: dict[str, list[BreakpointResponse]]


# Execution responses


class LocationResponse(BaseModel):
    """Code location."""

    file: str | None = None
    line: int
    column: int | None = None
    function: str | None = None


class ExecutionResponse(BaseModel):
    """Response for execution operations."""

    status: str
    location: LocationResponse | None = None


# Inspection responses


class ThreadResponse(BaseModel):
    """Thread information."""

    id: int
    name: str


class ThreadListResponse(BaseModel):
    """List of threads."""

    threads: list[ThreadResponse]


class SourceResponse(BaseModel):
    """Source file reference."""

    name: str | None = None
    path: str | None = None


class StackFrameResponse(BaseModel):
    """Stack frame information."""

    id: int
    name: str
    source: SourceResponse | None = None
    line: int
    column: int = 0


class StackTraceResponse(BaseModel):
    """Stack trace response."""

    frames: list[StackFrameResponse]
    total_frames: int


class ScopeResponse(BaseModel):
    """Variable scope."""

    name: str
    variables_reference: int
    expensive: bool = False


class ScopesResponse(BaseModel):
    """Scopes response."""

    scopes: list[ScopeResponse]


class VariableResponse(BaseModel):
    """Variable information."""

    name: str
    value: str
    type: str | None = None
    variables_reference: int = 0
    named_variables: int | None = None
    indexed_variables: int | None = None


class VariablesResponse(BaseModel):
    """Variables response."""

    variables: list[VariableResponse]


class EvaluateResponse(BaseModel):
    """Expression evaluation response."""

    result: str
    type: str | None = None
    variables_reference: int = 0


# Output responses


class OutputLineResponse(BaseModel):
    """Single output line."""

    line_number: int
    category: str
    content: str
    timestamp: datetime


class OutputResponse(BaseModel):
    """Output response."""

    lines: list[OutputLineResponse]
    offset: int
    limit: int
    total: int
    has_more: bool
    truncated: bool


# Event responses


class EventResponse(BaseModel):
    """Debug event."""

    type: str
    timestamp: datetime
    data: dict[str, Any] = Field(default_factory=dict)


class EventsResponse(BaseModel):
    """Events response."""

    events: list[EventResponse]


# Server responses


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    active_sessions: int


class InfoResponse(BaseModel):
    """Server info response."""

    name: str
    version: str
    python_version: str
    debugpy_version: str | None = None
    max_sessions: int
    active_sessions: int


# Watch expression responses


class WatchListResponse(BaseModel):
    """List of watch expressions."""

    expressions: list[str]


class WatchResultResponse(BaseModel):
    """Single watch expression result."""

    expression: str
    result: str | None = None
    type: str | None = None
    variables_reference: int = 0
    error: str | None = None


class WatchResultsResponse(BaseModel):
    """Results of evaluating all watch expressions."""

    results: list[WatchResultResponse]


# Recovery responses


class RecoverableSessionResponse(BaseModel):
    """Information about a recoverable session."""

    id: str
    name: str
    project_root: str
    previous_state: str
    created_at: datetime
    last_activity: datetime
    saved_at: datetime
    server_shutdown: bool
    breakpoint_count: int
    watch_expression_count: int


class RecoverableSessionsResponse(BaseModel):
    """List of recoverable sessions."""

    sessions: list[RecoverableSessionResponse]
    total: int
