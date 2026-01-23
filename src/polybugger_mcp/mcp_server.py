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
from polybugger_mcp.models.dap import AttachConfig, LaunchConfig, PathMapping, SourceBreakpoint
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
    name="polybugger",
    instructions="""Multi-language debugger supporting Python, JavaScript/TypeScript, Go, and Rust. Workflow: list_languages (optional) -> create_session(language) -> set_breakpoints -> launch -> poll_events -> get_stacktrace/variables/evaluate -> step/continue. Use watches to track expressions.""",
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
    language: str = "python",
    name: str | None = None,
    timeout_minutes: int = 60,
    python_path: str | None = None,
) -> dict[str, Any]:
    """Create a debug session. Returns session_id for other operations.

    Args:
        project_root: Project root path
        language: Programming language (python, javascript, go, rust)
        name: Session name (optional)
        timeout_minutes: Timeout (default 60)
        python_path: Path to Python interpreter (e.g., .venv/bin/python). Uses system default if not set.
    """
    from polybugger_mcp.adapters.factory import is_language_supported

    manager = _get_manager()
    try:
        # Validate language
        if not is_language_supported(language):
            from polybugger_mcp.adapters.factory import get_supported_languages

            return {
                "error": f"Unsupported language: {language}",
                "code": "UNSUPPORTED_LANGUAGE",
                "supported": get_supported_languages(),
            }

        config = SessionConfig(
            project_root=project_root,
            language=language,
            name=name,
            timeout_minutes=timeout_minutes,
            python_path=python_path,
        )
        session = await manager.create_session(config)
        result = {
            "session_id": session.id,
            "name": session.name,
            "project_root": str(session.project_root),
            "language": session.language,
            "state": session.state.value,
            "message": f"Session created for {language}. Set breakpoints and then launch.",
        }
        if session.python_path:
            result["python_path"] = session.python_path
        return result
    except SessionLimitError as e:
        return {"error": str(e), "code": "SESSION_LIMIT"}


