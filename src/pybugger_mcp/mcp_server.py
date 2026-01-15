"""MCP Server for Python debugging.

This module provides an MCP (Model Context Protocol) server that exposes
the debug relay server functionality as MCP tools. AI agents can use these
tools to debug Python code interactively.

Usage:
    # Run as stdio server (for AI host integration)
    python -m pybugger_mcp.mcp_server

    # Or via entry point
    python-debugger-mcp-server
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP

from pybugger_mcp.core.exceptions import (
    InvalidSessionStateError,
    SessionLimitError,
    SessionNotFoundError,
)
from pybugger_mcp.core.session import SessionManager
from pybugger_mcp.models.dap import LaunchConfig, SourceBreakpoint
from pybugger_mcp.models.session import SessionConfig
from pybugger_mcp.utils.tui_formatter import TUIFormatter

logger = logging.getLogger(__name__)

# Global session manager (initialized in lifespan)
_session_manager: SessionManager | None = None

# Global TUI formatter instance
_tui_formatter: TUIFormatter | None = None


def _get_formatter() -> TUIFormatter:
    """Get the TUI formatter, creating if needed."""
    global _tui_formatter
    if _tui_formatter is None:
        _tui_formatter = TUIFormatter()
    return _tui_formatter


@asynccontextmanager
async def lifespan(app: FastMCP):  # type: ignore[no-untyped-def]
    """Manage the lifecycle of the session manager."""
    global _session_manager
    _session_manager = SessionManager()
    await _session_manager.start()
    logger.info("MCP Debug Server started")
    try:
        yield {"session_manager": _session_manager}
    finally:
        await _session_manager.stop()
        logger.info("MCP Debug Server stopped")


# Create the MCP server
mcp = FastMCP(
    name="python-debugger",
    instructions="""Python Debug Server - Debug Python code interactively.

Use these tools to:
1. Create a debug session for your project
2. Set breakpoints on specific lines
3. Launch the program
4. When execution stops, inspect variables and evaluate expressions
5. Step through code or continue execution
6. Use watch expressions to track values across steps

Typical workflow:
1. debug_create_session - Create session for your project
2. debug_set_breakpoints - Set breakpoints where you want to stop
3. debug_launch - Start the program
4. debug_poll_events - Wait for stopped event
5. debug_get_stacktrace, debug_get_variables - Inspect state
6. debug_evaluate - Test expressions
7. debug_step_over/into/out or debug_continue - Resume execution
""",
    lifespan=lifespan,
)


def _get_manager() -> SessionManager:
    """Get the session manager, raising if not initialized."""
    if _session_manager is None:
        raise RuntimeError("Session manager not initialized")
    return _session_manager


# =============================================================================
# Session Management Tools
# =============================================================================


@mcp.tool()
async def debug_create_session(
    project_root: str,
    name: str | None = None,
    timeout_minutes: int = 60,
) -> dict[str, Any]:
    """Create a new debug session for a project.

    Args:
        project_root: Absolute path to the project root directory
        name: Optional friendly name for the session
        timeout_minutes: Session timeout in minutes (default 60)

    Returns:
        Session information including session_id needed for other operations
    """
    manager = _get_manager()
    try:
        config = SessionConfig(
            project_root=project_root,
            name=name,
            timeout_minutes=timeout_minutes,
        )
        session = await manager.create_session(config)
        return {
            "session_id": session.id,
            "name": session.name,
            "project_root": str(session.project_root),
            "state": session.state.value,
            "message": "Session created. Set breakpoints and then launch.",
        }
    except SessionLimitError as e:
        return {"error": str(e), "code": "SESSION_LIMIT"}


@mcp.tool()
async def debug_list_sessions() -> dict[str, Any]:
    """List all active debug sessions.

    Returns:
        List of active sessions with their current state
    """
    manager = _get_manager()
    sessions = await manager.list_sessions()
    return {
        "sessions": [
            {
                "session_id": s.id,
                "name": s.name,
                "project_root": str(s.project_root),
                "state": s.state.value,
                "stop_reason": s.stop_reason,
            }
            for s in sessions
        ],
        "total": len(sessions),
    }


@mcp.tool()
async def debug_get_session(session_id: str) -> dict[str, Any]:
    """Get detailed information about a debug session.

    Args:
        session_id: The session ID returned from debug_create_session

    Returns:
        Detailed session state including stop reason and location
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)
        return {
            "session_id": session.id,
            "name": session.name,
            "project_root": str(session.project_root),
            "state": session.state.value,
            "current_thread_id": session.current_thread_id,
            "stop_reason": session.stop_reason,
            "stop_location": session.stop_location,
        }
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}


