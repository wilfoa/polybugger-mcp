"""Integration tests for the watches API."""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from python_debugger_mcp.core.session import SessionManager
from python_debugger_mcp.main import create_app
from python_debugger_mcp.persistence.breakpoints import BreakpointStore
from python_debugger_mcp.persistence.sessions import SessionStore


@pytest.fixture
def watches_breakpoint_store(tmp_path: Path) -> BreakpointStore:
    """Create a breakpoint store for testing."""
    bp_dir = tmp_path / "breakpoints"
    bp_dir.mkdir(parents=True, exist_ok=True)
    return BreakpointStore(base_dir=bp_dir)


@pytest.fixture
def watches_session_store(tmp_path: Path) -> SessionStore:
    """Create a session store for testing (isolated from global)."""
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return SessionStore(base_dir=sessions_dir)


@pytest_asyncio.fixture
async def watches_session_manager(
    watches_breakpoint_store: BreakpointStore,
    watches_session_store: SessionStore,
) -> AsyncGenerator[SessionManager, None]:
    """Create an isolated session manager for testing."""
    manager = SessionManager(
        breakpoint_store=watches_breakpoint_store,
        session_store=watches_session_store,
    )
    await manager.start()
    yield manager
    await manager.stop()


@pytest_asyncio.fixture
async def watches_client(
    watches_session_manager: SessionManager,
) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with isolated session manager."""
    app = create_app()
    app.state.session_manager = watches_session_manager

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest_asyncio.fixture
async def watches_session_id(watches_client: AsyncClient, tmp_path: Path) -> str:
    """Create a session and return its ID."""
    response = await watches_client.post(
        "/api/v1/sessions",
        json={"project_root": str(tmp_path)},
    )
    assert response.status_code == 201, f"Failed to create session: {response.json()}"
    return response.json()["id"]


class TestWatchesAPI:
    """Tests for watch expression endpoints."""

    @pytest.mark.asyncio
    async def test_add_watch(self, watches_client: AsyncClient, watches_session_id: str):
        """Test adding a watch expression."""
        response = await watches_client.post(
            f"/api/v1/sessions/{watches_session_id}/watches",
            json={"expression": "x + y"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "x + y" in data["expressions"]

    @pytest.mark.asyncio
    async def test_add_multiple_watches(self, watches_client: AsyncClient, watches_session_id: str):
        """Test adding multiple watch expressions."""
        await watches_client.post(
            f"/api/v1/sessions/{watches_session_id}/watches",
            json={"expression": "a"},
        )
        await watches_client.post(
            f"/api/v1/sessions/{watches_session_id}/watches",
            json={"expression": "b"},
        )

        response = await watches_client.get(f"/api/v1/sessions/{watches_session_id}/watches")

        assert response.status_code == 200
        data = response.json()
        assert len(data["expressions"]) == 2
        assert "a" in data["expressions"]
        assert "b" in data["expressions"]

    @pytest.mark.asyncio
    async def test_remove_watch(self, watches_client: AsyncClient, watches_session_id: str):
        """Test removing a watch expression."""
        await watches_client.post(
            f"/api/v1/sessions/{watches_session_id}/watches",
            json={"expression": "x"},
        )

        response = await watches_client.request(
            "DELETE",
            f"/api/v1/sessions/{watches_session_id}/watches",
            json={"expression": "x"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "x" not in data["expressions"]

    @pytest.mark.asyncio
    async def test_list_watches_empty(self, watches_client: AsyncClient, watches_session_id: str):
        """Test listing watches when empty."""
        response = await watches_client.get(f"/api/v1/sessions/{watches_session_id}/watches")

        assert response.status_code == 200
        data = response.json()
        assert data["expressions"] == []

    @pytest.mark.asyncio
    async def test_add_watch_nonexistent_session(self, watches_client: AsyncClient):
        """Test adding watch to non-existent session."""
        response = await watches_client.post(
            "/api/v1/sessions/nonexistent/watches",
            json={"expression": "x"},
        )

        assert response.status_code == 404
