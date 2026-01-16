"""Tests for MCP server tools."""

from polybugger_mcp.mcp_server import mcp


class TestMCPServerRegistration:
    """Tests for MCP tool registration."""

    def test_tools_registered(self):
        """Test that all expected tools are registered."""
        tools = list(mcp._tool_manager._tools.keys())

        # Session tools
        assert "debug_create_session" in tools
        assert "debug_list_languages" in tools  # Multi-language support
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
        assert "debug_step" in tools  # Merged: over/into/out
        assert "debug_pause" in tools

        # Inspection tools
        assert "debug_get_stacktrace" in tools
        assert "debug_get_scopes" in tools
        assert "debug_get_variables" in tools
        assert "debug_evaluate" in tools
        assert "debug_inspect_variable" in tools
        assert "debug_get_call_chain" in tools

        # Watch tools
        assert "debug_watch" in tools  # Merged: add/remove/list
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
        # 24 tools: session (5), breakpoint (3), execution (4), inspection (6), watch (2), event/output (2), recovery (2)
        assert len(tools) == 24

    def test_server_name(self):
        """Test server name is set."""
        assert mcp.name == "polybugger"

    def test_server_has_instructions(self):
        """Test server has instructions."""
        assert mcp.instructions is not None
        assert "debug" in mcp.instructions.lower()
