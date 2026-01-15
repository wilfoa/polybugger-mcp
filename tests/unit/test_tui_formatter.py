"""Tests for TUI formatter."""

import pytest

from pybugger_mcp.utils.tui_formatter import (
    TUIConfig,
    TUIFormatter,
    format_call_chain,
    format_scopes,
    format_stack_trace,
    format_variables,
    get_formatter,
)


class TestTUIConfig:
    """Tests for TUIConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = TUIConfig()

        assert config.max_width == 80
        assert config.value_max_len == 40
        assert config.name_max_len == 25
        assert config.type_max_len == 15
        assert config.file_max_len == 30
        assert config.show_frame_ids is False
        assert config.ascii_mode is True
        assert config.max_variables == 15
        assert config.max_frames == 10
        assert config.max_source_lines == 5

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = TUIConfig(max_width=100, value_max_len=30)

        assert config.max_width == 100
        assert config.value_max_len == 30

    def test_ascii_box_characters(self) -> None:
        """Test ASCII box drawing characters (default)."""
        config = TUIConfig()

        assert config.BOX_TL == "+"
        assert config.BOX_TR == "+"
        assert config.BOX_BL == "+"
        assert config.BOX_BR == "+"
        assert config.BOX_H == "-"
        assert config.BOX_V == "|"

    def test_unicode_box_characters(self) -> None:
        """Test Unicode box drawing characters when ascii_mode=False."""
        config = TUIConfig(ascii_mode=False)

        assert config.BOX_TL == "┌"
        assert config.BOX_TR == "┐"
        assert config.BOX_BL == "└"
        assert config.BOX_BR == "┘"
        assert config.BOX_H == "─"
        assert config.BOX_V == "│"


class TestTUIFormatter:
    """Tests for TUIFormatter class."""

    @pytest.fixture
    def formatter(self) -> TUIFormatter:
        """Create formatter with default config."""
        return TUIFormatter()

    @pytest.fixture
    def sample_frames(self) -> list[dict]:
        """Create sample stack frames."""
        return [
            {
                "id": 1,
                "name": "calculate_total",
                "file": "/path/to/billing.py",
                "line": 45,
                "column": 4,
            },
            {
                "id": 2,
                "name": "process_order",
                "file": "/path/to/orders.py",
                "line": 123,
                "column": 8,
            },
            {
                "id": 3,
                "name": "main",
                "file": "/path/to/app.py",
                "line": 50,
                "column": 0,
            },
        ]

    @pytest.fixture
    def sample_variables(self) -> list[dict]:
        """Create sample variables."""
        return [
            {
                "name": "items",
                "value": "[100, 200, 300]",
                "type": "list",
                "variables_reference": 1001,
            },
            {
                "name": "total",
                "value": "600",
                "type": "int",
                "variables_reference": 0,
            },
            {
                "name": "tax_rate",
                "value": "0.08",
                "type": "float",
                "variables_reference": 0,
            },
        ]

    @pytest.fixture
    def sample_scopes(self) -> list[dict]:
        """Create sample scopes."""
        return [
            {
                "name": "Locals",
                "variables_reference": 1001,
                "expensive": False,
            },
            {
                "name": "Globals",
                "variables_reference": 1002,
                "expensive": True,
            },
        ]

    # =========================================================================
    # Stack Trace Tests
    # =========================================================================

    def test_format_stack_trace_basic(
        self,
        formatter: TUIFormatter,
        sample_frames: list[dict],
    ) -> None:
        """Test basic stack trace formatting."""
        output = formatter.format_stack_trace(sample_frames)

        # Check it contains expected elements
        assert "STACK TRACE" in output
        assert "3 frames" in output
        assert "calculate_total" in output
        assert "process_order" in output
        assert "main" in output
        assert "billing.py:45" in output

    def test_format_stack_trace_empty(self, formatter: TUIFormatter) -> None:
        """Test formatting empty stack trace."""
        output = formatter.format_stack_trace([])

        assert "STACK TRACE" in output
        assert "No frames available" in output

    def test_format_stack_trace_custom_title(
        self,
        formatter: TUIFormatter,
        sample_frames: list[dict],
    ) -> None:
        """Test custom title for stack trace."""
        output = formatter.format_stack_trace(sample_frames, title="CALL STACK")

        assert "CALL STACK" in output
        assert "STACK TRACE" not in output

    def test_format_stack_trace_single_frame(self, formatter: TUIFormatter) -> None:
        """Test formatting single frame."""
        frames = [{"id": 1, "name": "main", "file": "/app.py", "line": 10, "column": 0}]
        output = formatter.format_stack_trace(frames)

        assert "1 frame" in output  # Singular
        assert "main" in output

    def test_format_stack_trace_has_borders(
        self,
        formatter: TUIFormatter,
        sample_frames: list[dict],
    ) -> None:
        """Test that output has proper box borders (ASCII by default)."""
        output = formatter.format_stack_trace(sample_frames)
        lines = output.split("\n")

        # First line should start with top-left corner (ASCII +)
        assert lines[0].startswith("+")
        assert lines[0].endswith("+")

        # Last line should start with bottom-left corner (ASCII +)
        assert lines[-1].startswith("+")
        assert lines[-1].endswith("+")

    def test_format_stack_trace_no_file(self, formatter: TUIFormatter) -> None:
        """Test formatting frame with no file."""
        frames = [{"id": 1, "name": "eval", "file": None, "line": 0, "column": 0}]
        output = formatter.format_stack_trace(frames)

        assert "eval" in output
        assert "<unknown>" in output

    # =========================================================================
    # Variables Tests
    # =========================================================================

    def test_format_variables_basic(
        self,
        formatter: TUIFormatter,
        sample_variables: list[dict],
    ) -> None:
        """Test basic variable formatting."""
        output = formatter.format_variables(sample_variables)

        assert "VARIABLES" in output
        assert "Name" in output
        assert "Type" in output
        assert "Value" in output
        assert "items" in output
        assert "list" in output
        assert "[100, 200, 300]" in output

    def test_format_variables_empty(self, formatter: TUIFormatter) -> None:
        """Test formatting empty variables."""
        output = formatter.format_variables([])

        assert "VARIABLES" in output
        assert "No variables available" in output

    def test_format_variables_custom_title(
        self,
        formatter: TUIFormatter,
        sample_variables: list[dict],
    ) -> None:
        """Test custom title for variables."""
        output = formatter.format_variables(sample_variables, title="LOCAL VARS")

        assert "LOCAL VARS" in output
        assert "VARIABLES" not in output

    def test_format_variables_expandable_indicator(
        self,
        formatter: TUIFormatter,
    ) -> None:
        """Test expandable variable indicator (ASCII >)."""
        variables = [
            {
                "name": "data",
                "value": "{'key': ...}",
                "type": "dict",
                "variables_reference": 1001,
                "has_children": True,
            },
        ]
        output = formatter.format_variables(variables)

        # Should have expand indicator (ASCII >)
        assert ">" in output

    def test_format_variables_long_value_truncated(
        self,
        formatter: TUIFormatter,
    ) -> None:
        """Test that long values are truncated."""
        variables = [
            {
                "name": "long_list",
                "value": "[" + ", ".join(str(i) for i in range(100)) + "]",
                "type": "list",
                "variables_reference": 0,
            },
        ]
        output = formatter.format_variables(variables)

        # Should contain truncation indicator
        assert "..." in output

    def test_format_variables_missing_type(self, formatter: TUIFormatter) -> None:
        """Test variable with missing type."""
        variables = [
            {
                "name": "unknown",
                "value": "something",
                "type": None,
                "variables_reference": 0,
            },
        ]
        output = formatter.format_variables(variables)

        # Should not crash, should display variable
        assert "unknown" in output
        assert "something" in output

    # =========================================================================
    # Scopes Tests
    # =========================================================================

    def test_format_scopes_basic(
        self,
        formatter: TUIFormatter,
        sample_scopes: list[dict],
    ) -> None:
        """Test basic scope formatting."""
        output = formatter.format_scopes(sample_scopes)

        assert "SCOPES" in output
        assert "Scope" in output
        assert "Reference" in output
        assert "Expensive" in output
        assert "Locals" in output
        assert "Globals" in output
        assert "Yes" in output  # Expensive: True
        assert "No" in output  # Expensive: False

    def test_format_scopes_empty(self, formatter: TUIFormatter) -> None:
        """Test formatting empty scopes."""
        output = formatter.format_scopes([])

        assert "SCOPES" in output
        assert "No scopes available" in output

    def test_format_scopes_custom_title(
        self,
        formatter: TUIFormatter,
        sample_scopes: list[dict],
    ) -> None:
        """Test custom title for scopes."""
        output = formatter.format_scopes(sample_scopes, title="FRAME SCOPES")

        assert "FRAME SCOPES" in output

    # =========================================================================
    # Call Chain Tests
    # =========================================================================

    def test_format_call_chain_basic(
        self,
        formatter: TUIFormatter,
        sample_frames: list[dict],
    ) -> None:
        """Test basic call chain formatting."""
        output = formatter.format_call_chain(sample_frames)

        assert "Call Chain:" in output
        assert "main" in output
        assert "process_order" in output
        assert "calculate_total" in output
        assert "YOU ARE HERE" in output
        assert "└─▶" in output

    def test_format_call_chain_empty(self, formatter: TUIFormatter) -> None:
        """Test formatting empty call chain."""
        output = formatter.format_call_chain([])

        assert "Call Chain:" in output
        assert "(no frames)" in output

    def test_format_call_chain_single_frame(self, formatter: TUIFormatter) -> None:
        """Test call chain with single frame."""
        frames = [{"id": 1, "name": "main", "file": "/app.py", "line": 10, "column": 0}]
        output = formatter.format_call_chain(frames)

        assert "main" in output
        assert "YOU ARE HERE" in output
        # Single frame should not have arrow prefix (it's the entry point)
        lines = output.split("\n")
        main_line = [line for line in lines if "main" in line][0]
        assert not main_line.strip().startswith("└─▶")

    def test_format_call_chain_shows_reversed_order(
        self,
        formatter: TUIFormatter,
        sample_frames: list[dict],
    ) -> None:
        """Test that call chain shows entry point first."""
        output = formatter.format_call_chain(sample_frames)
        lines = output.split("\n")

        # Find lines with function names
        func_lines = [
            line
            for line in lines
            if any(f in line for f in ["main", "process_order", "calculate_total"])
        ]

        # main should appear before process_order which should appear before calculate_total
        main_idx = next(i for i, line in enumerate(func_lines) if "main" in line)
        process_idx = next(i for i, line in enumerate(func_lines) if "process_order" in line)
        calc_idx = next(i for i, line in enumerate(func_lines) if "calculate_total" in line)

        assert main_idx < process_idx < calc_idx

    # =========================================================================
    # Custom Config Tests
    # =========================================================================

    def test_custom_max_width(self, sample_frames: list[dict]) -> None:
        """Test formatter with custom max width."""
        config = TUIConfig(max_width=60)
        formatter = TUIFormatter(config)
        output = formatter.format_stack_trace(sample_frames)

        lines = output.split("\n")
        # All lines should be <= max_width
        for line in lines:
            assert len(line) <= 60

    def test_truncation_with_narrow_width(self) -> None:
        """Test that content is truncated with narrow width."""
        config = TUIConfig(max_width=40, name_max_len=10)
        formatter = TUIFormatter(config)

        variables = [
            {
                "name": "very_long_variable_name",
                "value": "a" * 100,
                "type": "str",
                "variables_reference": 0,
            },
        ]
        output = formatter.format_variables(variables)

        # Should contain truncation
        assert "..." in output


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_formatter_returns_instance(self) -> None:
        """Test get_formatter returns a TUIFormatter."""
        formatter = get_formatter()
        assert isinstance(formatter, TUIFormatter)

    def test_get_formatter_caches_default(self) -> None:
        """Test get_formatter returns same instance for default config."""
        formatter1 = get_formatter()
        formatter2 = get_formatter()
        assert formatter1 is formatter2

    def test_get_formatter_with_config_returns_new(self) -> None:
        """Test get_formatter with config returns new instance."""
        config = TUIConfig(max_width=80)
        formatter1 = get_formatter()
        formatter2 = get_formatter(config)
        assert formatter1 is not formatter2

    def test_format_stack_trace_function(self) -> None:
        """Test convenience function format_stack_trace."""
        frames = [{"id": 1, "name": "main", "file": "/app.py", "line": 10, "column": 0}]
        output = format_stack_trace(frames)

        assert "STACK TRACE" in output
        assert "main" in output

    def test_format_variables_function(self) -> None:
        """Test convenience function format_variables."""
        variables = [{"name": "x", "value": "10", "type": "int", "variables_reference": 0}]
        output = format_variables(variables)

        assert "VARIABLES" in output
        assert "x" in output

    def test_format_scopes_function(self) -> None:
        """Test convenience function format_scopes."""
        scopes = [{"name": "Locals", "variables_reference": 1001, "expensive": False}]
        output = format_scopes(scopes)

        assert "SCOPES" in output
        assert "Locals" in output

    def test_format_call_chain_function(self) -> None:
        """Test convenience function format_call_chain."""
        frames = [{"id": 1, "name": "main", "file": "/app.py", "line": 10, "column": 0}]
        output = format_call_chain(frames)

        assert "Call Chain:" in output
        assert "main" in output


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def formatter(self) -> TUIFormatter:
        """Create formatter with default config."""
        return TUIFormatter()

    def test_frame_with_empty_name(self, formatter: TUIFormatter) -> None:
        """Test frame with empty function name."""
        frames = [{"id": 1, "name": "", "file": "/app.py", "line": 10, "column": 0}]
        output = formatter.format_stack_trace(frames)

        # Should not crash
        assert "STACK TRACE" in output

    def test_variable_with_empty_name(self, formatter: TUIFormatter) -> None:
        """Test variable with empty name."""
        variables = [{"name": "", "value": "10", "type": "int", "variables_reference": 0}]
        output = formatter.format_variables(variables)

        # Should not crash
        assert "VARIABLES" in output

    def test_scope_with_missing_expensive(self, formatter: TUIFormatter) -> None:
        """Test scope with missing expensive field."""
        scopes = [{"name": "Locals", "variables_reference": 1001}]
        output = formatter.format_scopes(scopes)

        # Should default to False (No)
        assert "No" in output

    def test_windows_path_handling(self, formatter: TUIFormatter) -> None:
        """Test Windows-style path handling."""
        frames = [
            {
                "id": 1,
                "name": "main",
                "file": "C:\\Users\\test\\project\\app.py",
                "line": 10,
                "column": 0,
            }
        ]
        output = formatter.format_stack_trace(frames)

        # Should extract just the filename
        assert "app.py" in output

    def test_unicode_in_values(self, formatter: TUIFormatter) -> None:
        """Test unicode characters in values."""
        variables = [
            {
                "name": "message",
                "value": "Hello, 世界! 🌍",
                "type": "str",
                "variables_reference": 0,
            }
        ]
        output = formatter.format_variables(variables)

        # Should handle unicode
        assert "世界" in output
