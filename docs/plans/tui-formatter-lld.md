# TUI Formatter - Low-Level Design

## Document Metadata
- **Feature**: TUI/Terminal Formatting for Rich Output
- **Status**: Ready for Implementation
- **Author**: Backend Developer Agent
- **Created**: 2026-01-14

---

## 1. Overview

This document provides the complete implementation plan for the TUI Formatter feature, which produces rich ASCII/Unicode terminal graphics for debugging information.

### Scope
- `TUIFormatter` class with all formatting methods
- Integration with existing MCP tools
- Unit tests for all formatters

### Out of Scope
- ANSI color codes (plain ASCII for universal compatibility)
- DataFrame-specific formatting (separate feature)

---

## 2. Class Structure

### 2.1 TUIFormatter Class

```
src/pybugger_mcp/utils/tui_formatter.py
```

```python
"""Terminal UI formatting utilities for debug output.

Provides ASCII/Unicode box-drawn tables and diagrams for
stack traces, variables, scopes, and call chains.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TUIConfig:
    """Configuration for TUI formatting."""

    max_width: int = 100
    value_max_len: int = 50
    name_max_len: int = 30
    type_max_len: int = 20
    file_max_len: int = 40
    show_frame_ids: bool = False

    # Box drawing characters
    BOX_TL: str = "┌"  # Top-left
    BOX_TR: str = "┐"  # Top-right
    BOX_BL: str = "└"  # Bottom-left
    BOX_BR: str = "┘"  # Bottom-right
    BOX_H: str = "─"   # Horizontal
    BOX_V: str = "│"   # Vertical
    BOX_LT: str = "├"  # Left-tee
    BOX_RT: str = "┤"  # Right-tee
    BOX_TT: str = "┬"  # Top-tee
    BOX_BT: str = "┴"  # Bottom-tee
    BOX_X: str = "┼"   # Cross


class TUIFormatter:
    """Formats debug data as rich terminal output.

    Produces ASCII/Unicode box-drawn tables and diagrams
    for stack traces, variables, scopes, and call chains.

    Example:
        formatter = TUIFormatter()
        output = formatter.format_stack_trace(frames)
        print(output)
    """

    def __init__(self, config: TUIConfig | None = None):
        """Initialize the formatter.

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config or TUIConfig()

    # =========================================================================
    # Public Formatting Methods
    # =========================================================================

    def format_stack_trace(
        self,
        frames: list[dict[str, Any]],
        title: str = "STACK TRACE",
    ) -> str:
        """Format stack frames as a box-drawn table.

        Args:
            frames: List of stack frame dicts with keys:
                - id: int
                - name: str (function name)
                - file: str | None (file path)
                - line: int
                - column: int
            title: Title for the box header

        Returns:
            Box-drawn string representation of the stack trace.

        Example Output:
            ┌──────────────────────────────────────────────────────────┐
            │ STACK TRACE                                    3 frames │
            ├──────────────────────────────────────────────────────────┤
            │ #0  calculate_total        billing.py:45                │
            │ #1  process_order          orders.py:123                │
            │ #2  main                   app.py:50                    │
            └──────────────────────────────────────────────────────────┘
        """
        if not frames:
            return self._empty_box(title, "No frames available")

        # Calculate column widths
        widths = self._calculate_stack_widths(frames)
        inner_width = self.config.max_width - 4  # Account for "│ " and " │"

        lines: list[str] = []

        # Header
        header_text = f"{title}"
        frame_count = f"{len(frames)} frame{'s' if len(frames) != 1 else ''}"
        header_padding = inner_width - len(header_text) - len(frame_count)
        header = f"{header_text}{' ' * header_padding}{frame_count}"

        lines.append(self._box_top(inner_width))
        lines.append(self._box_row(header, inner_width))
        lines.append(self._box_separator(inner_width))

        # Frame rows
        for i, frame in enumerate(frames):
            frame_line = self._format_stack_frame(i, frame, widths, inner_width)
            lines.append(self._box_row(frame_line, inner_width))

        lines.append(self._box_bottom(inner_width))

        return "\n".join(lines)

    def format_variables(
        self,
        variables: list[dict[str, Any]],
        title: str = "VARIABLES",
    ) -> str:
        """Format variables as an aligned table.

        Args:
            variables: List of variable dicts with keys:
                - name: str
                - value: str
                - type: str | None
                - variables_reference: int
                - has_children: bool (optional)
            title: Title for the box header

        Returns:
            Box-drawn table of variables.

        Example Output:
            ┌────────────────────────────────────────────────────────────┐
            │ VARIABLES                                                  │
            ├──────────┬────────────┬────────────────────────────────────┤
            │ Name     │ Type       │ Value                              │
            ├──────────┼────────────┼────────────────────────────────────┤
            │ items    │ list       │ [100, 200, 300, 400, 500]          │
            │ total    │ int        │ 1500                               │
            │ tax_rate │ float      │ 0.08                               │
            └──────────┴────────────┴────────────────────────────────────┘
        """
        if not variables:
            return self._empty_box(title, "No variables available")

        # Calculate column widths
        col_widths = self._calculate_variable_widths(variables)
        inner_width = self.config.max_width - 4

        lines: list[str] = []

        # Title row
        lines.append(self._box_top(inner_width))
        lines.append(self._box_row(title, inner_width))

        # Column headers
        lines.append(self._table_separator(col_widths, "top"))
        header_row = self._table_row(["Name", "Type", "Value"], col_widths)
        lines.append(self._box_row(header_row, inner_width))
        lines.append(self._table_separator(col_widths, "middle"))

        # Variable rows
        for var in variables:
            name = self._truncate(var.get("name", ""), col_widths[0])
            type_str = self._truncate(var.get("type", "") or "", col_widths[1])
            value = self._truncate(var.get("value", ""), col_widths[2])

            # Add indicator for expandable variables
            if var.get("has_children") or var.get("variables_reference", 0) > 0:
                name = name.rstrip() + " ▸"
                name = self._truncate(name, col_widths[0])

            row = self._table_row([name, type_str, value], col_widths)
            lines.append(self._box_row(row, inner_width))

        lines.append(self._table_separator(col_widths, "bottom"))

        return "\n".join(lines)

    def format_scopes(
        self,
        scopes: list[dict[str, Any]],
        title: str = "SCOPES",
    ) -> str:
        """Format variable scopes as a table.

        Args:
            scopes: List of scope dicts with keys:
                - name: str
                - variables_reference: int
                - expensive: bool
            title: Title for the box header

        Returns:
            Box-drawn table of scopes.

        Example Output:
            ┌────────────────────────────────────────────────────────┐
            │ SCOPES                                                 │
            ├──────────────────┬────────────────────┬────────────────┤
            │ Scope            │ Reference          │ Expensive      │
            ├──────────────────┼────────────────────┼────────────────┤
            │ Locals           │ 1001               │ No             │
            │ Globals          │ 1002               │ Yes            │
            └──────────────────┴────────────────────┴────────────────┘
        """
        if not scopes:
            return self._empty_box(title, "No scopes available")

        inner_width = self.config.max_width - 4

        # Fixed column widths for scopes
        total_cols = inner_width - 4  # Account for " │ " separators
        col_widths = [total_cols // 3, total_cols // 3, total_cols - 2 * (total_cols // 3)]

        lines: list[str] = []

        # Title row
        lines.append(self._box_top(inner_width))
        lines.append(self._box_row(title, inner_width))

        # Column headers
        lines.append(self._table_separator(col_widths, "top"))
        header_row = self._table_row(["Scope", "Reference", "Expensive"], col_widths)
        lines.append(self._box_row(header_row, inner_width))
        lines.append(self._table_separator(col_widths, "middle"))

        # Scope rows
        for scope in scopes:
            name = self._truncate(scope.get("name", ""), col_widths[0])
            ref = str(scope.get("variables_reference", 0))
            expensive = "Yes" if scope.get("expensive", False) else "No"

            row = self._table_row([name, ref, expensive], col_widths)
            lines.append(self._box_row(row, inner_width))

        lines.append(self._table_separator(col_widths, "bottom"))

        return "\n".join(lines)

    def format_call_chain(
        self,
        frames: list[dict[str, Any]],
    ) -> str:
        """Format stack frames as a visual call chain.

        Shows the call flow from entry point to current location,
        with the current frame highlighted.

        Args:
            frames: List of stack frame dicts (same as format_stack_trace)

        Returns:
            ASCII art call chain diagram.

        Example Output:
            Call Chain:

            main (app.py:50)
              └─▶ process_order (orders.py:123)
                  └─▶ calculate_total (billing.py:45)  ◀── YOU ARE HERE
        """
        if not frames:
            return "Call Chain:\n\n  (no frames)"

        lines: list[str] = ["Call Chain:", ""]

        # Reverse frames to show call order (entry point first)
        reversed_frames = list(reversed(frames))

        for i, frame in enumerate(reversed_frames):
            indent = "  " + ("    " * i)
            func_name = frame.get("name", "<unknown>")
            file_name = self._get_short_filename(frame.get("file"))
            line = frame.get("line", 0)

            location = f"{func_name} ({file_name}:{line})"

            if i == 0:
                # Entry point - no arrow
                lines.append(f"{indent}{location}")
            else:
                # Subsequent calls - with arrow
                lines.append(f"{indent}└─▶ {location}")

            # Mark current frame (last in reversed = first in original)
            if i == len(reversed_frames) - 1:
                lines[-1] += "  ◀── YOU ARE HERE"

        return "\n".join(lines)

    # =========================================================================
    # Private Helper Methods - Box Drawing
    # =========================================================================

    def _box_top(self, width: int) -> str:
        """Create top border of a box.

        Args:
            width: Inner width of the box

        Returns:
            Top border string: ┌────────┐
        """
        c = self.config
        return f"{c.BOX_TL}{c.BOX_H * width}{c.BOX_TR}"

    def _box_bottom(self, width: int) -> str:
        """Create bottom border of a box.

        Args:
            width: Inner width of the box

        Returns:
            Bottom border string: └────────┘
        """
        c = self.config
        return f"{c.BOX_BL}{c.BOX_H * width}{c.BOX_BR}"

    def _box_separator(self, width: int) -> str:
        """Create horizontal separator inside a box.

        Args:
            width: Inner width of the box

        Returns:
            Separator string: ├────────┤
        """
        c = self.config
        return f"{c.BOX_LT}{c.BOX_H * width}{c.BOX_RT}"

    def _box_row(self, content: str, width: int) -> str:
        """Create a content row inside a box.

        Args:
            content: Text content for the row
            width: Inner width of the box

        Returns:
            Row string: │ content   │
        """
        c = self.config
        # Pad or truncate content to fit
        if len(content) > width:
            content = content[:width - 3] + "..."
        padded = content.ljust(width)
        return f"{c.BOX_V}{padded}{c.BOX_V}"

    def _empty_box(self, title: str, message: str) -> str:
        """Create an empty box with a message.

        Args:
            title: Box title
            message: Message to display

        Returns:
            Box with title and message
        """
        inner_width = self.config.max_width - 4
        lines = [
            self._box_top(inner_width),
            self._box_row(f" {title}", inner_width),
            self._box_separator(inner_width),
            self._box_row(f" {message}", inner_width),
            self._box_bottom(inner_width),
        ]
        return "\n".join(lines)

    # =========================================================================
    # Private Helper Methods - Table Drawing
    # =========================================================================

    def _table_separator(
        self,
        col_widths: list[int],
        position: str,
    ) -> str:
        """Create a table separator with column markers.

        Args:
            col_widths: List of column widths
            position: "top", "middle", or "bottom"

        Returns:
            Separator with appropriate junction characters
        """
        c = self.config

        if position == "top":
            left, mid, right = c.BOX_LT, c.BOX_TT, c.BOX_RT
        elif position == "middle":
            left, mid, right = c.BOX_LT, c.BOX_X, c.BOX_RT
        else:  # bottom
            left, mid, right = c.BOX_BL, c.BOX_BT, c.BOX_BR

        segments = [c.BOX_H * w for w in col_widths]
        inner = mid.join(segments)
        return f"{left}{inner}{right}"

    def _table_row(
        self,
        values: list[str],
        col_widths: list[int],
    ) -> str:
        """Create a table row with column separators.

        Args:
            values: List of cell values
            col_widths: List of column widths

        Returns:
            Row with values padded to column widths
        """
        c = self.config
        cells = []
        for i, (value, width) in enumerate(zip(values, col_widths)):
            cell = value.ljust(width)[:width]
            cells.append(cell)
        return f"{c.BOX_V}".join(cells)

    # =========================================================================
    # Private Helper Methods - Width Calculation
    # =========================================================================

    def _calculate_stack_widths(
        self,
        frames: list[dict[str, Any]],
    ) -> dict[str, int]:
        """Calculate column widths for stack trace display.

        Args:
            frames: List of stack frames

        Returns:
            Dict with 'index', 'name', 'location' widths
        """
        # Index column: "#XX  " = 5 chars
        index_width = 5

        # Calculate max function name length
        max_name = max(
            len(frame.get("name", "")) for frame in frames
        ) if frames else 10
        name_width = min(max_name, self.config.name_max_len)

        # Remaining space for location
        inner_width = self.config.max_width - 4
        location_width = inner_width - index_width - name_width - 4  # padding

        return {
            "index": index_width,
            "name": name_width,
            "location": location_width,
        }

    def _calculate_variable_widths(
        self,
        variables: list[dict[str, Any]],
    ) -> list[int]:
        """Calculate column widths for variable table.

        Uses dynamic sizing based on content, with max limits.

        Args:
            variables: List of variables

        Returns:
            List of [name_width, type_width, value_width]
        """
        inner_width = self.config.max_width - 4

        # Calculate content-based widths
        max_name = max(
            len(v.get("name", "")) for v in variables
        ) if variables else 8
        max_type = max(
            len(v.get("type", "") or "") for v in variables
        ) if variables else 8

        # Apply limits
        name_width = min(max_name + 2, self.config.name_max_len)  # +2 for " ▸"
        type_width = min(max_type + 1, self.config.type_max_len)

        # Value gets remaining space (minus separators: 2 " │ ")
        value_width = inner_width - name_width - type_width - 4
        value_width = max(value_width, 20)  # Minimum value column width

        return [name_width, type_width, value_width]

    # =========================================================================
    # Private Helper Methods - Text Processing
    # =========================================================================

    def _truncate(self, text: str, max_len: int) -> str:
        """Truncate text with ellipsis if too long.

        Args:
            text: Text to truncate
            max_len: Maximum length

        Returns:
            Truncated text with "..." if needed
        """
        if len(text) <= max_len:
            return text
        if max_len <= 3:
            return text[:max_len]
        return text[:max_len - 3] + "..."

    def _get_short_filename(self, path: str | None) -> str:
        """Extract filename from full path.

        Args:
            path: Full file path or None

        Returns:
            Just the filename, or "<unknown>" if None
        """
        if not path:
            return "<unknown>"
        # Handle both Unix and Windows paths
        parts = path.replace("\\", "/").split("/")
        return parts[-1] if parts else "<unknown>"

    def _format_stack_frame(
        self,
        index: int,
        frame: dict[str, Any],
        widths: dict[str, int],
        total_width: int,
    ) -> str:
        """Format a single stack frame as a row.

        Args:
            index: Frame index (0 = current)
            frame: Frame dict
            widths: Column widths from _calculate_stack_widths
            total_width: Total available width

        Returns:
            Formatted frame string
        """
        # Index
        idx_str = f"#{index}".ljust(widths["index"])

        # Function name
        name = self._truncate(frame.get("name", ""), widths["name"])
        name_str = name.ljust(widths["name"])

        # Location (file:line)
        file_name = self._get_short_filename(frame.get("file"))
        line = frame.get("line", 0)
        location = f"{file_name}:{line}"
        location = self._truncate(location, widths["location"])

        # Combine with spacing
        result = f" {idx_str} {name_str}  {location}"
        return result.ljust(total_width)[:total_width]


# =============================================================================
# Module-level convenience instance
# =============================================================================

# Default formatter instance for simple usage
_default_formatter: TUIFormatter | None = None


def get_formatter(config: TUIConfig | None = None) -> TUIFormatter:
    """Get a TUIFormatter instance.

    Args:
        config: Optional configuration. If None, returns cached default.

    Returns:
        TUIFormatter instance
    """
    global _default_formatter
    if config is not None:
        return TUIFormatter(config)
    if _default_formatter is None:
        _default_formatter = TUIFormatter()
    return _default_formatter


def format_stack_trace(
    frames: list[dict[str, Any]],
    title: str = "STACK TRACE",
) -> str:
    """Convenience function to format stack trace.

    Args:
        frames: List of stack frame dicts
        title: Box title

    Returns:
        Formatted stack trace string
    """
    return get_formatter().format_stack_trace(frames, title)


def format_variables(
    variables: list[dict[str, Any]],
    title: str = "VARIABLES",
) -> str:
    """Convenience function to format variables.

    Args:
        variables: List of variable dicts
        title: Box title

    Returns:
        Formatted variables table string
    """
    return get_formatter().format_variables(variables, title)


def format_scopes(
    scopes: list[dict[str, Any]],
    title: str = "SCOPES",
) -> str:
    """Convenience function to format scopes.

    Args:
        scopes: List of scope dicts
        title: Box title

    Returns:
        Formatted scopes table string
    """
    return get_formatter().format_scopes(scopes, title)


def format_call_chain(frames: list[dict[str, Any]]) -> str:
    """Convenience function to format call chain.

    Args:
        frames: List of stack frame dicts

    Returns:
        Formatted call chain string
    """
    return get_formatter().format_call_chain(frames)
```

