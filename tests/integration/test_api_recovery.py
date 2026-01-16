"""Integration tests for the recovery API."""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from polybugger_mcp.core.session import SessionManager
from polybugger_mcp.main import create_app
from polybugger_mcp.persistence.breakpoints import BreakpointStore
from polybugger_mcp.persistence.sessions import SessionStore


@pytest.fixture
def recovery_breakpoint_store(tmp_path: Path) -> BreakpointStore:
    """Create a breakpoint store for testing."""
    bp_dir = tmp_path / "breakpoints"
    bp_dir.mkdir(parents=True, exist_ok=True)
    return BreakpointStore(base_dir=bp_dir)


@pytest.fixture
def recovery_session_store(tmp_path: Path) -> SessionStore:
    """Create a session store for testing (isolated from global)."""
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return SessionStore(base_dir=sessions_dir)


@pytest_asyncio.fixture
async def recovery_session_manager(
    recovery_breakpoint_store: BreakpointStore,
    recovery_session_store: SessionStore,
) -> AsyncGenerator[SessionManager, None]:
    """Create an isolated session manager for testing."""
    manager = SessionManager(
        breakpoint_store=recovery_breakpoint_store,
        session_store=recovery_session_store,
    )
    await manager.start()
    yield manager
    await manager.stop()


@pytest_asyncio.fixture
async def recovery_client(
    recovery_session_manager: SessionManager,
) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with isolated session manager."""
    app = create_app()
    app.state.session_manager = recovery_session_manager

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


class TestRecoveryAPI:
    """Tests for recovery endpoints."""

    @pytest.mark.asyncio
    async def test_list_recoverable_empty(self, recovery_client: AsyncClient):
        """Test listing recoverable sessions when empty."""
        response = await recovery_client.get("/api/v1/recovery/sessions")

        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_recover_nonexistent_session(self, recovery_client: AsyncClient):
        """Test recovering a non-existent session."""
        response = await recovery_client.post("/api/v1/recovery/sessions/nonexistent/recover")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_recoverable_nonexistent(self, recovery_client: AsyncClient):
        """Test deleting a non-existent recoverable session."""
        response = await recovery_client.delete("/api/v1/recovery/sessions/nonexistent")

        assert response.status_code == 404
