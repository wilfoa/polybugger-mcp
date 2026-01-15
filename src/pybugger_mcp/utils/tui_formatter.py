"""Terminal UI formatting utilities for debug output.

Provides ASCII/Unicode box-drawn tables and diagrams for
stack traces, variables, scopes, and call chains.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class TUIConfig:
    """Configuration for TUI formatting."""

    max_width: int = 80
    value_max_len: int = 40
    name_max_len: int = 25
    type_max_len: int = 15
    file_max_len: int = 30
    show_frame_ids: bool = False

    # Summarization limits (0 = no limit)
    max_variables: int = 15
    max_frames: int = 10
    max_source_lines: int = 5

    # Use ASCII instead of Unicode box drawing (better tokenization)
    ascii_mode: bool = True

    # Box drawing characters (set by __post_init__ based on ascii_mode)
    BOX_TL: str = "+"
    BOX_TR: str = "+"
    BOX_BL: str = "+"
    BOX_BR: str = "+"
    BOX_H: str = "-"
    BOX_V: str = "|"
    BOX_LT: str = "+"
    BOX_RT: str = "+"
    BOX_TT: str = "+"
    BOX_BT: str = "+"
    BOX_X: str = "+"

    def __post_init__(self) -> None:
        """Set box characters based on ascii_mode."""
        if not self.ascii_mode:
            # Unicode box drawing (prettier but more tokens)
            self.BOX_TL = "┌"
            self.BOX_TR = "┐"
            self.BOX_BL = "└"
            self.BOX_BR = "┘"
            self.BOX_H = "─"
            self.BOX_V = "│"
            self.BOX_LT = "├"
            self.BOX_RT = "┤"
            self.BOX_TT = "┬"
            self.BOX_BT = "┴"
            self.BOX_X = "┼"


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

        # Apply summarization limit
        total_count = len(frames)
        truncated = False
        if self.config.max_frames > 0 and total_count > self.config.max_frames:
            # Keep first few and last few frames
            half = self.config.max_frames // 2
            frames = frames[:half] + frames[-(self.config.max_frames - half) :]
            truncated = True

        # Calculate column widths
        widths = self._calculate_stack_widths(frames)
        inner_width = self.config.max_width - 2  # Account for borders

        lines: list[str] = []

        # Header
        header_text = f" {title}"
        count_str = (
            f"{total_count} frames" if not truncated else f"{len(frames)}/{total_count} frames"
        )
        header_padding = inner_width - len(header_text) - len(count_str) - 1
        header = f"{header_text}{' ' * max(0, header_padding)}{count_str} "

        lines.append(self._box_top(inner_width))
        lines.append(self._box_row(header, inner_width))
        lines.append(self._box_separator(inner_width))

        # Frame rows
        for i, frame in enumerate(frames):
            frame_line = self._format_stack_frame(i, frame, widths, inner_width)
            lines.append(self._box_row(frame_line, inner_width))
            # Add truncation indicator after first half
            if truncated and i == (self.config.max_frames // 2) - 1:
                omitted = total_count - len(frames)
                lines.append(self._box_row(f" ... {omitted} frames omitted ...", inner_width))

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

        # Apply summarization limit
        total_count = len(variables)
        truncated = False
        if self.config.max_variables > 0 and total_count > self.config.max_variables:
            variables = variables[: self.config.max_variables]
            truncated = True

        # Calculate column widths
        col_widths = self._calculate_variable_widths(variables)
        inner_width = self.config.max_width - 2

        lines: list[str] = []

        # Title row with count
        count_str = f"{total_count} vars" if not truncated else f"{len(variables)}/{total_count}"
        title_line = f" {title} ({count_str})"
        lines.append(self._box_top(inner_width))
        lines.append(self._box_row(title_line, inner_width))

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

            # Add indicator for expandable variables (use ASCII arrow)
            if var.get("has_children") or var.get("variables_reference", 0) > 0:
                if len(name) < col_widths[0] - 3:
                    name = name + " >"

            row = self._table_row([name, type_str, value], col_widths)
            lines.append(self._box_row(row, inner_width))

        # Add truncation notice
        if truncated:
            omitted = total_count - len(variables)
            lines.append(self._box_row(f" ... {omitted} more variables omitted", inner_width))

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

    def format_call_chain_with_context(
        self,
        call_chain: list[dict[str, Any]],
        include_source: bool = True,
    ) -> str:
        """Format call chain with source context.

        Shows the call flow from entry point to current location,
        with source context for each frame.

        Args:
            call_chain: List of call chain frame dicts with:
                - depth: int
                - function: str
                - file: str | None
                - line: int
                - source: str | None
                - context: dict with 'before' and 'after' lists
                - call_expression: str | None
            include_source: Whether to include source context

        Returns:
            Rich ASCII art call chain with source context.

        Example Output:
            CALL CHAIN (3 frames)
            ══════════════════════════════════════════════════════════

            main (app.py:50)
            │    48 │ def main():
            │    49 │     order = load_order()
            │ >> 50 │     process_order(order)
            │    51 │     return
            │
            └─▶ process_order (orders.py:123)
                │   121 │ def process_order(order):
                │   122 │     billing = Billing()
                │ >> 123 │     total = billing.calculate_total(order.items)
                │   124 │     return total
                │
                └─▶ calculate_total (billing.py:45)  ◀── YOU ARE HERE
                    │    43 │     def calculate_total(self, items):
                    │    44 │         '''Calculate total with tax.'''
                    │ >> 45 │         total = sum(items)
                    │    46 │         return total * (1 + self.tax_rate)
        """
        if not call_chain:
            return "CALL CHAIN\n======================\n\n  (no frames)"

        # Apply frame limit
        total_frames = len(call_chain)
        truncated = False
        if self.config.max_frames > 0 and total_frames > self.config.max_frames:
            # Keep first and last frames
            half = self.config.max_frames // 2
            call_chain = call_chain[:half] + call_chain[-(self.config.max_frames - half) :]
            truncated = True

        lines: list[str] = []
        count_str = (
            f"{total_frames} frames"
            if not truncated
            else f"{len(call_chain)}/{total_frames} frames"
        )
        lines.append(f"CALL CHAIN ({count_str})")
        lines.append("=" * 50)
        lines.append("")

        # Reverse to show call order (entry point first)
        reversed_chain = list(reversed(call_chain))

        for i, frame in enumerate(reversed_chain):
            # Calculate indent based on position (cap indent to avoid runaway)
            indent_level = min(i, 5)
            base_indent = "  " * indent_level
            func_name = frame.get("function", "<unknown>")
            file_name = self._get_short_filename(frame.get("file"))
            line = frame.get("line", 0)

            location = f"{func_name} ({file_name}:{line})"

            # Function header line (use ASCII arrows)
            header = f"{base_indent}{location}" if i == 0 else f"{base_indent}+-> {location}"

            # Add "YOU ARE HERE" marker for current frame (ASCII)
            is_current = i == len(reversed_chain) - 1
            if is_current:
                header += "  <-- HERE"

            lines.append(header)

            # Add source context if available (with line limit)
            if include_source and frame.get("source") is not None:
                context = frame.get("context", {})
                before_lines = context.get("before", [])
                after_lines = context.get("after", [])
                current_line = frame.get("source", "")
                line_numbers = frame.get("line_numbers", {})

                # Limit context lines
                max_ctx = self.config.max_source_lines // 2
                if max_ctx > 0:
                    before_lines = before_lines[-max_ctx:]
                    after_lines = after_lines[:max_ctx]

                start_line = line_numbers.get("start", line - len(before_lines))

                # Source indent (deeper than function header)
                source_indent = base_indent + ("  " if i > 0 else "")

                # Format source lines with line numbers
                source_lines = before_lines + [current_line] + after_lines
                line_num_width = len(str(start_line + len(source_lines)))

                for j, src_line in enumerate(source_lines):
                    line_num = start_line + j
                    num_str = str(line_num).rjust(line_num_width)
                    is_current_line = line_num == line
                    prefix = "| >>" if is_current_line else "|   "
                    # Truncate long source lines
                    if len(src_line) > 60:
                        src_line = src_line[:57] + "..."
                    lines.append(f"{source_indent}{prefix} {num_str} | {src_line}")

                # Add blank line between frames (except last)
                if i < len(reversed_chain) - 1:
                    lines.append(f"{source_indent}|")

            # Add truncation indicator
            if truncated and i == (len(reversed_chain) // 2) - 1:
                omitted = total_frames - len(call_chain)
                lines.append(f"{base_indent}  ... {omitted} frames omitted ...")

        return "\n".join(lines)

    def format_inspection(
        self,
        inspection: dict[str, Any],
        title: str | None = None,
    ) -> str:
        """Format variable inspection result as rich terminal output.

        Args:
            inspection: Inspection result dict with keys:
                - name: str
                - type: str
                - detected_type: str
                - structure: dict
                - preview: dict
                - statistics: dict | None
                - summary: str
                - warnings: list[str]
            title: Optional custom title (defaults to "VARIABLE: {name}")

        Returns:
            Box-drawn string representation of the inspection.

        Example Output:
            ┌──────────────────────────────────────────────────────────────────┐
            │ VARIABLE: df                                                     │
            ├──────────────────────────────────────────────────────────────────┤
            │ DataFrame with 1000 rows x 5 columns, 78.1 KB                    │
            ├──────────────────────────────────────────────────────────────────┤
            │ COLUMNS                                                          │
            │ ┌────────────┬────────────────┬────────┐                         │
            │ │ Name       │ Type           │ Nulls  │                         │
            │ ├────────────┼────────────────┼────────┤                         │
            │ │ id         │ int64          │ 0      │                         │
            │ │ name       │ object         │ 5      │                         │
            │ └────────────┴────────────────┴────────┘                         │
            └──────────────────────────────────────────────────────────────────┘
        """
        name = inspection.get("name", "unknown")
        detected_type = inspection.get("detected_type", "unknown")
        display_title = title or f"VARIABLE: {name}"

        inner_width = self.config.max_width - 2
        lines: list[str] = []

        # Header
        lines.append(self._box_top(inner_width))
        lines.append(self._box_row(f" {display_title}", inner_width))
        lines.append(self._box_separator(inner_width))

        # Summary line
        summary = inspection.get("summary", "")
        lines.append(self._box_row(f" {summary}", inner_width))

        # Type-specific formatting
        if detected_type == "dataframe":
            lines.extend(self._format_dataframe_inspection(inspection, inner_width))
        elif detected_type == "series":
            lines.extend(self._format_series_inspection(inspection, inner_width))
        elif detected_type == "ndarray":
            lines.extend(self._format_ndarray_inspection(inspection, inner_width))
        elif detected_type == "dict":
            lines.extend(self._format_dict_inspection(inspection, inner_width))
        elif detected_type == "list":
            lines.extend(self._format_list_inspection(inspection, inner_width))
        else:
            lines.extend(self._format_unknown_inspection(inspection, inner_width))

        # Warnings
        warnings = inspection.get("warnings", [])
        if warnings:
            lines.append(self._box_separator(inner_width))
            lines.append(self._box_row(" WARNINGS", inner_width))
            for warning in warnings:
                lines.append(self._box_row(f"   ⚠ {warning}", inner_width))

        lines.append(self._box_bottom(inner_width))

        return "\n".join(lines)

    def _format_dataframe_inspection(
        self,
        inspection: dict[str, Any],
        inner_width: int,
    ) -> list[str]:
        """Format DataFrame-specific inspection data."""
        lines: list[str] = []
        structure = inspection.get("structure", {})
        preview = inspection.get("preview", {})

        lines.append(self._box_separator(inner_width))

        # Column information
        columns = structure.get("columns", [])
        dtypes = structure.get("dtypes", {})
        null_counts = structure.get("null_counts", {})

        if columns:
            lines.append(self._box_row(" COLUMNS", inner_width))

            # Build mini-table for columns
            col_data = []
            for col_name in columns[:10]:  # Limit to first 10
                dtype = dtypes.get(col_name, "?")
                nulls = null_counts.get(col_name, 0)
                col_data.append(
                    {
                        "name": col_name,
                        "type": dtype,
                        "nulls": str(nulls) if nulls > 0 else "-",
                    }
                )

            if col_data:
                mini_table = self._format_mini_table(
                    col_data,
                    ["name", "type", "nulls"],
                    ["Name", "Type", "Nulls"],
                )
                for row in mini_table.split("\n"):
                    lines.append(self._box_row(f"   {row}", inner_width))

            if len(columns) > 10:
                lines.append(
                    self._box_row(f"   ... and {len(columns) - 10} more columns", inner_width)
                )

        # Preview data
        head_data = preview.get("head", [])
        if head_data and isinstance(head_data, list):
            lines.append(self._box_separator(inner_width))
            lines.append(self._box_row(f" PREVIEW (first {len(head_data)} rows)", inner_width))

            # Show first few rows as key-value pairs
            for i, row in enumerate(head_data[:3]):
                if isinstance(row, dict):
                    row_str = ", ".join(
                        f"{k}={self._truncate(str(v), 15)}" for k, v in list(row.items())[:4]
                    )
                    lines.append(
                        self._box_row(
                            f"   [{i}] {self._truncate(row_str, inner_width - 8)}", inner_width
                        )
                    )

        return lines

    def _format_series_inspection(
        self,
        inspection: dict[str, Any],
        inner_width: int,
    ) -> list[str]:
        """Format Series-specific inspection data."""
        lines: list[str] = []
        structure = inspection.get("structure", {})
        preview = inspection.get("preview", {})
        statistics = inspection.get("statistics")

        lines.append(self._box_separator(inner_width))

        # Series info
        dtype = structure.get("dtype", "unknown")
        length = structure.get("length", 0)
        lines.append(self._box_row(f" Type: {dtype}, Length: {length:,}", inner_width))

        # Statistics
        if statistics:
            stats_parts = []
            if statistics.get("min") is not None:
                stats_parts.append(f"min={statistics['min']:.3g}")
            if statistics.get("max") is not None:
                stats_parts.append(f"max={statistics['max']:.3g}")
            if statistics.get("mean") is not None:
                stats_parts.append(f"mean={statistics['mean']:.3g}")
            if statistics.get("std") is not None:
                stats_parts.append(f"std={statistics['std']:.3g}")
            if stats_parts:
                lines.append(self._box_row(f" Stats: {', '.join(stats_parts)}", inner_width))

        # Preview
        head_data = preview.get("head", [])
        if head_data:
            lines.append(self._box_row(f" Head: {head_data[:5]}", inner_width))

        return lines

    def _format_ndarray_inspection(
        self,
        inspection: dict[str, Any],
        inner_width: int,
    ) -> list[str]:
        """Format ndarray-specific inspection data."""
        lines: list[str] = []
        structure = inspection.get("structure", {})
        preview = inspection.get("preview", {})
        statistics = inspection.get("statistics")

        lines.append(self._box_separator(inner_width))

        # Array info
        shape = structure.get("shape", ())
        dtype = structure.get("dtype", "unknown")
        lines.append(self._box_row(f" Shape: {shape}, Dtype: {dtype}", inner_width))

        # Statistics
        if statistics:
            stats_parts = []
            if statistics.get("min") is not None:
                stats_parts.append(f"min={statistics['min']:.3g}")
            if statistics.get("max") is not None:
                stats_parts.append(f"max={statistics['max']:.3g}")
            if statistics.get("mean") is not None:
                stats_parts.append(f"mean={statistics['mean']:.3g}")
            if statistics.get("std") is not None:
                stats_parts.append(f"std={statistics['std']:.3g}")
            if stats_parts:
                lines.append(self._box_row(f" Stats: {', '.join(stats_parts)}", inner_width))

        # Sample values
        sample = preview.get("sample", [])
        if sample:
            sample_str = str(sample[:8])
            lines.append(
                self._box_row(
                    f" Sample: {self._truncate(sample_str, inner_width - 12)}", inner_width
                )
            )

        return lines

    def _format_dict_inspection(
        self,
        inspection: dict[str, Any],
        inner_width: int,
    ) -> list[str]:
        """Format dict-specific inspection data."""
        lines: list[str] = []
        structure = inspection.get("structure", {})
        preview = inspection.get("preview", {})

        lines.append(self._box_separator(inner_width))

        # Dict info
        length = structure.get("length", 0)
        key_types = structure.get("key_types", [])
        value_types = structure.get("value_types", [])

        key_type_str = key_types[0] if len(key_types) == 1 else "mixed"
        value_type_str = ", ".join(value_types[:3]) if value_types else "unknown"

        lines.append(self._box_row(f" Keys: {length:,} ({key_type_str})", inner_width))
        lines.append(self._box_row(f" Value types: {value_type_str}", inner_width))

        # Key preview
        keys_preview = preview.get("keys", [])
        if keys_preview:
            keys_str = ", ".join(str(k) for k in keys_preview[:5])
            lines.append(
                self._box_row(
                    f" Sample keys: {self._truncate(keys_str, inner_width - 15)}", inner_width
                )
            )

        return lines

    def _format_list_inspection(
        self,
        inspection: dict[str, Any],
        inner_width: int,
    ) -> list[str]:
        """Format list-specific inspection data."""
        lines: list[str] = []
        structure = inspection.get("structure", {})
        preview = inspection.get("preview", {})

        lines.append(self._box_separator(inner_width))

        # List info
        length = structure.get("length", 0)
        element_types = structure.get("element_types", [])
        uniform = structure.get("uniform", False)

        type_info = element_types[0] if len(element_types) == 1 else "mixed"
        uniformity = "uniform" if uniform else "mixed types"

        lines.append(self._box_row(f" Length: {length:,} ({type_info}, {uniformity})", inner_width))

        # Preview
        head_data = preview.get("head", [])
        if head_data:
            preview_str = str(head_data[:5])
            lines.append(
                self._box_row(
                    f" Preview: {self._truncate(preview_str, inner_width - 12)}", inner_width
                )
            )

        return lines

    def _format_unknown_inspection(
        self,
        inspection: dict[str, Any],
        inner_width: int,
    ) -> list[str]:
        """Format unknown type inspection data."""
        lines: list[str] = []
        structure = inspection.get("structure", {})

        lines.append(self._box_separator(inner_width))

        # Type info
        type_module = structure.get("type_module", "")
        type_name = structure.get("type_name", "unknown")
        full_type = f"{type_module}.{type_name}" if type_module else type_name
        lines.append(self._box_row(f" Full type: {full_type}", inner_width))

        # Attributes
        attributes = structure.get("attributes", [])
        if attributes:
            attr_str = ", ".join(attributes[:5])
            lines.append(
                self._box_row(
                    f" Attributes: {self._truncate(attr_str, inner_width - 14)}", inner_width
                )
            )
            if len(attributes) > 5:
                lines.append(self._box_row(f"   ... and {len(attributes) - 5} more", inner_width))

        # Repr
        repr_str = structure.get("repr", "")
        if repr_str:
            lines.append(
                self._box_row(f" Repr: {self._truncate(repr_str, inner_width - 9)}", inner_width)
            )

        # Hint
        hint = inspection.get("hint")
        if hint:
            lines.append(self._box_separator(inner_width))
            lines.append(
                self._box_row(f" Hint: {self._truncate(hint, inner_width - 9)}", inner_width)
            )

        return lines

    def _format_mini_table(
        self,
        data: list[dict[str, Any]],
        keys: list[str],
        headers: list[str],
    ) -> str:
        """Format a small inline table.

        Args:
            data: List of row dicts
            keys: Keys to extract from each row
            headers: Column headers

        Returns:
            Mini table string
        """
        if not data:
            return ""

        # Calculate column widths
        widths = []
        for i, key in enumerate(keys):
            max_width = max(
                len(headers[i]),
                max(len(str(row.get(key, ""))) for row in data),
            )
            widths.append(min(max_width + 2, 20))

        c = self.config
        lines: list[str] = []

        # Top border
        segments = [c.BOX_H * w for w in widths]
        lines.append(f"{c.BOX_TL}{c.BOX_TT.join(segments)}{c.BOX_TR}")

        # Header row
        cells = [f" {h}".ljust(w)[:w] for h, w in zip(headers, widths)]
        lines.append(f"{c.BOX_V}{c.BOX_V.join(cells)}{c.BOX_V}")

        # Header separator
        lines.append(f"{c.BOX_LT}{c.BOX_X.join(segments)}{c.BOX_RT}")

        # Data rows
        for row in data:
            cells = [f" {str(row.get(k, ''))}".ljust(w)[:w] for k, w in zip(keys, widths)]
            lines.append(f"{c.BOX_V}{c.BOX_V.join(cells)}{c.BOX_V}")

        # Bottom border
        lines.append(f"{c.BOX_BL}{c.BOX_BT.join(segments)}{c.BOX_BR}")

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


def format_call_chain_with_context(
    call_chain: list[dict[str, Any]],
    include_source: bool = True,
) -> str:
    """Convenience function to format call chain with source context.

    Args:
        call_chain: List of call chain frame dicts with source context
        include_source: Whether to include source context

    Returns:
        Formatted call chain string with source lines
    """
    return get_formatter().format_call_chain_with_context(call_chain, include_source)
