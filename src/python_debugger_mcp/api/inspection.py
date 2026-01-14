"""State inspection endpoints."""

from fastapi import APIRouter, Query

from python_debugger_mcp.api.deps import SessionDep
from python_debugger_mcp.models.requests import EvaluateRequest
from python_debugger_mcp.models.responses import (
    EvaluateResponse,
    ScopeResponse,
    ScopesResponse,
    SourceResponse,
    StackFrameResponse,
    StackTraceResponse,
    ThreadListResponse,
    ThreadResponse,
    VariableResponse,
    VariablesResponse,
)

router = APIRouter(prefix="/sessions/{session_id}", tags=["Inspection"])


@router.get("/threads", response_model=ThreadListResponse)
async def get_threads(session: SessionDep) -> ThreadListResponse:
    """Get all threads."""
    threads = await session.get_threads()
    return ThreadListResponse(threads=[ThreadResponse(id=t.id, name=t.name) for t in threads])


@router.get("/stacktrace", response_model=StackTraceResponse)
async def get_stack_trace(
    session: SessionDep,
    thread_id: int | None = Query(None, description="Thread ID"),
    start_frame: int = Query(0, ge=0, description="Starting frame index"),
    levels: int = Query(20, ge=1, le=100, description="Number of frames"),
) -> StackTraceResponse:
    """Get stack trace for a thread."""
    frames = await session.get_stack_trace(thread_id, start_frame, levels)
    return StackTraceResponse(
        frames=[
            StackFrameResponse(
                id=f.id,
                name=f.name,
                source=SourceResponse(
                    name=f.source.name if f.source else None,
                    path=f.source.path if f.source else None,
                )
                if f.source
                else None,
                line=f.line,
                column=f.column,
            )
            for f in frames
        ],
        total_frames=len(frames),
    )


@router.get("/scopes", response_model=ScopesResponse)
async def get_scopes(
    session: SessionDep,
    frame_id: int = Query(..., description="Frame ID"),
) -> ScopesResponse:
    """Get variable scopes for a frame."""
    scopes = await session.get_scopes(frame_id)
    return ScopesResponse(
        scopes=[
            ScopeResponse(
                name=s.name,
                variables_reference=s.variables_reference,
                expensive=s.expensive,
            )
            for s in scopes
        ]
    )


@router.get("/variables", response_model=VariablesResponse)
async def get_variables(
    session: SessionDep,
    variables_ref: int = Query(..., alias="ref", description="Variable reference"),
    start: int = Query(0, ge=0, description="Starting index"),
    count: int = Query(100, ge=1, le=1000, description="Number of variables"),
) -> VariablesResponse:
    """Get variables for a scope or compound variable."""
    variables = await session.get_variables(variables_ref, start, count)
    return VariablesResponse(
        variables=[
            VariableResponse(
                name=v.name,
                value=v.value,
                type=v.type,
                variables_reference=v.variables_reference,
                named_variables=v.named_variables,
                indexed_variables=v.indexed_variables,
            )
            for v in variables
        ]
    )


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_expression(
    session: SessionDep,
    request: EvaluateRequest,
) -> EvaluateResponse:
    """Evaluate an expression in the current context."""
    result = await session.evaluate(
        expression=request.expression,
        frame_id=request.frame_id,
        context=request.context,
    )
    return EvaluateResponse(
        result=result.get("result", ""),
        type=result.get("type"),
        variables_reference=result.get("variablesReference", 0),
    )
