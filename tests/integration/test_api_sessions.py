"""Integration tests for session API endpoints."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from polybugger_mcp.core.session import SessionManager
from polybugger_mcp.main import create_app


@pytest_asyncio.fixture
async def test_client(tmp_path):
    """Create test client with properly initialized app."""
    app = create_app()

    # Initialize session manager manually for testing
    from polybugger_mcp.persistence.breakpoints import BreakpointStore

    breakpoint_store = BreakpointStore(base_dir=tmp_path / "breakpoints")
    session_manager = SessionManager(breakpoint_store=breakpoint_store)
    await session_manager.start()
    app.state.session_manager = session_manager

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    await session_manager.stop()


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_ok(self, test_client: AsyncClient) -> None:
        """Test health endpoint returns healthy status."""
        response = await test_client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data  # Version is dynamic, just check it exists
        assert "active_sessions" in data


class TestInfoEndpoint:
    """Tests for /info endpoint."""

    @pytest.mark.asyncio
    async def test_info_returns_server_info(self, test_client: AsyncClient) -> None:
        """Test info endpoint returns server information."""
        response = await test_client.get("/api/v1/info")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "OpenCode Debug Relay"
        assert "python_version" in data
        assert "max_sessions" in data


class TestSessionsEndpoint:
    """Tests for /sessions endpoints."""

    @pytest.mark.asyncio
    async def test_create_session(self, test_client: AsyncClient, tmp_path) -> None:
        """Test creating a new session."""
        response = await test_client.post(
            "/api/v1/sessions",
            json={"project_root": str(tmp_path)},
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["id"].startswith("sess_")
        assert data["state"] == "created"
        assert data["project_root"] == str(tmp_path)

    @pytest.mark.asyncio
    async def test_create_session_with_name(self, test_client: AsyncClient, tmp_path) -> None:
        """Test creating a session with custom name."""
        response = await test_client.post(
            "/api/v1/sessions",
            json={"project_root": str(tmp_path), "name": "my-debug-session"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "my-debug-session"

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, test_client: AsyncClient) -> None:
        """Test listing sessions when none exist."""
        response = await test_client.get("/api/v1/sessions")

        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_sessions_with_sessions(self, test_client: AsyncClient, tmp_path) -> None:
        """Test listing sessions after creating some."""
        # Create two sessions
        await test_client.post(
            "/api/v1/sessions",
            json={"project_root": str(tmp_path)},
        )
        await test_client.post(
            "/api/v1/sessions",
            json={"project_root": str(tmp_path)},
        )

        response = await test_client.get("/api/v1/sessions")

        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 2
        assert data["total"] == 2

    @pytest.mark.asyncio
    async def test_get_session(self, test_client: AsyncClient, tmp_path) -> None:
        """Test getting a specific session."""
        # Create session
        create_response = await test_client.post(
            "/api/v1/sessions",
            json={"project_root": str(tmp_path)},
        )
        session_id = create_response.json()["id"]

        # Get session
        response = await test_client.get(f"/api/v1/sessions/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert data["state"] == "created"

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, test_client: AsyncClient) -> None:
        """Test getting a session that doesn't exist."""
        response = await test_client.get("/api/v1/sessions/sess_notfound")

        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "SESSION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_delete_session(self, test_client: AsyncClient, tmp_path) -> None:
        """Test deleting a session."""
        # Create session
        create_response = await test_client.post(
            "/api/v1/sessions",
            json={"project_root": str(tmp_path)},
        )
        session_id = create_response.json()["id"]

        # Delete session
        response = await test_client.delete(f"/api/v1/sessions/{session_id}")

        assert response.status_code == 204

        # Verify it's gone
        get_response = await test_client.get(f"/api/v1/sessions/{session_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self, test_client: AsyncClient) -> None:
        """Test deleting a session that doesn't exist."""
        response = await test_client.delete("/api/v1/sessions/sess_notfound")

        assert response.status_code == 404


class TestBreakpointsEndpoint:
    """Tests for /breakpoints endpoints."""

    @pytest.mark.asyncio
    async def test_set_breakpoints(self, test_client: AsyncClient, tmp_path) -> None:
        """Test setting breakpoints."""
        # Create session
        create_response = await test_client.post(
            "/api/v1/sessions",
            json={"project_root": str(tmp_path)},
        )
        session_id = create_response.json()["id"]

        # Set breakpoints
        response = await test_client.post(
            f"/api/v1/sessions/{session_id}/breakpoints",
            json={
                "source": "/path/to/file.py",
                "breakpoints": [
                    {"line": 10},
                    {"line": 20, "condition": "x > 5"},
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["breakpoints"]) == 2
        # Before launch, breakpoints are unverified
        assert data["breakpoints"][0]["line"] == 10
        assert data["breakpoints"][1]["line"] == 20

    @pytest.mark.asyncio
    async def test_list_breakpoints(self, test_client: AsyncClient, tmp_path) -> None:
        """Test listing breakpoints."""
        # Create session
        create_response = await test_client.post(
            "/api/v1/sessions",
            json={"project_root": str(tmp_path)},
        )
        session_id = create_response.json()["id"]

        # Set breakpoints
        await test_client.post(
            f"/api/v1/sessions/{session_id}/breakpoints",
            json={
                "source": "/path/to/file.py",
                "breakpoints": [{"line": 10}],
            },
        )

        # List breakpoints
        response = await test_client.get(f"/api/v1/sessions/{session_id}/breakpoints")

        assert response.status_code == 200
        data = response.json()
        assert "/path/to/file.py" in data["files"]
        assert len(data["files"]["/path/to/file.py"]) == 1

    @pytest.mark.asyncio
    async def test_clear_breakpoints(self, test_client: AsyncClient, tmp_path) -> None:
        """Test clearing all breakpoints."""
        # Create session
        create_response = await test_client.post(
            "/api/v1/sessions",
            json={"project_root": str(tmp_path)},
        )
        session_id = create_response.json()["id"]

        # Set breakpoints
        await test_client.post(
            f"/api/v1/sessions/{session_id}/breakpoints",
            json={
                "source": "/path/to/file.py",
                "breakpoints": [{"line": 10}],
            },
        )

        # Clear breakpoints
        response = await test_client.delete(f"/api/v1/sessions/{session_id}/breakpoints")

        assert response.status_code == 204

        # Verify cleared
        list_response = await test_client.get(f"/api/v1/sessions/{session_id}/breakpoints")
        assert list_response.json()["files"] == {}
