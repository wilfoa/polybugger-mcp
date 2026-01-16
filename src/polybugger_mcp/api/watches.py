"""Watch expression endpoints."""

from fastapi import APIRouter

from polybugger_mcp.api.deps import SessionDep
from polybugger_mcp.models.requests import (
    AddWatchRequest,
    EvaluateWatchesRequest,
    RemoveWatchRequest,
)
from polybugger_mcp.models.responses import (
    WatchListResponse,
    WatchResultResponse,
    WatchResultsResponse,
)

router = APIRouter(prefix="/sessions/{session_id}/watches", tags=["Watches"])


@router.get("", response_model=WatchListResponse)
async def list_watches(session: SessionDep) -> WatchListResponse:
    """List all watch expressions for a session."""
    return WatchListResponse(expressions=session.list_watches())


@router.post("", response_model=WatchListResponse)
async def add_watch(
    session: SessionDep,
    request: AddWatchRequest,
) -> WatchListResponse:
    """Add a watch expression."""
    expressions = session.add_watch(request.expression)
    return WatchListResponse(expressions=expressions)


@router.delete("", response_model=WatchListResponse)
async def remove_watch(
    session: SessionDep,
    request: RemoveWatchRequest,
) -> WatchListResponse:
    """Remove a watch expression."""
    expressions = session.remove_watch(request.expression)
    return WatchListResponse(expressions=expressions)


@router.delete("/all", response_model=WatchListResponse)
async def clear_watches(session: SessionDep) -> WatchListResponse:
    """Clear all watch expressions."""
    session.clear_watches()
    return WatchListResponse(expressions=[])


@router.post("/evaluate", response_model=WatchResultsResponse)
async def evaluate_watches(
    session: SessionDep,
    request: EvaluateWatchesRequest,
) -> WatchResultsResponse:
    """Evaluate all watch expressions.

    Returns the current value of each watch expression.
    Only works when the session is paused at a breakpoint.
    """
    results = await session.evaluate_watches(frame_id=request.frame_id)
    return WatchResultsResponse(
        results=[
            WatchResultResponse(
                expression=r["expression"],
                result=r["result"],
                type=r["type"],
                variables_reference=r["variables_reference"],
                error=r["error"],
            )
            for r in results
        ]
    )