---

## 3. Method Signatures Summary

| Method | Signature | Description |
|--------|-----------|-------------|
| `__init__` | `(config: TUIConfig \| None = None) -> None` | Initialize with optional config |
| `format_stack_trace` | `(frames: list[dict], title: str = "STACK TRACE") -> str` | Format stack as box table |
| `format_variables` | `(variables: list[dict], title: str = "VARIABLES") -> str` | Format vars as aligned table |
| `format_scopes` | `(scopes: list[dict], title: str = "SCOPES") -> str` | Format scopes as table |
| `format_call_chain` | `(frames: list[dict]) -> str` | Format as ASCII call flow |
| `_box_top` | `(width: int) -> str` | Create `┌───┐` line |
| `_box_bottom` | `(width: int) -> str` | Create `└───┘` line |
| `_box_separator` | `(width: int) -> str` | Create `├───┤` line |
| `_box_row` | `(content: str, width: int) -> str` | Create `│ content │` line |
| `_empty_box` | `(title: str, message: str) -> str` | Create box with message |
| `_table_separator` | `(col_widths: list[int], position: str) -> str` | Create `├──┬──┤` with columns |
| `_table_row` | `(values: list[str], col_widths: list[int]) -> str` | Create `val│val│val` |
| `_calculate_stack_widths` | `(frames: list[dict]) -> dict[str, int]` | Calculate stack column widths |
| `_calculate_variable_widths` | `(variables: list[dict]) -> list[int]` | Calculate variable column widths |
| `_truncate` | `(text: str, max_len: int) -> str` | Truncate with `...` |
| `_get_short_filename` | `(path: str \| None) -> str` | Extract filename from path |
| `_format_stack_frame` | `(index: int, frame: dict, widths: dict, total_width: int) -> str` | Format single frame |

