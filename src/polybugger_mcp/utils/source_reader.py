"""Source code reading utilities for debug context.

Provides functionality to read source code context around
specific lines for enhanced debugging visualization.
"""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Simple LRU cache for file contents
_file_cache: dict[str, list[str]] = {}
_MAX_CACHE_SIZE = 50


def _get_file_lines(file_path: str) -> list[str] | None:
    """Read and cache file contents.

    Args:
        file_path: Path to the source file

    Returns:
        List of lines (without newlines) or None if file cannot be read
    """
    global _file_cache

    # Check cache
    if file_path in _file_cache:
        return _file_cache[file_path]

    # Try to read file
    try:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return None

        with open(path, encoding="utf-8", errors="replace") as f:
            lines = [line.rstrip("\n\r") for line in f.readlines()]

        # Manage cache size
        if len(_file_cache) >= _MAX_CACHE_SIZE:
            # Remove oldest entry (first key)
            oldest = next(iter(_file_cache))
            del _file_cache[oldest]

        _file_cache[file_path] = lines
        return lines

    except Exception as e:
        logger.debug(f"Failed to read source file {file_path}: {e}")
        return None


def clear_cache() -> None:
    """Clear the source file cache."""
    global _file_cache
    _file_cache.clear()


def get_source_line(file_path: str, line_number: int) -> str | None:
    """Get a single source line.

    Args:
        file_path: Path to the source file
        line_number: 1-based line number

    Returns:
        Source line content or None if unavailable
    """
    lines = _get_file_lines(file_path)
    if lines is None:
        return None

    # Convert to 0-based index
    idx = line_number - 1
    if 0 <= idx < len(lines):
        return lines[idx]

    return None


def get_source_context(
    file_path: str,
    line_number: int,
    context_lines: int = 2,
) -> dict[str, Any]:
    """Get source context around a specific line.

    Args:
        file_path: Path to the source file
        line_number: 1-based line number (the focal point)
        context_lines: Number of lines before and after to include

    Returns:
        Dict with:
            - before: list of lines before the target
            - current: the target line
            - after: list of lines after the target
            - line_numbers: dict with 'start', 'current', 'end' line numbers

    Example:
        >>> get_source_context("example.py", 10, context_lines=2)
        {
            "before": ["    def foo():", "        x = 1"],
            "current": "        y = x + 1  # line 10",
            "after": ["        return y", ""],
            "line_numbers": {"start": 8, "current": 10, "end": 12}
        }
    """
    lines = _get_file_lines(file_path)
    if lines is None:
        return {
            "before": [],
            "current": None,
            "after": [],
            "line_numbers": {"start": line_number, "current": line_number, "end": line_number},
        }

    # Convert to 0-based index
    idx = line_number - 1
    total_lines = len(lines)

    # Calculate range
    start_idx = max(0, idx - context_lines)
    end_idx = min(total_lines - 1, idx + context_lines)

    # Get before lines
    before = []
    for i in range(start_idx, idx):
        if 0 <= i < total_lines:
            before.append(lines[i])

    # Get current line
    current = lines[idx] if 0 <= idx < total_lines else None

    # Get after lines
    after = []
    for i in range(idx + 1, end_idx + 1):
        if 0 <= i < total_lines:
            after.append(lines[i])

    return {
        "before": before,
        "current": current,
        "after": after,
        "line_numbers": {
            "start": start_idx + 1,  # Convert back to 1-based
            "current": line_number,
            "end": end_idx + 1,
        },
    }


def get_function_context(
    file_path: str,
    line_number: int,
    max_lines_back: int = 20,
) -> dict[str, Any]:
    """Try to find the function definition containing a line.

    Looks backwards from the given line to find a 'def' or 'async def'
    statement, which likely indicates the containing function.

    Args:
        file_path: Path to the source file
        line_number: 1-based line number within the function
        max_lines_back: Maximum lines to search backwards

    Returns:
        Dict with:
            - function_line: The 'def ...' line if found
            - function_line_number: 1-based line number of the def
            - found: True if a function definition was found
    """
    lines = _get_file_lines(file_path)
    if lines is None:
        return {"function_line": None, "function_line_number": None, "found": False}

    # Convert to 0-based index
    idx = line_number - 1
    if idx < 0 or idx >= len(lines):
        return {"function_line": None, "function_line_number": None, "found": False}

    # Search backwards for function definition
    search_start = max(0, idx - max_lines_back)
    for i in range(idx, search_start - 1, -1):
        line = lines[i].lstrip()
        if line.startswith("def ") or line.startswith("async def "):
            return {
                "function_line": lines[i],
                "function_line_number": i + 1,  # Convert to 1-based
                "found": True,
            }

    return {"function_line": None, "function_line_number": None, "found": False}


def extract_call_expression(source_line: str) -> str | None:
    """Try to extract a function call expression from a source line.

    This is a best-effort extraction that looks for common call patterns.

    Args:
        source_line: A line of Python source code

    Returns:
        The likely call expression or None if not identifiable

    Examples:
        >>> extract_call_expression("    result = foo.bar(x, y)")
        "foo.bar(x, y)"
        >>> extract_call_expression("    process(data)")
        "process(data)"
    """
    if source_line is None:
        return None

    line = source_line.strip()

    # Skip empty lines and comments
    if not line or line.startswith("#"):
        return None

    # Look for assignment with call
    if "=" in line and "(" in line:
        # Get the right side of assignment
        parts = line.split("=", 1)
        if len(parts) == 2:
            rhs = parts[1].strip()
            # Check if it looks like a function call
            if "(" in rhs:
                return rhs

    # Look for standalone call
    if "(" in line and not line.startswith(("def ", "class ", "if ", "while ", "for ", "with ")):
        # Return the whole line as the call expression
        return line

    return None


def format_source_with_line_numbers(
    lines: list[str],
    start_line: int,
    highlight_line: int | None = None,
    indent: str = "  ",
) -> str:
    """Format source lines with line numbers.

    Args:
        lines: List of source lines
        start_line: 1-based line number of the first line
        highlight_line: 1-based line number to highlight (optional)
        indent: Indentation prefix for each line

    Returns:
        Formatted string with line numbers

    Example:
        >>> format_source_with_line_numbers(["x = 1", "y = 2"], 10, 11)
        "  10 │ x = 1
           11 │ y = 2  ◀──"
    """
    if not lines:
        return ""

    # Calculate line number width
    max_line_num = start_line + len(lines) - 1
    width = len(str(max_line_num))

    formatted_lines = []
    for i, line in enumerate(lines):
        line_num = start_line + i
        num_str = str(line_num).rjust(width)

        if highlight_line and line_num == highlight_line:
            formatted_lines.append(f"{indent}{num_str} │ {line}  ◀──")
        else:
            formatted_lines.append(f"{indent}{num_str} │ {line}")

    return "\n".join(formatted_lines)
