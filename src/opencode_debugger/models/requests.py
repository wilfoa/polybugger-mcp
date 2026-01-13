"""API request models."""

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class CreateSessionRequest(BaseModel):
    """Request to create a new debug session."""

    project_root: str
    name: Optional[str] = None
    timeout_minutes: int = Field(default=60, ge=1, le=1440)


class LaunchRequest(BaseModel):
    """Request to launch a debug target."""

    program: Optional[str] = None
    module: Optional[str] = None
    args: list[str] = Field(default_factory=list)
    python_args: list[str] = Field(default_factory=list)
    cwd: Optional[str] = None
    env: dict[str, str] = Field(default_factory=dict)
    python_path: Optional[str] = None
    stop_on_entry: bool = False
    stop_on_exception: bool = True

    @field_validator("program", "module")
    @classmethod
    def check_program_or_module(cls, v: Optional[str], info: Any) -> Optional[str]:
        return v

    def model_post_init(self, __context: Any) -> None:
        if not self.program and not self.module:
            raise ValueError("Either 'program' or 'module' must be specified")


class AttachRequest(BaseModel):
    """Request to attach to a running process."""

    process_id: Optional[int] = None
    host: str = "localhost"
    port: int = 5678

    def model_post_init(self, __context: Any) -> None:
        if self.process_id is None and self.port is None:
            raise ValueError("Either 'process_id' or 'port' must be specified")


class BreakpointRequest(BaseModel):
    """Single breakpoint specification."""

    line: int = Field(ge=1)
    column: Optional[int] = Field(default=None, ge=1)
    condition: Optional[str] = None
    hit_condition: Optional[str] = None
    log_message: Optional[str] = None
    enabled: bool = True


class SetBreakpointsRequest(BaseModel):
    """Request to set breakpoints for a file."""

    source: str  # File path
    breakpoints: list[BreakpointRequest] = Field(default_factory=list)


class EvaluateRequest(BaseModel):
    """Request to evaluate an expression."""

    expression: str
    frame_id: Optional[int] = None
    context: str = Field(default="watch", pattern="^(watch|repl|hover)$")


class ContinueRequest(BaseModel):
    """Request to continue execution."""

    thread_id: Optional[int] = None


class PauseRequest(BaseModel):
    """Request to pause execution."""

    thread_id: Optional[int] = None


class StepRequest(BaseModel):
    """Request for step operations."""

    thread_id: Optional[int] = None


class AddWatchRequest(BaseModel):
    """Request to add a watch expression."""

    expression: str


class RemoveWatchRequest(BaseModel):
    """Request to remove a watch expression."""

    expression: str


class EvaluateWatchesRequest(BaseModel):
    """Request to evaluate all watch expressions."""

    frame_id: Optional[int] = None
