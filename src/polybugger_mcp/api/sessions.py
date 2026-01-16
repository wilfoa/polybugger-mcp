"""Session management endpoints."""

from fastapi import APIRouter, status

from polybugger_mcp.api.deps import SessionDep, SessionManagerDep
from polybugger_mcp.models.dap import AttachConfig, LaunchConfig
from polybugger_mcp.models.requests import (
    AttachRequest,
    CreateSessionRequest,
    LaunchRequest,
)
from polybugger_mcp.models.responses import (
    ExecutionResponse,
    SessionListResponse,
    SessionResponse,
)
from polybugger_mcp.models.session import SessionConfig

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: CreateSessionRequest,
    session_manager: SessionManagerDep,
) -> SessionResponse:
    """Create a new debug session."""
    config = SessionConfig(
        project_root=request.project_root,
        name=request.name,
        timeout_minutes=request.timeout_minutes,
    )
    session = await session_manager.create_session(config)
    info = session.to_info()
    return SessionResponse(**info.model_dump())


@router.get("", response_model=SessionListResponse)
async def list_sessions(session_manager: SessionManagerDep) -> SessionListResponse:
    """List all active sessions."""
    sessions = await session_manager.list_sessions()
    return SessionListResponse(
        sessions=[SessionResponse(**s.to_info().model_dump()) for s in sessions],
        total=len(sessions),
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session: SessionDep) -> SessionResponse:
    """Get session details."""
    info = session.to_info()
    return SessionResponse(**info.model_dump())


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def terminate_session(
    session_id: str,
    session_manager: SessionManagerDep,
) -> None:
    """Terminate a debug session."""
    await session_manager.terminate_session(session_id)


@router.post("/{session_id}/launch", response_model=ExecutionResponse)
async def launch_program(
    request: LaunchRequest,
    session: SessionDep,
) -> ExecutionResponse:
    """Launch the debug target."""
    config = LaunchConfig(
        program=request.program,
        module=request.module,
        args=request.args,
        python_args=request.python_args,
        cwd=request.cwd or str(session.project_root),
        env=request.env,
        python_path=request.python_path,
        stop_on_entry=request.stop_on_entry,
        stop_on_exception=request.stop_on_exception,
    )
    await session.launch(config)
    return ExecutionResponse(status=session.state.value)


@router.post("/{session_id}/attach", response_model=ExecutionResponse)
async def attach_to_process(
    request: AttachRequest,
    session: SessionDep,
) -> ExecutionResponse:
    """Attach to a running process."""
    config = AttachConfig(
        process_id=request.process_id,
        host=request.host,
        port=request.port,
    )
    await session.attach(config)
    return ExecutionResponse(status=session.state.value)
