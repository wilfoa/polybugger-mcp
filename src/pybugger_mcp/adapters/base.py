"""Abstract base class for debug adapters.

This module defines the interface that all language-specific debug adapters
must implement. The abstraction allows supporting multiple languages
(Python, Node.js, Go, etc.) through the same MCP interface.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from enum import Enum
from typing import Any

from pybugger_mcp.models.dap import (
    Breakpoint,
    Scope,
    SourceBreakpoint,
    StackFrame,
    Thread,
    Variable,
)
from pybugger_mcp.models.events import EventType


class Language(str, Enum):
    """Supported programming languages."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUST = "rust"
    CPP = "cpp"
    C = "c"
    JAVA = "java"
    RUBY = "ruby"
    PHP = "php"


@dataclass
class LaunchConfig:
    """Language-agnostic launch configuration.

    Each adapter may use different subsets of these options
    or interpret them differently based on the language.
    """

    program: str | None = None
    args: list[str] | None = None
    cwd: str | None = None
    env: dict[str, str] | None = None
    stop_on_entry: bool = False

    # Language-specific options (passed through to adapter)
    # Python: module, django, flask, etc.
    # Node: runtimeArgs, skipFiles, etc.
    # Go: buildFlags, dlvFlags, etc.
    extra: dict[str, Any] | None = None


@dataclass
class AttachConfig:
    """Language-agnostic attach configuration."""

    # Common options
    host: str = "127.0.0.1"
    port: int | None = None
    process_id: int | None = None

    # Language-specific options
    extra: dict[str, Any] | None = None


