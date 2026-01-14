"""Breakpoint management endpoints."""

from fastapi import APIRouter, status

from python_debugger_mcp.api.deps import SessionDep, SessionManagerDep
from python_debugger_mcp.models.dap import SourceBreakpoint
from python_debugger_mcp.models.requests import SetBreakpointsRequest
from python_debugger_mcp.models.responses import (
    BreakpointListResponse,
    BreakpointResponse,
    SetBreakpointsResponse,
)

router = APIRouter(prefix="/sessions/{session_id}/breakpoints", tags=["Breakpoints"])


@router.post("", response_model=SetBreakpointsResponse)
async def set_breakpoints(
    request: SetBreakpointsRequest,
    session: SessionDep,
    session_manager: SessionManagerDep,
) -> SetBreakpointsResponse:
    """Set breakpoints for a source file.

    This replaces all breakpoints for the specified file.
    """
    breakpoints = [
        SourceBreakpoint(
            line=bp.line,
            column=bp.column,
            condition=bp.condition,
            hit_condition=bp.hit_condition,
            log_message=bp.log_message,
            enabled=bp.enabled,
        )
        for bp in request.breakpoints
    ]

    results = await session.set_breakpoints(request.source, breakpoints)

    # Save breakpoints to persistence
    await session_manager.save_breakpoints(session)

    return SetBreakpointsResponse(
        breakpoints=[
            BreakpointResponse(
                id=bp.id,
                verified=bp.verified,
                line=bp.line,
                column=bp.column,
                message=bp.message,
                source=request.source,
            )
            for bp in results
        ]
    )


@router.get("", response_model=BreakpointListResponse)
async def list_breakpoints(session: SessionDep) -> BreakpointListResponse:
    """List all breakpoints for the session."""
    files: dict[str, list[BreakpointResponse]] = {}

    for file_path, breakpoints in session._breakpoints.items():
        files[file_path] = [
            BreakpointResponse(
                verified=False,  # Can't know verification status without querying
                line=bp.line,
                column=bp.column,
                source=file_path,
            )
            for bp in breakpoints
        ]

    return BreakpointListResponse(files=files)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_breakpoints(
    session: SessionDep,
    session_manager: SessionManagerDep,
) -> None:
    """Clear all breakpoints for the session."""
    # Clear all breakpoints
    for file_path in list(session._breakpoints.keys()):
        await session.set_breakpoints(file_path, [])

    session._breakpoints.clear()
    await session_manager.save_breakpoints(session)
