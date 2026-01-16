"""Tests for MCP server tool functions."""

import pytest

import polybugger_mcp.mcp_server as mcp_server
from polybugger_mcp.core.session import SessionManager
from polybugger_mcp.mcp_server import (
    _get_manager,
    debug_clear_breakpoints,
    debug_continue,
    debug_create_session,
    debug_evaluate,
    debug_evaluate_watches,
    debug_get_breakpoints,
    debug_get_output,
    debug_get_scopes,
    debug_get_session,
    debug_get_stacktrace,
    debug_get_variables,
    debug_launch,
    debug_list_recoverable,
    debug_list_sessions,
    debug_pause,
    debug_poll_events,
    debug_recover_session,
    debug_set_breakpoints,
    debug_step,
    debug_terminate_session,
    debug_watch,
)


@pytest.fixture
async def session_manager(tmp_path):
    """Create and start a session manager for testing."""
    from polybugger_mcp.persistence.breakpoints import BreakpointStore

    breakpoint_store = BreakpointStore(base_dir=tmp_path / "breakpoints")
    manager = SessionManager(breakpoint_store=breakpoint_store)
    await manager.start()

    # Set global session manager
    mcp_server._session_manager = manager

    yield manager

    await manager.stop()
    mcp_server._session_manager = None


class TestGetManager:
    """Tests for _get_manager helper."""

    def test_get_manager_not_initialized(self):
        """Test that _get_manager raises when not initialized."""
        old_manager = mcp_server._session_manager
        mcp_server._session_manager = None
        try:
            with pytest.raises(RuntimeError, match="not initialized"):
                _get_manager()
        finally:
            mcp_server._session_manager = old_manager

    @pytest.mark.asyncio
    async def test_get_manager_initialized(self, session_manager):
        """Test that _get_manager returns manager when initialized."""
        manager = _get_manager()
        assert manager is session_manager


