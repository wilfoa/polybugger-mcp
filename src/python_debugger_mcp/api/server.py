"""Server endpoints - health and info."""

import sys

from fastapi import APIRouter

from python_debugger_mcp import __version__
from python_debugger_mcp.api.deps import SessionManagerDep
from python_debugger_mcp.config import settings
from python_debugger_mcp.models.responses import HealthResponse, InfoResponse

router = APIRouter(tags=["Server"])


@router.get("/health", response_model=HealthResponse)
async def health_check(session_manager: SessionManagerDep) -> HealthResponse:
    """Check server health status."""
    return HealthResponse(
        status="healthy",
        version=__version__,
        active_sessions=session_manager.active_count,
    )


@router.get("/info", response_model=InfoResponse)
async def server_info(session_manager: SessionManagerDep) -> InfoResponse:
    """Get server information."""
    # Try to get debugpy version
    debugpy_version = None
    try:
        import debugpy

        debugpy_version = getattr(debugpy, "__version__", None)
    except ImportError:
        pass

    return InfoResponse(
        name="OpenCode Debug Relay",
        version=__version__,
        python_version=sys.version.split()[0],
        debugpy_version=debugpy_version,
        max_sessions=settings.max_sessions,
        active_sessions=session_manager.active_count,
    )
