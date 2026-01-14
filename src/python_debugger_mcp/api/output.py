"""Output and events endpoints."""

from fastapi import APIRouter, Query

from python_debugger_mcp.api.deps import SessionDep
from python_debugger_mcp.models.responses import (
    EventResponse,
    EventsResponse,
    OutputLineResponse,
    OutputResponse,
)

router = APIRouter(prefix="/sessions/{session_id}", tags=["Output"])


@router.get("/output", response_model=OutputResponse)
async def get_output(
    session: SessionDep,
    offset: int = Query(0, ge=0, description="Starting offset"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum lines"),
    category: str | None = Query(None, description="Filter by category"),
    since: int | None = Query(None, ge=0, description="Get lines after this line number"),
) -> OutputResponse:
    """Get captured output from the debug target."""
    if since is not None:
        page = session.output_buffer.get_since(since, limit)
    else:
        page = session.output_buffer.get_page(offset, limit, category)

    return OutputResponse(
        lines=[
            OutputLineResponse(
                line_number=line.line_number,
                category=line.category,
                content=line.content,
                timestamp=line.timestamp,
            )
            for line in page.lines
        ],
        offset=page.offset,
        limit=page.limit,
        total=page.total,
        has_more=page.has_more,
        truncated=page.truncated,
    )


@router.get("/events", response_model=EventsResponse)
async def get_events(
    session: SessionDep,
    timeout: float | None = Query(
        None,
        ge=0,
        le=60,
        description="Long-poll timeout in seconds",
    ),
) -> EventsResponse:
    """Poll for debug events.

    If timeout is specified and no events are pending, waits up to
    timeout seconds for at least one event (long-polling).
    """
    events = await session.event_queue.get_all(timeout=timeout)

    return EventsResponse(
        events=[
            EventResponse(
                type=event.type.value,
                timestamp=event.timestamp,
                data=event.data,
            )
            for event in events
        ]
    )
