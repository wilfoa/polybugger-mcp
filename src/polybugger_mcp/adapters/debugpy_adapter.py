"""debugpy subprocess adapter."""

import asyncio
import logging
import os
import signal
import socket
import sys
from collections.abc import Callable, Coroutine
from typing import Any

from polybugger_mcp.adapters.base import (
    AttachConfig as BaseAttachConfig,
)
from polybugger_mcp.adapters.base import (
    DebugAdapter,
    Language,
)
from polybugger_mcp.adapters.base import (
    LaunchConfig as BaseLaunchConfig,
)
from polybugger_mcp.adapters.dap_client import DAPClient
from polybugger_mcp.adapters.factory import register_adapter
from polybugger_mcp.config import settings
from polybugger_mcp.core.exceptions import DAPConnectionError, LaunchError
from polybugger_mcp.models.dap import (
    AttachConfig,
    Breakpoint,
    LaunchConfig,
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


@register_adapter(Language.PYTHON)
class DebugpyAdapter(DebugAdapter):
    """Adapter for communicating with debugpy via DAP.

    Manages a debugpy adapter subprocess and translates high-level
    debugging operations to DAP protocol messages.
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
            session_id: ID of the owning session
            output_callback: Callback for output (category, content)
            event_callback: Async callback for debug events
        """
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
        """The language this adapter supports."""
        return Language.PYTHON

    @property
    def is_connected(self) -> bool:
        """Whether the adapter is connected to the debug server."""
        return self._client is not None and self._initialized

    async def initialize(self) -> dict[str, Any]:
        """Start debugpy and initialize DAP connection.

        Returns:
            Debugger capabilities dictionary
        """
        # Get a free port for debugpy to listen on
        self._port = _get_free_port()
        python_path = settings.default_python_path or sys.executable

        # Preexec function to fully detach from TTY in child process
        def _detach_from_tty() -> None:
            """Detach from controlling TTY to prevent suspension of parent."""
            # Ignore TTY signals
            signal.signal(signal.SIGTTIN, signal.SIG_IGN)
            signal.signal(signal.SIGTTOU, signal.SIG_IGN)

            # Create new session (detaches from controlling terminal)
            try:
                os.setsid()
            except OSError:
                pass

            # Close and reopen stdin/stdout/stderr to /dev/null
            # This ensures no TTY access even if debugpy tries
            try:
                devnull_fd = os.open(os.devnull, os.O_RDWR)
                # Only redirect stdin - stdout/stderr are pipes we need
                os.dup2(devnull_fd, 0)
                os.close(devnull_fd)
            except OSError:
                pass

        # Start debugpy adapter in server mode (listening on socket)
        # - stdin=DEVNULL: prevent reading from parent's stdin
        # - start_new_session=True: detach from controlling TTY
        # - preexec_fn: ignore TTY signals in child process
        self._process = await asyncio.create_subprocess_exec(
            python_path,
            "-m",
            "debugpy.adapter",
            "--host",
            "127.0.0.1",
            "--port",
            str(self._port),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
            preexec_fn=_detach_from_tty if sys.platform != "win32" else None,
        )

        # Wait for debugpy to start listening
        # We retry connection a few times with backoff
        max_attempts = 10
        last_error: Exception | None = None

        for attempt in range(max_attempts):
            try:
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection("127.0.0.1", self._port),
                    timeout=1.0,
                )
                break
            except (ConnectionRefusedError, asyncio.TimeoutError, OSError) as e:
                last_error = e
                # Check if process died
                if self._process.returncode is not None:
                    stderr = ""
                    if self._process.stderr:
                        stderr_bytes = await self._process.stderr.read()
                        stderr = stderr_bytes.decode()[:500]
                    raise DAPConnectionError(
                        f"debugpy process exited with code {self._process.returncode}: {stderr}"
                    )
                await asyncio.sleep(0.1 * (attempt + 1))
        else:
            raise DAPConnectionError(
                f"Failed to connect to debugpy after {max_attempts} attempts: {last_error}"
            )

        # Create DAP client with socket streams
        assert self._reader is not None
        assert self._writer is not None
        self._client = DAPClient(
            reader=self._reader,
            writer=self._writer,
            event_callback=self._handle_event,
            timeout=settings.dap_timeout_seconds,
        )
        await self._client.start()

        # Send initialize request
        self._capabilities = await self._client.send_request(
            "initialize",
            {
                "clientID": "python-debugger-mcp",
                "clientName": "Python Debugger MCP",
                "adapterID": "python",
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
        logger.info(f"Session {self.session_id}: debugpy initialized on port {self._port}")
        return self._capabilities

    async def launch(
        self,
        config: LaunchConfig | BaseLaunchConfig | Any,
        configure_callback: Callable[[], Coroutine[Any, Any, None]] | None = None,
        **kwargs: Any,
    ) -> None:
        """Launch the debug target.

        The DAP launch sequence requires:
        1. Send 'launch' request
        2. Wait for 'initialized' event from debugpy
        3. Configure breakpoints (via configure_callback)
        4. Send 'configurationDone' request
        5. Receive 'launch' response

        Args:
            config: Launch configuration (LaunchConfig or base LaunchConfig)
            configure_callback: Optional async callback to set breakpoints during
                               configuration phase (after 'initialized' event)
            **kwargs: Additional options (unused, for ABC compatibility)
        """
        client = self._require_initialized()

        # Handle base LaunchConfig by converting to DAP LaunchConfig
        if isinstance(config, BaseLaunchConfig):
            dap_config = LaunchConfig(
                program=config.program,
                stop_on_entry=config.stop_on_entry,
            )
            if config.args:
                dap_config.args = config.args
            if config.cwd:
                dap_config.cwd = config.cwd
            if config.env:
                dap_config.env = config.env
            config = dap_config

        # Merge user env with vars that prevent TTY access in subprocess
        env = {
            **config.env,
            "PYTHONUNBUFFERED": "1",  # Don't buffer output
            "TERM": "dumb",  # Disable terminal features
        }

        args: dict[str, Any] = {
            "cwd": str(config.cwd),
            "env": env,
            "stopOnEntry": config.stop_on_entry,
            "justMyCode": False,  # Always debug all code
            "console": config.console,
            "redirectOutput": True,
            "redirectInput": config.redirect_input,
        }

        if config.program:
            args["program"] = str(config.program)
        elif config.module:
            args["module"] = config.module
        else:
            raise LaunchError("Either program or module must be specified")

        if config.args:
            args["args"] = config.args

        if config.python_args:
            args["pythonArgs"] = config.python_args

        if config.python_path:
            args["python"] = str(config.python_path)

        try:
            # Set up event to wait for 'initialized' event
            self._initialized_event = asyncio.Event()
            initialized_event = self._initialized_event

            # Launch request and configurationDone must be coordinated:
            # - launch request triggers debugpy to send 'initialized' event
            # - we must set breakpoints after 'initialized' event
            # - then send 'configurationDone'
            # - only then does launch response arrive

            async def send_launch() -> None:
                """Send launch and wait for response."""
                await client.send_request(
                    "launch",
                    args,
                    timeout=settings.dap_launch_timeout_seconds,
                )

            async def wait_configure_done() -> None:
                """Wait for initialized event, configure, and send configurationDone."""
                try:
                    await asyncio.wait_for(
                        initialized_event.wait(),
                        timeout=settings.dap_launch_timeout_seconds,
                    )
                    # Run configuration callback (set breakpoints, etc.)
                    if configure_callback:
                        await configure_callback()
                    await client.send_request("configurationDone", {})
                except asyncio.TimeoutError:
                    raise LaunchError("Timeout waiting for initialized event")

            # Run both concurrently - launch waits for response which comes after configurationDone
            await asyncio.gather(send_launch(), wait_configure_done())

            self._launched = True
            logger.info(f"Session {self.session_id}: launched {config.program or config.module}")
        except Exception as e:
            raise LaunchError(str(e))
        finally:
            self._initialized_event = None

    async def attach(
        self,
        config: AttachConfig | BaseAttachConfig | Any,
        configure_callback: Callable[[], Coroutine[Any, Any, None]] | None = None,
        **kwargs: Any,
    ) -> None:
        """Attach to a running process.

        The DAP attach sequence requires the same coordination as launch:
        1. Send 'attach' request
        2. Wait for 'initialized' event
        3. Configure breakpoints (via configure_callback)
        4. Send 'configurationDone' request
        5. Receive 'attach' response

        Args:
            config: Attach configuration (AttachConfig or base AttachConfig)
            configure_callback: Optional async callback to set breakpoints during
                               configuration phase (after 'initialized' event)
            **kwargs: Additional options (unused, for ABC compatibility)
        """
        client = self._require_initialized()

        # Handle base AttachConfig by converting to DAP AttachConfig
        if isinstance(config, BaseAttachConfig):
            dap_config = AttachConfig(
                host=config.host,
                process_id=config.process_id,
            )
            if config.port is not None:
                dap_config.port = config.port
            config = dap_config

        args: dict[str, Any] = {
            "justMyCode": False,
            "redirectOutput": True,
        }

        if config.process_id:
            args["processId"] = config.process_id
        else:
            args["connect"] = {
                "host": config.host,
                "port": config.port,
            }

        # Add path mappings for remote/container debugging
        if config.path_mappings:
            args["pathMappings"] = [
                {
                    "localRoot": pm.local_root,
                    "remoteRoot": pm.remote_root,
                }
                for pm in config.path_mappings
            ]

        try:
            self._initialized_event = asyncio.Event()
            initialized_event = self._initialized_event

            async def send_attach() -> None:
                await client.send_request("attach", args)

            async def wait_configure_done() -> None:
                try:
                    await asyncio.wait_for(
                        initialized_event.wait(),
                        timeout=settings.dap_launch_timeout_seconds,
                    )
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

    async def disconnect(self, terminate: bool = True) -> None:
        """Disconnect and cleanup.

        Args:
            terminate: Whether to terminate the debuggee (default True)
        """
        if self._client:
            try:
                await self._client.send_request(
                    "disconnect",
                    {"terminateDebuggee": terminate},
                    timeout=5.0,
                )
            except Exception:
                pass

            await self._client.stop()
            self._client = None

        # Close socket connection
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
        """Set breakpoints for a source file.

        Args:
            source_path: Path to source file
            breakpoints: List of breakpoints to set

        Returns:
            List of verified breakpoints
        """
        client = self._require_initialized()

        # Filter only enabled breakpoints
        enabled_breakpoints = [bp for bp in breakpoints if bp.enabled]

        bp_args = []
        for bp in enabled_breakpoints:
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

    async def set_exception_breakpoints(self, filters: list[str]) -> None:
        """Set exception breakpoints.

        Args:
            filters: List of exception filters ("raised", "uncaught", etc.)
        """
        client = self._require_initialized()

        await client.send_request(
            "setExceptionBreakpoints",
            {"filters": filters},
        )

    async def set_function_breakpoints(self, names: list[str]) -> list[Breakpoint]:
        """Set breakpoints on function names.

        Args:
            names: List of function names

        Returns:
            List of actual breakpoints
        """
        client = self._require_initialized()

        breakpoints = [{"name": name} for name in names]
        response = await client.send_request(
            "setFunctionBreakpoints",
            {"breakpoints": breakpoints},
        )

        return [Breakpoint(**bp) for bp in response.get("breakpoints", [])]

    async def continue_execution(self, thread_id: int | None = None) -> None:
        """Continue execution.

        Args:
            thread_id: Thread to continue (required for debugpy)
        """
        client = self._require_initialized()
        if thread_id is None:
            raise ValueError("thread_id is required for debugpy")
        await client.send_request("continue", {"threadId": thread_id})

    # Alias for backward compatibility
    async def continue_(self, thread_id: int) -> None:
        """Continue execution (deprecated, use continue_execution)."""
        await self.continue_execution(thread_id)

    async def pause(self, thread_id: int | None = None) -> None:
        """Pause execution.

        Args:
            thread_id: Thread to pause (required for debugpy)
        """
        client = self._require_initialized()
        if thread_id is None:
            raise ValueError("thread_id is required for debugpy")
        await client.send_request("pause", {"threadId": thread_id})

    async def step_over(self, thread_id: int | None = None) -> None:
        """Step over (next line).

        Args:
            thread_id: Thread to step (required for debugpy)
        """
        client = self._require_initialized()
        if thread_id is None:
            raise ValueError("thread_id is required for debugpy")
        await client.send_request("next", {"threadId": thread_id})

    async def step_into(self, thread_id: int | None = None) -> None:
        """Step into function.

        Args:
            thread_id: Thread to step (required for debugpy)
        """
        client = self._require_initialized()
        if thread_id is None:
            raise ValueError("thread_id is required for debugpy")
        await client.send_request("stepIn", {"threadId": thread_id})

    async def step_out(self, thread_id: int | None = None) -> None:
        """Step out of function.

        Args:
            thread_id: Thread to step (required for debugpy)
        """
        client = self._require_initialized()
        if thread_id is None:
            raise ValueError("thread_id is required for debugpy")
        await client.send_request("stepOut", {"threadId": thread_id})

    async def get_threads(self) -> list[Thread]:
        """Get all threads.

        Returns:
            List of threads
        """
        client = self._require_initialized()
        response = await client.send_request("threads")
        return [Thread(**t) for t in response.get("threads", [])]

    # Alias for backward compatibility
    async def threads(self) -> list[Thread]:
        """Get all threads (deprecated, use get_threads)."""
        return await self.get_threads()

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
            levels: Maximum number of frames

        Returns:
            List of stack frames
        """
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

    # Alias for backward compatibility
    async def stack_trace(
        self,
        thread_id: int,
        start_frame: int = 0,
        levels: int = 20,
    ) -> list[StackFrame]:
        """Get stack trace (deprecated, use get_stack_trace)."""
        return await self.get_stack_trace(thread_id, start_frame, levels)

    async def get_scopes(self, frame_id: int) -> list[Scope]:
        """Get scopes for a stack frame.

        Args:
            frame_id: Frame ID

        Returns:
            List of scopes
        """
        client = self._require_initialized()

        response = await client.send_request(
            "scopes",
            {"frameId": frame_id},
        )

        return [Scope(**s) for s in response.get("scopes", [])]

    # Alias for backward compatibility
    async def scopes(self, frame_id: int) -> list[Scope]:
        """Get scopes (deprecated, use get_scopes)."""
        return await self.get_scopes(frame_id)

    async def get_variables(
        self,
        variables_reference: int,
        start: int = 0,
        count: int = 100,
    ) -> list[Variable]:
        """Get variables for a scope or variable reference.

        Args:
            variables_reference: Variable reference ID
            start: Starting index
            count: Maximum variables to return (0 = all)

        Returns:
            List of variables
        """
        client = self._require_initialized()

        response = await client.send_request(
            "variables",
            {
                "variablesReference": variables_reference,
                "start": start,
                "count": count if count > 0 else 100,
            },
        )

        return [Variable(**v) for v in response.get("variables", [])]

    # Alias for backward compatibility
    async def variables(
        self,
        variables_ref: int,
        start: int = 0,
        count: int = 100,
    ) -> list[Variable]:
        """Get variables (deprecated, use get_variables)."""
        return await self.get_variables(variables_ref, start, count)

    async def evaluate(
        self,
        expression: str,
        frame_id: int | None = None,
        context: str = "watch",
    ) -> dict[str, Any]:
        """Evaluate an expression.

        Args:
            expression: Expression to evaluate
            frame_id: Frame context (optional)
            context: Evaluation context ("watch", "repl", "hover")

        Returns:
            Evaluation result with "result" and "type" keys
        """
        client = self._require_initialized()

        args: dict[str, Any] = {
            "expression": expression,
            "context": context,
        }
        if frame_id is not None:
            args["frameId"] = frame_id

        return await client.send_request("evaluate", args)

    async def _handle_event(self, event_type: str, body: dict[str, Any]) -> None:
        """Handle DAP events from debugpy."""
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

    def _require_initialized(self) -> DAPClient:
        """Raise if not initialized, otherwise return the client.

        Returns:
            The DAP client (guaranteed non-None after initialization)

        Raises:
            DAPConnectionError: If adapter is not initialized
        """
        if not self._initialized or self._client is None:
            raise DAPConnectionError("Adapter not initialized")
        return self._client

    @property
    def is_initialized(self) -> bool:
        """Check if adapter is initialized."""
        return self._initialized

    @property
    def is_launched(self) -> bool:
        """Check if debug target is launched."""
        return self._launched

    @property
    def capabilities(self) -> dict[str, Any]:
        """Get debugger capabilities."""
        return self._capabilities