@mcp.tool()
async def debug_terminate_session(session_id: str) -> dict[str, Any]:
    """Terminate a debug session and clean up resources.

    Args:
        session_id: The session ID to terminate

    Returns:
        Confirmation of termination
    """
    manager = _get_manager()
    try:
        await manager.terminate_session(session_id)
        return {"status": "terminated", "session_id": session_id}
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}


# =============================================================================
# Breakpoint Tools
# =============================================================================


@mcp.tool()
async def debug_set_breakpoints(
    session_id: str,
    file_path: str,
    lines: list[int],
    conditions: list[str | None] | None = None,
) -> dict[str, Any]:
    """Set breakpoints in a source file.

    Args:
        session_id: The debug session ID
        file_path: Absolute path to the source file
        lines: List of line numbers to set breakpoints on
        conditions: Optional list of conditions (same length as lines)
                   Use None for unconditional breakpoints

    Returns:
        List of verified breakpoints with their actual locations
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)

        # Build breakpoint list
        breakpoints = []
        for i, line in enumerate(lines):
            condition = None
            if conditions and i < len(conditions):
                condition = conditions[i]
            breakpoints.append(SourceBreakpoint(line=line, condition=condition))

        result = await session.set_breakpoints(file_path, breakpoints)

        # Save to persistence
        await manager.save_breakpoints(session)

        return {
            "file": file_path,
            "breakpoints": [
                {
                    "line": bp.line,
                    "verified": bp.verified,
                    "message": bp.message,
                }
                for bp in result
            ],
        }
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}


@mcp.tool()
async def debug_get_breakpoints(session_id: str) -> dict[str, Any]:
    """Get all breakpoints for a session.

    Args:
        session_id: The debug session ID

    Returns:
        All breakpoints organized by file
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)
        return {
            "files": {
                path: [{"line": bp.line, "condition": bp.condition} for bp in bps]
                for path, bps in session._breakpoints.items()
            }
        }
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}


@mcp.tool()
async def debug_clear_breakpoints(
    session_id: str,
    file_path: str | None = None,
) -> dict[str, Any]:
    """Clear breakpoints from a file or all files.

    Args:
        session_id: The debug session ID
        file_path: Path to clear breakpoints from (None = clear all)

    Returns:
        Confirmation of cleared breakpoints
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)

        if file_path:
            await session.set_breakpoints(file_path, [])
            return {"status": "cleared", "file": file_path}
        else:
            for path in list(session._breakpoints.keys()):
                await session.set_breakpoints(path, [])
            return {"status": "cleared", "files": "all"}
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}


# =============================================================================
# Launch and Execution Tools
# =============================================================================


@mcp.tool()
async def debug_launch(
    session_id: str,
    program: str | None = None,
    module: str | None = None,
    args: list[str] | None = None,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    stop_on_entry: bool = False,
    stop_on_exception: bool = True,
) -> dict[str, Any]:
    """Launch a Python program for debugging.

    Args:
        session_id: The debug session ID
        program: Path to Python script to run (use this OR module)
        module: Python module to run with -m (use this OR program)
        args: Command-line arguments to pass to the program
        cwd: Working directory for the program
        env: Additional environment variables
        stop_on_entry: Stop at first line of code
        stop_on_exception: Stop on uncaught exceptions

    Returns:
        Launch status - poll for events to detect when stopped
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)

        if not program and not module:
            return {"error": "Either program or module must be specified"}

        launch_kwargs: dict[str, Any] = {
            "program": program,
            "module": module,
            "args": args or [],
            "env": env or {},
            "stop_on_entry": stop_on_entry,
            "stop_on_exception": stop_on_exception,
        }
        if cwd is not None:
            launch_kwargs["cwd"] = cwd

        config = LaunchConfig(**launch_kwargs)

        await session.launch(config)

        return {
            "status": "launched",
            "session_id": session_id,
            "state": session.state.value,
            "message": "Program launched. Poll events or wait for stopped state.",
        }
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}
    except InvalidSessionStateError as e:
        return {"error": str(e), "code": "INVALID_STATE"}
    except Exception as e:
        return {"error": str(e), "code": "LAUNCH_FAILED"}


