"""MCP Server for Python debugging.

This module provides an MCP (Model Context Protocol) server that exposes
the debug relay server functionality as MCP tools. AI agents can use these
tools to debug Python code interactively.

Usage:
    # Run as stdio server (for AI host integration)
    python -m polybugger_mcp.mcp_server

    # Or via entry point
    python-debugger-mcp-server
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP

from polybugger_mcp.core.exceptions import (
    InvalidSessionStateError,
    SessionLimitError,
    SessionNotFoundError,
)
from polybugger_mcp.core.session import SessionManager
from polybugger_mcp.models.dap import LaunchConfig, SourceBreakpoint
from polybugger_mcp.models.session import SessionConfig
from polybugger_mcp.utils.tui_formatter import TUIFormatter

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
    instructions="""Python debugger. Workflow: create_session -> set_breakpoints -> launch -> poll_events -> get_stacktrace/variables/evaluate -> step/continue. Use watches to track expressions.""",
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
    """Create a debug session. Returns session_id for other operations.

    Args:
        project_root: Project root path
        name: Session name (optional)
        timeout_minutes: Timeout (default 60)
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
    """List all active debug sessions."""
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
    """Get session state, stop reason, and location."""
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
    """Terminate session and clean up."""
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
    """Set breakpoints in a file.

    Args:
        session_id: Session ID
        file_path: Source file path
        lines: Line numbers
        conditions: Optional conditions per line
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
    """Get all breakpoints organized by file."""
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
    """Clear breakpoints from file or all files.

    Args:
        session_id: Session ID
        file_path: File path (None = all files)
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
    """Launch program for debugging. Use program OR module.

    Args:
        session_id: Session ID
        program: Script path
        module: Module to run with -m
        args: Arguments
        cwd: Working directory
        env: Environment variables
        stop_on_entry: Stop at first line
        stop_on_exception: Stop on exceptions
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
    """Continue until next breakpoint or end."""
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
async def debug_step(
    session_id: str,
    mode: str,
    thread_id: int | None = None,
) -> dict[str, Any]:
    """Step execution: over (next line), into (enter function), out (exit function).

    Args:
        session_id: Session ID
        mode: "over", "into", or "out"
        thread_id: Thread ID (default: current)
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)

        if mode == "over":
            await session.step_over(thread_id)
        elif mode == "into":
            await session.step_into(thread_id)
        elif mode == "out":
            await session.step_out(thread_id)
        else:
            return {
                "error": f"Invalid mode: {mode}. Use 'over', 'into', or 'out'",
                "code": "INVALID_MODE",
            }

        return {"status": "stepping", "mode": mode}
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}
    except InvalidSessionStateError as e:
        return {"error": str(e), "code": "INVALID_STATE"}


@mcp.tool()
async def debug_pause(
    session_id: str,
    thread_id: int | None = None,
) -> dict[str, Any]:
    """Pause a running program."""
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
    format: str = "tui",
) -> dict[str, Any]:
    """Get call stack frames.

    Args:
        session_id: Session ID
        thread_id: Thread ID (default: current)
        max_frames: Max frames (default 20)
        format: "json" or "tui"
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
    format: str = "tui",
) -> dict[str, Any]:
    """Get scopes (locals, globals) for a frame.

    Args:
        session_id: Session ID
        frame_id: Frame ID from stacktrace
        format: "json" or "tui"
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
    format: str = "tui",
) -> dict[str, Any]:
    """Get variables from a scope or compound variable.

    Args:
        session_id: Session ID
        variables_reference: Ref from scopes or nested variable
        max_count: Max variables (default 100)
        format: "json" or "tui"
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
    """Evaluate a Python expression.

    Args:
        session_id: Session ID
        expression: Expression to evaluate
        frame_id: Frame ID (default: topmost)
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