class DebugAdapter(ABC):
    """Abstract base class for debug adapters.

    Each language-specific adapter (debugpy, delve, vscode-js-debug, etc.)
    must implement this interface. The adapter is responsible for:

    1. Starting/managing the debug server process
    2. Translating high-level operations to DAP messages
    3. Handling language-specific quirks and options

    The DAPClient handles the low-level protocol communication.
    """

    def __init__(
        self,
        session_id: str,
        output_callback: Callable[[str, str], Any] | None = None,
        event_callback: Callable[[EventType, dict[str, Any]], Coroutine[Any, Any, None]]
        | None = None,
    ):
        """Initialize the adapter.

        Args:
            session_id: Unique session identifier
            output_callback: Callback for program output (category, text)
            event_callback: Async callback for debug events
        """
        self.session_id = session_id
        self._output_callback = output_callback
        self._event_callback = event_callback

    @property
    @abstractmethod
    def language(self) -> Language:
        """The language this adapter supports."""
        ...

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Whether the adapter is connected to the debug server."""
        ...

    @property
    @abstractmethod
    def is_launched(self) -> bool:
        """Whether a debug target has been launched."""
        ...

    @property
    @abstractmethod
    def capabilities(self) -> dict[str, Any]:
        """Debug adapter capabilities from initialize response."""
        ...

    # =========================================================================
    # Lifecycle Methods
    # =========================================================================

    @abstractmethod
    async def initialize(self) -> dict[str, Any]:
        """Start the debug server and initialize DAP connection.

        This should:
        1. Start the debug adapter process (debugpy, dlv, etc.)
        2. Establish DAP connection
        3. Send DAP initialize request
        4. Return capabilities

        Returns:
            Debug adapter capabilities dictionary
        """
        ...

    @abstractmethod
    async def launch(self, config: LaunchConfig | Any, **kwargs: Any) -> None:
        """Launch a program for debugging.

        Args:
            config: Launch configuration (adapter-specific type allowed)
            **kwargs: Additional adapter-specific options

        Raises:
            LaunchError: If launch fails

        Note:
            Each adapter may accept its own config type with language-specific
            options. The base LaunchConfig provides common options.
        """
        ...

    @abstractmethod
    async def attach(self, config: AttachConfig | Any, **kwargs: Any) -> None:
        """Attach to a running process.

        Args:
            config: Attach configuration (adapter-specific type allowed)
            **kwargs: Additional adapter-specific options

        Raises:
            LaunchError: If attach fails

        Note:
            Each adapter may accept its own config type with language-specific
            options. The base AttachConfig provides common options.
        """
        ...

    @abstractmethod
    async def disconnect(self, terminate: bool = False) -> None:
        """Disconnect from the debug target.

        Args:
            terminate: Whether to terminate the debuggee
        """
        ...

    @abstractmethod
    async def terminate(self) -> None:
        """Terminate the debug target and cleanup."""
        ...

    # =========================================================================
    # Breakpoint Methods
    # =========================================================================

    @abstractmethod
    async def set_breakpoints(
        self,
        source_path: str,
        breakpoints: list[SourceBreakpoint],
    ) -> list[Breakpoint]:
        """Set breakpoints in a source file.

        Args:
            source_path: Absolute path to source file
            breakpoints: List of breakpoint specifications

        Returns:
            List of actual breakpoints (may differ from requested)
        """
        ...

    @abstractmethod
    async def set_function_breakpoints(
        self,
        names: list[str],
    ) -> list[Breakpoint]:
        """Set breakpoints on function names.

        Args:
            names: List of function names

        Returns:
            List of actual breakpoints
        """
        ...

    @abstractmethod
    async def set_exception_breakpoints(
        self,
        filters: list[str],
    ) -> None:
        """Configure exception breakpoints.

        Args:
            filters: Exception filter IDs (language-specific)
        """
        ...

    # =========================================================================
    # Execution Control
    # =========================================================================

    @abstractmethod
    async def continue_execution(self, thread_id: int | None = None) -> None:
        """Continue execution.

        Args:
            thread_id: Specific thread to continue (None = all)
        """
        ...

    @abstractmethod
    async def pause(self, thread_id: int | None = None) -> None:
        """Pause execution.

        Args:
            thread_id: Specific thread to pause (None = all)
        """
        ...

    @abstractmethod
    async def step_over(self, thread_id: int | None = None) -> None:
        """Step over (next line, skip function calls).

        Args:
            thread_id: Thread to step
        """
        ...

    @abstractmethod
    async def step_into(self, thread_id: int | None = None) -> None:
        """Step into (enter function calls).

        Args:
            thread_id: Thread to step
        """
        ...

    @abstractmethod
    async def step_out(self, thread_id: int | None = None) -> None:
        """Step out (exit current function).

        Args:
            thread_id: Thread to step
        """
        ...

    # =========================================================================
    # Inspection Methods
    # =========================================================================

    @abstractmethod
    async def get_threads(self) -> list[Thread]:
        """Get all threads.

        Returns:
            List of threads
        """
        ...

    @abstractmethod
    async def get_stack_trace(
        self,
        thread_id: int,
        start_frame: int = 0,
        levels: int = 20,
    ) -> list[StackFrame]:
        """Get stack trace for a thread.

        Args:
            thread_id: Thread ID
            start_frame: Starting frame index
            levels: Maximum frames to return

        Returns:
            List of stack frames
        """
        ...

    @abstractmethod
    async def get_scopes(self, frame_id: int) -> list[Scope]:
        """Get variable scopes for a frame.

        Args:
            frame_id: Stack frame ID

        Returns:
            List of scopes (locals, globals, etc.)
        """
        ...

    @abstractmethod
    async def get_variables(
        self,
        variables_reference: int,
        start: int = 0,
        count: int = 0,
    ) -> list[Variable]:
        """Get variables for a scope or container.

        Args:
            variables_reference: Reference from scope or variable
            start: Starting index (for paging)
            count: Maximum to return (0 = all)

        Returns:
            List of variables
        """
        ...

    @abstractmethod
    async def evaluate(
        self,
        expression: str,
        frame_id: int | None = None,
        context: str = "repl",
    ) -> dict[str, Any]:
        """Evaluate an expression.

        Args:
            expression: Expression to evaluate
            frame_id: Stack frame context (None = global)
            context: Evaluation context ("watch", "repl", "hover")

        Returns:
            Evaluation result with 'result', 'type', 'variablesReference'
        """
        ...

    # =========================================================================
    # Optional Methods (default implementations)
    # =========================================================================

    async def get_completions(
        self,
        text: str,
        frame_id: int | None = None,
        column: int = 0,
    ) -> list[dict[str, Any]]:
        """Get code completions (if supported).

        Args:
            text: Text to complete
            frame_id: Stack frame context
            column: Cursor column position

        Returns:
            List of completion items
        """
        return []  # Default: no completions

    async def get_loaded_sources(self) -> list[dict[str, Any]]:
        """Get list of loaded source files (if supported).

        Returns:
            List of source references
        """
        return []  # Default: not supported

    async def get_modules(self) -> list[dict[str, Any]]:
        """Get loaded modules/libraries (if supported).

        Returns:
            List of module info
        """
        return []  # Default: not supported
