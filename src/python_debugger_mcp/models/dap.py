"""Debug Adapter Protocol (DAP) models."""

from typing import Any

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
    message: str | None = None
    body: dict[str, Any] = Field(default_factory=dict)


class DAPEvent(DAPMessage):
    """DAP event message."""

    type: str = "event"
    event: str
    body: dict[str, Any] = Field(default_factory=dict)


class LaunchConfig(BaseModel):
    """Configuration for launching a debug target."""

    program: str | None = None
    module: str | None = None  # Alternative to program (e.g., "pytest")
    args: list[str] = Field(default_factory=list)
    python_args: list[str] = Field(default_factory=list)  # Args to Python interpreter
    cwd: str = "."
    env: dict[str, str] = Field(default_factory=dict)
    python_path: str | None = None
    stop_on_entry: bool = False
    stop_on_exception: bool = True
    console: str = "internalConsole"  # internalConsole, integratedTerminal, externalTerminal


class AttachConfig(BaseModel):
    """Configuration for attaching to a process."""

    process_id: int | None = None
    host: str = "localhost"
    port: int = 5678


class SourceBreakpoint(BaseModel):
    """Breakpoint definition for a source file."""

    line: int
    column: int | None = None
    condition: str | None = None
    hit_condition: str | None = None
    log_message: str | None = None
    enabled: bool = True


class Breakpoint(BaseModel):
    """Verified breakpoint from debugpy."""

    id: int | None = None
    verified: bool
    line: int | None = None
    column: int | None = None
    message: str | None = None
    source: dict[str, Any] | None = None


class Source(BaseModel):
    """Source file information."""

    name: str | None = None
    path: str | None = None
    source_reference: int | None = Field(None, alias="sourceReference")

    class Config:
        populate_by_name = True


class StackFrame(BaseModel):
    """Stack frame information."""

    id: int
    name: str
    source: Source | None = None
    line: int
    column: int = 0
    end_line: int | None = Field(None, alias="endLine")
    end_column: int | None = Field(None, alias="endColumn")
    module_id: str | None = Field(None, alias="moduleId")

    class Config:
        populate_by_name = True


class Scope(BaseModel):
    """Variable scope."""

    name: str
    presentation_hint: str | None = Field(None, alias="presentationHint")
    variables_reference: int = Field(alias="variablesReference")
    named_variables: int | None = Field(None, alias="namedVariables")
    indexed_variables: int | None = Field(None, alias="indexedVariables")
    expensive: bool = False

    class Config:
        populate_by_name = True


class Variable(BaseModel):
    """Variable information."""

    name: str
    value: str
    type: str | None = None
    variables_reference: int = Field(0, alias="variablesReference")
    named_variables: int | None = Field(None, alias="namedVariables")
    indexed_variables: int | None = Field(None, alias="indexedVariables")
    evaluate_name: str | None = Field(None, alias="evaluateName")

    class Config:
        populate_by_name = True


class Thread(BaseModel):
    """Thread information."""

    id: int
    name: str


class Module(BaseModel):
    """Module information."""

    id: str | int
    name: str
    path: str | None = None
    version: str | None = None