@mcp.tool()
async def debug_list_languages() -> dict[str, Any]:
    """List supported programming languages for debugging."""
    from polybugger_mcp.adapters.factory import get_supported_languages

    return {
        "languages": get_supported_languages(),
        "default": "python",
        "message": "Use language parameter in debug_create_session to specify language.",
    }


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
                "language": s.language,
                "python_path": s.python_path,
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
        result = {
            "session_id": session.id,
            "name": session.name,
            "project_root": str(session.project_root),
            "language": session.language,
            "state": session.state.value,
            "current_thread_id": session.current_thread_id,
            "stop_reason": session.stop_reason,
            "stop_location": session.stop_location,
        }
        if session.python_path:
            result["python_path"] = session.python_path
        return result
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
    hit_conditions: list[str | None] | None = None,
    log_messages: list[str | None] | None = None,
) -> dict[str, Any]:
    """Set breakpoints in a file with optional conditions, hit counts, and log messages.

    Args:
        session_id: Session ID
        file_path: Source file path
        lines: Line numbers
        conditions: Optional conditions per line (e.g., "x > 5", "len(items) == 0")
        hit_conditions: Optional hit count conditions per line (e.g., ">=5", "==10", "%3==0")
        log_messages: Optional log messages per line (logpoints). Can include {expressions}.
                      Example: "Value is {x}, length is {len(items)}"
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)

        # Build breakpoint list
        breakpoints = []
        for i, line in enumerate(lines):
            condition = None
            hit_condition = None
            log_message = None
            if conditions and i < len(conditions):
                condition = conditions[i]
            if hit_conditions and i < len(hit_conditions):
                hit_condition = hit_conditions[i]
            if log_messages and i < len(log_messages):
                log_message = log_messages[i]
            breakpoints.append(
                SourceBreakpoint(
                    line=line,
                    condition=condition,
                    hit_condition=hit_condition,
                    log_message=log_message,
                )
            )

        result = await session.set_breakpoints(file_path, breakpoints)

        # Save to persistence
        await manager.save_breakpoints(session)

        # Return breakpoint info including conditions
        return {
            "file": file_path,
            "breakpoints": [
                {
                    "line": bp.line,
                    "verified": bp.verified,
                    "message": bp.message,
                    "condition": breakpoints[i].condition,
                    "hit_condition": breakpoints[i].hit_condition,
                    "log_message": breakpoints[i].log_message,
                }
                for i, bp in enumerate(result)
            ],
        }
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}


@mcp.tool()
async def debug_get_breakpoints(session_id: str) -> dict[str, Any]:
    """Get all breakpoints organized by file, including conditions, hit counts, and log messages."""
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)
        return {
            "files": {
                path: [
                    {
                        "line": bp.line,
                        "condition": bp.condition,
                        "hit_condition": bp.hit_condition,
                        "log_message": bp.log_message,
                    }
                    for bp in bps
                ]
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

        # Use session's python_path if configured
        if session.python_path:
            launch_kwargs["python_path"] = session.python_path

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
async def debug_attach(
    session_id: str,
    host: str = "localhost",
    port: int = 5678,
    process_id: int | None = None,
    path_mappings: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Attach to a remote debugpy server.

    Use this to attach to a Python process that's already running debugpy.
    The target process must have called debugpy.listen() or been started with
    `python -m debugpy --listen host:port`.

    Args:
        session_id: Session ID
        host: Remote host running debugpy (default localhost)
        port: debugpy port (default 5678)
        process_id: PID to attach to (alternative to host:port for local processes)
        path_mappings: Local/remote path mappings for source files.
                       Each mapping is {"local_root": "/local/path", "remote_root": "/remote/path"}
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)

        # Build path mappings
        mappings: list[PathMapping] = []
        if path_mappings:
            for pm in path_mappings:
                mappings.append(
                    PathMapping(
                        local_root=pm.get("local_root", ""),
                        remote_root=pm.get("remote_root", ""),
                    )
                )

        config = AttachConfig(
            host=host,
            port=port,
            process_id=process_id,
            path_mappings=mappings,
        )

        await session.attach(config)

        return {
            "status": "attached",
            "session_id": session_id,
            "state": session.state.value,
            "host": host,
            "port": port,
            "message": "Attached to debugpy. Poll events or wait for stopped state.",
        }
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}
    except InvalidSessionStateError as e:
        return {"error": str(e), "code": "INVALID_STATE"}
    except Exception as e:
        return {"error": str(e), "code": "ATTACH_FAILED"}


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
# Container Debugging Tools
# =============================================================================


@mcp.tool()
async def debug_container_list_processes(
    runtime: str,
    container: str,
    namespace: str = "default",
    container_name: str | None = None,
    ssh_host: str | None = None,
    ssh_user: str | None = None,
    ssh_key_path: str | None = None,
) -> dict[str, Any]:
    """List Python processes in a container.

    Args:
        runtime: Container runtime - "docker", "podman", or "kubernetes"
        container: Container ID/name (or pod name for Kubernetes)
        namespace: Kubernetes namespace (ignored for docker/podman)
        container_name: Container name within pod (for multi-container pods)
        ssh_host: SSH host for remote containers
        ssh_user: SSH username for remote containers
        ssh_key_path: Path to SSH private key
    """
    from polybugger_mcp.containers.base import (
        ContainerError,
        ContainerNotFoundError,
        ContainerNotRunningError,
    )
    from polybugger_mcp.containers.factory import create_runtime, is_runtime_supported
    from polybugger_mcp.containers.ssh_tunnel import SSHTunnelError
    from polybugger_mcp.models.container import (
        ContainerRuntime,
        ContainerTarget,
        SSHConfig,
    )

    # Validate runtime
    if not is_runtime_supported(runtime):
        from polybugger_mcp.containers.factory import get_supported_runtimes

        return {
            "error": f"Unsupported runtime: {runtime}",
            "code": "UNSUPPORTED_RUNTIME",
            "supported": get_supported_runtimes(),
        }

    try:
        # Create target
        runtime_enum = ContainerRuntime(runtime.lower())
        ssh_config = None
        if ssh_host and ssh_user:
            ssh_config = SSHConfig(
                host=ssh_host,
                user=ssh_user,
                key_path=ssh_key_path,
            )

        target = ContainerTarget(
            runtime=runtime_enum,
            container_id=container if not container.startswith("/") else None,
            container_name=container
            if container.startswith("/") or not container.isalnum()
            else None,
            namespace=namespace,
            pod_name=container if runtime_enum == ContainerRuntime.KUBERNETES else None,
            pod_container=container_name,
            ssh=ssh_config,
        )

        # For Docker/Podman, set container_name if it looks like a name
        if runtime_enum in (ContainerRuntime.DOCKER, ContainerRuntime.PODMAN):
            if not target.container_id:
                target.container_name = container

        # Create runtime adapter
        adapter = create_runtime(runtime)

        # Check if available
        if not await adapter.is_available():
            return {
                "error": f"{runtime} CLI not available",
                "code": "RUNTIME_NOT_AVAILABLE",
                "hint": f"Ensure {adapter.cli_command} is installed and accessible",
            }

        # Find Python processes
        processes = await adapter.find_python_processes(target)

        return {
            "container": target.identifier,
            "runtime": runtime,
            "processes": [
                {
                    "pid": p.pid,
                    "name": p.name,
                    "cmdline": p.cmdline,
                    "user": p.user,
                    "is_python": p.is_python,
                }
                for p in processes
            ],
            "total": len(processes),
        }

    except ContainerNotFoundError as e:
        return {"error": e.message, "code": e.code, "details": e.details}
    except ContainerNotRunningError as e:
        return {"error": e.message, "code": e.code, "details": e.details}
    except ContainerError as e:
        return {"error": e.message, "code": e.code, "details": e.details}
    except SSHTunnelError as e:
        return {"error": e.message, "code": "SSH_ERROR", "details": e.details}
    except Exception as e:
        return {"error": str(e), "code": "CONTAINER_ERROR"}


@mcp.tool()
async def debug_container_attach(
    session_id: str,
    runtime: str,
    container: str,
    namespace: str = "default",
    container_name: str | None = None,
    process_id: int | None = None,
    process_name: str | None = None,
    inject_debugpy: bool = True,
    debugpy_port: int = 5678,
    path_mappings: list[dict[str, str]] | None = None,
    ssh_host: str | None = None,
    ssh_user: str | None = None,
    ssh_key_path: str | None = None,
) -> dict[str, Any]:
    """Attach debugger to a Python process in a container.

    This tool handles:
    1. Finding the target process (by PID or name)
    2. Injecting debugpy if not already running
    3. Setting up port forwarding if needed
    4. Attaching the debugger session

    Args:
        session_id: Debug session ID (from debug_create_session)
        runtime: Container runtime - "docker", "podman", or "kubernetes"
        container: Container ID/name (or pod name for Kubernetes)
        namespace: Kubernetes namespace
        container_name: Container name within pod (for multi-container pods)
        process_id: PID of Python process inside container
        process_name: Process name filter (e.g., "python", "gunicorn")
        inject_debugpy: Auto-inject debugpy if not running (requires SYS_PTRACE)
        debugpy_port: Port for debugpy to listen on (default 5678)
        path_mappings: Local/remote path mappings for source files
        ssh_host: SSH host for remote containers
        ssh_user: SSH username for remote containers
        ssh_key_path: Path to SSH private key
    """
    from polybugger_mcp.containers.base import (
        ContainerError,
        ContainerNotFoundError,
        ContainerNotRunningError,
        ContainerSecurityError,
    )
    from polybugger_mcp.containers.factory import create_runtime, is_runtime_supported
    from polybugger_mcp.containers.ssh_tunnel import SSHTunnelError, get_tunnel_manager
    from polybugger_mcp.models.container import (
        ContainerRuntime,
        ContainerTarget,
        SSHConfig,
    )

    manager = _get_manager()

    # Validate runtime
    if not is_runtime_supported(runtime):
        from polybugger_mcp.containers.factory import get_supported_runtimes

        return {
            "error": f"Unsupported runtime: {runtime}",
            "code": "UNSUPPORTED_RUNTIME",
            "supported": get_supported_runtimes(),
        }

    try:
        session = await manager.get_session(session_id)

        # Create target
        runtime_enum = ContainerRuntime(runtime.lower())
        ssh_config = None
        if ssh_host and ssh_user:
            ssh_config = SSHConfig(
                host=ssh_host,
                user=ssh_user,
                key_path=ssh_key_path,
            )

        target = ContainerTarget(
            runtime=runtime_enum,
            container_name=container,
            namespace=namespace,
            pod_name=container if runtime_enum == ContainerRuntime.KUBERNETES else None,
            pod_container=container_name,
            ssh=ssh_config,
        )

        # Create runtime adapter
        adapter = create_runtime(runtime)

        if not await adapter.is_available():
            return {
                "error": f"{runtime} CLI not available",
                "code": "RUNTIME_NOT_AVAILABLE",
            }

        # Find the target process
        if process_id is None:
            processes = await adapter.find_python_processes(target)
            if process_name:
                processes = [p for p in processes if process_name.lower() in p.cmdline.lower()]

            if not processes:
                return {
                    "error": "No matching Python processes found",
                    "code": "NO_PROCESS",
                    "hint": "Use debug_container_list_processes to see available processes",
                }

            if len(processes) > 1:
                return {
                    "error": f"Multiple Python processes found ({len(processes)})",
                    "code": "MULTIPLE_PROCESSES",
                    "processes": [{"pid": p.pid, "cmdline": p.cmdline} for p in processes],
                    "hint": "Specify process_id to select one",
                }

            process_id = processes[0].pid

        # Inject debugpy if requested
        if inject_debugpy:
            await adapter.inject_debugpy(target, process_id, debugpy_port)

        # Get debugpy endpoint
        host, port = await adapter.get_debugpy_endpoint(target, debugpy_port)

        # Handle SSH tunneling for remote containers
        if ssh_config:
            tunnel_manager = get_tunnel_manager()
            tunnel = await tunnel_manager.create_tunnel(
                ssh_config=ssh_config,
                remote_host=host,
                remote_port=port,
            )
            host = "127.0.0.1"
            port = tunnel.local_port

        # Build path mappings
        mappings: list[PathMapping] = []
        if path_mappings:
            for pm in path_mappings:
                mappings.append(
                    PathMapping(
                        local_root=pm.get("local_root", ""),
                        remote_root=pm.get("remote_root", ""),
                    )
                )

        # Create attach config and attach
        attach_config = AttachConfig(
            host=host,
            port=port,
            path_mappings=mappings,
        )

        await session.attach(attach_config)

        return {
            "status": "attached",
            "session_id": session_id,
            "state": session.state.value,
            "container": target.identifier,
            "runtime": runtime,
            "process_id": process_id,
            "debugpy_endpoint": f"{host}:{port}",
            "message": "Attached to container process. Poll events or wait for stopped state.",
        }

    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}
    except InvalidSessionStateError as e:
        return {"error": str(e), "code": "INVALID_STATE"}
    except ContainerSecurityError as e:
        return {
            "error": e.message,
            "code": e.code,
            "instructions": e.instructions,
        }
    except ContainerNotFoundError as e:
        return {"error": e.message, "code": e.code, "details": e.details}
    except ContainerNotRunningError as e:
        return {"error": e.message, "code": e.code, "details": e.details}
    except ContainerError as e:
        return {"error": e.message, "code": e.code, "details": e.details}
    except SSHTunnelError as e:
        return {"error": e.message, "code": "SSH_ERROR", "details": e.details}
    except Exception as e:
        logger.exception("Container attach failed")
        return {"error": str(e), "code": "ATTACH_FAILED"}


@mcp.tool()
async def debug_container_launch(
    session_id: str,
    runtime: str,
    container: str,
    namespace: str = "default",
    container_name: str | None = None,
    program: str | None = None,
    module: str | None = None,
    args: list[str] | None = None,
    cwd: str = "/app",
    env: dict[str, str] | None = None,
    debugpy_port: int = 5678,
    stop_on_entry: bool = False,
    path_mappings: list[dict[str, str]] | None = None,
    ssh_host: str | None = None,
    ssh_user: str | None = None,
    ssh_key_path: str | None = None,
) -> dict[str, Any]:
    """Launch a Python program with debugging in a container.

    This starts a new process with debugpy listening, then attaches
    the debug session. Does not require SYS_PTRACE capability.

    Args:
        session_id: Debug session ID (from debug_create_session)
        runtime: Container runtime - "docker", "podman", or "kubernetes"
        container: Container ID/name (or pod name for Kubernetes)
        namespace: Kubernetes namespace
        container_name: Container name within pod (for multi-container pods)
        program: Python script path inside container
        module: Python module to run (e.g., "pytest")
        args: Program arguments
        cwd: Working directory inside container (default /app)
        env: Environment variables
        debugpy_port: Port for debugpy (default 5678)
        stop_on_entry: Pause at first line (default False)
        path_mappings: Local/remote path mappings
        ssh_host: SSH host for remote containers
        ssh_user: SSH username for remote containers
        ssh_key_path: Path to SSH private key
    """
    from polybugger_mcp.containers.base import (
        ContainerError,
        ContainerNotFoundError,
        ContainerNotRunningError,
    )
    from polybugger_mcp.containers.factory import create_runtime, is_runtime_supported
    from polybugger_mcp.containers.ssh_tunnel import SSHTunnelError, get_tunnel_manager
    from polybugger_mcp.models.container import (
        ContainerRuntime,
        ContainerTarget,
        SSHConfig,
    )

    manager = _get_manager()

    if not program and not module:
        return {"error": "Either program or module must be specified", "code": "INVALID_ARGS"}

    # Validate runtime
    if not is_runtime_supported(runtime):
        from polybugger_mcp.containers.factory import get_supported_runtimes

        return {
            "error": f"Unsupported runtime: {runtime}",
            "code": "UNSUPPORTED_RUNTIME",
            "supported": get_supported_runtimes(),
        }

    try:
        session = await manager.get_session(session_id)

        # Create target
        runtime_enum = ContainerRuntime(runtime.lower())
        ssh_config = None
        if ssh_host and ssh_user:
            ssh_config = SSHConfig(
                host=ssh_host,
                user=ssh_user,
                key_path=ssh_key_path,
            )

        target = ContainerTarget(
            runtime=runtime_enum,
            container_name=container,
            namespace=namespace,
            pod_name=container if runtime_enum == ContainerRuntime.KUBERNETES else None,
            pod_container=container_name,
            ssh=ssh_config,
        )

        # Create runtime adapter
        adapter = create_runtime(runtime)

        if not await adapter.is_available():
            return {
                "error": f"{runtime} CLI not available",
                "code": "RUNTIME_NOT_AVAILABLE",
            }

        # Build command to launch
        command: list[str] = []
        if module:
            command = ["-m", module]
        elif program:
            command = [program]

        if args:
            command.extend(args)

        # Launch with debugpy
        await adapter.launch_with_debugpy(
            target=target,
            command=command,
            port=debugpy_port,
            wait_for_client=True,
            env=env,
            workdir=cwd,
        )

        # Give debugpy time to start - container processes may take longer
        import asyncio

        await asyncio.sleep(2.0)

        # Get debugpy endpoint
        host, port = await adapter.get_debugpy_endpoint(target, debugpy_port)

        # Handle SSH tunneling
        if ssh_config:
            tunnel_manager = get_tunnel_manager()
            tunnel = await tunnel_manager.create_tunnel(
                ssh_config=ssh_config,
                remote_host=host,
                remote_port=port,
            )
            host = "127.0.0.1"
            port = tunnel.local_port

        # Build path mappings
        mappings: list[PathMapping] = []
        if path_mappings:
            for pm in path_mappings:
                mappings.append(
                    PathMapping(
                        local_root=pm.get("local_root", ""),
                        remote_root=pm.get("remote_root", ""),
                    )
                )

        # Attach to the launched process
        attach_config = AttachConfig(
            host=host,
            port=port,
            path_mappings=mappings,
        )

        await session.attach(attach_config)

        return {
            "status": "launched",
            "session_id": session_id,
            "state": session.state.value,
            "container": target.identifier,
            "runtime": runtime,
            "program": program or module,
            "debugpy_endpoint": f"{host}:{port}",
            "message": "Program launched in container. Poll events or wait for stopped state.",
        }

    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}
    except InvalidSessionStateError as e:
        return {"error": str(e), "code": "INVALID_STATE"}
    except ContainerNotFoundError as e:
        return {"error": e.message, "code": e.code, "details": e.details}
    except ContainerNotRunningError as e:
        return {"error": e.message, "code": e.code, "details": e.details}
    except ContainerError as e:
        return {"error": e.message, "code": e.code, "details": e.details}
    except SSHTunnelError as e:
        return {"error": e.message, "code": "SSH_ERROR", "details": e.details}
    except Exception as e:
        logger.exception("Container launch failed")
        return {"error": str(e), "code": "LAUNCH_FAILED"}


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
