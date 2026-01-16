"""Go debug adapter (delve).

This adapter enables debugging Go applications using delve's DAP mode.

Requirements:
- Go 1.16+ installed
- Delve: go install github.com/go-delve/delve/cmd/dlv@latest

Delve supports DAP natively via: dlv dap --listen=:port
"""

import asyncio
import logging
import shutil
import socket
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from polybugger_mcp.adapters.base import (
    AttachConfig as BaseAttachConfig,
    DebugAdapter,
    Language,
    LaunchConfig as BaseLaunchConfig,
)
from polybugger_mcp.adapters.dap_client import DAPClient
from polybugger_mcp.adapters.factory import register_adapter
from polybugger_mcp.core.exceptions import DAPConnectionError, LaunchError
from polybugger_mcp.models.dap import (
    Breakpoint,
    Scope,
    SourceBreakpoint,
    StackFrame,
    Thread,
    Variable,
)
from polybugger_mcp.models.events import EventType

logger = logging.getLogger(__name__)


def _get_free_port() -> int:
    """Get an available port number."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port: int = s.getsockname()[1]
        return port


@dataclass
class GoLaunchConfig:
    """Go-specific launch configuration."""

    program: str | None = None  # Path to main package or .go file
    args: list[str] | None = None
    cwd: str = "."
    env: dict[str, str] | None = None
    stop_on_entry: bool = False

    # Go-specific options
    mode: str = "debug"  # debug, test, exec
    build_flags: list[str] | None = None  # Flags passed to go build
    dlv_flags: list[str] | None = None  # Flags passed to dlv
    output: str | None = None  # Output path for compiled binary


@dataclass
class GoAttachConfig:
    """Go-specific attach configuration."""

    host: str = "127.0.0.1"
    port: int | None = None
    process_id: int | None = None
    mode: str = "local"  # local or remote


@register_adapter(Language.GO)
class DelveAdapter(DebugAdapter):
    """Debug adapter for Go using delve.

    This adapter communicates with delve's built-in DAP server
    to debug Go applications.
    """

    # Name of the delve CLI command
    DLV_CLI = "dlv"

    def __init__(
        self,
        session_id: str,
        output_callback: Callable[[str, str], Any] | None = None,
        event_callback: Callable[[EventType, dict[str, Any]], Coroutine[Any, Any, None]]
        | None = None,
    ):
        """Initialize the adapter."""
        super().__init__(session_id, output_callback, event_callback)

        self._process: asyncio.subprocess.Process | None = None
        self._client: DAPClient | None = None
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._port: int | None = None
        self._initialized = False
        self._capabilities: dict[str, Any] = {}
        self._launched = False
        self._initialized_event: asyncio.Event | None = None

    @property
    def language(self) -> Language:
        return Language.GO

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._initialized

    @property
    def is_launched(self) -> bool:
        return self._launched

    @property
    def capabilities(self) -> dict[str, Any]:
        return self._capabilities

    def _require_initialized(self) -> DAPClient:
        """Raise if not initialized, otherwise return the client."""
        if not self._initialized or self._client is None:
            raise DAPConnectionError("Adapter not initialized")
        return self._client

    async def initialize(self) -> dict[str, Any]:
        """Start delve DAP server and initialize connection.

        Returns:
            Debug adapter capabilities
        """
        # Find dlv CLI
        dlv_path = shutil.which(self.DLV_CLI)
        if not dlv_path:
            raise DAPConnectionError(
                f"'{self.DLV_CLI}' not found. Install with: go install github.com/go-delve/delve/cmd/dlv@latest"
            )

        # Get a free port for the DAP server
        self._port = _get_free_port()

        try:
            # Start dlv in DAP mode
            # dlv dap starts a DAP server that waits for launch/attach requests
            self._process = await asyncio.create_subprocess_exec(
                dlv_path,
                "dap",
                f"--listen=127.0.0.1:{self._port}",
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Wait for the server to start
            await asyncio.sleep(0.3)

            # Connect to the DAP server
            for attempt in range(10):
                try:
                    self._reader, self._writer = await asyncio.wait_for(
                        asyncio.open_connection("127.0.0.1", self._port),
                        timeout=2.0,
                    )
                    break
                except (ConnectionRefusedError, asyncio.TimeoutError):
                    if attempt == 9:
                        raise DAPConnectionError(f"Failed to connect to dlv on port {self._port}")
                    await asyncio.sleep(0.2)

            # Create DAP client
            assert self._reader is not None
            assert self._writer is not None
            self._client = DAPClient(
                reader=self._reader,
                writer=self._writer,
                event_callback=self._handle_event,
            )
            await self._client.start()

            # Send initialize request
            self._capabilities = await self._client.send_request(
                "initialize",
                {
                    "clientID": "polybugger-mcp",
                    "clientName": "Python Debugger MCP",
                    "adapterID": "dlv-dap",
                    "pathFormat": "path",
                    "linesStartAt1": True,
                    "columnsStartAt1": True,
                    "supportsVariableType": True,
                    "supportsVariablePaging": True,
                    "supportsRunInTerminalRequest": False,
                    "supportsProgressReporting": False,
                },
            )

            self._initialized = True
            logger.info(f"Session {self.session_id}: dlv initialized on port {self._port}")
            return self._capabilities

        except Exception as e:
            await self._cleanup()
            raise DAPConnectionError(f"Failed to initialize dlv: {e}")

    async def launch(
        self,
        config: GoLaunchConfig | BaseLaunchConfig | Any,
        configure_callback: Callable[[], Coroutine[Any, Any, None]] | None = None,
        **kwargs: Any,
    ) -> None:
        """Launch a Go program for debugging."""
        client = self._require_initialized()

        # Handle base LaunchConfig by converting to GoLaunchConfig
        if isinstance(config, BaseLaunchConfig):
            config = GoLaunchConfig(
                program=config.program,
                args=config.args,
                cwd=config.cwd or ".",
                env=config.env,
                stop_on_entry=config.stop_on_entry,
            )

        if not config.program:
            raise LaunchError("Program path is required for Go launch")

        # Delve DAP launch request format
        args: dict[str, Any] = {
            "request": "launch",
            "mode": getattr(config, "mode", "debug"),
            "program": config.program,
            "cwd": config.cwd,
            "stopOnEntry": config.stop_on_entry,
        }

        if config.args:
            args["args"] = config.args

        if config.env:
            args["env"] = config.env

        if hasattr(config, "build_flags") and config.build_flags:
            args["buildFlags"] = " ".join(config.build_flags)

        if hasattr(config, "output") and config.output:
            args["output"] = config.output

        try:
            self._initialized_event = asyncio.Event()
            initialized_event = self._initialized_event

            async def send_launch() -> None:
                await client.send_request("launch", args, timeout=60.0)

            async def wait_configure_done() -> None:
                try:
                    await asyncio.wait_for(initialized_event.wait(), timeout=30.0)
                    if configure_callback:
                        await configure_callback()
                    await client.send_request("configurationDone", {})
                except asyncio.TimeoutError:
                    raise LaunchError("Timeout waiting for initialized event")

            await asyncio.gather(send_launch(), wait_configure_done())

            self._launched = True
            logger.info(f"Session {self.session_id}: launched {config.program}")
        except Exception as e:
            raise LaunchError(str(e))
        finally:
            self._initialized_event = None

    async def attach(
        self,
        config: GoAttachConfig | BaseAttachConfig | Any,
        configure_callback: Callable[[], Coroutine[Any, Any, None]] | None = None,
        **kwargs: Any,
    ) -> None:
        """Attach to a running Go process."""
        client = self._require_initialized()

        # Handle base AttachConfig
        if isinstance(config, BaseAttachConfig):
            config = GoAttachConfig(
                host=config.host,
                port=config.port,
                process_id=config.process_id,
            )

        args: dict[str, Any] = {
            "request": "attach",
            "mode": getattr(config, "mode", "local"),
        }

        if config.process_id:
            args["processId"] = config.process_id
        elif config.port:
            args["host"] = config.host
            args["port"] = config.port

        try:
            self._initialized_event = asyncio.Event()
            initialized_event = self._initialized_event

            async def send_attach() -> None:
                await client.send_request("attach", args, timeout=60.0)

            async def wait_configure_done() -> None:
                try:
                    await asyncio.wait_for(initialized_event.wait(), timeout=30.0)
                    if configure_callback:
                        await configure_callback()
                    await client.send_request("configurationDone", {})
                except asyncio.TimeoutError:
                    raise LaunchError("Timeout waiting for initialized event during attach")

            await asyncio.gather(send_attach(), wait_configure_done())

            self._launched = True
            logger.info(f"Session {self.session_id}: attached to Go process")
        except Exception as e:
            raise LaunchError(str(e))
        finally:
            self._initialized_event = None

    async def disconnect(self, terminate: bool = False) -> None:
        """Disconnect and cleanup."""
        if self._client:
            try:
                await self._client.send_request(
                    "disconnect",
                    {"terminateDebuggee": terminate},
                    timeout=5.0,
                )
            except Exception:
                pass

        await self._cleanup()

    async def _cleanup(self) -> None:
        """Clean up resources."""
        if self._client:
            await self._client.stop()
            self._client = None

        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None

        if self._process:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
            self._process = None

        self._initialized = False
        self._launched = False
        self._port = None
        logger.info(f"Session {self.session_id}: disconnected")

    async def terminate(self) -> None:
        """Terminate the debug target and cleanup."""
        await self.disconnect(terminate=True)

    async def set_breakpoints(
        self,
        source_path: str,
        breakpoints: list[SourceBreakpoint],
    ) -> list[Breakpoint]:
        """Set breakpoints for a source file."""
        client = self._require_initialized()

        bp_args = []
        for bp in breakpoints:
            if not getattr(bp, "enabled", True):
                continue
            bp_arg: dict[str, Any] = {"line": bp.line}
            if bp.column:
                bp_arg["column"] = bp.column
            if bp.condition:
                bp_arg["condition"] = bp.condition
            if bp.hit_condition:
                bp_arg["hitCondition"] = bp.hit_condition
            if bp.log_message:
                bp_arg["logMessage"] = bp.log_message
            bp_args.append(bp_arg)

        response = await client.send_request(
            "setBreakpoints",
            {
                "source": {"path": source_path},
                "breakpoints": bp_args,
            },
        )

        return [Breakpoint(**bp) for bp in response.get("breakpoints", [])]

    async def set_function_breakpoints(self, names: list[str]) -> list[Breakpoint]:
        """Set breakpoints on function names."""
        client = self._require_initialized()

        breakpoints = [{"name": name} for name in names]
        response = await client.send_request(
            "setFunctionBreakpoints",
            {"breakpoints": breakpoints},
        )

        return [Breakpoint(**bp) for bp in response.get("breakpoints", [])]

    async def set_exception_breakpoints(self, filters: list[str]) -> None:
        """Configure exception breakpoints.

        Go/delve exception filters:
        - "panic": Break on panic
        - "fatal": Break on fatal errors
        """
        client = self._require_initialized()

        await client.send_request(
            "setExceptionBreakpoints",
            {"filters": filters},
        )

    async def continue_execution(self, thread_id: int | None = None) -> None:
        """Continue execution."""
        client = self._require_initialized()
        if thread_id is None:
            raise ValueError("thread_id is required")
        await client.send_request("continue", {"threadId": thread_id})

    async def pause(self, thread_id: int | None = None) -> None:
        """Pause execution."""
        client = self._require_initialized()
        if thread_id is None:
            raise ValueError("thread_id is required")
        await client.send_request("pause", {"threadId": thread_id})

    async def step_over(self, thread_id: int | None = None) -> None:
        """Step over (next line)."""
        client = self._require_initialized()
        if thread_id is None:
            raise ValueError("thread_id is required")
        await client.send_request("next", {"threadId": thread_id})

    async def step_into(self, thread_id: int | None = None) -> None:
        """Step into function."""
        client = self._require_initialized()
        if thread_id is None:
            raise ValueError("thread_id is required")
        await client.send_request("stepIn", {"threadId": thread_id})

    async def step_out(self, thread_id: int | None = None) -> None:
        """Step out of function."""
        client = self._require_initialized()
        if thread_id is None:
            raise ValueError("thread_id is required")
        await client.send_request("stepOut", {"threadId": thread_id})

    async def get_threads(self) -> list[Thread]:
        """Get all threads (goroutines)."""
        client = self._require_initialized()
        response = await client.send_request("threads")
        return [Thread(**t) for t in response.get("threads", [])]

    async def get_stack_trace(
        self,
        thread_id: int,
        start_frame: int = 0,
        levels: int = 20,
    ) -> list[StackFrame]:
        """Get stack trace for a goroutine."""
        client = self._require_initialized()

        response = await client.send_request(
            "stackTrace",
            {
                "threadId": thread_id,
                "startFrame": start_frame,
                "levels": levels,
            },
        )

        return [StackFrame(**f) for f in response.get("stackFrames", [])]

    async def get_scopes(self, frame_id: int) -> list[Scope]:
        """Get scopes for a stack frame."""
        client = self._require_initialized()

        response = await client.send_request(
            "scopes",
            {"frameId": frame_id},
        )

        return [Scope(**s) for s in response.get("scopes", [])]

    async def get_variables(
        self,
        variables_reference: int,
        start: int = 0,
        count: int = 0,
    ) -> list[Variable]:
        """Get variables for a scope or variable reference."""
        client = self._require_initialized()

        args: dict[str, Any] = {"variablesReference": variables_reference}
        if start > 0:
            args["start"] = start
        if count > 0:
            args["count"] = count

        response = await client.send_request("variables", args)

        return [Variable(**v) for v in response.get("variables", [])]

    async def evaluate(
        self,
        expression: str,
        frame_id: int | None = None,
        context: str = "repl",
    ) -> dict[str, Any]:
        """Evaluate an expression."""
        client = self._require_initialized()

        args: dict[str, Any] = {
            "expression": expression,
            "context": context,
        }
        if frame_id is not None:
            args["frameId"] = frame_id

        return await client.send_request("evaluate", args)

    async def _handle_event(self, event_type: str, body: dict[str, Any]) -> None:
        """Handle DAP events from delve."""
        # Handle 'initialized' event for launch sequence coordination
        if event_type == "initialized" and self._initialized_event:
            self._initialized_event.set()
            return

        # Map DAP events to our event types
        event_mapping = {
            "stopped": EventType.STOPPED,
            "continued": EventType.CONTINUED,
            "terminated": EventType.TERMINATED,
            "exited": EventType.EXITED,
            "output": EventType.OUTPUT,
            "breakpoint": EventType.BREAKPOINT,
            "thread": EventType.THREAD,
            "module": EventType.MODULE,
        }

        # Handle output events specially
        if event_type == "output" and self._output_callback:
            category = body.get("category", "stdout")
            output = body.get("output", "")
            self._output_callback(category, output)

        # Forward to event callback
        if self._event_callback and event_type in event_mapping:
            await self._event_callback(event_mapping[event_type], body)
