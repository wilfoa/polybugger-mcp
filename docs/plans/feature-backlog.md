# polybugger-mcp Feature Backlog

This document contains detailed plans for upcoming features. Each feature needs full grooming (user story, HLD, LLD, test plans) before implementation.

---

## Feature 1: TUI/Terminal Formatting for Rich Output

### Status: Planning

### Overview
Create a formatting layer that produces rich terminal graphics for debugging information - ASCII art call flows, box-drawn stack traces, colored variable tables, etc.

### Goals
- Provide optional `format="tui"` parameter on inspection tools
- Generate ASCII/Unicode box drawings for structured data
- Create call flow diagrams
- Color-code by type/importance (via ANSI or markdown)
- Keep plain JSON as default for programmatic use

### Target Users
- AI agents (Claude, GPT, etc.) presenting debug info to developers
- Developers viewing debug output in terminals

### Proposed Implementation

#### New Module: `src/polybugger_mcp/utils/tui_formatter.py`

```python
"""Terminal UI formatting utilities."""

from typing import Any

class TUIFormatter:
    """Formats debug data as rich terminal output."""

    def format_stack_trace(self, frames: list[dict]) -> str:
        """Format stack trace as box-drawn diagram."""

    def format_variables(self, variables: list[dict]) -> str:
        """Format variables as aligned table."""

    def format_call_flow(self, call_chain: list[dict]) -> str:
        """Format call chain as tree diagram."""

    def format_dataframe_preview(self, df_info: dict) -> str:
        """Format DataFrame preview as table."""
```

#### Output Format Examples

**Stack Trace:**
```
┌─────────────────────────────────────────────────────────────┐
│ STACK TRACE                                     3 frames    │
├─────────────────────────────────────────────────────────────┤
│ #0  calculate_total      billing.py:45                      │
│     → total = sum(items)                                    │
├─────────────────────────────────────────────────────────────┤
│ #1  process_order        orders.py:123                      │
│     → total = billing.calculate_total(order.items)          │
├─────────────────────────────────────────────────────────────┤
│ #2  main                 app.py:50                          │
│     → process_order(order)                                  │
└─────────────────────────────────────────────────────────────┘
```

**Call Flow:**
```
                    ┌──────────────────┐
                    │  main (app.py)   │
                    └────────┬─────────┘
                             │
                             ▼
                ┌────────────────────────┐
                │ process_order (orders) │
                └────────────┬───────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
          ──▶ │ calculate_total (billing:45) │ ◀── YOU ARE HERE
              └──────────────────────────────┘
```

**Variables Table:**
```
┌──────────────────────────────────────────────────────────┐
│ LOCAL VARIABLES                              frame #0    │
├──────────┬────────────┬─────────────────────────────────┤
│ Name     │ Type       │ Value                           │
├──────────┼────────────┼─────────────────────────────────┤
│ items    │ list[int]  │ [100, 200, 300, 400, 500]       │
│ total    │ int        │ 1500                            │
│ tax_rate │ float      │ 0.08                            │
│ result   │ NoneType   │ None                            │
└──────────┴────────────┴─────────────────────────────────┘
```

**DataFrame Preview:**
```
┌─────────────────────────────────────────────────────────────┐
│ DataFrame: df                    1000 rows × 5 cols  78 KB  │
├───────┬──────────┬─────────┬────────────┬──────────────────┤
│ id    │ name     │ value   │ date       │ status           │
│ int64 │ object   │ float64 │ datetime64 │ object           │
├───────┼──────────┼─────────┼────────────┼──────────────────┤
│ 1     │ Alice    │ 100.50  │ 2024-01-15 │ active           │
│ 2     │ Bob      │ 200.30  │ 2024-01-16 │ pending          │
│ 3     │ Charlie  │ 150.00  │ 2024-01-17 │ active           │
│ ...   │ ...      │ ...     │ ...        │ ...              │
│ 998   │ Yuki     │ 175.25  │ 2024-12-30 │ inactive         │
│ 999   │ Zara     │ 225.00  │ 2024-12-31 │ active           │
└───────┴──────────┴─────────┴────────────┴──────────────────┘
```

#### Integration with Existing Tools

Add optional `format` parameter to inspection tools:

```python
@mcp.tool()
async def debug_get_stacktrace(
    session_id: str,
    thread_id: int | None = None,
    format: str = "json",  # "json" | "tui" | "markdown"
) -> dict[str, Any]:
```

When `format="tui"`, include a `formatted` key with the ASCII art:

```json
{
  "frames": [...],
  "total": 3,
  "formatted": "┌─────────────...",
  "format": "tui"
}
```

#### Files to Modify/Create

| File | Changes |
|------|---------|
| `src/polybugger_mcp/utils/tui_formatter.py` | New - all formatting logic |
| `src/polybugger_mcp/mcp_server.py` | Add `format` param to inspection tools |
| `tests/unit/test_tui_formatter.py` | New - unit tests for formatting |

#### Box Drawing Characters Reference

