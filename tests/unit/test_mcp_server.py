"""Tests for MCP server tools."""

from pybugger_mcp.mcp_server import mcp


class TestMCPServerRegistration:
    """Tests for MCP tool registration."""

    def test_tools_registered(self):
        """Test that all expected tools are registered."""
        tools = list(mcp._tool_manager._tools.keys())

        # Session tools
        assert "debug_create_session" in tools
        assert "debug_list_sessions" in tools
        assert "debug_get_session" in tools
        assert "debug_terminate_session" in tools

        # Breakpoint tools
        assert "debug_set_breakpoints" in tools
        assert "debug_get_breakpoints" in tools
        assert "debug_clear_breakpoints" in tools

        # Execution tools
        assert "debug_launch" in tools
        assert "debug_continue" in tools
        assert "debug_step_over" in tools
        assert "debug_step_into" in tools
        assert "debug_step_out" in tools
        assert "debug_pause" in tools

        # Inspection tools
        assert "debug_get_stacktrace" in tools
        assert "debug_get_scopes" in tools
        assert "debug_get_variables" in tools
        assert "debug_evaluate" in tools

        # Watch tools
        assert "debug_add_watch" in tools
        assert "debug_remove_watch" in tools
        assert "debug_list_watches" in tools
        assert "debug_evaluate_watches" in tools

        # Event/output tools
        assert "debug_poll_events" in tools
        assert "debug_get_output" in tools

        # Recovery tools
        assert "debug_list_recoverable" in tools
        assert "debug_recover_session" in tools

    def test_tool_count(self):
        """Test total number of tools."""
        tools = list(mcp._tool_manager._tools.keys())
        assert len(tools) == 26  # Includes debug_inspect_variable

    def test_server_name(self):
        """Test server name is set."""
        assert mcp.name == "python-debugger"

    def test_server_has_instructions(self):
        """Test server has instructions."""
        assert mcp.instructions is not None
        assert "debug" in mcp.instructions.lower()