---

## 4. Algorithm Details

### 4.1 Column Width Calculation

**Stack Trace Columns:**
```
Total width: config.max_width (default 100)
Inner width: max_width - 4 (for │ and │ borders)

Layout:
│ #0  function_name     file.py:123                           │
  ^^^  ^^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  5    name_width       remaining (location)

1. index_width = 5 (fixed for "#XX  ")
2. name_width = min(max_func_name_len, config.name_max_len)
3. location_width = inner_width - index_width - name_width - 4
```

**Variable Table Columns:**
```
│ Name     │ Type       │ Value                              │
  ^^^^^^^^   ^^^^^^^^^^   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  name_w     type_w       value_w (remaining)

1. name_width = min(max_name_len + 2, config.name_max_len)
   - +2 for potential " ▸" expand indicator
2. type_width = min(max_type_len + 1, config.type_max_len)
3. value_width = inner_width - name_width - type_width - 4
   - -4 for column separators
```

### 4.2 Truncation Algorithm

```python
def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text           # No truncation needed
    if max_len <= 3:
        return text[:max_len] # Too short for ellipsis
    return text[:max_len - 3] + "..."
```

**Examples:**
- `"hello"` with max_len=10 → `"hello"`
- `"hello world"` with max_len=8 → `"hello..."`
- `"hi"` with max_len=2 → `"hi"`

