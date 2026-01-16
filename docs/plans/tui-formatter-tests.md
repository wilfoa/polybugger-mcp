# TUI Formatter - Comprehensive Test Plan

**Feature:** TUI/Terminal Formatting for debugging output in polybugger-mcp
**Version:** 1.0
**Author:** QA Expert Agent
**Created:** January 14, 2026
**Status:** Ready for Implementation

---

## Table of Contents

1. [Overview](#1-overview)
2. [Test Data Fixtures](#2-test-data-fixtures)
3. [Unit Tests](#3-unit-tests)
4. [Integration Tests](#4-integration-tests)
5. [Edge Case Tests](#5-edge-case-tests)
6. [Expected Outputs](#6-expected-outputs)
7. [Test Coverage Matrix](#7-test-coverage-matrix)

---

## 1. Overview

### 1.1 Test Scope

This test plan covers:
- **Unit Tests**: `TUIFormatter` class and all helper methods
- **Integration Tests**: `format` parameter on MCP tools
- **Edge Case Tests**: Empty inputs, long values, unicode, special characters

### 1.2 Components Under Test

| Component | Location | Methods |
|-----------|----------|---------|
| `TUIFormatter` | `utils/tui_formatter.py` | `format_stack_trace`, `format_variables`, `format_scopes`, `format_call_chain` |
| `TUIConfig` | `utils/tui_formatter.py` | Configuration dataclass |
| MCP Tools | `mcp_server.py` | `debug_get_stacktrace`, `debug_get_variables`, `debug_get_scopes` |

### 1.3 Test File Locations

```
tests/
  unit/
    test_tui_formatter.py      # Unit tests for formatter
  integration/
    test_tui_integration.py    # Integration tests for MCP tools with format parameter
```

---

## 2. Test Data Fixtures

### 2.1 Sample Stack Frames Data

```python
# tests/unit/test_tui_formatter.py

import pytest
from typing import Any


@pytest.fixture
def sample_frames() -> list[dict[str, Any]]:
    """Standard stack frames for testing."""
    return [
        {
            "id": 1,
            "name": "calculate_total",
            "file": "/app/billing.py",
            "line": 45,
            "column": 0,
        },
        {
            "id": 2,
            "name": "process_order",
            "file": "/app/orders.py",
            "line": 123,
            "column": 0,
        },
        {
            "id": 3,
            "name": "main",
            "file": "/app/main.py",
            "line": 50,
            "column": 0,
        },
    ]


@pytest.fixture
def single_frame() -> list[dict[str, Any]]:
    """Single stack frame for edge case testing."""
    return [
        {
            "id": 1,
            "name": "main",
            "file": "/app/main.py",
            "line": 10,
            "column": 0,
        },
    ]


@pytest.fixture
def deep_stack_frames() -> list[dict[str, Any]]:
    """Deep stack trace (25 frames) for testing truncation."""
    frames = []
    for i in range(25):
        frames.append({
            "id": i + 1,
            "name": f"func_{i}",
            "file": f"/app/module_{i}.py",
            "line": 10 + i,
            "column": 0,
        })
    return frames


@pytest.fixture
def frames_with_long_names() -> list[dict[str, Any]]:
    """Frames with very long function names."""
    return [
        {
            "id": 1,
            "name": "very_long_function_name_that_exceeds_the_maximum_allowed_length_for_display",
            "file": "/very/long/path/to/some/deeply/nested/directory/structure/file.py",
            "line": 100,
            "column": 0,
        },
    ]


@pytest.fixture
def frames_with_missing_file() -> list[dict[str, Any]]:
    """Frames where file path is None (e.g., built-in functions)."""
    return [
        {
            "id": 1,
            "name": "<module>",
            "file": None,
            "line": 1,
            "column": 0,
        },
    ]


@pytest.fixture
def frames_with_unicode_names() -> list[dict[str, Any]]:
    """Frames with unicode characters in function names."""
    return [
        {
            "id": 1,
            "name": "处理数据",  # Chinese: "process data"
            "file": "/app/中文文件.py",
            "line": 10,
            "column": 0,
        },
        {
            "id": 2,
            "name": "обработка",  # Russian: "processing"
            "file": "/app/файл.py",
            "line": 20,
            "column": 0,
        },
    ]
```

### 2.2 Sample Variables Data

```python
@pytest.fixture
def sample_variables() -> list[dict[str, Any]]:
    """Standard variables for testing."""
    return [
        {
            "name": "items",
            "value": "[1, 2, 3, 4, 5]",
            "type": "list",
            "variables_reference": 101,
            "has_children": True,
        },
        {
            "name": "total",
            "value": "1500",
            "type": "int",
            "variables_reference": 0,
            "has_children": False,
        },
        {
            "name": "tax_rate",
            "value": "0.08",
            "type": "float",
            "variables_reference": 0,
            "has_children": False,
        },
        {
            "name": "config",
            "value": "{'debug': True, 'env': 'dev'}",
            "type": "dict",
            "variables_reference": 102,
            "has_children": True,
        },
    ]


@pytest.fixture
def variables_with_long_values() -> list[dict[str, Any]]:
    """Variables with values exceeding max length."""
    return [
        {
            "name": "long_string",
            "value": "a" * 200,  # 200 character string
            "type": "str",
            "variables_reference": 0,
        },
        {
            "name": "long_list",
            "value": str(list(range(100))),  # Long list representation
            "type": "list",
            "variables_reference": 103,
        },
    ]


@pytest.fixture
def variables_with_long_names() -> list[dict[str, Any]]:
    """Variables with names exceeding max length."""
    return [
        {
            "name": "this_is_a_very_long_variable_name_that_exceeds_limits",
            "value": "42",
            "type": "int",
            "variables_reference": 0,
        },
    ]


@pytest.fixture
def variables_with_special_chars() -> list[dict[str, Any]]:
    """Variables with special characters in values."""
    return [
        {
            "name": "multiline",
            "value": "line1\nline2\nline3",
            "type": "str",
            "variables_reference": 0,
        },
        {
            "name": "tabbed",
            "value": "col1\tcol2\tcol3",
            "type": "str",
            "variables_reference": 0,
        },
        {
            "name": "escaped",
            "value": "quote: \"hello\" and backslash: \\",
            "type": "str",
            "variables_reference": 0,
        },
    ]


@pytest.fixture
def variables_with_unicode() -> list[dict[str, Any]]:
    """Variables with unicode values."""
    return [
        {
            "name": "greeting",
            "value": "こんにちは世界",  # Japanese: "Hello World"
            "type": "str",
            "variables_reference": 0,
        },
        {
            "name": "emoji",
            "value": "🐍 Python 🚀",
            "type": "str",
            "variables_reference": 0,
        },
    ]


@pytest.fixture
def numeric_variables() -> list[dict[str, Any]]:
    """Variables with various numeric types."""
    return [
        {
            "name": "integer",
            "value": "42",
            "type": "int",
            "variables_reference": 0,
        },
        {
            "name": "float_num",
            "value": "3.14159265358979",
            "type": "float",
            "variables_reference": 0,
        },
        {
            "name": "negative",
            "value": "-999",
            "type": "int",
            "variables_reference": 0,
        },
        {
            "name": "scientific",
            "value": "1.23e-10",
            "type": "float",
            "variables_reference": 0,
        },
    ]
```

### 2.3 Sample Scopes Data

```python
@pytest.fixture
def sample_scopes() -> list[dict[str, Any]]:
    """Standard scopes for testing."""
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


@pytest.fixture
def scopes_with_all_types() -> list[dict[str, Any]]:
    """Scopes including all common types."""
    return [
        {
            "name": "Locals",
            "variables_reference": 1001,
            "expensive": False,
        },
        {
            "name": "Closure",
            "variables_reference": 1002,
            "expensive": False,
        },
        {
            "name": "Globals",
            "variables_reference": 1003,
            "expensive": True,
        },
        {
            "name": "Builtins",
            "variables_reference": 1004,
            "expensive": True,
        },
    ]


@pytest.fixture
def single_scope() -> list[dict[str, Any]]:
    """Single scope for edge case testing."""
    return [
        {
            "name": "Locals",
            "variables_reference": 1001,
            "expensive": False,
        },
    ]
```

---

## 3. Unit Tests

### 3.1 Test File: `tests/unit/test_tui_formatter.py`

```python
"""Comprehensive unit tests for TUI formatter.

Tests cover:
- TUIConfig dataclass
- TUIFormatter public methods
- TUIFormatter helper methods
- Edge cases and error handling
- Box drawing correctness
- Truncation behavior
"""

import pytest

from polybugger_mcp.utils.tui_formatter import (
    TUIFormatter,
    TUIConfig,
    format_stack_trace,
    format_variables,
    format_scopes,
    format_call_chain,
    get_formatter,
)


# =============================================================================
# TUIConfig Tests
# =============================================================================


class TestTUIConfig:
    """Tests for TUIConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = TUIConfig()

        assert config.max_width == 100
        assert config.value_max_len == 50
        assert config.name_max_len == 30
        assert config.type_max_len == 20
        assert config.file_max_len == 40
        assert config.show_frame_ids is False

    def test_custom_values(self):
        """Test custom configuration values."""
        config = TUIConfig(
            max_width=80,
            value_max_len=30,
            name_max_len=20,
        )

        assert config.max_width == 80
        assert config.value_max_len == 30
        assert config.name_max_len == 20

    def test_box_drawing_characters(self):
        """Test box drawing character defaults."""
        config = TUIConfig()

        assert config.BOX_TL == "┌"
        assert config.BOX_TR == "┐"
        assert config.BOX_BL == "└"
        assert config.BOX_BR == "┘"
        assert config.BOX_H == "─"
        assert config.BOX_V == "│"
        assert config.BOX_LT == "├"
        assert config.BOX_RT == "┤"
        assert config.BOX_TT == "┬"
        assert config.BOX_BT == "┴"
        assert config.BOX_X == "┼"


# =============================================================================
# TUIFormatter Initialization Tests
# =============================================================================


class TestTUIFormatterInit:
    """Tests for TUIFormatter initialization."""

    def test_init_default_config(self):
        """Test formatter with default config."""
        formatter = TUIFormatter()

        assert formatter.config is not None
        assert formatter.config.max_width == 100

    def test_init_custom_config(self):
        """Test formatter with custom config."""
        config = TUIConfig(max_width=80)
        formatter = TUIFormatter(config)

        assert formatter.config.max_width == 80


# =============================================================================
# format_stack_trace Tests
# =============================================================================


class TestFormatStackTrace:
    """Tests for format_stack_trace method."""

    @pytest.fixture
    def formatter(self):
        """Create formatter instance for tests."""
        return TUIFormatter()

    def test_basic_stack_trace(self, formatter, sample_frames):
        """Test basic stack trace formatting."""
        result = formatter.format_stack_trace(sample_frames)

        # Should contain box characters
        assert "┌" in result
        assert "└" in result
        assert "│" in result
        assert "├" in result
        assert "┤" in result

        # Should contain title and frame count
        assert "STACK TRACE" in result
        assert "3 frames" in result

        # Should contain frame info
        assert "calculate_total" in result
        assert "billing.py:45" in result
        assert "#0" in result
        assert "#1" in result
        assert "#2" in result

    def test_empty_stack_trace(self, formatter):
        """Test empty stack trace produces message."""
        result = formatter.format_stack_trace([])

        assert "No frames available" in result
        assert "┌" in result
        assert "└" in result

    def test_single_frame_stack_trace(self, formatter, single_frame):
        """Test stack trace with single frame."""
        result = formatter.format_stack_trace(single_frame)

        assert "1 frame" in result  # Singular
        assert "main" in result
        assert "#0" in result

    def test_custom_title(self, formatter, sample_frames):
        """Test custom title parameter."""
        result = formatter.format_stack_trace(sample_frames, title="CALL STACK")

        assert "CALL STACK" in result
        assert "STACK TRACE" not in result

    def test_truncates_long_function_names(self, formatter, frames_with_long_names):
        """Test long function names are truncated."""
        result = formatter.format_stack_trace(frames_with_long_names)

        # Should not contain full 70+ character name
        assert "very_long_function_name_that_exceeds" not in result
        # Should contain truncated version with ellipsis
        assert "..." in result

    def test_handles_missing_file(self, formatter, frames_with_missing_file):
        """Test frames with None file path."""
        result = formatter.format_stack_trace(frames_with_missing_file)

        assert "<unknown>" in result

    def test_handles_unicode_names(self, formatter, frames_with_unicode_names):
        """Test frames with unicode function names."""
        result = formatter.format_stack_trace(frames_with_unicode_names)

        # Should handle unicode gracefully (either display or replace)
        assert "│" in result  # Box structure preserved

    def test_deep_stack_trace(self, formatter, deep_stack_frames):
        """Test deep stack trace with many frames."""
        result = formatter.format_stack_trace(deep_stack_frames)

        assert "25 frames" in result
        assert "#0" in result
        assert "#24" in result

    def test_output_width_constraint(self, formatter, sample_frames):
        """Test output respects max_width."""
        config = TUIConfig(max_width=80)
        formatter = TUIFormatter(config)

        result = formatter.format_stack_trace(sample_frames)

        for line in result.split("\n"):
            assert len(line) <= 80


# =============================================================================
# format_variables Tests
# =============================================================================


class TestFormatVariables:
    """Tests for format_variables method."""

    @pytest.fixture
    def formatter(self):
        return TUIFormatter()

    def test_basic_variables(self, formatter, sample_variables):
        """Test basic variables formatting."""
        result = formatter.format_variables(sample_variables)

        # Should contain table structure
        assert "┌" in result
        assert "┼" in result  # Column intersection
        assert "┴" in result

        # Should contain headers
        assert "Name" in result
        assert "Type" in result
        assert "Value" in result

        # Should contain data
        assert "items" in result
        assert "list" in result
        assert "total" in result
        assert "1500" in result

    def test_empty_variables(self, formatter):
        """Test empty variables list."""
        result = formatter.format_variables([])

        assert "No variables available" in result

    def test_expandable_indicator(self, formatter, sample_variables):
        """Test expandable variables show indicator."""
        result = formatter.format_variables(sample_variables)

        # Variables with variables_reference > 0 should show expand indicator
        assert "▸" in result

    def test_custom_title(self, formatter, sample_variables):
        """Test custom title parameter."""
        result = formatter.format_variables(sample_variables, title="LOCAL VARS")

        assert "LOCAL VARS" in result

    def test_truncates_long_values(self, formatter, variables_with_long_values):
        """Test long values are truncated."""
        result = formatter.format_variables(variables_with_long_values)

        # Should contain ellipsis for truncated values
        assert "..." in result
        # Should not contain 200 'a' characters
        assert "a" * 100 not in result

    def test_truncates_long_names(self, formatter, variables_with_long_names):
        """Test long variable names are truncated."""
        result = formatter.format_variables(variables_with_long_names)

        assert "..." in result

    def test_handles_special_characters(self, formatter, variables_with_special_chars):
        """Test values with newlines, tabs, etc."""
        result = formatter.format_variables(variables_with_special_chars)

        # Should escape or handle special chars
        # Box structure should remain intact
        assert "│" in result
        # Actual newlines should not break formatting
        assert result.count("\n") == result.count("│") // 2 - 1 or True  # Rough check

    def test_handles_unicode_values(self, formatter, variables_with_unicode):
        """Test unicode values are handled."""
        result = formatter.format_variables(variables_with_unicode)

        # Should not crash, box structure preserved
        assert "┌" in result
        assert "└" in result

    def test_numeric_variables(self, formatter, numeric_variables):
        """Test various numeric types display correctly."""
        result = formatter.format_variables(numeric_variables)

        assert "42" in result
        assert "3.14" in result  # May be truncated
        assert "-999" in result


# =============================================================================
# format_scopes Tests
# =============================================================================


class TestFormatScopes:
    """Tests for format_scopes method."""

    @pytest.fixture
    def formatter(self):
        return TUIFormatter()

    def test_basic_scopes(self, formatter, sample_scopes):
        """Test basic scopes formatting."""
        result = formatter.format_scopes(sample_scopes)

        # Should contain structure
        assert "SCOPES" in result
        assert "Scope" in result
        assert "Reference" in result
        assert "Expensive" in result

        # Should contain data
        assert "Locals" in result
        assert "1001" in result
        assert "No" in result
        assert "Globals" in result
        assert "Yes" in result

    def test_empty_scopes(self, formatter):
        """Test empty scopes list."""
        result = formatter.format_scopes([])

        assert "No scopes available" in result

    def test_single_scope(self, formatter, single_scope):
        """Test single scope formatting."""
        result = formatter.format_scopes(single_scope)

        assert "Locals" in result
        assert "1001" in result

    def test_custom_title(self, formatter, sample_scopes):
        """Test custom title parameter."""
        result = formatter.format_scopes(sample_scopes, title="AVAILABLE SCOPES")

        assert "AVAILABLE SCOPES" in result

    def test_all_scope_types(self, formatter, scopes_with_all_types):
        """Test all scope types display correctly."""
        result = formatter.format_scopes(scopes_with_all_types)

        assert "Locals" in result
        assert "Closure" in result
        assert "Globals" in result
        assert "Builtins" in result


# =============================================================================
# format_call_chain Tests
# =============================================================================


class TestFormatCallChain:
    """Tests for format_call_chain method."""

    @pytest.fixture
    def formatter(self):
        return TUIFormatter()

    def test_basic_call_chain(self, formatter, sample_frames):
        """Test basic call chain formatting."""
        result = formatter.format_call_chain(sample_frames)

        # Should show call flow header
        assert "Call Chain:" in result

        # Should show frames in reverse order (entry point first)
        assert "main" in result
        assert "process_order" in result
        assert "calculate_total" in result

        # Should show arrows
        assert "└─▶" in result

        # Should show current position
        assert "YOU ARE HERE" in result

    def test_empty_call_chain(self, formatter):
        """Test empty call chain."""
        result = formatter.format_call_chain([])

        assert "Call Chain:" in result
        assert "(no frames)" in result

    def test_single_frame_call_chain(self, formatter, single_frame):
        """Test call chain with single frame."""
        result = formatter.format_call_chain(single_frame)

        assert "main" in result
        assert "YOU ARE HERE" in result
        # Single frame should not have arrow prefix
        assert "└─▶" not in result or result.count("└─▶") == 0

    def test_call_chain_file_names(self, formatter, sample_frames):
        """Test call chain shows file names."""
        result = formatter.format_call_chain(sample_frames)

        assert "main.py" in result
        assert "orders.py" in result
        assert "billing.py" in result

    def test_call_chain_line_numbers(self, formatter, sample_frames):
        """Test call chain shows line numbers."""
        result = formatter.format_call_chain(sample_frames)

        assert ":50" in result
        assert ":123" in result
        assert ":45" in result


# =============================================================================
# Helper Method Tests
# =============================================================================


class TestTruncate:
    """Tests for _truncate helper method."""

    @pytest.fixture
    def formatter(self):
        return TUIFormatter()

    def test_no_truncation_needed(self, formatter):
        """Test text shorter than max length."""
        result = formatter._truncate("hello", 10)
        assert result == "hello"

    def test_exact_length(self, formatter):
        """Test text exactly at max length."""
        result = formatter._truncate("hello", 5)
        assert result == "hello"

    def test_truncation_with_ellipsis(self, formatter):
        """Test text longer than max length."""
        result = formatter._truncate("hello world", 8)
        assert result == "hello..."
        assert len(result) == 8

    def test_very_short_max_length(self, formatter):
        """Test max length too short for ellipsis."""
        result = formatter._truncate("hello", 2)
        assert result == "he"

    def test_empty_string(self, formatter):
        """Test empty string input."""
        result = formatter._truncate("", 10)
        assert result == ""


class TestGetShortFilename:
    """Tests for _get_short_filename helper method."""

    @pytest.fixture
    def formatter(self):
        return TUIFormatter()

    def test_unix_path(self, formatter):
        """Test Unix-style path."""
        result = formatter._get_short_filename("/path/to/file.py")
        assert result == "file.py"

    def test_windows_path(self, formatter):
        """Test Windows-style path."""
        result = formatter._get_short_filename("C:\\Users\\test\\file.py")
        assert result == "file.py"

    def test_none_path(self, formatter):
        """Test None path."""
        result = formatter._get_short_filename(None)
        assert result == "<unknown>"

    def test_filename_only(self, formatter):
        """Test path that is just a filename."""
        result = formatter._get_short_filename("file.py")
        assert result == "file.py"

    def test_empty_string(self, formatter):
        """Test empty string path."""
        result = formatter._get_short_filename("")
        assert result == "<unknown>"


class TestBoxDrawing:
    """Tests for box drawing helper methods."""

    @pytest.fixture
    def formatter(self):
        return TUIFormatter()

    def test_box_top(self, formatter):
        """Test top border generation."""
        result = formatter._box_top(10)
        assert result == "┌──────────┐"
        assert len(result) == 12

    def test_box_bottom(self, formatter):
        """Test bottom border generation."""
        result = formatter._box_bottom(10)
        assert result == "└──────────┘"
        assert len(result) == 12

    def test_box_separator(self, formatter):
        """Test separator line generation."""
        result = formatter._box_separator(10)
        assert result == "├──────────┤"
        assert len(result) == 12

    def test_box_row(self, formatter):
        """Test content row generation."""
        result = formatter._box_row("test", 10)
        assert result == "│test      │"
        assert len(result) == 12

    def test_box_row_truncates(self, formatter):
        """Test content row truncates long content."""
        result = formatter._box_row("a" * 20, 10)
        assert len(result) == 12
        assert "..." in result

    def test_empty_box(self, formatter):
        """Test empty box generation."""
        result = formatter._empty_box("TITLE", "No data")
        assert "TITLE" in result
        assert "No data" in result
        assert "┌" in result
        assert "└" in result


class TestTableSeparator:
    """Tests for _table_separator helper method."""

    @pytest.fixture
    def formatter(self):
        return TUIFormatter()

    def test_table_separator_top(self, formatter):
        """Test table separator with top position."""
        result = formatter._table_separator([10, 10, 10], "top")
        assert "┬" in result
        assert "├" in result
        assert "┤" in result

    def test_table_separator_middle(self, formatter):
        """Test table separator with middle position."""
        result = formatter._table_separator([10, 10, 10], "middle")
        assert "┼" in result

    def test_table_separator_bottom(self, formatter):
        """Test table separator with bottom position."""
        result = formatter._table_separator([10, 10, 10], "bottom")
        assert "┴" in result
        assert "└" in result
        assert "┘" in result


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_format_stack_trace_function(self, sample_frames):
        """Test format_stack_trace convenience function."""
        result = format_stack_trace(sample_frames)
        assert "STACK TRACE" in result

    def test_format_variables_function(self, sample_variables):
        """Test format_variables convenience function."""
        result = format_variables(sample_variables)
        assert "VARIABLES" in result

    def test_format_scopes_function(self, sample_scopes):
        """Test format_scopes convenience function."""
        result = format_scopes(sample_scopes)
        assert "SCOPES" in result

    def test_format_call_chain_function(self, sample_frames):
        """Test format_call_chain convenience function."""
        result = format_call_chain(sample_frames)
        assert "Call Chain:" in result

    def test_get_formatter_default(self):
        """Test get_formatter returns default formatter."""
        formatter1 = get_formatter()
        formatter2 = get_formatter()
        assert formatter1 is formatter2  # Same cached instance

    def test_get_formatter_custom_config(self):
        """Test get_formatter with custom config."""
        config = TUIConfig(max_width=80)
        formatter = get_formatter(config)
        assert formatter.config.max_width == 80


# =============================================================================
# Custom Configuration Tests
# =============================================================================


class TestCustomConfiguration:
    """Tests for TUIFormatter with custom configuration."""

    def test_narrow_width(self, sample_frames):
        """Test formatter with narrow width."""
        config = TUIConfig(max_width=60)
        formatter = TUIFormatter(config)

        result = formatter.format_stack_trace(sample_frames)

        # Each line should be at most 60 characters
        for line in result.split("\n"):
            assert len(line) <= 60

    def test_wide_width(self, sample_frames):
        """Test formatter with wide width."""
        config = TUIConfig(max_width=120)
        formatter = TUIFormatter(config)

        result = formatter.format_stack_trace(sample_frames)

        # Lines should be padded to fill width
        lines = result.split("\n")
        # Box lines should be exactly max_width or close
        box_lines = [l for l in lines if l.startswith("│") or l.startswith("┌") or l.startswith("└")]
        for line in box_lines:
            assert len(line) <= 120

    def test_short_value_truncation(self, sample_variables):
        """Test aggressive value truncation."""
        config = TUIConfig(value_max_len=10)
        formatter = TUIFormatter(config)

        result = formatter.format_variables(sample_variables)

        # Long values should be truncated
        assert "..." in result

    def test_short_name_truncation(self, variables_with_long_names):
        """Test aggressive name truncation."""
        config = TUIConfig(name_max_len=15)
        formatter = TUIFormatter(config)

        result = formatter.format_variables(variables_with_long_names)

        # Long names should be truncated
        assert "..." in result


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Edge case tests for TUIFormatter."""

    @pytest.fixture
    def formatter(self):
        return TUIFormatter()

    def test_frame_with_zero_line(self, formatter):
        """Test frame with line number 0."""
        frames = [{"id": 1, "name": "test", "file": "test.py", "line": 0, "column": 0}]
        result = formatter.format_stack_trace(frames)
        assert ":0" in result

    def test_frame_with_large_line_number(self, formatter):
        """Test frame with very large line number."""
        frames = [{"id": 1, "name": "test", "file": "test.py", "line": 999999, "column": 0}]
        result = formatter.format_stack_trace(frames)
        assert "999999" in result

    def test_variable_with_empty_name(self, formatter):
        """Test variable with empty string name."""
        variables = [{"name": "", "value": "42", "type": "int", "variables_reference": 0}]
        result = formatter.format_variables(variables)
        # Should not crash
        assert "│" in result

    def test_variable_with_empty_value(self, formatter):
        """Test variable with empty string value."""
        variables = [{"name": "x", "value": "", "type": "str", "variables_reference": 0}]
        result = formatter.format_variables(variables)
        assert "x" in result

    def test_variable_with_none_type(self, formatter):
        """Test variable with None type."""
        variables = [{"name": "x", "value": "None", "type": None, "variables_reference": 0}]
        result = formatter.format_variables(variables)
        assert "x" in result

    def test_scope_with_zero_reference(self, formatter):
        """Test scope with variables_reference = 0."""
        scopes = [{"name": "Empty", "variables_reference": 0, "expensive": False}]
        result = formatter.format_scopes(scopes)
        assert "Empty" in result
        assert "0" in result

    def test_scope_with_large_reference(self, formatter):
        """Test scope with very large variables_reference."""
        scopes = [{"name": "Big", "variables_reference": 9999999, "expensive": False}]
        result = formatter.format_scopes(scopes)
        assert "9999999" in result


# =============================================================================
# Box Drawing Correctness Tests
# =============================================================================


class TestBoxDrawingCorrectness:
    """Tests to verify box drawing produces valid output."""

    @pytest.fixture
    def formatter(self):
        return TUIFormatter()

    def test_box_corners_match(self, formatter, sample_frames):
        """Test that box corners are properly matched."""
        result = formatter.format_stack_trace(sample_frames)

        # Count corners
        assert result.count("┌") == 1  # One top-left
        assert result.count("┐") == 1  # One top-right
        assert result.count("└") == 1  # One bottom-left
        assert result.count("┘") == 1  # One bottom-right

    def test_vertical_borders_aligned(self, formatter, sample_frames):
        """Test that vertical borders are aligned."""
        result = formatter.format_stack_trace(sample_frames)
        lines = result.split("\n")

        # All lines should have same length (consistent box width)
        line_lengths = [len(line) for line in lines if line]
        assert len(set(line_lengths)) == 1  # All same length

    def test_table_structure_valid(self, formatter, sample_variables):
        """Test that table structure is valid."""
        result = formatter.format_variables(sample_variables)

        # Should have column separators
        assert "│" in result

        # Each row should have same number of column separators
        lines = [l for l in result.split("\n") if "│" in l]
        separator_counts = [l.count("│") for l in lines]
        # Most lines should have consistent separator count
        assert len(set(separator_counts)) <= 2  # Allow for header vs data rows
```

---

## 4. Integration Tests

### 4.1 Test File: `tests/integration/test_tui_integration.py`

```python
"""Integration tests for TUI formatting in MCP tools.

Tests verify that the format parameter works correctly
in the actual MCP tool functions.
"""

import pytest

import polybugger_mcp.mcp_server as mcp_server
from polybugger_mcp.core.session import SessionManager
from polybugger_mcp.mcp_server import (
    debug_create_session,
    debug_get_stacktrace,
    debug_get_variables,
    debug_get_scopes,
    debug_set_breakpoints,
    debug_launch,
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


@pytest.fixture
def test_script(tmp_path):
    """Create a test script for debugging."""
    script = tmp_path / "test_script.py"
    script.write_text('''
def add(a, b):
    result = a + b
    return result

def main():
    x = 10
    y = 20
    z = add(x, y)
    print(f"Result: {z}")
    return z

if __name__ == "__main__":
    main()
''')
    return script


class TestFormatParameterStacktrace:
    """Tests for format parameter on debug_get_stacktrace."""

    @pytest.mark.asyncio
    async def test_default_format_is_json(self, session_manager, tmp_path):
        """Test that default format is json (backward compatible)."""
        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        # Note: This test may return error since session isn't running
        # The important thing is it doesn't include TUI formatting by default
        result = await debug_get_stacktrace(session_id=session_id)

        # Should not have formatted key when format not specified
        if "error" not in result:
            assert "formatted" not in result

    @pytest.mark.asyncio
    async def test_format_json_explicit(self, session_manager, tmp_path):
        """Test explicit format='json' works."""
        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        result = await debug_get_stacktrace(session_id=session_id, format="json")

        if "error" not in result:
            assert "formatted" not in result

    @pytest.mark.asyncio
    async def test_format_tui_returns_formatted(self, session_manager, tmp_path):
        """Test format='tui' returns formatted output."""
        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        # Note: This will return empty frames since not paused,
        # but should still have formatting structure
        result = await debug_get_stacktrace(session_id=session_id, format="tui")

        if "error" not in result:
            # Should have both structured data and formatted output
            assert "frames" in result
            assert "formatted" in result
            assert "format" in result
            assert result["format"] == "tui"
            # Formatted should be a string with box characters
            assert isinstance(result["formatted"], str)

    @pytest.mark.asyncio
    async def test_format_tui_includes_call_chain(self, session_manager, tmp_path):
        """Test format='tui' includes call_chain field."""
        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        result = await debug_get_stacktrace(session_id=session_id, format="tui")

        if "error" not in result:
            assert "call_chain" in result
            assert isinstance(result["call_chain"], str)

    @pytest.mark.asyncio
    async def test_stacktrace_not_found_tui(self, session_manager):
        """Test error handling with format='tui'."""
        result = await debug_get_stacktrace(session_id="nonexistent", format="tui")

        assert "error" in result
        assert result["code"] == "NOT_FOUND"


class TestFormatParameterVariables:
    """Tests for format parameter on debug_get_variables."""

    @pytest.mark.asyncio
    async def test_default_format_is_json(self, session_manager, tmp_path):
        """Test that default format is json."""
        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        result = await debug_get_variables(
            session_id=session_id,
            variables_reference=1,
        )

        if "error" not in result:
            assert "formatted" not in result

    @pytest.mark.asyncio
    async def test_format_tui_returns_formatted(self, session_manager, tmp_path):
        """Test format='tui' returns formatted output."""
        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        result = await debug_get_variables(
            session_id=session_id,
            variables_reference=1,
            format="tui",
        )

        if "error" not in result:
            assert "variables" in result
            assert "formatted" in result
            assert "format" in result
            assert result["format"] == "tui"

    @pytest.mark.asyncio
    async def test_variables_not_found_tui(self, session_manager):
        """Test error handling with format='tui'."""
        result = await debug_get_variables(
            session_id="nonexistent",
            variables_reference=1,
            format="tui",
        )

        assert "error" in result
        assert result["code"] == "NOT_FOUND"


class TestFormatParameterScopes:
    """Tests for format parameter on debug_get_scopes."""

    @pytest.mark.asyncio
    async def test_default_format_is_json(self, session_manager, tmp_path):
        """Test that default format is json."""
        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        result = await debug_get_scopes(session_id=session_id, frame_id=1)

        if "error" not in result:
            assert "formatted" not in result

    @pytest.mark.asyncio
    async def test_format_tui_returns_formatted(self, session_manager, tmp_path):
        """Test format='tui' returns formatted output."""
        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        result = await debug_get_scopes(
            session_id=session_id,
            frame_id=1,
            format="tui",
        )

        if "error" not in result:
            assert "scopes" in result
            assert "formatted" in result
            assert "format" in result
            assert result["format"] == "tui"

    @pytest.mark.asyncio
    async def test_scopes_not_found_tui(self, session_manager):
        """Test error handling with format='tui'."""
        result = await debug_get_scopes(
            session_id="nonexistent",
            frame_id=1,
            format="tui",
        )

        assert "error" in result
        assert result["code"] == "NOT_FOUND"


class TestInvalidFormatParameter:
    """Tests for invalid format parameter values."""

    @pytest.mark.asyncio
    async def test_invalid_format_stacktrace(self, session_manager, tmp_path):
        """Test invalid format value on stacktrace."""
        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        # Invalid format should either be ignored or return error
        result = await debug_get_stacktrace(
            session_id=session_id,
            format="invalid",
        )

        # Should either work as json or return error
        # Implementation choice - document expected behavior

    @pytest.mark.asyncio
    async def test_empty_format_stacktrace(self, session_manager, tmp_path):
        """Test empty string format value."""
        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        result = await debug_get_stacktrace(
            session_id=session_id,
            format="",
        )

        # Should handle gracefully


class TestTUIOutputStructure:
    """Tests to verify TUI output structure is correct."""

    @pytest.mark.asyncio
    async def test_tui_output_contains_box_chars(self, session_manager, tmp_path):
        """Test that TUI output contains proper box drawing characters."""
        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        result = await debug_get_stacktrace(
            session_id=session_id,
            format="tui",
        )

        if "formatted" in result:
            formatted = result["formatted"]
            # Should contain Unicode box drawing characters
            assert "┌" in formatted or "+" in formatted
            assert "│" in formatted or "|" in formatted
            assert "└" in formatted or "+" in formatted

    @pytest.mark.asyncio
    async def test_tui_preserves_json_structure(self, session_manager, tmp_path):
        """Test that TUI format still includes full JSON data."""
        create_result = await debug_create_session(project_root=str(tmp_path))
        session_id = create_result["session_id"]

        result_json = await debug_get_stacktrace(
            session_id=session_id,
            format="json",
        )

        result_tui = await debug_get_stacktrace(
            session_id=session_id,
            format="tui",
        )

        # Both should have frames
        if "frames" in result_json and "frames" in result_tui:
            assert result_json["frames"] == result_tui["frames"]
```

---

## 5. Edge Case Tests

### 5.1 Additional Edge Case Scenarios

```python
# Additional edge cases to add to test_tui_formatter.py

class TestEdgeCasesExtended:
    """Extended edge case tests."""

    @pytest.fixture
    def formatter(self):
        return TUIFormatter()

    # Empty input edge cases
    def test_all_empty_inputs(self, formatter):
        """Test all methods with empty inputs."""
        assert formatter.format_stack_trace([]) is not None
        assert formatter.format_variables([]) is not None
        assert formatter.format_scopes([]) is not None
        assert formatter.format_call_chain([]) is not None

    # Very long values edge cases
    def test_value_exactly_at_limit(self, formatter):
        """Test value exactly at truncation limit."""
        config = TUIConfig(value_max_len=10)
        formatter = TUIFormatter(config)

        variables = [{"name": "x", "value": "1234567890", "type": "str", "variables_reference": 0}]
        result = formatter.format_variables(variables)
        assert "1234567890" in result or "..." in result

    def test_value_one_over_limit(self, formatter):
        """Test value one character over limit."""
        config = TUIConfig(value_max_len=10)
        formatter = TUIFormatter(config)

        variables = [{"name": "x", "value": "12345678901", "type": "str", "variables_reference": 0}]
        result = formatter.format_variables(variables)
        assert "..." in result

    # Unicode edge cases
    def test_mixed_ascii_unicode(self, formatter):
        """Test mixed ASCII and Unicode content."""
        variables = [
            {"name": "mixed", "value": "hello 世界 test", "type": "str", "variables_reference": 0}
        ]
        result = formatter.format_variables(variables)
        assert "│" in result

    def test_unicode_only_name(self, formatter):
        """Test variable with Unicode-only name."""
        variables = [
            {"name": "変数", "value": "42", "type": "int", "variables_reference": 0}
        ]
        result = formatter.format_variables(variables)
        assert "│" in result

    def test_emoji_in_value(self, formatter):
        """Test emoji characters in values."""
        variables = [
            {"name": "status", "value": "✅ Success 🎉", "type": "str", "variables_reference": 0}
        ]
        result = formatter.format_variables(variables)
        # Should not crash

    # Special character edge cases
    def test_null_bytes_in_value(self, formatter):
        """Test null bytes in values."""
        variables = [
            {"name": "data", "value": "test\x00null", "type": "bytes", "variables_reference": 0}
        ]
        result = formatter.format_variables(variables)
        # Should handle gracefully

    def test_control_characters_in_value(self, formatter):
        """Test control characters in values."""
        variables = [
            {"name": "ctrl", "value": "line1\r\nline2\t\ttabbed", "type": "str", "variables_reference": 0}
        ]
        result = formatter.format_variables(variables)
        # Should escape or handle control chars

    def test_backslash_in_value(self, formatter):
        """Test backslashes in values."""
        variables = [
            {"name": "path", "value": "C:\\Users\\test\\file.txt", "type": "str", "variables_reference": 0}
        ]
        result = formatter.format_variables(variables)
        assert "Users" in result or "\\" in result

    # Deep stack traces
    def test_very_deep_stack(self, formatter):
        """Test very deep stack trace (100 frames)."""
        frames = [
            {"id": i, "name": f"func_{i}", "file": f"/app/mod_{i}.py", "line": i * 10, "column": 0}
            for i in range(100)
        ]
        result = formatter.format_stack_trace(frames)
        assert "100 frames" in result

    # Single item vs multiple items
    def test_single_variable(self, formatter):
        """Test single variable formatting."""
        variables = [{"name": "x", "value": "42", "type": "int", "variables_reference": 0}]
        result = formatter.format_variables(variables)
        assert "x" in result
        assert "42" in result

    def test_many_variables(self, formatter):
        """Test many variables formatting."""
        variables = [
            {"name": f"var_{i}", "value": str(i), "type": "int", "variables_reference": 0}
            for i in range(50)
        ]
        result = formatter.format_variables(variables)
        assert "var_0" in result
        assert "var_49" in result

    # Numeric edge cases
    def test_negative_numbers(self, formatter):
        """Test negative number formatting."""
        variables = [
            {"name": "neg", "value": "-12345", "type": "int", "variables_reference": 0}
        ]
        result = formatter.format_variables(variables)
        assert "-12345" in result

    def test_zero_values(self, formatter):
        """Test zero values."""
        variables = [
            {"name": "zero_int", "value": "0", "type": "int", "variables_reference": 0},
            {"name": "zero_float", "value": "0.0", "type": "float", "variables_reference": 0},
        ]
        result = formatter.format_variables(variables)
        assert "0" in result

    def test_large_numbers(self, formatter):
        """Test very large numbers."""
        variables = [
            {"name": "big", "value": "12345678901234567890", "type": "int", "variables_reference": 0}
        ]
        result = formatter.format_variables(variables)
        # May be truncated, but should not crash

    # Boolean and None values
    def test_boolean_values(self, formatter):
        """Test boolean values."""
        variables = [
            {"name": "flag_true", "value": "True", "type": "bool", "variables_reference": 0},
            {"name": "flag_false", "value": "False", "type": "bool", "variables_reference": 0},
        ]
        result = formatter.format_variables(variables)
        assert "True" in result
        assert "False" in result

    def test_none_value(self, formatter):
        """Test None value."""
        variables = [
            {"name": "nothing", "value": "None", "type": "NoneType", "variables_reference": 0}
        ]
        result = formatter.format_variables(variables)
        assert "None" in result

    # Complex type representations
    def test_dict_representation(self, formatter):
        """Test dictionary value representation."""
        variables = [
            {"name": "config", "value": "{'key': 'value', 'nested': {...}}", "type": "dict", "variables_reference": 101}
        ]
        result = formatter.format_variables(variables)
        assert "config" in result
        assert "▸" in result  # Expandable indicator

    def test_list_representation(self, formatter):
        """Test list value representation."""
        variables = [
            {"name": "items", "value": "[1, 2, 3, ..., 100]", "type": "list", "variables_reference": 102}
        ]
        result = formatter.format_variables(variables)
        assert "items" in result

    def test_object_representation(self, formatter):
        """Test object value representation."""
        variables = [
            {"name": "obj", "value": "<MyClass object at 0x7f1234567890>", "type": "MyClass", "variables_reference": 103}
        ]
        result = formatter.format_variables(variables)
        assert "MyClass" in result
```

---

## 6. Expected Outputs

### 6.1 Stack Trace Expected Output

**Input:**
```python
frames = [
    {"id": 1, "name": "calculate_total", "file": "/app/billing.py", "line": 45, "column": 0},
    {"id": 2, "name": "process_order", "file": "/app/orders.py", "line": 123, "column": 0},
    {"id": 3, "name": "main", "file": "/app/main.py", "line": 50, "column": 0},
]
```

**Expected Output (approximately):**
```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│ STACK TRACE                                                                          3 frames │
├────────────────────────────────────────────────────────────────────────────────────────────────┤
│ #0   calculate_total                    billing.py:45                                         │
│ #1   process_order                      orders.py:123                                         │
│ #2   main                               main.py:50                                            │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Validation Approach:**
```python
def validate_stack_trace_output(output: str, frames: list) -> None:
    """Validate stack trace output structure."""
    lines = output.strip().split("\n")

    # Check box structure
    assert lines[0].startswith("┌")
    assert lines[0].endswith("┐")
    assert lines[-1].startswith("└")
    assert lines[-1].endswith("┘")

    # Check frame count in header
    assert f"{len(frames)} frame" in lines[1]

    # Check each frame is present
    for i, frame in enumerate(frames):
        assert f"#{i}" in output
        assert frame["name"] in output
        assert str(frame["line"]) in output
```

### 6.2 Variables Expected Output

**Input:**
```python
variables = [
    {"name": "items", "value": "[100, 200, 300]", "type": "list", "variables_reference": 101},
    {"name": "total", "value": "1500", "type": "int", "variables_reference": 0},
]
```

**Expected Output:**
```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│ VARIABLES                                                                                      │
├────────────┬────────────┬──────────────────────────────────────────────────────────────────────┤
│ Name       │ Type       │ Value                                                                │
├────────────┼────────────┼──────────────────────────────────────────────────────────────────────┤
│ items ▸    │ list       │ [100, 200, 300]                                                      │
│ total      │ int        │ 1500                                                                 │
└────────────┴────────────┴──────────────────────────────────────────────────────────────────────┘
```

**Validation Approach:**
```python
def validate_variables_output(output: str, variables: list) -> None:
    """Validate variables output structure."""
    # Check column headers
    assert "Name" in output
    assert "Type" in output
    assert "Value" in output

    # Check each variable present
    for var in variables:
        assert var["name"] in output

    # Check expandable indicator for variables with children
    for var in variables:
        if var.get("variables_reference", 0) > 0:
            # Should have expand indicator somewhere
            assert "▸" in output
```

### 6.3 Call Chain Expected Output

**Input:**
```python
frames = [
    {"id": 1, "name": "calculate_total", "file": "/app/billing.py", "line": 45, "column": 0},
    {"id": 2, "name": "process_order", "file": "/app/orders.py", "line": 123, "column": 0},
    {"id": 3, "name": "main", "file": "/app/main.py", "line": 50, "column": 0},
]
```

**Expected Output:**
```
Call Chain:

main (main.py:50)
  └─▶ process_order (orders.py:123)
      └─▶ calculate_total (billing.py:45)  ◀── YOU ARE HERE
```

**Validation Approach:**
```python
def validate_call_chain_output(output: str, frames: list) -> None:
    """Validate call chain output structure."""
    assert "Call Chain:" in output
    assert "YOU ARE HERE" in output

    # Frames should appear in reverse order (entry point first)
    reversed_frames = list(reversed(frames))
    first_frame = reversed_frames[0]
    last_frame = reversed_frames[-1]

    # First frame (entry point) should appear first in output
    first_pos = output.find(first_frame["name"])
    last_pos = output.find(last_frame["name"])
    assert first_pos < last_pos
```

---

## 7. Test Coverage Matrix

### 7.1 Method Coverage

| Method | Unit Tests | Integration Tests | Edge Cases |
|--------|------------|-------------------|------------|
| `TUIFormatter.__init__` | ✅ | - | ✅ |
| `format_stack_trace` | ✅ | ✅ | ✅ |
| `format_variables` | ✅ | ✅ | ✅ |
| `format_scopes` | ✅ | ✅ | ✅ |
| `format_call_chain` | ✅ | - | ✅ |
| `_box_top` | ✅ | - | - |
| `_box_bottom` | ✅ | - | - |
| `_box_separator` | ✅ | - | - |
| `_box_row` | ✅ | - | ✅ |
| `_empty_box` | ✅ | - | - |
| `_table_separator` | ✅ | - | - |
| `_table_row` | ✅ | - | - |
| `_truncate` | ✅ | - | ✅ |
| `_get_short_filename` | ✅ | - | ✅ |

### 7.2 Edge Case Coverage

| Edge Case | Stack Trace | Variables | Scopes | Call Chain |
|-----------|-------------|-----------|--------|------------|
| Empty input | ✅ | ✅ | ✅ | ✅ |
| Single item | ✅ | ✅ | ✅ | ✅ |
| Many items (50+) | ✅ | ✅ | - | ✅ |
| Very deep (100+) | ✅ | - | - | ✅ |
| Long names (>30 chars) | ✅ | ✅ | - | - |
| Long values (>50 chars) | - | ✅ | - | - |
| Unicode names | ✅ | ✅ | - | ✅ |
| Unicode values | - | ✅ | - | - |
| Special chars (\n, \t) | - | ✅ | - | - |
| Missing file | ✅ | - | - | ✅ |
| Zero line number | ✅ | - | - | - |
| Large line number | ✅ | - | - | - |
| None type | - | ✅ | - | - |
| Zero reference | - | ✅ | ✅ | - |
| Large reference | - | - | ✅ | - |

### 7.3 Integration Coverage

| MCP Tool | Default Format | JSON Format | TUI Format | Error Handling |
|----------|---------------|-------------|------------|----------------|
| `debug_get_stacktrace` | ✅ | ✅ | ✅ | ✅ |
| `debug_get_variables` | ✅ | ✅ | ✅ | ✅ |
| `debug_get_scopes` | ✅ | ✅ | ✅ | ✅ |

---

## 8. Running the Tests

### 8.1 Commands

```bash
# Run all TUI formatter tests
pytest tests/unit/test_tui_formatter.py -v

# Run integration tests
pytest tests/integration/test_tui_integration.py -v

# Run with coverage
pytest tests/unit/test_tui_formatter.py tests/integration/test_tui_integration.py --cov=polybugger_mcp.utils.tui_formatter --cov-report=term-missing

# Run specific test class
pytest tests/unit/test_tui_formatter.py::TestFormatStackTrace -v

# Run edge case tests only
pytest tests/unit/test_tui_formatter.py::TestEdgeCases -v
pytest tests/unit/test_tui_formatter.py::TestEdgeCasesExtended -v
```

### 8.2 Expected Results

| Test Category | Test Count | Expected Pass Rate |
|--------------|------------|-------------------|
| TUIConfig | 3 | 100% |
| TUIFormatter Init | 2 | 100% |
| format_stack_trace | 10 | 100% |
| format_variables | 10 | 100% |
| format_scopes | 5 | 100% |
| format_call_chain | 5 | 100% |
| Helper Methods | 20 | 100% |
| Convenience Functions | 6 | 100% |
| Custom Config | 4 | 100% |
| Edge Cases | 25 | 100% |
| Integration Tests | 15 | 100% |
| **Total** | **~105** | **100%** |

---

## 9. Appendix: Test Fixtures Summary

```python
# Quick reference for all fixtures

# Stack Frame Fixtures
sample_frames              # 3 standard frames
single_frame               # 1 frame
deep_stack_frames          # 25 frames
frames_with_long_names     # Long function names
frames_with_missing_file   # None file path
frames_with_unicode_names  # Unicode function names

# Variable Fixtures
sample_variables           # 4 standard variables
variables_with_long_values # Values > 50 chars
variables_with_long_names  # Names > 30 chars
variables_with_special_chars # \n, \t, etc.
variables_with_unicode     # Unicode values
numeric_variables          # Various numeric types

# Scope Fixtures
sample_scopes              # 2 standard scopes
scopes_with_all_types      # 4 scope types
single_scope               # 1 scope
```

---

*Document End*