```
Single line: ─ │ ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼
Double line: ═ ║ ╔ ╗ ╚ ╝ ╠ ╣ ╦ ╩ ╬
Rounded:     ╭ ╮ ╰ ╯
Arrows:      → ← ↑ ↓ ▶ ◀ ▲ ▼ ➤
Misc:        • ● ○ ◉ ◎ ★ ☆
```

#### Estimated Effort
- **Medium**: 3-4 hours
- Most work is string formatting/alignment

---

## Feature 2: DataFrame/NumPy Smart Preview

### Status: Planning

### Overview
Enhance variable inspection to detect pandas DataFrames, NumPy arrays, and other common data structures, providing AI-friendly summaries instead of truncated string representations.

### Goals
- Detect `pandas.DataFrame`, `pandas.Series`, `numpy.ndarray`, `dict`, `list` types
- Return structured metadata (shape, dtype, columns, memory)
- Provide preview data (head/tail rows, sample values)
- Keep responses lightweight (don't transfer entire datasets)

### Proposed Implementation

#### New Module: `src/polybugger_mcp/utils/data_inspector.py`

```python
"""Smart data structure inspection utilities."""

from typing import Any

# Type detection patterns (evaluated via debugpy)
INSPECTION_EXPRESSIONS = {
    "dataframe": {
        "detect": "hasattr({var}, 'shape') and hasattr({var}, 'columns')",
        "shape": "{var}.shape",
        "columns": "list({var}.columns)",
        "dtypes": "{var}.dtypes.to_dict()",
        "head": "{var}.head(5).to_dict('records')",
        "memory": "{var}.memory_usage(deep=True).sum()",
    },
    "ndarray": {
        "detect": "type({var}).__module__ == 'numpy' and hasattr({var}, 'shape')",
        "shape": "{var}.shape",
        "dtype": "str({var}.dtype)",
        "sample": "{var}.flatten()[:10].tolist()",
    },
    "dict": {
        "detect": "isinstance({var}, dict)",
        "length": "len({var})",
        "keys": "list({var}.keys())[:20]",
        "sample": "dict(list({var}.items())[:5])",
    },
    "list": {
        "detect": "isinstance({var}, list)",
        "length": "len({var})",
        "sample": "{var}[:10]",
        "types": "list(set(type(x).__name__ for x in {var}[:100]))",
    },
}
```

#### New MCP Tool: `debug_inspect_variable`

```python
@mcp.tool()
async def debug_inspect_variable(
    session_id: str,
    variable_name: str,
    frame_id: int | None = None,
    max_preview_rows: int = 5,
) -> dict[str, Any]:
    """Deep inspect a variable with smart type detection.

    For DataFrames: returns shape, columns, dtypes, head rows, memory usage
    For NumPy arrays: returns shape, dtype, sample values
    For dicts/lists: returns length, keys/indices, sample values

    Args:
        session_id: Debug session ID
        variable_name: Name of variable to inspect
        frame_id: Stack frame ID (uses current frame if not specified)
        max_preview_rows: Max rows to include in preview (default 5)

    Returns:
        Structured inspection result with type-specific metadata
    """
```

#### Response Format Examples

**DataFrame:**
```json
{
  "name": "df",
  "type": "DataFrame",
  "structure": {
    "shape": [1000, 5],
    "columns": ["id", "name", "value", "date", "status"],
    "dtypes": {"id": "int64", "name": "object", "value": "float64"},
    "memory_bytes": 80000
  },
  "preview": {
    "head": [
      {"id": 1, "name": "Alice", "value": 100.5},
      {"id": 2, "name": "Bob", "value": 200.3}
    ]
  },
  "summary": "DataFrame with 1000 rows x 5 columns, 78.1 KB"
}
```

**NumPy Array:**
```json
{
  "name": "arr",
  "type": "ndarray",
  "structure": {
    "shape": [100, 100],
    "dtype": "float64",
    "size": 10000
  },
  "preview": {
    "sample": [0.1, 0.2, 0.3, 0.4, 0.5],
    "min": 0.0,
    "max": 1.0,
    "mean": 0.5
  },
  "summary": "ndarray float64 [100, 100], 800 KB"
}
```

#### Files to Modify/Create

| File | Changes |
|------|---------|
| `src/polybugger_mcp/utils/data_inspector.py` | New - inspection logic |
| `src/polybugger_mcp/adapters/debugpy_adapter.py` | Add `inspect_variable()` method |
| `src/polybugger_mcp/core/session.py` | Add `inspect_variable()` delegation |
| `src/polybugger_mcp/mcp_server.py` | Add `debug_inspect_variable` tool |
| `tests/unit/test_data_inspector.py` | New - unit tests |
| `tests/e2e/test_data_inspection.py` | New - e2e tests with real pandas/numpy |

#### Dependencies
- No new runtime dependencies (uses evaluate to introspect)
- Optional: Add `pandas` and `numpy` to dev dependencies for testing

#### Estimated Effort
- **Low-Medium**: 2-3 hours
- Most logic is string expressions evaluated via existing `evaluate()` method

---

## Feature 3: Code Intelligence - Call Hierarchy

### Status: Planning

### Overview
Provide tools to analyze call relationships at debug time - what functions called the current function (callers/runtime call chain) with source context.

### Goals
- Show complete call chain from entry point to current location
- Provide source locations for navigation
- Include source context for each frame

### Proposed Implementation

#### Enhanced Call Chain Tool

```python
@mcp.tool()
async def debug_get_call_chain(
    session_id: str,
    include_source_context: bool = True,
    context_lines: int = 2,
) -> dict[str, Any]:
    """Get the call chain leading to current location.

    Returns the stack trace with source context for each frame,
    formatted as a call hierarchy showing how we got here.

    Args:
        session_id: Debug session ID
        include_source_context: Include surrounding source lines
        context_lines: Lines of context before/after (default 2)

    Returns:
        Call chain with source context and formatted visualization
    """
```

#### Response Format

```json
{
  "call_chain": [
    {
      "depth": 0,
      "function": "calculate_total",
      "file": "billing.py",
      "line": 45,
      "source": "        total = sum(items)  # <-- CURRENT",
      "context": {
        "before": ["    def calculate_total(self, items):", "        '''Calculate total'''"],
        "after": ["        return total * (1 + self.tax_rate)"]
      }
    },
    {
      "depth": 1,
      "function": "process_order",
      "file": "orders.py",
      "line": 123,
      "source": "    total = billing.calculate_total(order.items)",
      "call_expression": "billing.calculate_total(order.items)"
    },
    {
      "depth": 2,
      "function": "main",
      "file": "app.py",
      "line": 50,
      "source": "    process_order(order)",
      "call_expression": "process_order(order)"
    }
  ],
  "formatted": "main (app.py:50)\n  └─> process_order (orders.py:123)\n      └─> calculate_total (billing.py:45)  <-- YOU ARE HERE"
}
```

#### Files to Modify/Create

| File | Changes |
|------|---------|
| `src/polybugger_mcp/mcp_server.py` | Add `debug_get_call_chain` tool |
| `src/polybugger_mcp/utils/source_reader.py` | New - read source context |
| `tests/unit/test_call_hierarchy.py` | New - unit tests |

#### Future Enhancement: Static Analysis

For finding ALL callers/callees (not just runtime), would need AST analysis:

```python
@mcp.tool()
async def debug_find_callers(
    session_id: str,
    function_name: str,
    search_paths: list[str] | None = None,
) -> dict[str, Any]:
    """Find all call sites of a function in the project.

    Uses static analysis to find where a function is called.
    """
```

This requires:
1. Parse Python files with `ast` module
2. Find `Call` nodes matching function name
3. Track imports to resolve qualified names

**Defer static analysis to Phase 2** - runtime call chain is more immediately useful.

#### Estimated Effort
- **Phase 1 (Runtime)**: 1-2 hours
- **Phase 2 (Static)**: 4-6 hours (AST parsing)

---

## Priority & Recommended Order

| Feature | Value | Effort | Priority |
|---------|-------|--------|----------|
| TUI/Terminal Formatting | High | Medium | **P1** |
| DataFrame/NumPy Smart Preview | High | Low-Medium | **P2** |
| Call Hierarchy (Runtime) | Medium | Low | **P3** |
| Call Hierarchy (Static) | Medium | High | Defer |

### Recommended Implementation Order

1. **TUI Formatter** - Foundation for rich output
2. **DataFrame Smart Preview** - High value, can use TUI formatter
3. **Call Chain** - Quick win, enhances stack trace

---

## Technical Context

### Current Codebase Structure

```
src/polybugger_mcp/
├── mcp_server.py         # MCP tools defined here with @mcp.tool()
├── adapters/
│   └── debugpy_adapter.py # DAP communication, has evaluate() method
├── core/
│   └── session.py        # Session management, delegates to adapter
├── models/
│   └── dap.py            # Variable, StackFrame, Scope models
└── utils/
    └── output_buffer.py  # Existing utility module
```

### Key Integration Points

1. **Adding new MCP tools**: Add function with `@mcp.tool()` in `mcp_server.py`
2. **Evaluating expressions**: Use `session.adapter.evaluate(expr, frame_id)`
3. **Getting variables**: Use `session.adapter.variables(ref)`
4. **Getting stack trace**: Use `session.adapter.stack_trace(thread_id)`

### Response Format Pattern

All MCP tools return `dict[str, Any]`. Include both structured data AND formatted output:

```python
return {
    "data": [...],           # Structured data (always)
    "formatted": "...",      # TUI representation (when format="tui")
    "format": "tui"          # Indicator of format used
}
```

---

## Next Steps

1. Run full feature grooming (user story, HLD, LLD, test plans) for each feature
2. Implement in priority order
3. Add tests for each feature
4. Update README with new capabilities

---

*Last updated: 2026-01-14*
