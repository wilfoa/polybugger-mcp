"""Unit tests for source_reader module."""

import tempfile
from pathlib import Path

import pytest

from polybugger_mcp.utils.source_reader import (
    clear_cache,
    extract_call_expression,
    format_source_with_line_numbers,
    get_function_context,
    get_source_context,
    get_source_line,
)


@pytest.fixture
def sample_source_file():
    """Create a temporary Python source file for testing."""
    content = """\
def outer_function():
    '''Outer function docstring.'''
    x = 1
    y = 2
    result = inner_function(x, y)
    return result

def inner_function(a, b):
    '''Inner function docstring.'''
    total = a + b
    return total

class Calculator:
    def add(self, x, y):
        return x + y

    async def async_add(self, x, y):
        return x + y
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(content)
        f.flush()
        yield f.name
    # Cleanup
    Path(f.name).unlink(missing_ok=True)
    clear_cache()


@pytest.fixture(autouse=True)
def clear_cache_between_tests():
    """Clear the file cache between tests."""
    clear_cache()
    yield
    clear_cache()


class TestGetSourceLine:
    """Tests for get_source_line function."""

    def test_get_valid_line(self, sample_source_file):
        """Should return the correct line content."""
        line = get_source_line(sample_source_file, 1)
        assert line == "def outer_function():"

    def test_get_middle_line(self, sample_source_file):
        """Should return lines from the middle of the file."""
        line = get_source_line(sample_source_file, 3)
        assert line == "    x = 1"

    def test_get_last_line(self, sample_source_file):
        """Should return the last line."""
        line = get_source_line(sample_source_file, 18)
        assert line == "        return x + y"

    def test_get_line_zero(self, sample_source_file):
        """Line 0 should return None (1-based indexing)."""
        line = get_source_line(sample_source_file, 0)
        assert line is None

    def test_get_negative_line(self, sample_source_file):
        """Negative line numbers should return None."""
        line = get_source_line(sample_source_file, -1)
        assert line is None

    def test_get_line_beyond_file(self, sample_source_file):
        """Lines beyond file end should return None."""
        line = get_source_line(sample_source_file, 1000)
        assert line is None

    def test_nonexistent_file(self):
        """Nonexistent file should return None."""
        line = get_source_line("/nonexistent/path/to/file.py", 1)
        assert line is None


class TestGetSourceContext:
    """Tests for get_source_context function."""

    def test_context_with_default_lines(self, sample_source_file):
        """Should return 2 lines before and after by default."""
        context = get_source_context(sample_source_file, 5)
        assert len(context["before"]) == 2
        assert context["current"] == "    result = inner_function(x, y)"
        assert len(context["after"]) == 2

    def test_context_at_file_start(self, sample_source_file):
        """Should handle lines at the start with fewer 'before' lines."""
        context = get_source_context(sample_source_file, 1, context_lines=2)
        assert context["before"] == []
        assert context["current"] == "def outer_function():"
        assert len(context["after"]) == 2

    def test_context_at_file_end(self, sample_source_file):
        """Should handle lines at the end with fewer 'after' lines."""
        context = get_source_context(sample_source_file, 18, context_lines=2)
        assert len(context["before"]) == 2
        assert context["current"] == "        return x + y"
        assert context["after"] == []

    def test_context_line_numbers(self, sample_source_file):
        """Should return correct line numbers."""
        context = get_source_context(sample_source_file, 10, context_lines=2)
        assert context["line_numbers"]["current"] == 10
        assert context["line_numbers"]["start"] == 8
        assert context["line_numbers"]["end"] == 12

    def test_context_custom_lines(self, sample_source_file):
        """Should respect custom context_lines parameter."""
        context = get_source_context(sample_source_file, 10, context_lines=1)
        assert len(context["before"]) == 1
        assert len(context["after"]) == 1

    def test_context_zero_lines(self, sample_source_file):
        """Should return just the current line with context_lines=0."""
        context = get_source_context(sample_source_file, 10, context_lines=0)
        assert context["before"] == []
        assert context["current"] is not None
        assert context["after"] == []

    def test_context_nonexistent_file(self):
        """Nonexistent file should return empty context."""
        context = get_source_context("/nonexistent/file.py", 10)
        assert context["before"] == []
        assert context["current"] is None
        assert context["after"] == []


class TestGetFunctionContext:
    """Tests for get_function_context function."""

    def test_find_function_def(self, sample_source_file):
        """Should find function definition above the line."""
        result = get_function_context(sample_source_file, 5)
        assert result["found"] is True
        assert "def outer_function" in result["function_line"]
        assert result["function_line_number"] == 1

    def test_find_inner_function(self, sample_source_file):
        """Should find the correct enclosing function."""
        result = get_function_context(sample_source_file, 10)
        assert result["found"] is True
        assert "def inner_function" in result["function_line"]
        assert result["function_line_number"] == 8

    def test_find_method(self, sample_source_file):
        """Should find method definitions."""
        result = get_function_context(sample_source_file, 15)
        assert result["found"] is True
        assert "def add" in result["function_line"]

    def test_find_async_function(self, sample_source_file):
        """Should find async function definitions."""
        result = get_function_context(sample_source_file, 18)
        assert result["found"] is True
        assert "async def async_add" in result["function_line"]

    def test_no_function_found(self, sample_source_file):
        """Should return found=False when no function is above."""
        # Create a file with no function definition
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("x = 1\ny = 2\nz = x + y\n")
            f.flush()
            result = get_function_context(f.name, 2)
            assert result["found"] is False
            Path(f.name).unlink()

    def test_nonexistent_file(self):
        """Nonexistent file should return found=False."""
        result = get_function_context("/nonexistent/file.py", 10)
        assert result["found"] is False


class TestExtractCallExpression:
    """Tests for extract_call_expression function."""

    def test_simple_call(self):
        """Should extract simple function calls."""
        result = extract_call_expression("    foo()")
        assert result == "foo()"

    def test_call_with_args(self):
        """Should extract calls with arguments."""
        result = extract_call_expression("    result = calculate(x, y)")
        assert result == "calculate(x, y)"

    def test_method_call(self):
        """Should extract method calls."""
        result = extract_call_expression("    total = obj.method(arg)")
        assert result == "obj.method(arg)"

    def test_chained_call(self):
        """Should extract chained calls."""
        result = extract_call_expression("    data = foo.bar.baz(x)")
        assert result == "foo.bar.baz(x)"

    def test_empty_line(self):
        """Empty line should return None."""
        result = extract_call_expression("")
        assert result is None

    def test_comment_line(self):
        """Comment line should return None."""
        result = extract_call_expression("    # This is a comment")
        assert result is None

    def test_def_statement(self):
        """Function definition should return None."""
        result = extract_call_expression("def foo():")
        assert result is None

    def test_class_statement(self):
        """Class definition should return None."""
        result = extract_call_expression("class Foo:")
        assert result is None

    def test_none_input(self):
        """None input should return None."""
        result = extract_call_expression(None)  # type: ignore[arg-type]
        assert result is None


class TestFormatSourceWithLineNumbers:
    """Tests for format_source_with_line_numbers function."""

    def test_basic_formatting(self):
        """Should format lines with line numbers."""
        lines = ["x = 1", "y = 2"]
        result = format_source_with_line_numbers(lines, start_line=10)
        assert "10 │ x = 1" in result
        assert "11 │ y = 2" in result

    def test_highlighted_line(self):
        """Should highlight specified line."""
        lines = ["x = 1", "y = 2", "z = 3"]
        result = format_source_with_line_numbers(lines, start_line=10, highlight_line=11)
        assert "11 │ y = 2  ◀──" in result
        assert "◀──" not in result.split("\n")[0]  # Line 10 not highlighted
        assert "◀──" not in result.split("\n")[2]  # Line 12 not highlighted

    def test_custom_indent(self):
        """Should use custom indentation."""
        lines = ["x = 1"]
        result = format_source_with_line_numbers(lines, start_line=1, indent="    ")
        assert result.startswith("    ")

    def test_empty_lines(self):
        """Empty list should return empty string."""
        result = format_source_with_line_numbers([], start_line=1)
        assert result == ""

    def test_line_number_alignment(self):
        """Should align line numbers for multi-digit numbers."""
        lines = ["a", "b", "c"]
        result = format_source_with_line_numbers(lines, start_line=98)
        # Line numbers should be right-justified
        assert " 98 │" in result
        assert " 99 │" in result
        assert "100 │" in result


class TestCacheManagement:
    """Tests for cache management."""

    def test_clear_cache(self, sample_source_file):
        """Cache should be cleared."""
        # Read to populate cache
        get_source_line(sample_source_file, 1)
        # Clear cache
        clear_cache()
        # Cache should be empty now (no assertion, just no error)

    def test_caching_works(self, sample_source_file):
        """Multiple reads should use cache."""
        # First read
        line1 = get_source_line(sample_source_file, 1)
        # Second read (should use cache)
        line2 = get_source_line(sample_source_file, 1)
        assert line1 == line2
