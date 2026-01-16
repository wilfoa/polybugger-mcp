"""Main API router aggregator."""

from fastapi import APIRouter

from polybugger_mcp.api import (
    breakpoints,
    execution,
    inspection,
    output,
    recovery,
    server,
    sessions,
    watches,
)

# Create main router with API version prefix
api_router = APIRouter(prefix="/api/v1")

# Include all sub-routers
api_router.include_router(server.router)
api_router.include_router(sessions.router)
api_router.include_router(breakpoints.router)
api_router.include_router(execution.router)
api_router.include_router(inspection.router)
api_router.include_router(output.router)
api_router.include_router(watches.router)
api_router.include_router(recovery.router)
