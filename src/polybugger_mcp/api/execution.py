"""Execution control endpoints."""

from fastapi import APIRouter

from polybugger_mcp.api.deps import SessionDep
from polybugger_mcp.models.requests import ContinueRequest, PauseRequest, StepRequest
from polybugger_mcp.models.responses import ExecutionResponse, LocationResponse

router = APIRouter(prefix="/sessions/{session_id}", tags=["Execution"])


def _make_location(session: SessionDep) -> LocationResponse | None:
    """Create location response from session state."""
    if session.stop_location:
        return LocationResponse(
            file=session.stop_location.get("file"),
            line=session.stop_location.get("line", 0),
            column=session.stop_location.get("column"),
            function=session.stop_location.get("function"),
        )
    return None


@router.post("/continue", response_model=ExecutionResponse)
async def continue_execution(
    session: SessionDep,
    request: ContinueRequest | None = None,
) -> ExecutionResponse:
    """Continue program execution."""
    thread_id = request.thread_id if request else None
    await session.continue_(thread_id)
    return ExecutionResponse(
        status=session.state.value,
        location=_make_location(session),
    )


@router.post("/pause", response_model=ExecutionResponse)
async def pause_execution(
    session: SessionDep,
    request: PauseRequest | None = None,
) -> ExecutionResponse:
    """Pause program execution."""
    thread_id = request.thread_id if request else None
    await session.pause(thread_id)
    return ExecutionResponse(
        status=session.state.value,
        location=_make_location(session),
    )


@router.post("/step-over", response_model=ExecutionResponse)
async def step_over(
    session: SessionDep,
    request: StepRequest | None = None,
) -> ExecutionResponse:
    """Step over to the next line."""
    thread_id = request.thread_id if request else None
    await session.step_over(thread_id)
    return ExecutionResponse(
        status=session.state.value,
        location=_make_location(session),
    )


@router.post("/step-into", response_model=ExecutionResponse)
async def step_into(
    session: SessionDep,
    request: StepRequest | None = None,
) -> ExecutionResponse:
    """Step into a function call."""
    thread_id = request.thread_id if request else None
    await session.step_into(thread_id)
    return ExecutionResponse(
        status=session.state.value,
        location=_make_location(session),
    )


@router.post("/step-out", response_model=ExecutionResponse)
async def step_out(
    session: SessionDep,
    request: StepRequest | None = None,
) -> ExecutionResponse:
    """Step out of the current function."""
    thread_id = request.thread_id if request else None
    await session.step_out(thread_id)
    return ExecutionResponse(
        status=session.state.value,
        location=_make_location(session),
    )