### 4.3 Box Building Algorithm

```python
def build_box(title: str, rows: list[str]) -> str:
    """Pseudocode for box construction."""
    inner_width = config.max_width - 4

    lines = []
    lines.append(f"┌{'─' * inner_width}┐")           # Top
    lines.append(f"│{title.ljust(inner_width)}│")    # Title
    lines.append(f"├{'─' * inner_width}┤")           # Separator

    for row in rows:
        padded = row.ljust(inner_width)[:inner_width]
        lines.append(f"│{padded}│")                  # Content rows

    lines.append(f"└{'─' * inner_width}┘")           # Bottom

    return "\n".join(lines)
```

### 4.4 Table Building Algorithm

```python
def build_table(headers: list[str], rows: list[list[str]], col_widths: list[int]) -> str:
    """Pseudocode for table construction."""
    lines = []

    # Header separator: ├──────┬──────┬──────┤
    lines.append(make_separator(col_widths, "top"))

    # Header row: │ Name │ Type │ Value │
    lines.append(make_row(headers, col_widths))

    # Middle separator: ├──────┼──────┼──────┤
    lines.append(make_separator(col_widths, "middle"))

    # Data rows
    for row in rows:
        lines.append(make_row(row, col_widths))

    # Bottom separator: └──────┴──────┴──────┘
    lines.append(make_separator(col_widths, "bottom"))

    return "\n".join(lines)
```

