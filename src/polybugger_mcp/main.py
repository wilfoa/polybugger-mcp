"""Main application entry point."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from polybugger_mcp import __version__
from polybugger_mcp.api.errors import register_error_handlers
from polybugger_mcp.api.router import api_router
from polybugger_mcp.config import settings
from polybugger_mcp.core.session import SessionManager

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info(f"Starting OpenCode Debug Relay v{__version__}")
    logger.info(f"Max sessions: {settings.max_sessions}")
    logger.info(f"Data directory: {settings.data_dir}")

    session_manager = SessionManager()
    await session_manager.start()
    app.state.session_manager = session_manager

    yield

    # Shutdown
    logger.info("Shutting down...")
    await session_manager.stop()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="OpenCode Debug Relay",
        description="HTTP relay server for Python debugging via debugpy/DAP",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Register routers
    app.include_router(api_router)

    # Register error handlers
    register_error_handlers(app)

    return app


# Create app instance
app = create_app()


def main() -> None:
    """Run the server."""
    uvicorn.run(
        "polybugger_mcp.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
