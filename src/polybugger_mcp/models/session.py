"""Session models."""

from datetime import datetime

from pydantic import BaseModel, Field


class SessionConfig(BaseModel):
    """Configuration for creating a new session."""

    project_root: str
    name: str | None = None
    language: str = Field(default="python", description="Programming language to debug")
    timeout_minutes: int = Field(default=60, ge=1, le=1440)  # Max 24 hours
    recover_from: str | None = None  # Session ID to recover settings from


class SessionInfo(BaseModel):
    """Session information for API responses."""

    id: str
    name: str
    project_root: str
    state: str
    created_at: datetime
    last_activity: datetime
    current_thread_id: int | None = None
    stop_reason: str | None = None
    stop_location: dict[str, str | int] | None = None


class SessionLocation(BaseModel):
    """Current execution location."""

    file: str
    line: int
    column: int | None = None
    function: str | None = None
