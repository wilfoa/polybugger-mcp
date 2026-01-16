"""Rust/C/C++ debug adapter (CodeLLDB).

This adapter enables debugging Rust, C, and C++ applications using CodeLLDB,
which is LLDB with a DAP interface.

Requirements:
- LLDB installed (usually comes with Xcode on macOS or llvm package on Linux)
- CodeLLDB extension: Download from VS Code marketplace or build from source

CodeLLDB can be obtained from:
- VS Code extension: vadimcn.vscode-lldb
- GitHub: https://github.com/vadimcn/codelldb
"""

import asyncio
import logging
import os
import platform
import shutil
import socket
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from pathlib import Path
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


def _find_codelldb() -> tuple[str | None, str]:
    """Find the CodeLLDB or lldb-dap adapter executable.

    Returns:
        Tuple of (path, adapter_type) where adapter_type is 'codelldb' or 'lldb-dap'.
        lldb-dap uses stdin/stdout, while codelldb uses TCP port.

    Searches in common locations:
    - PATH (codelldb, lldb-dap)
    - VS Code extensions directory
    - Common installation paths
    """
    # Check PATH first - prefer lldb-dap over codelldb (lldb-dap is more reliable)
    for cmd, adapter_type in [
        ("lldb-dap", "lldb-dap"),
        ("lldb-vscode", "lldb-dap"),
        ("codelldb", "codelldb"),
    ]:
        path = shutil.which(cmd)
        if path:
            return path, adapter_type

    # Check VS Code extensions directory
    home = Path.home()
    vscode_extensions = [
        home / ".vscode" / "extensions",
        home / ".vscode-server" / "extensions",
    ]

    for ext_dir in vscode_extensions:
        if not ext_dir.exists():
            continue

        # Find codelldb extension
        for ext in ext_dir.glob("vadimcn.vscode-lldb-*"):
            system = platform.system().lower()
            if system == "darwin":
                adapter = ext / "adapter" / "codelldb"
            elif system == "linux":
                adapter = ext / "adapter" / "codelldb"
            else:  # Windows
                adapter = ext / "adapter" / "codelldb.exe"

            if adapter.exists():
                return str(adapter), "codelldb"

    # Check common installation paths - prefer lldb-dap over codelldb
    common_paths = [
        ("/usr/local/bin/lldb-dap", "lldb-dap"),
        ("/usr/bin/lldb-dap", "lldb-dap"),
        ("/usr/local/bin/codelldb", "codelldb"),
        ("/usr/bin/codelldb", "codelldb"),
    ]

    for path, adapter_type in common_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path, adapter_type

    return None, ""


@dataclass
class RustLaunchConfig:
    """Rust/LLDB-specific launch configuration."""

    program: str | None = None  # Path to compiled executable
    args: list[str] | None = None
    cwd: str = "."
    env: dict[str, str] | None = None
    stop_on_entry: bool = False

    # LLDB-specific options
    source_map: dict[str, str] | None = None  # Source path remapping
    init_commands: list[str] | None = None  # LLDB commands to run at start
    pre_run_commands: list[str] | None = None  # Commands before running
    post_run_commands: list[str] | None = None  # Commands after running
    exit_commands: list[str] | None = None  # Commands on exit
    expressions: str = "native"  # Expression evaluator: native, simple, python
    terminal: str = "console"  # console, integrated, external


@dataclass
class RustAttachConfig:
    """Rust/LLDB-specific attach configuration."""

    host: str = "127.0.0.1"
    port: int | None = None
    process_id: int | None = None
    program: str | None = None  # Path to executable (for symbols)
    wait_for: str | None = None  # Process name to wait for


