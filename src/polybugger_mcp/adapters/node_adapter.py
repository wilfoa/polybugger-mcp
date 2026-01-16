"""Node.js debug adapter (vscode-js-debug).

This adapter enables debugging Node.js/JavaScript/TypeScript applications
using the vscode-js-debug DAP server.

Requirements:
- Node.js 14+ installed
- vscode-js-debug: npm install -g @vscode/js-debug-cli

The vscode-js-debug adapter supports:
- Node.js
- Chrome/Edge debugging
- TypeScript (with source maps)
- Deno
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
class NodeLaunchConfig:
    """Node.js-specific launch configuration."""

    program: str | None = None
    args: list[str] | None = None
    cwd: str = "."
    env: dict[str, str] | None = None
    stop_on_entry: bool = False

    # Node-specific options
    runtime_executable: str | None = None  # Path to node/ts-node/deno
    runtime_args: list[str] | None = None  # Args to runtime (e.g., --inspect)
    skip_files: list[str] | None = None  # Glob patterns to skip
    source_maps: bool = True  # Enable source map support
    out_files: list[str] | None = None  # Where to find compiled JS
    timeout: int = 30000  # Launch timeout in ms


@dataclass
class NodeAttachConfig:
    """Node.js-specific attach configuration."""

    host: str = "127.0.0.1"
    port: int = 9229  # Default Node.js inspector port
    process_id: int | None = None
    timeout: int = 30000


@register_adapter(Language.JAVASCRIPT)
@register_adapter(Language.TYPESCRIPT)
class NodeAdapter(DebugAdapter):
    """Debug adapter for Node.js using vscode-js-debug.

    This adapter communicates with the vscode-js-debug DAP server
    to debug JavaScript and TypeScript applications.
    """

    # Name of the js-debug CLI command
    JS_DEBUG_CLI = "js-debug"

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
        return Language.JAVASCRIPT

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
        """Start vscode-js-debug and initialize DAP connection.

        Returns:
            Debug adapter capabilities
        """
        # Find js-debug CLI
        js_debug_path = shutil.which(self.JS_DEBUG_CLI)
        if not js_debug_path:
            raise DAPConnectionError(
                f"'{self.JS_DEBUG_CLI}' not found. Install with: npm install -g @vscode/js-debug-cli"
            )

        # Get a free port for the DAP server
        self._port = _get_free_port()

        try:
            # Start js-debug in DAP server mode
            self._process = await asyncio.create_subprocess_exec(
                js_debug_path,
                "dap",
                f"--host=127.0.0.1",
                f"--port={self._port}",
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Wait for the server to start
            await asyncio.sleep(0.5)

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
                        raise DAPConnectionError(
                            f"Failed to connect to js-debug on port {self._port}"
                        )
                    await asyncio.sleep(0.3)

            # Create DAP client (reader/writer guaranteed non-None here)
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
                    "adapterID": "pwa-node",
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
            logger.info(f"Session {self.session_id}: js-debug initialized on port {self._port}")
            return self._capabilities

        except Exception as e:
            await self._cleanup()
            raise DAPConnectionError(f"Failed to initialize js-debug: {e}")

    async def launch(
        self,
        config: NodeLaunchConfig | BaseLaunchConfig | Any,
        configure_callback: Callable[[], Coroutine[Any, Any, None]] | None = None,
        **kwargs: Any,
    ) -> None:
        """Launch a Node.js program for debugging."""
        client = self._require_initialized()

        # Handle base LaunchConfig by converting to NodeLaunchConfig
        if isinstance(config, BaseLaunchConfig):
            config = NodeLaunchConfig(
                program=config.program,
                args=config.args,
                cwd=config.cwd or ".",
                env=config.env,
                stop_on_entry=config.stop_on_entry,
            )

        if not config.program:
            raise LaunchError("Program path is required for Node.js launch")

        args: dict[str, Any] = {
            "type": "pwa-node",
            "request": "launch",
            "name": "Node.js Debug",
            "program": config.program,
            "cwd": config.cwd,
            "stopOnEntry": config.stop_on_entry,
            "sourceMaps": getattr(config, "source_maps", True),
            "timeout": getattr(config, "timeout", 30000),
        }

        if config.args:
            args["args"] = config.args

        if config.env:
            args["env"] = config.env

        if hasattr(config, "runtime_executable") and config.runtime_executable:
            args["runtimeExecutable"] = config.runtime_executable

        if hasattr(config, "runtime_args") and config.runtime_args:
            args["runtimeArgs"] = config.runtime_args

        if hasattr(config, "skip_files") and config.skip_files:
            args["skipFiles"] = config.skip_files

        if hasattr(config, "out_files") and config.out_files:
            args["outFiles"] = config.out_files

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
        config: NodeAttachConfig | BaseAttachConfig | Any,
        configure_callback: Callable[[], Coroutine[Any, Any, None]] | None = None,
        **kwargs: Any,
    ) -> None:
        """Attach to a running Node.js process."""
        client = self._require_initialized()

        # Handle base AttachConfig
        if isinstance(config, BaseAttachConfig):
            config = NodeAttachConfig(
                host=config.host,
                port=config.port or 9229,
                process_id=config.process_id,
            )

        args: dict[str, Any] = {
            "type": "pwa-node",
            "request": "attach",
            "name": "Attach to Node.js",
            "timeout": getattr(config, "timeout", 30000),
        }

        if config.process_id:
            args["processId"] = config.process_id
        else:
            args["address"] = config.host
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
            logger.info(f"Session {self.session_id}: attached to Node.js process")
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

        Node.js exception filters:
        - "all": Break on all exceptions
        - "uncaught": Break on uncaught exceptions
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
        """Get all threads."""
        client = self._require_initialized()
        response = await client.send_request("threads")
        return [Thread(**t) for t in response.get("threads", [])]

    async def get_stack_trace(
        self,
        thread_id: int,
        start_frame: int = 0,
        levels: int = 20,
    ) -> list[StackFrame]:
        """Get stack trace for a thread."""
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
        """Handle DAP events from js-debug."""
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
