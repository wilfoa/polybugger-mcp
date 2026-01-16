"""Session recovery endpoints."""

from fastapi import APIRouter, HTTPException

from polybugger_mcp.api.deps import SessionManagerDep
from polybugger_mcp.core.exceptions import SessionLimitError, SessionNotFoundError
from polybugger_mcp.models.responses import (
    RecoverableSessionResponse,
    RecoverableSessionsResponse,
    SessionResponse,
)

router = APIRouter(prefix="/recovery", tags=["Recovery"])


@router.get("/sessions", response_model=RecoverableSessionsResponse)
async def list_recoverable_sessions(
    manager: SessionManagerDep,
) -> RecoverableSessionsResponse:
    """List all sessions available for recovery.

    These are sessions from a previous server run that were either:
    - Saved during graceful shutdown
    - Periodically persisted during operation (for crash recovery)

    Use POST /recovery/sessions/{session_id} to recover a session,
    or DELETE /recovery/sessions/{session_id} to dismiss it.
    """
    sessions = await manager.list_recoverable_sessions()
    return RecoverableSessionsResponse(
        sessions=[
            RecoverableSessionResponse(
                id=s.id,
                name=s.name,
                project_root=s.project_root,
                previous_state=s.state,
                created_at=s.created_at,
                last_activity=s.last_activity,
                saved_at=s.saved_at,
                server_shutdown=s.server_shutdown,
                breakpoint_count=sum(len(bps) for bps in s.breakpoints.values()),
                watch_expression_count=len(s.watch_expressions),
            )
            for s in sessions
        ],
        total=len(sessions),
    )


@router.post("/sessions/{session_id}", response_model=SessionResponse)
async def recover_session(
    session_id: str,
    manager: SessionManagerDep,
) -> SessionResponse:
    """Recover a session from previous server run.

    This creates a NEW debug session initialized with the settings
    (breakpoints, watch expressions) from the previous session.

    Note: The debug process itself cannot be restored - you will need
    to launch/attach again after recovery.
    """
    try:
        session = await manager.recover_session(session_id)
        info = session.to_info()
        return SessionResponse(
            id=info.id,
            name=info.name,
            project_root=info.project_root,
            state=info.state,
            created_at=info.created_at,
            last_activity=info.last_activity,
            current_thread_id=info.current_thread_id,
            stop_reason=info.stop_reason,
            stop_location=info.stop_location,
        )
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    except SessionLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))


@router.delete("/sessions/{session_id}")
async def dismiss_recoverable_session(
    session_id: str,
    manager: SessionManagerDep,
) -> dict[str, str]:
    """Dismiss a recoverable session without recovering it.

    This permanently removes the session from the recovery list.
    """
    dismissed = await manager.dismiss_recoverable_session(session_id)
    if not dismissed:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return {"status": "dismissed", "session_id": session_id}


@router.delete("/sessions")
async def dismiss_all_recoverable_sessions(
    manager: SessionManagerDep,
) -> dict[str, int]:
    """Dismiss all recoverable sessions.

    This clears the entire recovery list.
    """
    sessions = await manager.list_recoverable_sessions()
    count = 0
    for session in sessions:
        if await manager.dismiss_recoverable_session(session.id):
            count += 1
    return {"dismissed": count}