@mcp.tool()
async def debug_inspect_variable(
    session_id: str,
    variable_name: str,
    frame_id: int | None = None,
    max_preview_rows: int = 5,
    include_statistics: bool = True,
    format: str = "tui",
) -> dict[str, Any]:
    """Smart inspect DataFrames, arrays, dicts, lists with type-aware metadata.

    Args:
        session_id: Session ID
        variable_name: Variable to inspect
        frame_id: Frame ID (default: topmost)
        max_preview_rows: Preview limit (default 5, max 100)
        include_statistics: Include numeric stats
        format: "json" or "tui"

    Returns: name, type, detected_type, structure, preview, statistics, summary, warnings
    """
    from polybugger_mcp.models.inspection import InspectionOptions

    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)

        # Build options
        options = InspectionOptions(
            max_preview_rows=min(max_preview_rows, 100),
            max_preview_items=min(max_preview_rows * 2, 100),
            include_statistics=include_statistics,
        )

        # Perform inspection
        result = await session.inspect_variable(
            variable_name=variable_name,
            frame_id=frame_id,
            options=options,
        )

        # Convert to dict
        result_dict = result.model_dump(exclude_none=True)
        result_dict["format"] = format

        # Add TUI formatting if requested
        if format == "tui":
            formatter = _get_formatter()
            result_dict["formatted"] = formatter.format_inspection(result_dict)

        return result_dict

    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}
    except InvalidSessionStateError as e:
        return {
            "error": str(e),
            "code": "INVALID_STATE",
            "hint": "Session must be paused at a breakpoint to inspect variables",
        }
    except ValueError as e:
        return {
            "error": str(e),
            "code": "INVALID_VARIABLE",
            "hint": "Check variable name is valid and in scope",
        }
    except Exception as e:
        logger.exception(f"Inspection failed for {variable_name}")
        return {
            "error": str(e),
            "code": "INSPECTION_ERROR",
            "hint": "Use debug_evaluate for manual inspection",
        }


@mcp.tool()
async def debug_get_call_chain(
    session_id: str,
    thread_id: int | None = None,
    include_source_context: bool = True,
    context_lines: int = 2,
    format: str = "tui",
) -> dict[str, Any]:
    """Get call stack with source context showing path to current location.

    Args:
        session_id: Session ID
        thread_id: Thread ID (default: current)
        include_source_context: Include surrounding lines
        context_lines: Lines before/after (default 2)
        format: "json" or "tui"

    Returns: call_chain (frames with depth, function, file, line, source, context), total_frames
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)
        result = await session.get_call_chain(
            thread_id=thread_id,
            include_source_context=include_source_context,
            context_lines=context_lines,
        )

        result["format"] = format

        if format == "tui":
            formatter = _get_formatter()
            result["formatted"] = formatter.format_call_chain_with_context(
                result["call_chain"],
                include_source=include_source_context,
            )

        return result

    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}
    except InvalidSessionStateError as e:
        return {
            "error": str(e),
            "code": "INVALID_STATE",
            "hint": "Session must be paused at a breakpoint to get call chain",
        }
    except Exception as e:
        logger.exception("Failed to get call chain")
        return {"error": str(e), "code": "CALL_CHAIN_ERROR"}


# =============================================================================
# Watch Expression Tools
# =============================================================================


@mcp.tool()
async def debug_watch(
    session_id: str,
    action: str,
    expression: str | None = None,
) -> dict[str, Any]:
    """Manage watch expressions: add, remove, or list.

    Args:
        session_id: Session ID
        action: "add", "remove", or "list"
        expression: Expression (required for add/remove)
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)

        if action == "add":
            if not expression:
                return {"error": "Expression required for add", "code": "MISSING_EXPRESSION"}
            watches = session.add_watch(expression)
        elif action == "remove":
            if not expression:
                return {"error": "Expression required for remove", "code": "MISSING_EXPRESSION"}
            watches = session.remove_watch(expression)
        elif action == "list":
            watches = session.list_watches()
        else:
            return {
                "error": f"Invalid action: {action}. Use 'add', 'remove', or 'list'",
                "code": "INVALID_ACTION",
            }

        return {"watches": watches}
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}


@mcp.tool()
async def debug_evaluate_watches(
    session_id: str,
    frame_id: int | None = None,
) -> dict[str, Any]:
    """Evaluate all watch expressions and return results.

    Args:
        session_id: Session ID
        frame_id: Frame ID (default: topmost)
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
    """Poll for events (stopped, continued, terminated). Use after launch/step.

    Args:
        session_id: Session ID
        timeout_seconds: Wait time (default 5s)
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
    """Get program stdout/stderr output.

    Args:
        session_id: Session ID
        offset: Start line
        limit: Max lines (default 100)
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
    """List recoverable sessions from previous server run."""
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
    """Recover session (restores breakpoints/watches, requires re-launch)."""
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
