"""debugpy subprocess adapter."""

import asyncio
import logging
import socket
import sys
from collections.abc import Callable, Coroutine
from typing import Any

from python_debugger_mcp.adapters.dap_client import DAPClient
from python_debugger_mcp.config import settings
from python_debugger_mcp.core.exceptions import DAPConnectionError, LaunchError
from python_debugger_mcp.models.dap import (
    AttachConfig,
    Breakpoint,
    LaunchConfig,
    Scope,
    SourceBreakpoint,
    StackFrame,
    Thread,
    Variable,
)
from python_debugger_mcp.models.events import EventType

logger = logging.getLogger(__name__)


def _get_free_port() -> int:
    """Get an available port number."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port: int = s.getsockname()[1]
        return port


class DebugpyAdapter:
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
        self.session_id = session_id
        self._output_callback = output_callback
        self._event_callback = event_callback

        self._process: asyncio.subprocess.Process | None = None
        self._client: DAPClient | None = None
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._port: int | None = None
        self._initialized = False
        self._capabilities: dict[str, Any] = {}
        self._launched = False
        self._initialized_event: asyncio.Event | None = None

    async def initialize(self) -> dict[str, Any]:
        """Start debugpy and initialize DAP connection.

        Returns:
            Debugger capabilities dictionary
        """
        # Get a free port for debugpy to listen on
        self._port = _get_free_port()
        python_path = settings.default_python_path or sys.executable

        # Start debugpy adapter in server mode (listening on socket)
        self._process = await asyncio.create_subprocess_exec(
            python_path,
            "-m",
            "debugpy.adapter",
            "--host",
            "127.0.0.1",
            "--port",
            str(self._port),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
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
        config: LaunchConfig,
        configure_callback: Callable[[], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        """Launch the debug target.

        The DAP launch sequence requires:
        1. Send 'launch' request
        2. Wait for 'initialized' event from debugpy
        3. Configure breakpoints (via configure_callback)
        4. Send 'configurationDone' request
        5. Receive 'launch' response

        Args:
            config: Launch configuration
            configure_callback: Optional async callback to set breakpoints during
                               configuration phase (after 'initialized' event)
        """
        self._require_initialized()

        args: dict[str, Any] = {
            "cwd": str(config.cwd),
            "env": config.env,
            "stopOnEntry": config.stop_on_entry,
            "justMyCode": False,  # Always debug all code
            "console": config.console,
            "redirectOutput": True,
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

            # Launch request and configurationDone must be coordinated:
            # - launch request triggers debugpy to send 'initialized' event
            # - we must set breakpoints after 'initialized' event
            # - then send 'configurationDone'
            # - only then does launch response arrive

            async def send_launch() -> None:
                """Send launch and wait for response."""
                await self._client.send_request(  # type: ignore
                    "launch",
                    args,
                    timeout=settings.dap_launch_timeout_seconds,
                )

            async def wait_configure_done() -> None:
                """Wait for initialized event, configure, and send configurationDone."""
                try:
                    await asyncio.wait_for(
                        self._initialized_event.wait(),  # type: ignore
                        timeout=settings.dap_launch_timeout_seconds,
                    )
                    # Run configuration callback (set breakpoints, etc.)
                    if configure_callback:
                        await configure_callback()
                    await self._client.send_request("configurationDone", {})  # type: ignore
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
        config: AttachConfig,
        configure_callback: Callable[[], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        """Attach to a running process.

        The DAP attach sequence requires the same coordination as launch:
        1. Send 'attach' request
        2. Wait for 'initialized' event
        3. Configure breakpoints (via configure_callback)
        4. Send 'configurationDone' request
        5. Receive 'attach' response

        Args:
            config: Attach configuration
            configure_callback: Optional async callback to set breakpoints during
                               configuration phase (after 'initialized' event)
        """
        self._require_initialized()

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

        try:
            self._initialized_event = asyncio.Event()

            async def send_attach() -> None:
                await self._client.send_request("attach", args)  # type: ignore

            async def wait_configure_done() -> None:
                try:
                    await asyncio.wait_for(
                        self._initialized_event.wait(),  # type: ignore
                        timeout=settings.dap_launch_timeout_seconds,
                    )
                    if configure_callback:
                        await configure_callback()
                    await self._client.send_request("configurationDone", {})  # type: ignore
                except asyncio.TimeoutError:
                    raise LaunchError("Timeout waiting for initialized event during attach")

            await asyncio.gather(send_attach(), wait_configure_done())

            self._launched = True
            logger.info(f"Session {self.session_id}: attached to process")
        except Exception as e:
            raise LaunchError(str(e))
        finally:
            self._initialized_event = None

    async def disconnect(self) -> None:
        """Disconnect and cleanup."""
        if self._client:
            try:
                await self._client.send_request(
                    "disconnect",
                    {"terminateDebuggee": True},
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
        self._require_initialized()

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

        response = await self._client.send_request(  # type: ignore
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
        self._require_initialized()

        await self._client.send_request(  # type: ignore
            "setExceptionBreakpoints",
            {"filters": filters},
        )

    async def continue_(self, thread_id: int) -> None:
        """Continue execution.

        Args:
            thread_id: Thread to continue
        """
        self._require_initialized()
        await self._client.send_request("continue", {"threadId": thread_id})  # type: ignore

    async def pause(self, thread_id: int) -> None:
        """Pause execution.

        Args:
            thread_id: Thread to pause
        """
        self._require_initialized()
        await self._client.send_request("pause", {"threadId": thread_id})  # type: ignore

    async def step_over(self, thread_id: int) -> None:
        """Step over (next line).

        Args:
            thread_id: Thread to step
        """
        self._require_initialized()
        await self._client.send_request("next", {"threadId": thread_id})  # type: ignore

    async def step_into(self, thread_id: int) -> None:
        """Step into function.

        Args:
            thread_id: Thread to step
        """
        self._require_initialized()
        await self._client.send_request("stepIn", {"threadId": thread_id})  # type: ignore

    async def step_out(self, thread_id: int) -> None:
        """Step out of function.

        Args:
            thread_id: Thread to step
        """
        self._require_initialized()
        await self._client.send_request("stepOut", {"threadId": thread_id})  # type: ignore

    async def threads(self) -> list[Thread]:
        """Get all threads.

        Returns:
            List of threads
        """
        self._require_initialized()
        response = await self._client.send_request("threads")  # type: ignore
        return [Thread(**t) for t in response.get("threads", [])]

    async def stack_trace(
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
        self._require_initialized()

        response = await self._client.send_request(  # type: ignore
            "stackTrace",
            {
                "threadId": thread_id,
                "startFrame": start_frame,
                "levels": levels,
            },
        )

        return [StackFrame(**f) for f in response.get("stackFrames", [])]

    async def scopes(self, frame_id: int) -> list[Scope]:
        """Get scopes for a stack frame.

        Args:
            frame_id: Frame ID

        Returns:
            List of scopes
        """
        self._require_initialized()

        response = await self._client.send_request(  # type: ignore
            "scopes",
            {"frameId": frame_id},
        )

        return [Scope(**s) for s in response.get("scopes", [])]

    async def variables(
        self,
        variables_ref: int,
        start: int = 0,
        count: int = 100,
    ) -> list[Variable]:
        """Get variables for a scope or variable reference.

        Args:
            variables_ref: Variable reference ID
            start: Starting index
            count: Maximum variables to return

        Returns:
            List of variables
        """
        self._require_initialized()

        response = await self._client.send_request(  # type: ignore
            "variables",
            {
                "variablesReference": variables_ref,
                "start": start,
                "count": count,
            },
        )

        return [Variable(**v) for v in response.get("variables", [])]

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
        self._require_initialized()

        args: dict[str, Any] = {
            "expression": expression,
            "context": context,
        }
        if frame_id is not None:
            args["frameId"] = frame_id

        return await self._client.send_request("evaluate", args)  # type: ignore

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

    def _require_initialized(self) -> None:
        """Raise if not initialized."""
        if not self._initialized:
            raise DAPConnectionError("Adapter not initialized")

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
