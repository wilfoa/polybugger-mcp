"""API dependencies."""

from typing import Annotated

from fastapi import Depends, Path, Request

from polybugger_mcp.core.session import Session, SessionManager


async def get_session_manager(request: Request) -> SessionManager:
    """Get the session manager from app state."""
    manager: SessionManager = request.app.state.session_manager
    return manager


async def get_session(
    session_id: Annotated[str, Path(description="Session ID")],
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
) -> Session:
    """Get a session by ID."""
    return await session_manager.get_session(session_id)


SessionManagerDep = Annotated[SessionManager, Depends(get_session_manager)]
SessionDep = Annotated[Session, Depends(get_session)]
