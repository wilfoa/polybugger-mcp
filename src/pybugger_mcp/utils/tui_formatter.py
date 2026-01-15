"""Terminal UI formatting utilities for debug output.

Provides ASCII/Unicode box-drawn tables and diagrams for
stack traces, variables, scopes, and call chains.
"""

from dataclasses import dataclass
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
    BOX_H: str = "─"  # Horizontal
    BOX_V: str = "│"  # Vertical
    BOX_LT: str = "├"  # Left-tee
    BOX_RT: str = "┤"  # Right-tee
    BOX_TT: str = "┬"  # Top-tee
    BOX_BT: str = "┴"  # Bottom-tee
    BOX_X: str = "┼"  # Cross


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
        inner_width = self.config.max_width - 2  # Account for borders

        lines: list[str] = []

        # Header
        header_text = f" {title}"
        frame_count = f"{len(frames)} frame{'s' if len(frames) != 1 else ''} "
        header_padding = inner_width - len(header_text) - len(frame_count)
        header = f"{header_text}{' ' * max(0, header_padding)}{frame_count}"

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
        inner_width = self.config.max_width - 2

        lines: list[str] = []

        # Title row
        lines.append(self._box_top(inner_width))
        lines.append(self._box_row(f" {title}", inner_width))

        # Column headers
        lines.append(self._table_separator(col_widths, "top"))
        header_row = self._table_row(["Name", "Type", "Value"], col_widths)
        lines.append(self._box_row(header_row, inner_width))
        lines.append(self._table_separator(col_widths, "middle"))

        # Variable rows
        for var in variables:
            name = self._truncate(var.get("name", ""), col_widths[0] - 1)
            type_str = self._truncate(var.get("type", "") or "", col_widths[1] - 1)
            value = self._truncate(var.get("value", ""), col_widths[2] - 1)

            # Add indicator for expandable variables
            if var.get("has_children") or var.get("variables_reference", 0) > 0:
                if len(name) < col_widths[0] - 3:
                    name = name + " ▸"

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

        inner_width = self.config.max_width - 2

        # Fixed column widths for scopes
        total_cols = inner_width - 4  # Account for separators
        col_widths = [
            total_cols // 3,
            total_cols // 3,
            total_cols - 2 * (total_cols // 3),
        ]

        lines: list[str] = []

        # Title row
        lines.append(self._box_top(inner_width))
        lines.append(self._box_row(f" {title}", inner_width))

        # Column headers
        lines.append(self._table_separator(col_widths, "top"))
        header_row = self._table_row(["Scope", "Reference", "Expensive"], col_widths)
        lines.append(self._box_row(header_row, inner_width))
        lines.append(self._table_separator(col_widths, "middle"))

        # Scope rows
        for scope in scopes:
            name = self._truncate(scope.get("name", ""), col_widths[0] - 1)
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
            content = content[: width - 3] + "..."
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
        inner_width = self.config.max_width - 2
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
        for value, width in zip(values, col_widths):
            cell = f" {value}".ljust(width)[:width]
            cells.append(cell)
        return c.BOX_V.join(cells)

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
        max_name = max(len(frame.get("name", "")) for frame in frames) if frames else 10
        name_width = min(max_name, self.config.name_max_len)

        # Remaining space for location
        inner_width = self.config.max_width - 2
        location_width = inner_width - index_width - name_width - 6  # padding

        return {
            "index": index_width,
            "name": name_width,
            "location": max(location_width, 20),
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
        inner_width = self.config.max_width - 2

        # Calculate content-based widths
        max_name = max(len(v.get("name", "")) for v in variables) if variables else 8
        max_type = max(len(v.get("type", "") or "") for v in variables) if variables else 8

        # Apply limits
        name_width = min(max_name + 4, self.config.name_max_len)  # +4 for " ▸" and padding
        type_width = min(max_type + 2, self.config.type_max_len)

        # Value gets remaining space (minus separators)
        value_width = inner_width - name_width - type_width - 2
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
        return text[: max_len - 3] + "..."

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
