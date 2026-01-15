# TUI Formatter - High-Level Design Document

**Feature:** ASCII/TUI Formatted Output for Debug Inspection Tools
**Version:** 1.0
**Date:** January 2026
**Status:** Draft

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Context](#2-system-context)
3. [Component Design](#3-component-design)
4. [Data Flow](#4-data-flow)
5. [API Design](#5-api-design)
6. [Key Design Decisions](#6-key-design-decisions)
7. [Dependencies](#7-dependencies)
8. [Risks & Mitigations](#8-risks--mitigations)
9. [Testing Strategy](#9-testing-strategy)
10. [Implementation Phases](#10-implementation-phases)

---

## 1. Executive Summary

### 1.1 Purpose

Add optional TUI (Text User Interface) formatting to pybugger-mcp's inspection tools, enabling AI agents to receive human-readable ASCII visualizations of debug state alongside structured JSON data.

### 1.2 Scope

**In Scope:**
- ASCII box drawings for stack traces
- Aligned tables for variables display
- Tree diagrams for call chains
- Format parameter for 3 inspection tools
- Edge case handling (truncation, unicode, empty results)

**Out of Scope:**
- Interactive TUI components
- Color/ANSI escape sequences
- Custom terminal emulation
- Persistent formatting preferences

### 1.3 Goals

| Goal | Success Criteria |
|------|------------------|
| Readability | AI agents can interpret formatted output without parsing JSON |
| Compatibility | Works in terminals 80-120 chars wide |
| Performance | < 5ms formatting overhead for typical datasets |
| Maintainability | Single module, < 500 LOC, 100% test coverage |

---

## 2. System Context

### 2.1 Current Architecture

```
+------------------+     +------------------+     +------------------+
|   AI Agent       |     |   MCP Server     |     |   debugpy        |
|   (Claude, etc.) |<--->|   (mcp_server.py)|<--->|   (DAP Protocol) |
+------------------+     +------------------+     +------------------+
                                  |
                                  v
                         +------------------+
                         |   Session        |
                         |   Management     |
                         +------------------+
                                  |
                    +-------------+-------------+
                    |             |             |
                    v             v             v
            +----------+   +----------+   +----------+
            | Output   |   | Event    |   | Models   |
            | Buffer   |   | Queue    |   | (DAP)    |
            +----------+   +----------+   +----------+
```

### 2.2 Architecture with TUI Formatter

```
+------------------+     +------------------+     +------------------+
|   AI Agent       |     |   MCP Server     |     |   debugpy        |
|   (Claude, etc.) |<--->|   (mcp_server.py)|<--->|   (DAP Protocol) |
+------------------+     +------------------+     +------------------+
                                  |
                                  | format="tui"
                                  v
                         +------------------+
                         |  TUI Formatter   |  <-- NEW COMPONENT
                         |  (utils/)        |
                         +------------------+
                                  |
                                  v
                         +------------------+
                         |   Session        |
                         |   Management     |
                         +------------------+
```

### 2.3 Integration Points

| Component | Integration Type | Description |
|-----------|-----------------|-------------|
| `mcp_server.py` | Consumer | Calls formatter after data retrieval |
| `models/dap.py` | Input | Provides StackFrame, Variable, Scope models |
| `utils/output_buffer.py` | Peer | Follows same utility pattern |

---

## 3. Component Design

### 3.1 Module Structure

```
src/pybugger_mcp/
  utils/
    __init__.py
    output_buffer.py      # Existing
    tui_formatter.py      # NEW - TUI formatting utilities
```

### 3.2 TUIFormatter Class

```python
"""TUI formatting utilities for debug output.

Provides ASCII-based visual representations of debug data
for enhanced readability in terminal environments.
"""

from dataclasses import dataclass
from typing import Literal

from pybugger_mcp.models.dap import Scope, StackFrame, Variable


FormatType = Literal["json", "tui"]


@dataclass
class FormatterConfig:
    """Configuration for TUI formatter."""

    max_width: int = 100          # Maximum output width
    min_width: int = 80           # Minimum output width
    max_value_length: int = 50    # Max length for variable values
    max_name_length: int = 30     # Max length for variable names
    max_type_length: int = 20     # Max length for type names
    truncation_suffix: str = "..."
    indent_size: int = 2


class TUIFormatter:
    """Formats debug data as ASCII/TUI visualizations.

    Thread-safe, stateless formatter that converts debug model
    objects into human-readable ASCII representations.

    Example:
        formatter = TUIFormatter()
        output = formatter.format_stacktrace(frames)
    """

    def __init__(self, config: FormatterConfig | None = None):
        """Initialize formatter with optional configuration."""
        self.config = config or FormatterConfig()

    def format_stacktrace(
        self,
        frames: list[StackFrame],
        title: str = "Call Stack",
    ) -> str:
        """Format stack frames as ASCII box drawing.

        Args:
            frames: List of StackFrame objects
            title: Optional title for the box

        Returns:
            ASCII box drawing string
        """
        ...

    def format_variables(
        self,
        variables: list[Variable],
        title: str = "Variables",
    ) -> str:
        """Format variables as aligned table.

        Args:
            variables: List of Variable objects
            title: Optional title for the table

        Returns:
            ASCII table string
        """
        ...

    def format_scopes(
        self,
        scopes: list[Scope],
        title: str = "Scopes",
    ) -> str:
        """Format scopes as tree diagram.

        Args:
            scopes: List of Scope objects
            title: Optional title for the tree

        Returns:
            ASCII tree string
        """
        ...

    def format_call_chain(
        self,
        frames: list[StackFrame],
    ) -> str:
        """Format stack frames as call chain tree.

        Args:
            frames: List of StackFrame objects (top to bottom)

        Returns:
            ASCII tree diagram string
        """
        ...

    # Private helper methods
    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text with suffix if too long."""
        ...

    def _sanitize_unicode(self, text: str) -> str:
        """Replace problematic unicode with safe alternatives."""
        ...

    def _create_box(
        self,
        content: list[str],
        title: str | None = None,
        width: int | None = None,
    ) -> str:
        """Create ASCII box around content."""
        ...

    def _create_table(
        self,
        headers: list[str],
        rows: list[list[str]],
        alignments: list[str] | None = None,
    ) -> str:
        """Create ASCII table with headers and rows."""
        ...
```

### 3.3 Box Drawing Characters

Using ASCII-compatible characters for maximum terminal compatibility:

```
Standard Box:
+------------------+
| Title            |
+------------------+
| Content line 1   |
| Content line 2   |
+------------------+

Table:
+--------+--------+--------+
| Name   | Value  | Type   |
+--------+--------+--------+
| foo    | 42     | int    |
| bar    | "test" | str    |
+--------+--------+--------+

Tree (Call Chain):
main()
  -> process_data()
       -> validate()
            -> check_value()  <-- current
```

### 3.4 Output Examples

**Stack Trace (Box Drawing):**
```
+------------------------------------------------------------------+
| Call Stack (4 frames)                                            |
+------------------------------------------------------------------+
| #0 | check_value      | validator.py:45    | <-- current        |
| #1 | validate         | validator.py:23    |                    |
| #2 | process_data     | main.py:67         |                    |
| #3 | main             | main.py:12         |                    |
+------------------------------------------------------------------+
```

**Variables (Aligned Table):**
```
+-------------------------------------------------------------------+
| Variables (Locals)                                                |
+------------+--------------------------------+----------------------+
| Name       | Value                          | Type                 |
+------------+--------------------------------+----------------------+
| user_id    | 12345                          | int                  |
| username   | "alice_wonder"                 | str                  |
| data       | {'key': 'value', 'items': ...  | dict (3 items)       |
| is_valid   | True                           | bool                 |
+------------+--------------------------------+----------------------+
```

**Call Chain (Tree Diagram):**
```
Call Chain:
  main()                          main.py:12
    -> process_data()             main.py:67
         -> validate()            validator.py:23
              -> check_value()    validator.py:45  <-- stopped here
```

**Scopes (Tree):**
```
Scopes:
  +-- Locals (ref: 1001)
  +-- Globals (ref: 1002) [expensive]
  +-- Builtins (ref: 1003) [expensive]
```

---

## 4. Data Flow

### 4.1 Request Processing Flow

```
                    MCP Tool Call
                         |
                         v
               +-------------------+
               | debug_get_*       |
               | (mcp_server.py)   |
               +-------------------+
                         |
                         | 1. Extract format parameter
                         v
               +-------------------+
               | Session.get_*     |
               | (core/session.py) |
               +-------------------+
                         |
                         | 2. Retrieve raw data (StackFrame, Variable, etc.)
                         v
               +-------------------+
               | format == "tui"?  |
               +-------------------+
                    |         |
              Yes   |         | No (json)
                    v         v
        +---------------+  +---------------+
        | TUIFormatter  |  | Return JSON   |
        | .format_*()   |  | directly      |
        +---------------+  +---------------+
                    |
                    | 3. Generate ASCII output
                    v
        +----------------------------+
        | Combined Response:         |
        | {                          |
        |   "frames": [...],         |
        |   "formatted": "ASCII...", |
        |   "format": "tui"          |
        | }                          |
        +----------------------------+
```

### 4.2 Sequence Diagram

```
AI Agent          mcp_server.py        Session           TUIFormatter
   |                   |                   |                   |
   |--debug_get_stacktrace(format="tui")-->|                   |
   |                   |                   |                   |
   |                   |--get_stack_trace()-->                 |
   |                   |                   |                   |
   |                   |<--[StackFrame]-----|                   |
   |                   |                   |                   |
   |                   |--format_stacktrace([frames])--------->|
   |                   |                   |                   |
   |                   |<--"ASCII string"----------------------|
   |                   |                   |                   |
   |<--{frames: [], formatted: "...", format: "tui"}-----------|
   |                   |                   |                   |
```

### 4.3 Data Transformation

| Input Type | Formatter Method | Output |
|------------|-----------------|--------|
| `list[StackFrame]` | `format_stacktrace()` | ASCII box with numbered frames |
| `list[Variable]` | `format_variables()` | ASCII table with columns |
| `list[Scope]` | `format_scopes()` | ASCII tree diagram |
| `list[StackFrame]` | `format_call_chain()` | ASCII tree with arrows |

---

## 5. API Design

### 5.1 Format Parameter Specification

```python
# Type definition
FormatType = Literal["json", "tui"]

# Parameter signature for affected tools
async def debug_get_stacktrace(
    session_id: str,
    thread_id: int | None = None,
    max_frames: int = 20,
    format: FormatType = "json",  # NEW PARAMETER
) -> dict[str, Any]:
    ...
```

### 5.2 Response Structure

**Format: JSON (default)**
```json
{
  "frames": [
    {
      "id": 1,
      "name": "check_value",
      "file": "/path/to/validator.py",
      "line": 45,
      "column": 0
    }
  ],
  "total": 4
}
```

**Format: TUI**
```json
{
  "frames": [
    {
      "id": 1,
      "name": "check_value",
      "file": "/path/to/validator.py",
      "line": 45,
      "column": 0
    }
  ],
  "total": 4,
  "format": "tui",
  "formatted": "+------------------------------------------------------------------+\n| Call Stack (4 frames)                                            |\n..."
}
```

### 5.3 Affected Tools

| Tool | Current Parameters | New Parameter |
|------|-------------------|---------------|
| `debug_get_stacktrace` | session_id, thread_id, max_frames | + format |
| `debug_get_variables` | session_id, variables_reference, max_count | + format |
| `debug_get_scopes` | session_id, frame_id | + format |

### 5.4 Updated Tool Signatures

```python
@mcp.tool()
async def debug_get_stacktrace(
    session_id: str,
    thread_id: int | None = None,
    max_frames: int = 20,
    format: str = "json",  # "json" or "tui"
) -> dict[str, Any]:
    """Get the call stack when paused.

    Args:
        session_id: The debug session ID
        thread_id: Thread to get stack for (uses current thread if not specified)
        max_frames: Maximum number of frames to return
        format: Output format - "json" (default) or "tui" for ASCII visualization

    Returns:
        Stack frames with file, line, and function information.
        When format="tui", includes 'formatted' field with ASCII box drawing.
    """
    ...


@mcp.tool()
async def debug_get_variables(
    session_id: str,
    variables_reference: int,
    max_count: int = 100,
    format: str = "json",
) -> dict[str, Any]:
    """Get variables for a scope or compound variable.

    Args:
        session_id: The debug session ID
        variables_reference: Reference from debug_get_scopes or nested variable
        max_count: Maximum variables to return
        format: Output format - "json" (default) or "tui" for ASCII table

    Returns:
        List of variables with names, values, and types.
        When format="tui", includes 'formatted' field with ASCII table.
    """
    ...


@mcp.tool()
async def debug_get_scopes(
    session_id: str,
    frame_id: int,
    format: str = "json",
) -> dict[str, Any]:
    """Get variable scopes (locals, globals) for a stack frame.

    Args:
        session_id: The debug session ID
        frame_id: Frame ID from debug_get_stacktrace
        format: Output format - "json" (default) or "tui" for ASCII tree

    Returns:
        List of scopes with their variables_reference for fetching variables.
        When format="tui", includes 'formatted' field with ASCII tree.
    """
    ...
```

---

## 6. Key Design Decisions

### 6.1 Separate Formatter Module

**Decision:** Create `utils/tui_formatter.py` as a standalone utility module.

**Rationale:**
- **Separation of Concerns:** Formatting logic is distinct from debugging logic
- **Testability:** Pure functions with no I/O are easy to unit test
- **Reusability:** Can be used by both MCP server and REST API
- **Maintainability:** Changes to formatting don't affect core debug logic
- **Follows Existing Pattern:** Consistent with `utils/output_buffer.py`

**Alternatives Considered:**
- Inline formatting in mcp_server.py (rejected: code bloat, harder to test)
- Formatting in models (rejected: models should be pure data structures)
- Separate formatting service (rejected: over-engineering for this scope)

### 6.2 Include Both JSON and Formatted Output

**Decision:** TUI responses include both structured data AND formatted string.

**Rationale:**
- AI agents may need structured data for programmatic decisions
- Formatted output is for display/logging purposes
- Avoids needing separate API calls for different use cases
- Small overhead (formatted string is typically 1-5KB)

**Response Structure:**
```json
{
  "frames": [...],           // Always present - structured data
  "total": 4,                // Always present - metadata
  "format": "tui",           // Present when format != "json"
  "formatted": "ASCII..."    // Present when format == "tui"
}
```

### 6.3 Truncation Strategy

**Decision:** Truncate at display time with configurable limits.

**Strategy:**
| Field | Max Length | Truncation |
|-------|------------|------------|
| Variable name | 30 chars | Middle ellipsis: `very_long_...ame` |
| Variable value | 50 chars | End ellipsis: `"long string con...` |
| Type name | 20 chars | End ellipsis: `CustomTypeName...` |
| File path | 40 chars | Start ellipsis: `.../deep/path/file.py` |

**Rationale:**
- Preserves readability in fixed-width displays
- Middle ellipsis for names preserves prefix and suffix (useful for identification)
- Start ellipsis for paths preserves filename (most informative part)
- Configurable via `FormatterConfig` for flexibility

### 6.4 Width Handling

**Decision:** Default to 100 characters, adapt to 80-120 range.

**Approach:**
```python
@dataclass
class FormatterConfig:
    max_width: int = 100    # Target width
    min_width: int = 80     # Minimum for readability
```

**Behavior:**
1. Calculate content width requirements
2. If content fits in max_width, use max_width
3. If content needs more, truncate to fit max_width
4. Never go below min_width (will overflow if necessary)

**Rationale:**
- 80 chars is traditional terminal minimum
- 100 chars is comfortable for modern terminals
- 120 chars is common maximum for wide displays

### 6.5 Pure ASCII (No ANSI Codes)

**Decision:** Use only ASCII characters, no colors or escape sequences.

**Rationale:**
- Maximum compatibility across terminals and environments
- MCP responses may be displayed in various contexts (logs, UIs, etc.)
- AI agents don't need colors for parsing
- Simplifies implementation and testing

**Box Drawing Characters:**
```python
# ASCII-safe box characters
HORIZONTAL = "-"
VERTICAL = "|"
CORNER_TL = "+"
CORNER_TR = "+"
CORNER_BL = "+"
CORNER_BR = "+"
T_DOWN = "+"
T_UP = "+"
T_LEFT = "+"
T_RIGHT = "+"
CROSS = "+"
```

### 6.6 Stateless Formatter

**Decision:** TUIFormatter is stateless and thread-safe.

**Rationale:**
- No shared mutable state between formatting calls
- Safe for concurrent use across multiple sessions
- Can be instantiated per-request or shared globally
- Easier to reason about and test

---

## 7. Dependencies

### 7.1 Internal Dependencies

| Dependency | Module | Usage |
|------------|--------|-------|
| StackFrame | `models/dap.py` | Input model for stack formatting |
| Variable | `models/dap.py` | Input model for variable formatting |
| Scope | `models/dap.py` | Input model for scope formatting |

### 7.2 External Dependencies

**None required.** The TUI formatter uses only Python standard library:
- `dataclasses` - Configuration class
- `typing` - Type hints
- `textwrap` - Text wrapping (optional, for long values)

### 7.3 No New Dependencies

**Rationale:**
- Pure Python string manipulation is sufficient
- Avoids dependency bloat
- Keeps package lightweight
- Libraries like `rich` or `tabulate` are overkill for this use case

---

## 8. Risks & Mitigations

### 8.1 Unicode Rendering Issues

**Risk:** Unicode characters in variable names/values may render incorrectly in some terminals.

**Impact:** Medium - May produce misaligned output.

**Mitigation:**
```python
def _sanitize_unicode(self, text: str) -> str:
    """Replace problematic unicode with safe alternatives."""
    # Replace zero-width characters
    text = re.sub(r'[\u200b-\u200f\u2028-\u202f]', '', text)

    # Replace wide characters with placeholder
    # (CJK characters, emoji, etc. take 2 columns)
    sanitized = []
    for char in text:
        if unicodedata.east_asian_width(char) in ('W', 'F'):
            sanitized.append('??')  # Placeholder for wide chars
        else:
            sanitized.append(char)

    return ''.join(sanitized)
```

**Acceptance:** Documented limitation; users advised to inspect raw JSON for accurate unicode values.

### 8.2 Performance for Large Datasets

**Risk:** Formatting very large variable sets (1000+) may be slow.

**Impact:** Low - Rare in practice, bounded by max_count parameter.

**Mitigation:**
- Default `max_count=100` limits variable retrieval
- Formatter operates on already-limited datasets
- O(n) string building with list joins (not concatenation)
- Lazy evaluation where possible

**Benchmarks Target:**
| Dataset Size | Target Time |
|--------------|-------------|
| 10 items | < 1ms |
| 100 items | < 5ms |
| 1000 items | < 50ms |

### 8.3 Terminal Compatibility

**Risk:** ASCII box drawings may look wrong in non-standard terminals.

**Impact:** Low - Visual only, data is still accessible.

**Mitigation:**
- Use only ASCII characters (no Unicode box drawing)
- Document supported terminal widths (80-120)
- JSON format always available as fallback
- Test in common environments (bash, zsh, PowerShell, VS Code terminal)

### 8.4 Long Values Breaking Alignment

**Risk:** Variable values with embedded newlines or very long strings may break table alignment.

**Impact:** Medium - Affects readability.

**Mitigation:**
```python
def _sanitize_value(self, value: str) -> str:
    """Sanitize value for table display."""
    # Replace newlines with symbol
    value = value.replace('\n', '\\n').replace('\r', '\\r')

    # Replace tabs
    value = value.replace('\t', '\\t')

    # Truncate if too long
    return self._truncate(value, self.config.max_value_length)
```

### 8.5 Deep Stack Traces

**Risk:** Very deep stacks (100+ frames) produce unwieldy output.

**Impact:** Low - Already bounded by `max_frames` parameter.

**Mitigation:**
- Default `max_frames=20` is reasonable
- Clearly indicate truncation: "... and 80 more frames"
- Recommend `format="json"` for programmatic analysis of deep stacks

---

## 9. Testing Strategy

### 9.1 Unit Tests (`tests/unit/test_tui_formatter.py`)

```python
class TestTUIFormatter:
    """Unit tests for TUI formatter."""

    # Basic formatting
    def test_format_empty_stacktrace(self): ...
    def test_format_single_frame(self): ...
    def test_format_multiple_frames(self): ...

    # Variable formatting
    def test_format_empty_variables(self): ...
    def test_format_simple_variables(self): ...
    def test_format_nested_variable_indicator(self): ...

    # Scope formatting
    def test_format_scopes_tree(self): ...
    def test_format_expensive_scope_marker(self): ...

    # Edge cases
    def test_truncate_long_value(self): ...
    def test_truncate_long_name_middle(self): ...
    def test_truncate_long_path(self): ...
    def test_sanitize_unicode(self): ...
    def test_handle_newlines_in_value(self): ...

    # Configuration
    def test_custom_max_width(self): ...
    def test_custom_truncation_suffix(self): ...

    # Box drawing
    def test_box_with_title(self): ...
    def test_box_without_title(self): ...
    def test_table_alignment(self): ...
```

### 9.2 Integration Tests (`tests/integration/test_format_parameter.py`)

```python
class TestFormatParameter:
    """Integration tests for format parameter in MCP tools."""

    async def test_stacktrace_json_format(self): ...
    async def test_stacktrace_tui_format(self): ...
    async def test_variables_json_format(self): ...
    async def test_variables_tui_format(self): ...
    async def test_scopes_json_format(self): ...
    async def test_scopes_tui_format(self): ...
    async def test_invalid_format_parameter(self): ...
    async def test_default_format_is_json(self): ...
```

### 9.3 E2E Tests (`tests/e2e/test_tui_output.py`)

```python
class TestTUIOutput:
    """End-to-end tests for TUI formatted output."""

    async def test_full_debug_session_with_tui(self): ...
    async def test_tui_output_at_breakpoint(self): ...
    async def test_tui_variables_with_complex_types(self): ...
```

### 9.4 Test Coverage Targets

| Component | Target Coverage |
|-----------|----------------|
| `tui_formatter.py` | 100% |
| MCP tool changes | 90%+ |
| Edge case handling | 100% |

---

## 10. Implementation Phases

### Phase 1: Core Formatter (2-3 days)

**Deliverables:**
- `utils/tui_formatter.py` with `TUIFormatter` class
- `FormatterConfig` dataclass
- Basic formatting methods:
  - `format_stacktrace()`
  - `format_variables()`
  - `format_scopes()`
- Helper methods:
  - `_truncate()`
  - `_sanitize_unicode()`
  - `_create_box()`
  - `_create_table()`
- Unit tests for all methods

**Acceptance Criteria:**
- [ ] Formatter produces valid ASCII output
- [ ] All edge cases handled (empty, unicode, long values)
- [ ] 100% unit test coverage

### Phase 2: MCP Integration (1-2 days)

**Deliverables:**
- Updated `debug_get_stacktrace` with format parameter
- Updated `debug_get_variables` with format parameter
- Updated `debug_get_scopes` with format parameter
- Integration tests for format parameter

**Acceptance Criteria:**
- [ ] Format parameter works in all three tools
- [ ] Default format is "json" (backward compatible)
- [ ] TUI format includes both data and formatted string
- [ ] Invalid format values return helpful error

### Phase 3: Polish & Documentation (1 day)

**Deliverables:**
- `format_call_chain()` method (bonus feature)
- E2E tests with real debug sessions
- Updated tool docstrings
- Usage examples in README

**Acceptance Criteria:**
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Performance benchmarks met

---

## Appendix A: ASCII Art Reference

### Box Drawing

```
+-------------------------------+
| Title                         |
+-------------------------------+
| Content line with padding     |
| Another line                  |
+-------------------------------+
```

### Table

```
+----------+------------------+----------+
| Header 1 | Header 2         | Header 3 |
+----------+------------------+----------+
| Cell     | Longer cell text | Cell     |
| Cell     | Cell             | Cell     |
+----------+------------------+----------+
```

### Tree

```
Root
  +-- Child 1
  |     +-- Grandchild 1.1
  |     +-- Grandchild 1.2
  +-- Child 2
        +-- Grandchild 2.1
```

### Call Chain

```
main()                    main.py:10
  -> process()            process.py:25
       -> validate()      validate.py:15
            -> check()    check.py:42  <-- current
```

---

## Appendix B: Configuration Reference

```python
@dataclass
class FormatterConfig:
    """Configuration for TUI formatter.

    Attributes:
        max_width: Maximum line width (default: 100)
        min_width: Minimum line width (default: 80)
        max_value_length: Max chars for variable values (default: 50)
        max_name_length: Max chars for variable names (default: 30)
        max_type_length: Max chars for type names (default: 20)
        truncation_suffix: Suffix for truncated text (default: "...")
        indent_size: Spaces per indent level (default: 2)
    """
    max_width: int = 100
    min_width: int = 80
    max_value_length: int = 50
    max_name_length: int = 30
    max_type_length: int = 20
    truncation_suffix: str = "..."
    indent_size: int = 2
```

---

## Appendix C: Error Handling

| Scenario | Handling |
|----------|----------|
| Empty frame list | Return empty box with "No frames" message |
| Empty variable list | Return empty table with "No variables" message |
| Invalid format value | Return error dict with valid options |
| Unicode handling fails | Fall back to repr() of value |
| Extremely long single value | Hard truncate at 2x max_value_length |

---

*Document End*