@mcp.tool()
async def debug_continue(
    session_id: str,
    thread_id: int | None = None,
) -> dict[str, Any]:
    """Continue execution until next breakpoint or program end.

    Args:
        session_id: The debug session ID
        thread_id: Thread to continue (uses current thread if not specified)

    Returns:
        Execution status
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)
        await session.continue_(thread_id)
        return {"status": "continued", "state": session.state.value}
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}
    except InvalidSessionStateError as e:
        return {"error": str(e), "code": "INVALID_STATE"}


@mcp.tool()
async def debug_step_over(
    session_id: str,
    thread_id: int | None = None,
) -> dict[str, Any]:
    """Step over to the next line (don't enter functions).

    Args:
        session_id: The debug session ID
        thread_id: Thread to step (uses current thread if not specified)

    Returns:
        Step status - poll events for stopped notification
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)
        await session.step_over(thread_id)
        return {"status": "stepping", "action": "step_over"}
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}
    except InvalidSessionStateError as e:
        return {"error": str(e), "code": "INVALID_STATE"}


@mcp.tool()
async def debug_step_into(
    session_id: str,
    thread_id: int | None = None,
) -> dict[str, Any]:
    """Step into the next function call.

    Args:
        session_id: The debug session ID
        thread_id: Thread to step (uses current thread if not specified)

    Returns:
        Step status - poll events for stopped notification
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)
        await session.step_into(thread_id)
        return {"status": "stepping", "action": "step_into"}
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}
    except InvalidSessionStateError as e:
        return {"error": str(e), "code": "INVALID_STATE"}


@mcp.tool()
async def debug_step_out(
    session_id: str,
    thread_id: int | None = None,
) -> dict[str, Any]:
    """Step out of the current function.

    Args:
        session_id: The debug session ID
        thread_id: Thread to step (uses current thread if not specified)

    Returns:
        Step status - poll events for stopped notification
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)
        await session.step_out(thread_id)
        return {"status": "stepping", "action": "step_out"}
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}
    except InvalidSessionStateError as e:
        return {"error": str(e), "code": "INVALID_STATE"}


@mcp.tool()
async def debug_pause(
    session_id: str,
    thread_id: int | None = None,
) -> dict[str, Any]:
    """Pause a running program.

    Args:
        session_id: The debug session ID
        thread_id: Thread to pause (uses current thread if not specified)

    Returns:
        Pause status
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)
        await session.pause(thread_id)
        return {"status": "pausing"}
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}
    except InvalidSessionStateError as e:
        return {"error": str(e), "code": "INVALID_STATE"}


# =============================================================================
# Inspection Tools
# =============================================================================


@mcp.tool()
async def debug_get_stacktrace(
    session_id: str,
    thread_id: int | None = None,
    max_frames: int = 20,
    format: str = "json",
) -> dict[str, Any]:
    """Get the call stack when paused.

    Args:
        session_id: The debug session ID
        thread_id: Thread to get stack for (uses current thread if not specified)
        max_frames: Maximum number of frames to return
        format: Output format - "json" (structured data) or "tui" (rich terminal)

    Returns:
        Stack frames with file, line, and function information.
        If format="tui", includes formatted tables and call chain diagram.
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)
        frames = await session.get_stack_trace(thread_id, levels=max_frames)
        frame_dicts = [
            {
                "id": f.id,
                "name": f.name,
                "file": f.source.path if f.source else None,
                "line": f.line,
                "column": f.column,
            }
            for f in frames
        ]

        result: dict[str, Any] = {
            "frames": frame_dicts,
            "total": len(frames),
            "format": format,
        }

        if format == "tui":
            formatter = _get_formatter()
            result["formatted"] = formatter.format_stack_trace(frame_dicts)
            result["call_chain"] = formatter.format_call_chain(frame_dicts)

        return result
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}


