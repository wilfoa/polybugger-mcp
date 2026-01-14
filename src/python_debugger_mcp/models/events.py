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
    EXITED = "exited"


class StopReason(str, Enum):
    """Reasons for stopping execution."""

    BREAKPOINT = "breakpoint"
    STEP = "step"
    EXCEPTION = "exception"
    PAUSE = "pause"
    ENTRY = "entry"
    GOTO = "goto"
    FUNCTION_BREAKPOINT = "function breakpoint"
    DATA_BREAKPOINT = "data breakpoint"


class DebugEvent(BaseModel):
    """Debug event from debugpy."""

    type: EventType
    timestamp: datetime
    data: dict[str, Any] = Field(default_factory=dict)


class StoppedEventData(BaseModel):
    """Data for stopped events."""

    reason: StopReason
    thread_id: int
    all_threads_stopped: bool = True
    description: str | None = None
    text: str | None = None


class OutputEventData(BaseModel):
    """Data for output events."""

    category: str  # "stdout", "stderr", "console"
    output: str
    source: str | None = None
    line: int | None = None


class TerminatedEventData(BaseModel):
    """Data for terminated events."""

    restart: bool = False
    exit_code: int | None = None