---

## 5. Example Outputs

### 5.1 Stack Trace Output

**Input:**
```python
frames = [
    {"id": 1, "name": "calculate_total", "file": "/app/billing.py", "line": 45, "column": 0},
    {"id": 2, "name": "process_order", "file": "/app/orders.py", "line": 123, "column": 0},
    {"id": 3, "name": "main", "file": "/app/main.py", "line": 50, "column": 0},
]
output = formatter.format_stack_trace(frames)
```

**Output:**
```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│ STACK TRACE                                                                          3 frames │
├────────────────────────────────────────────────────────────────────────────────────────────────┤
│ #0   calculate_total                    billing.py:45                                         │
│ #1   process_order                      orders.py:123                                         │
│ #2   main                               main.py:50                                            │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Variables Output

**Input:**
```python
variables = [
    {"name": "items", "value": "[100, 200, 300, 400, 500]", "type": "list", "variables_reference": 101},
    {"name": "total", "value": "1500", "type": "int", "variables_reference": 0},
    {"name": "tax_rate", "value": "0.08", "type": "float", "variables_reference": 0},
    {"name": "config", "value": "{'debug': True, 'env': 'dev'}", "type": "dict", "variables_reference": 102},
]
output = formatter.format_variables(variables)
```

**Output:**
```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│ VARIABLES                                                                                      │
├────────────┬────────────┬──────────────────────────────────────────────────────────────────────┤
│ Name       │ Type       │ Value                                                                │
├────────────┼────────────┼──────────────────────────────────────────────────────────────────────┤
│ items ▸    │ list       │ [100, 200, 300, 400, 500]                                            │
│ total      │ int        │ 1500                                                                 │
│ tax_rate   │ float      │ 0.08                                                                 │
│ config ▸   │ dict       │ {'debug': True, 'env': 'dev'}                                        │
└────────────┴────────────┴──────────────────────────────────────────────────────────────────────┘
```

### 5.3 Scopes Output

**Input:**
```python
scopes = [
    {"name": "Locals", "variables_reference": 1001, "expensive": False},
    {"name": "Globals", "variables_reference": 1002, "expensive": True},
]
output = formatter.format_scopes(scopes)
```

**Output:**
```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│ SCOPES                                                                                         │
├──────────────────────────────────┬──────────────────────────────────┬──────────────────────────┤
│ Scope                            │ Reference                        │ Expensive                │
├──────────────────────────────────┼──────────────────────────────────┼──────────────────────────┤
│ Locals                           │ 1001                             │ No                       │
│ Globals                          │ 1002                             │ Yes                      │
└──────────────────────────────────┴──────────────────────────────────┴──────────────────────────┘
```

### 5.4 Call Chain Output

**Input:**
```python
frames = [
    {"id": 1, "name": "calculate_total", "file": "/app/billing.py", "line": 45, "column": 0},
    {"id": 2, "name": "process_order", "file": "/app/orders.py", "line": 123, "column": 0},
    {"id": 3, "name": "main", "file": "/app/main.py", "line": 50, "column": 0},
]
output = formatter.format_call_chain(frames)
```

**Output:**
```
Call Chain:

main (main.py:50)
  └─▶ process_order (orders.py:123)
      └─▶ calculate_total (billing.py:45)  ◀── YOU ARE HERE
```

---

## 6. Integration with MCP Server

### 6.1 Import Statement

Add to `mcp_server.py` imports:

```python
from pybugger_mcp.utils.tui_formatter import TUIFormatter, TUIConfig
```

### 6.2 Formatter Instance

Add after the `_session_manager` global:

```python
# Global formatter (initialized lazily)
_tui_formatter: TUIFormatter | None = None


def _get_formatter() -> TUIFormatter:
    """Get the TUI formatter instance."""
    global _tui_formatter
    if _tui_formatter is None:
        _tui_formatter = TUIFormatter()
    return _tui_formatter