@mcp.tool()
async def debug_get_scopes(
    session_id: str,
    frame_id: int,
    format: str = "json",
) -> dict[str, Any]:
    """Get variable scopes (locals, globals) for a stack frame.

    Args:
        session_id: The debug session ID
        frame_id: Frame ID from debug_get_stacktrace
        format: Output format - "json" (structured data) or "tui" (rich terminal)

    Returns:
        List of scopes with their variables_reference for fetching variables.
        If format="tui", includes formatted table.
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)
        scopes = await session.get_scopes(frame_id)
        scope_dicts = [
            {
                "name": s.name,
                "variables_reference": s.variables_reference,
                "expensive": s.expensive,
            }
            for s in scopes
        ]

        result: dict[str, Any] = {
            "scopes": scope_dicts,
            "format": format,
        }

        if format == "tui":
            formatter = _get_formatter()
            result["formatted"] = formatter.format_scopes(scope_dicts)

        return result
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}


@mcp.tool()
async def debug_get_variables(
    session_id: str,
    variables_reference: int,
    max_count: int = 100,
    format: str = "json",
) -> dict[str, Any]:
    """Get variables for a scope or compound variable.

    Args:
        session_id: The debug session ID
        variables_reference: Reference from debug_get_scopes or nested variable
        max_count: Maximum variables to return
        format: Output format - "json" (structured data) or "tui" (rich terminal)

    Returns:
        List of variables with names, values, and types.
        If format="tui", includes formatted table.
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)
        variables = await session.get_variables(variables_reference, count=max_count)
        var_dicts = [
            {
                "name": v.name,
                "value": v.value,
                "type": v.type,
                "variables_reference": v.variables_reference,
                "has_children": v.variables_reference > 0,
            }
            for v in variables
        ]

        result: dict[str, Any] = {
            "variables": var_dicts,
            "format": format,
        }

        if format == "tui":
            formatter = _get_formatter()
            result["formatted"] = formatter.format_variables(var_dicts)

        return result
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}


@mcp.tool()
async def debug_evaluate(
    session_id: str,
    expression: str,
    frame_id: int | None = None,
) -> dict[str, Any]:
    """Evaluate a Python expression in the current debug context.

    Args:
        session_id: The debug session ID
        expression: Python expression to evaluate
        frame_id: Stack frame to evaluate in (uses topmost if not specified)

    Returns:
        Expression result with value and type
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)
        result = await session.evaluate(expression, frame_id)
        return {
            "expression": expression,
            "result": result.get("result", ""),
            "type": result.get("type"),
            "variables_reference": result.get("variablesReference", 0),
        }
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}
    except Exception as e:
        return {"error": str(e), "code": "EVAL_ERROR"}


# =============================================================================
# Watch Expression Tools
# =============================================================================


@mcp.tool()
async def debug_add_watch(
    session_id: str,
    expression: str,
) -> dict[str, Any]:
    """Add a watch expression to track across debug steps.

    Args:
        session_id: The debug session ID
        expression: Python expression to watch

    Returns:
        Updated list of watch expressions
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)
        watches = session.add_watch(expression)
        return {"watches": watches}
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}


@mcp.tool()
async def debug_remove_watch(
    session_id: str,
    expression: str,
) -> dict[str, Any]:
    """Remove a watch expression.

    Args:
        session_id: The debug session ID
        expression: Expression to remove

    Returns:
        Updated list of watch expressions
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)
        watches = session.remove_watch(expression)
        return {"watches": watches}
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}


@mcp.tool()
async def debug_list_watches(session_id: str) -> dict[str, Any]:
    """List all watch expressions for a session.

    Args:
        session_id: The debug session ID

    Returns:
        List of watch expressions
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)
        return {"watches": session.list_watches()}
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}


