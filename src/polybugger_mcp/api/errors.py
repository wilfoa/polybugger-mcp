"""Error handlers for API."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from polybugger_mcp.core.exceptions import (
    BreakpointNotFoundError,
    DAPConnectionError,
    DAPTimeoutError,
    DebugRelayError,
    FrameNotFoundError,
    InvalidSessionStateError,
    LaunchError,
    SessionExpiredError,
    SessionLimitError,
    SessionNotFoundError,
    ThreadNotFoundError,
    VariableNotFoundError,
)

logger = logging.getLogger(__name__)

# Map exceptions to HTTP status codes
EXCEPTION_STATUS_MAP = {
    SessionNotFoundError: 404,
    SessionExpiredError: 410,
    SessionLimitError: 429,
    InvalidSessionStateError: 409,
    BreakpointNotFoundError: 404,
    ThreadNotFoundError: 404,
    FrameNotFoundError: 404,
    VariableNotFoundError: 404,
    DAPTimeoutError: 504,
    DAPConnectionError: 502,
    LaunchError: 500,
}


def make_error_response(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    status_code: int = 500,
) -> JSONResponse:
    """Create a standard error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            },
            "meta": {
                "request_id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        },
    )


async def debug_relay_error_handler(
    request: Request,
    exc: DebugRelayError,
) -> JSONResponse:
    """Handle DebugRelayError exceptions."""
    status_code = EXCEPTION_STATUS_MAP.get(type(exc), 500)
    logger.warning(f"DebugRelayError: {exc.code} - {exc.message}")
    return make_error_response(
        code=exc.code,
        message=exc.message,
        details=exc.details,
        status_code=status_code,
    )


async def validation_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle validation errors."""
    logger.warning(f"ValidationError: {exc}")
    return make_error_response(
        code="INVALID_REQUEST",
        message=str(exc),
        status_code=400,
    )


async def generic_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unexpected errors."""
    logger.exception(f"Unexpected error: {exc}")
    return make_error_response(
        code="INTERNAL_ERROR",
        message="An unexpected error occurred",
        details={"error": str(exc)},
        status_code=500,
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register all error handlers with the app."""
    app.add_exception_handler(DebugRelayError, debug_relay_error_handler)  # type: ignore
    app.add_exception_handler(ValueError, validation_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)