```

### 6.3 Modified Tool: `debug_get_stacktrace`

```python
@mcp.tool()
async def debug_get_stacktrace(
    session_id: str,
    thread_id: int | None = None,
    max_frames: int = 20,
    format: str = "json",  # NEW: "json" | "tui"
) -> dict[str, Any]:
    """Get the call stack when paused.

    Args:
        session_id: The debug session ID
        thread_id: Thread to get stack for (uses current thread if not specified)
        max_frames: Maximum number of frames to return
        format: Output format - "json" (default) or "tui" for ASCII art

    Returns:
        Stack frames with file, line, and function information.
        If format="tui", includes "formatted" key with ASCII art.
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)
        frames = await session.get_stack_trace(thread_id, levels=max_frames)

        frame_dicts = [
            {
                "id": f.id,
                "name": f.name,
                "file": f.source.path if f.source else None,
                "line": f.line,
                "column": f.column,
            }
            for f in frames
        ]

        result: dict[str, Any] = {
            "frames": frame_dicts,
            "total": len(frames),
        }

        # Add TUI formatting if requested
        if format == "tui":
            formatter = _get_formatter()
            result["formatted"] = formatter.format_stack_trace(frame_dicts)
            result["call_chain"] = formatter.format_call_chain(frame_dicts)
            result["format"] = "tui"

        return result
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}
```

### 6.4 Modified Tool: `debug_get_variables`

```python
@mcp.tool()
async def debug_get_variables(
    session_id: str,
    variables_reference: int,
    max_count: int = 100,
    format: str = "json",  # NEW: "json" | "tui"
) -> dict[str, Any]:
    """Get variables for a scope or compound variable.

    Args:
        session_id: The debug session ID
        variables_reference: Reference from debug_get_scopes or nested variable
        max_count: Maximum variables to return
        format: Output format - "json" (default) or "tui" for ASCII art

    Returns:
        List of variables with names, values, and types.
        If format="tui", includes "formatted" key with ASCII table.
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)
        variables = await session.get_variables(variables_reference, count=max_count)

        var_dicts = [
            {
                "name": v.name,
                "value": v.value,
                "type": v.type,
                "variables_reference": v.variables_reference,
                "has_children": v.variables_reference > 0,
            }
            for v in variables
        ]

        result: dict[str, Any] = {"variables": var_dicts}

        # Add TUI formatting if requested
        if format == "tui":
            formatter = _get_formatter()
            result["formatted"] = formatter.format_variables(var_dicts)
            result["format"] = "tui"

        return result
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}
```

### 6.5 Modified Tool: `debug_get_scopes`

```python
@mcp.tool()
async def debug_get_scopes(
    session_id: str,
    frame_id: int,
    format: str = "json",  # NEW: "json" | "tui"
) -> dict[str, Any]:
    """Get variable scopes (locals, globals) for a stack frame.

    Args:
        session_id: The debug session ID
        frame_id: Frame ID from debug_get_stacktrace
        format: Output format - "json" (default) or "tui" for ASCII art

    Returns:
        List of scopes with their variables_reference for fetching variables.
        If format="tui", includes "formatted" key with ASCII table.
    """
    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)
        scopes = await session.get_scopes(frame_id)

        scope_dicts = [
            {
                "name": s.name,
                "variables_reference": s.variables_reference,
                "expensive": s.expensive,
            }
            for s in scopes
        ]

        result: dict[str, Any] = {"scopes": scope_dicts}

        # Add TUI formatting if requested
        if format == "tui":
            formatter = _get_formatter()
            result["formatted"] = formatter.format_scopes(scope_dicts)
            result["format"] = "tui"

        return result
    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}
```

---

## 7. Unit Tests

### 7.1 Test File

```
tests/unit/test_tui_formatter.py
```

```python
"""Unit tests for TUI formatter."""

import pytest

from pybugger_mcp.utils.tui_formatter import (
    TUIFormatter,
    TUIConfig,
    format_stack_trace,
    format_variables,
    format_scopes,
    format_call_chain,
)


class TestTUIConfig:
    """Test TUIConfig dataclass."""

    def test_default_values(self):
        config = TUIConfig()
        assert config.max_width == 100
        assert config.value_max_len == 50
        assert config.name_max_len == 30
        assert config.BOX_TL == "┌"

    def test_custom_values(self):
        config = TUIConfig(max_width=80, value_max_len=30)
        assert config.max_width == 80
        assert config.value_max_len == 30


