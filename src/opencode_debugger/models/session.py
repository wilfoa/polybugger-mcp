"""Session models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SessionConfig(BaseModel):
    """Configuration for creating a new session."""

    project_root: str
    name: Optional[str] = None
    timeout_minutes: int = Field(default=60, ge=1, le=1440)  # Max 24 hours
    recover_from: Optional[str] = None  # Session ID to recover settings from


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
    stop_location: Optional[dict[str, str | int]] = None


class SessionLocation(BaseModel):
    """Current execution location."""

    file: str
    line: int
    column: Optional[int] = None
    function: Optional[str] = None