class TestSessionTools:
    """Tests for session management tools."""

    @pytest.mark.asyncio
    async def test_create_session(self, session_manager, tmp_path):
        """Test debug_create_session tool."""
        result = await debug_create_session(
            project_root=str(tmp_path),
            name="test-session",
            timeout_minutes=30,
        )

        assert "session_id" in result
        assert result["name"] == "test-session"
        assert result["state"] == "created"
        assert "message" in result

    @pytest.mark.asyncio
    async def test_create_session_limit_error(self, session_manager, tmp_path):
        """Test session limit error."""
        # Create max sessions
        for i in range(10):
            await debug_create_session(
                project_root=str(tmp_path),
                name=f"session-{i}",
            )

        # Try to create one more
        result = await debug_create_session(
            project_root=str(tmp_path),
            name="overflow",
        )
        assert "error" in result
        assert result["code"] == "SESSION_LIMIT"

    @pytest.mark.asyncio
    async def test_list_sessions(self, session_manager, tmp_path):
        """Test debug_list_sessions tool."""
        # Create a session
        await debug_create_session(project_root=str(tmp_path))

        result = await debug_list_sessions()

        assert "sessions" in result
        assert result["total"] == 1
        assert len(result["sessions"]) == 1

    @pytest.mark.asyncio
    async def test_get_session(self, session_manager, tmp_path):
        """Test debug_get_session tool."""
        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        result = await debug_get_session(session_id=session_id)

        assert result["session_id"] == session_id
        assert result["state"] == "created"

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, session_manager):
        """Test debug_get_session with non-existent session."""
        result = await debug_get_session(session_id="nonexistent")

        assert "error" in result
        assert result["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_terminate_session(self, session_manager, tmp_path):
        """Test debug_terminate_session tool."""
        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        result = await debug_terminate_session(session_id=session_id)

        assert result["status"] == "terminated"
        assert result["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_terminate_session_not_found(self, session_manager):
        """Test debug_terminate_session with non-existent session."""
        result = await debug_terminate_session(session_id="nonexistent")

        assert "error" in result
        assert result["code"] == "NOT_FOUND"


class TestBreakpointTools:
    """Tests for breakpoint management tools."""

    @pytest.mark.asyncio
    async def test_set_breakpoints(self, session_manager, tmp_path):
        """Test debug_set_breakpoints tool."""
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\ny = 2\nz = 3\n")

        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        result = await debug_set_breakpoints(
            session_id=session_id,
            file_path=str(test_file),
            lines=[1, 3],
            conditions=[None, "x > 0"],
        )

        assert result["file"] == str(test_file)
        assert len(result["breakpoints"]) == 2

    @pytest.mark.asyncio
    async def test_set_breakpoints_not_found(self, session_manager, tmp_path):
        """Test debug_set_breakpoints with non-existent session."""
        result = await debug_set_breakpoints(
            session_id="nonexistent",
            file_path="/test.py",
            lines=[1],
        )

        assert "error" in result
        assert result["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_breakpoints(self, session_manager, tmp_path):
        """Test debug_get_breakpoints tool."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        await debug_set_breakpoints(
            session_id=session_id,
            file_path=str(test_file),
            lines=[1],
        )

        result = await debug_get_breakpoints(session_id=session_id)

        assert "files" in result
        assert str(test_file) in result["files"]

    @pytest.mark.asyncio
    async def test_get_breakpoints_not_found(self, session_manager):
        """Test debug_get_breakpoints with non-existent session."""
        result = await debug_get_breakpoints(session_id="nonexistent")

        assert "error" in result
        assert result["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_clear_breakpoints(self, session_manager, tmp_path):
        """Test debug_clear_breakpoints tool."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")

        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        await debug_set_breakpoints(
            session_id=session_id,
            file_path=str(test_file),
            lines=[1],
        )

        result = await debug_clear_breakpoints(
            session_id=session_id,
            file_path=str(test_file),
        )

        assert result["status"] == "cleared"

    @pytest.mark.asyncio
    async def test_clear_all_breakpoints(self, session_manager, tmp_path):
        """Test clearing all breakpoints."""
        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        result = await debug_clear_breakpoints(session_id=session_id)

        assert result["status"] == "cleared"
        assert result["files"] == "all"

    @pytest.mark.asyncio
    async def test_clear_breakpoints_not_found(self, session_manager):
        """Test debug_clear_breakpoints with non-existent session."""
        result = await debug_clear_breakpoints(session_id="nonexistent")

        assert "error" in result
        assert result["code"] == "NOT_FOUND"


class TestWatchTools:
    """Tests for watch expression tools."""

    @pytest.mark.asyncio
    async def test_watch_add(self, session_manager, tmp_path):
        """Test debug_watch add action."""
        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        result = await debug_watch(session_id=session_id, action="add", expression="x + y")

        assert "watches" in result
        assert "x + y" in result["watches"]

    @pytest.mark.asyncio
    async def test_watch_add_not_found(self, session_manager):
        """Test debug_watch add with non-existent session."""
        result = await debug_watch(session_id="nonexistent", action="add", expression="x")

        assert "error" in result
        assert result["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_watch_add_missing_expression(self, session_manager, tmp_path):
        """Test debug_watch add without expression."""
        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        result = await debug_watch(session_id=session_id, action="add")

        assert "error" in result
        assert result["code"] == "MISSING_EXPRESSION"

    @pytest.mark.asyncio
    async def test_watch_remove(self, session_manager, tmp_path):
        """Test debug_watch remove action."""
        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        await debug_watch(session_id=session_id, action="add", expression="x")

        result = await debug_watch(session_id=session_id, action="remove", expression="x")

        assert "watches" in result
        assert "x" not in result["watches"]

    @pytest.mark.asyncio
    async def test_watch_remove_not_found(self, session_manager):
        """Test debug_watch remove with non-existent session."""
        result = await debug_watch(session_id="nonexistent", action="remove", expression="x")

        assert "error" in result
        assert result["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_watch_list(self, session_manager, tmp_path):
        """Test debug_watch list action."""
        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        await debug_watch(session_id=session_id, action="add", expression="a")
        await debug_watch(session_id=session_id, action="add", expression="b")

        result = await debug_watch(session_id=session_id, action="list")

        assert "watches" in result
        assert len(result["watches"]) == 2

    @pytest.mark.asyncio
    async def test_watch_list_not_found(self, session_manager):
        """Test debug_watch list with non-existent session."""
        result = await debug_watch(session_id="nonexistent", action="list")

        assert "error" in result
        assert result["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_watch_invalid_action(self, session_manager, tmp_path):
        """Test debug_watch with invalid action."""
        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        result = await debug_watch(session_id=session_id, action="invalid")

        assert "error" in result
        assert result["code"] == "INVALID_ACTION"


class TestOutputTools:
    """Tests for output tools."""

    @pytest.mark.asyncio
    async def test_get_output(self, session_manager, tmp_path):
        """Test debug_get_output tool."""
        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        result = await debug_get_output(session_id=session_id, offset=0, limit=10)

        assert "lines" in result
        assert "total" in result
        assert "has_more" in result

    @pytest.mark.asyncio
    async def test_get_output_not_found(self, session_manager):
        """Test debug_get_output with non-existent session."""
        result = await debug_get_output(session_id="nonexistent")

        assert "error" in result
        assert result["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_poll_events(self, session_manager, tmp_path):
        """Test debug_poll_events tool."""
        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        result = await debug_poll_events(session_id=session_id, timeout_seconds=0.1)

        assert "events" in result
        assert "session_state" in result

    @pytest.mark.asyncio
    async def test_poll_events_not_found(self, session_manager):
        """Test debug_poll_events with non-existent session."""
        result = await debug_poll_events(session_id="nonexistent")

        assert "error" in result
        assert result["code"] == "NOT_FOUND"


class TestRecoveryTools:
    """Tests for recovery tools."""

    @pytest.mark.asyncio
    async def test_list_recoverable(self, session_manager):
        """Test debug_list_recoverable tool."""
        result = await debug_list_recoverable()

        assert "sessions" in result
        assert "total" in result

    @pytest.mark.asyncio
    async def test_recover_session_not_found(self, session_manager):
        """Test debug_recover_session with non-existent session."""
        result = await debug_recover_session(session_id="nonexistent")

        assert "error" in result
        assert result["code"] == "NOT_FOUND"


class TestLaunchTool:
    """Tests for launch tool."""

    @pytest.mark.asyncio
    async def test_launch_no_program_or_module(self, session_manager, tmp_path):
        """Test debug_launch without program or module."""
        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        result = await debug_launch(session_id=session_id)

        assert "error" in result
        assert "program or module" in result["error"]

    @pytest.mark.asyncio
    async def test_launch_not_found(self, session_manager):
        """Test debug_launch with non-existent session."""
        result = await debug_launch(
            session_id="nonexistent",
            program="/test.py",
        )

        assert "error" in result
        assert result["code"] == "NOT_FOUND"


class TestExecutionToolsNotFound:
    """Tests for execution tools with non-existent sessions."""

    @pytest.mark.asyncio
    async def test_continue_not_found(self, session_manager):
        """Test debug_continue with non-existent session."""
        result = await debug_continue(session_id="nonexistent")
        assert "error" in result
        assert result["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_step_over_not_found(self, session_manager):
        """Test debug_step with mode='over' and non-existent session."""
        result = await debug_step(session_id="nonexistent", mode="over")
        assert "error" in result
        assert result["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_step_into_not_found(self, session_manager):
        """Test debug_step with mode='into' and non-existent session."""
        result = await debug_step(session_id="nonexistent", mode="into")
        assert "error" in result
        assert result["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_step_out_not_found(self, session_manager):
        """Test debug_step with mode='out' and non-existent session."""
        result = await debug_step(session_id="nonexistent", mode="out")
        assert "error" in result
        assert result["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_step_invalid_mode(self, session_manager, tmp_path):
        """Test debug_step with invalid mode."""
        # Create a valid session to test mode validation
        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        result = await debug_step(session_id=session_id, mode="invalid")
        assert "error" in result
        assert "Invalid mode" in result["error"]
        assert result["code"] == "INVALID_MODE"

    @pytest.mark.asyncio
    async def test_pause_not_found(self, session_manager):
        """Test debug_pause with non-existent session."""
        result = await debug_pause(session_id="nonexistent")
        assert "error" in result
        assert result["code"] == "NOT_FOUND"


class TestInspectionToolsNotFound:
    """Tests for inspection tools with non-existent sessions."""

    @pytest.mark.asyncio
    async def test_get_stacktrace_not_found(self, session_manager):
        """Test debug_get_stacktrace with non-existent session."""
        result = await debug_get_stacktrace(session_id="nonexistent")
        assert "error" in result
        assert result["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_scopes_not_found(self, session_manager):
        """Test debug_get_scopes with non-existent session."""
        result = await debug_get_scopes(session_id="nonexistent", frame_id=0)
        assert "error" in result
        assert result["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_variables_not_found(self, session_manager):
        """Test debug_get_variables with non-existent session."""
        result = await debug_get_variables(session_id="nonexistent", variables_reference=0)
        assert "error" in result
        assert result["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_evaluate_not_found(self, session_manager):
        """Test debug_evaluate with non-existent session."""
        result = await debug_evaluate(session_id="nonexistent", expression="x")
        assert "error" in result
        assert result["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_evaluate_watches_not_found(self, session_manager):
        """Test debug_evaluate_watches with non-existent session."""
        result = await debug_evaluate_watches(session_id="nonexistent")
        assert "error" in result
        assert result["code"] == "NOT_FOUND"