class TestTUIFormatter:
    """Test TUIFormatter class."""

    @pytest.fixture
    def formatter(self):
        return TUIFormatter()

    @pytest.fixture
    def sample_frames(self):
        return [
            {"id": 1, "name": "calculate_total", "file": "/app/billing.py", "line": 45, "column": 0},
            {"id": 2, "name": "process_order", "file": "/app/orders.py", "line": 123, "column": 0},
            {"id": 3, "name": "main", "file": "/app/main.py", "line": 50, "column": 0},
        ]

    @pytest.fixture
    def sample_variables(self):
        return [
            {"name": "items", "value": "[1, 2, 3]", "type": "list", "variables_reference": 101},
            {"name": "total", "value": "1500", "type": "int", "variables_reference": 0},
            {"name": "tax_rate", "value": "0.08", "type": "float", "variables_reference": 0},
        ]

    @pytest.fixture
    def sample_scopes(self):
        return [
            {"name": "Locals", "variables_reference": 1001, "expensive": False},
            {"name": "Globals", "variables_reference": 1002, "expensive": True},
        ]

    # =========================================================================
    # Stack Trace Tests
    # =========================================================================

    def test_format_stack_trace_basic(self, formatter, sample_frames):
        result = formatter.format_stack_trace(sample_frames)

        # Should contain box characters
        assert "┌" in result
        assert "└" in result
        assert "│" in result

        # Should contain title
        assert "STACK TRACE" in result
        assert "3 frames" in result

        # Should contain frame info
        assert "calculate_total" in result
        assert "billing.py:45" in result
        assert "#0" in result

    def test_format_stack_trace_empty(self, formatter):
        result = formatter.format_stack_trace([])
        assert "No frames available" in result

    def test_format_stack_trace_custom_title(self, formatter, sample_frames):
        result = formatter.format_stack_trace(sample_frames, title="CALL STACK")
        assert "CALL STACK" in result

    def test_format_stack_trace_truncates_long_names(self, formatter):
        frames = [
            {"id": 1, "name": "a" * 100, "file": "/path/file.py", "line": 1, "column": 0},
        ]
        result = formatter.format_stack_trace(frames)
        # Name should be truncated (not contain 100 'a's)
        assert "a" * 50 not in result

    def test_format_stack_trace_handles_missing_file(self, formatter):
        frames = [
            {"id": 1, "name": "test_func", "file": None, "line": 1, "column": 0},
        ]
        result = formatter.format_stack_trace(frames)
        assert "<unknown>" in result

    # =========================================================================
    # Variables Tests
    # =========================================================================

    def test_format_variables_basic(self, formatter, sample_variables):
        result = formatter.format_variables(sample_variables)

        # Should contain table structure
        assert "┌" in result
        assert "┼" in result  # Column intersection

        # Should contain headers
        assert "Name" in result
        assert "Type" in result
        assert "Value" in result

        # Should contain data
        assert "items" in result
        assert "list" in result
        assert "[1, 2, 3]" in result

    def test_format_variables_empty(self, formatter):
        result = formatter.format_variables([])
        assert "No variables available" in result

    def test_format_variables_expandable_indicator(self, formatter):
        variables = [
            {"name": "obj", "value": "{...}", "type": "dict", "variables_reference": 100},
        ]
        result = formatter.format_variables(variables)
        # Should show expand indicator
        assert "▸" in result

    def test_format_variables_custom_title(self, formatter, sample_variables):
        result = formatter.format_variables(sample_variables, title="LOCAL VARS")
        assert "LOCAL VARS" in result

    def test_format_variables_truncates_long_values(self, formatter):
        variables = [
            {"name": "x", "value": "a" * 200, "type": "str", "variables_reference": 0},
        ]
        result = formatter.format_variables(variables)
        assert "..." in result

    # =========================================================================
    # Scopes Tests
    # =========================================================================

    def test_format_scopes_basic(self, formatter, sample_scopes):
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

    def test_format_scopes_empty(self, formatter):
        result = formatter.format_scopes([])
        assert "No scopes available" in result

    # =========================================================================
    # Call Chain Tests
    # =========================================================================

    def test_format_call_chain_basic(self, formatter, sample_frames):
        result = formatter.format_call_chain(sample_frames)

        # Should show call flow
        assert "Call Chain:" in result
        assert "main" in result
        assert "process_order" in result
        assert "calculate_total" in result

        # Should show arrows and current indicator
        assert "└─▶" in result
        assert "YOU ARE HERE" in result

    def test_format_call_chain_empty(self, formatter):
        result = formatter.format_call_chain([])
        assert "(no frames)" in result

    def test_format_call_chain_single_frame(self, formatter):
        frames = [
            {"id": 1, "name": "main", "file": "/app/main.py", "line": 10, "column": 0},
        ]
        result = formatter.format_call_chain(frames)
        assert "main" in result
        assert "YOU ARE HERE" in result

    # =========================================================================
    # Helper Method Tests
    # =========================================================================

    def test_truncate_no_truncation_needed(self, formatter):
        result = formatter._truncate("hello", 10)
        assert result == "hello"

    def test_truncate_with_ellipsis(self, formatter):
        result = formatter._truncate("hello world", 8)
        assert result == "hello..."

    def test_truncate_very_short_max(self, formatter):
        result = formatter._truncate("hello", 2)
        assert result == "he"

    def test_get_short_filename_unix_path(self, formatter):
        result = formatter._get_short_filename("/path/to/file.py")
        assert result == "file.py"

    def test_get_short_filename_windows_path(self, formatter):
        result = formatter._get_short_filename("C:\\Users\\test\\file.py")
        assert result == "file.py"

    def test_get_short_filename_none(self, formatter):
        result = formatter._get_short_filename(None)
        assert result == "<unknown>"

    def test_box_top(self, formatter):
        result = formatter._box_top(10)
        assert result == "┌──────────┐"

    def test_box_bottom(self, formatter):
        result = formatter._box_bottom(10)
        assert result == "└──────────┘"

    def test_box_separator(self, formatter):
        result = formatter._box_separator(10)
        assert result == "├──────────┤"

    def test_box_row(self, formatter):
        result = formatter._box_row("test", 10)
        assert result == "│test      │"

    def test_box_row_truncates(self, formatter):
        result = formatter._box_row("a" * 20, 10)
        assert len(result) == 12  # 10 + 2 borders
        assert "..." in result


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    def test_format_stack_trace(self):
        frames = [{"id": 1, "name": "test", "file": "test.py", "line": 1, "column": 0}]
        result = format_stack_trace(frames)
        assert "STACK TRACE" in result

    def test_format_variables(self):
        variables = [{"name": "x", "value": "1", "type": "int", "variables_reference": 0}]
        result = format_variables(variables)
        assert "VARIABLES" in result

    def test_format_scopes(self):
        scopes = [{"name": "Locals", "variables_reference": 1, "expensive": False}]
        result = format_scopes(scopes)
        assert "SCOPES" in result

    def test_format_call_chain(self):
        frames = [{"id": 1, "name": "main", "file": "main.py", "line": 1, "column": 0}]
        result = format_call_chain(frames)
        assert "Call Chain:" in result