@mcp.tool()
async def debug_evaluate_watches(
    session_id: str,
    frame_id: int | None = None,
) -> dict[str, Any]:
    """Evaluate all watch expressions.

    Args:
        session_id: The debug session ID
        frame_id: Stack frame to evaluate in (uses topmost if not specified)

    Returns:
        Results for each watch expression
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)
        results = await session.evaluate_watches(frame_id)
        return {
            "results": [
                {
                    "expression": r["expression"],
                    "result": r["result"],
                    "type": r["type"],
                    "error": r["error"],
                }
                for r in results
            ]
        }
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}


# =============================================================================
# Event and Output Tools
# =============================================================================


@mcp.tool()
async def debug_poll_events(
    session_id: str,
    timeout_seconds: float = 5.0,
) -> dict[str, Any]:
    """Poll for debug events (stopped, continued, terminated, etc).

    Use this after launching or stepping to wait for the program to stop.

    Args:
        session_id: The debug session ID
        timeout_seconds: How long to wait for events (default 5s)

    Returns:
        List of events that occurred, or empty if timeout
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)
        events = await session.event_queue.get_all(timeout=timeout_seconds)
        return {
            "events": [
                {
                    "type": e.type.value,
                    "timestamp": e.timestamp.isoformat(),
                    "data": e.data,
                }
                for e in events
            ],
            "session_state": session.state.value,
        }
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}


@mcp.tool()
async def debug_get_output(
    session_id: str,
    offset: int = 0,
    limit: int = 100,
) -> dict[str, Any]:
    """Get program output (stdout/stderr).

    Args:
        session_id: The debug session ID
        offset: Start from this line number
        limit: Maximum lines to return

    Returns:
        Program output lines with category (stdout/stderr)
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)
        page = session.output_buffer.get_page(offset, limit)
        return {
            "lines": [
                {
                    "line_number": line.line_number,
                    "category": line.category,
                    "content": line.content,
                }
                for line in page.lines
            ],
            "offset": offset,
            "total": page.total,
            "has_more": page.has_more,
        }
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}


# =============================================================================
# Recovery Tools
# =============================================================================


@mcp.tool()
async def debug_list_recoverable() -> dict[str, Any]:
    """List sessions that can be recovered from previous server run.

    Returns:
        List of recoverable sessions with their saved state
    """
    manager = _get_manager()
    sessions = await manager.list_recoverable_sessions()
    return {
        "sessions": [
            {
                "session_id": s.id,
                "name": s.name,
                "project_root": s.project_root,
                "previous_state": s.state,
                "saved_at": s.saved_at.isoformat(),
                "breakpoint_count": sum(len(bps) for bps in s.breakpoints.values()),
                "watch_count": len(s.watch_expressions),
            }
            for s in sessions
        ],
        "total": len(sessions),
    }


@mcp.tool()
async def debug_recover_session(session_id: str) -> dict[str, Any]:
    """Recover a session from previous server run.

    This restores breakpoints and watch expressions but requires
    launching the program again.

    Args:
        session_id: ID of the recoverable session

    Returns:
        Recovered session information
    """
    manager = _get_manager()
    try:
        session = await manager.recover_session(session_id)
        return {
            "session_id": session.id,
            "name": session.name,
            "project_root": str(session.project_root),
            "state": session.state.value,
            "breakpoints_restored": sum(len(bps) for bps in session._breakpoints.values()),
            "watches_restored": len(session._watch_expressions),
            "message": "Session recovered. Set any additional breakpoints and launch.",
        }
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found in recovery list", "code": "NOT_FOUND"}
    except SessionLimitError as e:
        return {"error": str(e), "code": "SESSION_LIMIT"}


# =============================================================================
# Main Entry Point
# =============================================================================


def main():
    """Run the MCP server via stdio transport."""
    import signal
    import sys

    # Ignore SIGTTIN/SIGTTOU to prevent suspension when debugpy subprocesses
    # try to access the terminal. This allows the MCP server to continue
    # running even if child processes attempt TTY operations.
    if sys.platform != "win32":
        signal.signal(signal.SIGTTIN, signal.SIG_IGN)
        signal.signal(signal.SIGTTOU, signal.SIG_IGN)

    # Configure logging to stderr (stdout is for MCP protocol)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    # Run with stdio transport
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