@register_adapter(Language.RUST)
@register_adapter(Language.CPP)
@register_adapter(Language.C)
class CodeLLDBAdapter(DebugAdapter):
    """Debug adapter for Rust/C/C++ using CodeLLDB.

    This adapter communicates with CodeLLDB's DAP server
    to debug native applications.
    """

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
        self._codelldb_path: str | None = None
        self._adapter_type: str = ""  # 'codelldb' or 'lldb-dap'

    @property
    def language(self) -> Language:
        return Language.RUST

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
        """Start CodeLLDB or lldb-dap and initialize DAP connection.

        Returns:
            Debug adapter capabilities
        """
        # Find CodeLLDB or lldb-dap
        self._codelldb_path, self._adapter_type = _find_codelldb()
        if not self._codelldb_path:
            raise DAPConnectionError(
                "CodeLLDB or lldb-dap not found. Install options:\n"
                "1. VS Code extension: vadimcn.vscode-lldb\n"
                "2. From source: https://github.com/vadimcn/codelldb\n"
                "3. Install lldb-dap from LLVM: apt install lldb-17"
            )

        try:
            if self._adapter_type == "codelldb":
                # CodeLLDB accepts --port to start in multi-session server mode
                self._port = _get_free_port()
                self._process = await asyncio.create_subprocess_exec(
                    self._codelldb_path,
                    "--port",
                    str(self._port),
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
                                f"Failed to connect to CodeLLDB on port {self._port}"
                            )
                        await asyncio.sleep(0.3)
            else:
                # lldb-dap uses stdin/stdout for DAP communication
                self._process = await asyncio.create_subprocess_exec(
                    self._codelldb_path,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                # Use process stdin/stdout as reader/writer
                assert self._process.stdout is not None
                assert self._process.stdin is not None
                self._reader = self._process.stdout
                self._writer = self._process.stdin  # type: ignore[assignment]

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
                    "adapterID": "lldb",
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
            adapter_name = "CodeLLDB" if self._adapter_type == "codelldb" else "lldb-dap"
            if self._port:
                logger.info(
                    f"Session {self.session_id}: {adapter_name} initialized on port {self._port}"
                )
            else:
                logger.info(f"Session {self.session_id}: {adapter_name} initialized via stdio")
            return self._capabilities

        except Exception as e:
            await self._cleanup()
            raise DAPConnectionError(f"Failed to initialize LLDB adapter: {e}")

    async def launch(
        self,
        config: RustLaunchConfig | BaseLaunchConfig | Any,
        configure_callback: Callable[[], Coroutine[Any, Any, None]] | None = None,
        **kwargs: Any,
    ) -> None:
        """Launch a Rust/C/C++ program for debugging."""
        client = self._require_initialized()

        # Handle base LaunchConfig by converting to RustLaunchConfig
        if isinstance(config, BaseLaunchConfig):
            config = RustLaunchConfig(
                program=config.program,
                args=config.args,
                cwd=config.cwd or ".",
                env=config.env,
                stop_on_entry=config.stop_on_entry,
            )

        if not config.program:
            raise LaunchError("Program path is required for LLDB launch")

        # CodeLLDB launch request format
        args: dict[str, Any] = {
            "type": "lldb",
            "request": "launch",
            "name": "LLDB Debug",
            "program": config.program,
            "cwd": config.cwd,
            "stopOnEntry": config.stop_on_entry,
            "terminal": getattr(config, "terminal", "console"),
        }

        if config.args:
            args["args"] = config.args

        if config.env:
            args["env"] = config.env

        if hasattr(config, "source_map") and config.source_map:
            args["sourceMap"] = config.source_map

        if hasattr(config, "init_commands") and config.init_commands:
            args["initCommands"] = config.init_commands

        if hasattr(config, "pre_run_commands") and config.pre_run_commands:
            args["preRunCommands"] = config.pre_run_commands

        if hasattr(config, "post_run_commands") and config.post_run_commands:
            args["postRunCommands"] = config.post_run_commands

        if hasattr(config, "exit_commands") and config.exit_commands:
            args["exitCommands"] = config.exit_commands

        if hasattr(config, "expressions") and config.expressions:
            args["expressions"] = config.expressions

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
        config: RustAttachConfig | BaseAttachConfig | Any,
        configure_callback: Callable[[], Coroutine[Any, Any, None]] | None = None,
        **kwargs: Any,
    ) -> None:
        """Attach to a running process."""
        client = self._require_initialized()

        # Handle base AttachConfig
        if isinstance(config, BaseAttachConfig):
            config = RustAttachConfig(
                host=config.host,
                port=config.port,
                process_id=config.process_id,
            )

        args: dict[str, Any] = {
            "type": "lldb",
            "request": "attach",
            "name": "LLDB Attach",
        }

        if config.process_id:
            args["pid"] = config.process_id
        elif hasattr(config, "wait_for") and config.wait_for:
            args["waitFor"] = config.wait_for
        elif config.port:
            # Remote debugging
            args["connect"] = {
                "host": config.host,
                "port": config.port,
            }

        if hasattr(config, "program") and config.program:
            args["program"] = config.program

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
            logger.info(f"Session {self.session_id}: attached to process")
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
            # Check if process is still running before terminating
            if self._process.returncode is None:
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

        LLDB exception filters:
        - "cpp_throw": Break on C++ throw
        - "cpp_catch": Break on C++ catch
        - "rust_panic": Break on Rust panic
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
        """Handle DAP events from CodeLLDB."""
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