class TestCustomConfig:
    """Test TUIFormatter with custom configuration."""

    def test_narrow_width(self):
        config = TUIConfig(max_width=60)
        formatter = TUIFormatter(config)

        frames = [{"id": 1, "name": "test", "file": "test.py", "line": 1, "column": 0}]
        result = formatter.format_stack_trace(frames)

        # Each line should be at most 60 characters
        for line in result.split("\n"):
            assert len(line) <= 60

    def test_short_value_truncation(self):
        config = TUIConfig(value_max_len=10)
        formatter = TUIFormatter(config)

        variables = [
            {"name": "x", "value": "a" * 50, "type": "str", "variables_reference": 0},
        ]
        result = formatter.format_variables(variables)

        # Value should be truncated
        assert "a" * 50 not in result
```

---

## 8. File Changes Summary

### 8.1 Files to Create

| File | Purpose |
|------|---------|
| `src/pybugger_mcp/utils/tui_formatter.py` | TUIFormatter class and helpers |
| `tests/unit/test_tui_formatter.py` | Unit tests for formatter |

### 8.2 Files to Modify

| File | Changes |
|------|---------|
| `src/pybugger_mcp/utils/__init__.py` | Export TUIFormatter |
| `src/pybugger_mcp/mcp_server.py` | Add `format` param to 3 tools |

### 8.3 Detailed Change List

#### `src/pybugger_mcp/utils/__init__.py`

**Current (line 1-2):**
```python
"""Utility modules - output buffer, helpers."""

```

**New:**
```python
"""Utility modules - output buffer, TUI formatter, helpers."""

from pybugger_mcp.utils.tui_formatter import (
    TUIFormatter,
    TUIConfig,
    format_stack_trace,
    format_variables,
    format_scopes,
    format_call_chain,
)

__all__ = [
    "TUIFormatter",
    "TUIConfig",
    "format_stack_trace",
    "format_variables",
    "format_scopes",
    "format_call_chain",
]
```

#### `src/pybugger_mcp/mcp_server.py`

**Add import after line 28:**
```python
from pybugger_mcp.utils.tui_formatter import TUIFormatter
```

**Add after line 33 (_session_manager):**
```python
# TUI formatter for rich output
_tui_formatter: TUIFormatter | None = None


def _get_formatter() -> TUIFormatter:
    """Get the TUI formatter instance."""
    global _tui_formatter
    if _tui_formatter is None:
        _tui_formatter = TUIFormatter()
    return _tui_formatter
```

**Modify `debug_get_stacktrace` (lines 496-528):**
- Add `format: str = "json"` parameter
- Add TUI formatting logic before return

**Modify `debug_get_scopes` (lines 533-562):**
- Add `format: str = "json"` parameter
- Add TUI formatting logic before return

**Modify `debug_get_variables` (lines 565-598):**
- Add `format: str = "json"` parameter
- Add TUI formatting logic before return

---

## 9. Implementation Order

1. **Create `tui_formatter.py`** with full implementation
2. **Create `test_tui_formatter.py`** and run tests
3. **Update `utils/__init__.py`** exports
4. **Update `mcp_server.py`** with format parameter
5. **Run full test suite** to ensure no regressions

---

## 10. Acceptance Criteria

- [ ] `TUIFormatter` class implemented with all 4 public methods
- [ ] All private helper methods working correctly
- [ ] `TUIConfig` allows customization of widths and limits
- [ ] Empty data cases handled gracefully
- [ ] Long values/names truncated with "..."
- [ ] Expandable variables marked with "▸"
- [ ] Unit tests achieve >90% coverage of formatter module
- [ ] `format="tui"` parameter works on `debug_get_stacktrace`
- [ ] `format="tui"` parameter works on `debug_get_variables`
- [ ] `format="tui"` parameter works on `debug_get_scopes`
- [ ] Existing tests pass (no regressions)

---

## 11. Future Enhancements (Out of Scope)

- ANSI color codes for terminal highlighting
- Markdown output format option
- DataFrame-specific formatting (separate feature)
- Configurable box drawing style (double-line, rounded)
- Source code context in stack trace

---

*End of Low-Level Design Document*
