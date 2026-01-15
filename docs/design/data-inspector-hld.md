# DataFrame/NumPy Smart Preview - High-Level Design Document

**Feature:** Smart Variable Inspection for Data Science Types
**Story ID:** US-DATA-002
**Version:** 1.0
**Date:** January 2026
**Status:** Draft

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Context](#2-system-context)
3. [Component Architecture](#3-component-architecture)
4. [Data Flow](#4-data-flow)
5. [API Contract](#5-api-contract)
6. [Technology Decisions](#6-technology-decisions)
7. [Error Handling & Edge Cases](#7-error-handling--edge-cases)
8. [Performance Considerations](#8-performance-considerations)
9. [Security Considerations](#9-security-considerations)
10. [Testing Strategy](#10-testing-strategy)
11. [Domains Requiring LLD](#11-domains-requiring-lld)

---

## 1. Executive Summary

### 1.1 Purpose

Add a new MCP tool `debug_inspect_variable` that provides intelligent inspection of pandas DataFrames, NumPy arrays, dicts, and lists with structured metadata and preview data. This reduces the 5-10 tool calls currently needed to understand data structures down to a single call.

### 1.2 Scope

**In Scope:**
- New MCP tool `debug_inspect_variable`
- Type detection for DataFrame, Series, ndarray, dict, list, primitives
- Structured metadata extraction (shape, dtypes, columns, memory)
- Preview data generation (head rows, sample values)
- TUI formatting support via existing `TUIFormatter`
- Response size limiting (<100KB)
- Timeout handling for large datasets

**Out of Scope:**
- Data modification capabilities
- Full dataset transfer
- Visualization/plotting
- Custom type plugins
- Advanced statistical analysis

### 1.3 Goals

| Goal | Success Criteria |
|------|------------------|
| Efficiency | Single tool call replaces 5-10 evaluate calls |
| Structured Output | Machine-readable metadata, not strings to parse |
| Safety | Response size <100KB, per-expression timeout 2s |
| Compatibility | Works without pandas/numpy installed (graceful fallback) |
| Integration | Leverages existing TUIFormatter for `format="tui"` |

---

## 2. System Context

### 2.1 System Context Diagram

```
                                    External Systems
    +------------------------------------------------------------------+
    |                                                                  |
    |  +----------------+                        +------------------+  |
    |  |  AI Agent      |                        |  Target Python   |  |
    |  |  (Claude, GPT) |                        |  Process         |  |
    |  +-------+--------+                        |  (pandas/numpy)  |  |
    |          |                                 +--------+---------+  |
    |          | MCP Protocol                             |            |
    |          | (stdio)                                  | DAP        |
    +----------|------------------------------------------|-----------+
               |                                          |
               v                                          v
    +------------------------------------------------------------------+
    |                     pybugger-mcp Server                          |
    |                                                                  |
    |  +--------------------+     +--------------------+               |
    |  |   MCP Server       |     |   debugpy Adapter  |               |
    |  |   (mcp_server.py)  |<--->|   (DAP Client)     |               |
    |  +--------------------+     +--------------------+               |
    |           |                          |                           |
    |           v                          v                           |
    |  +--------------------+     +--------------------+               |
    |  | debug_inspect_     |     |   session.         |               |
    |  | variable tool      |     |   evaluate()       |               |
    |  +--------------------+     +--------------------+               |
    |           |                                                      |
    |           v                                                      |
    |  +--------------------+     +--------------------+               |
    |  |  DataInspector     |     |  TUIFormatter      |               |
    |  |  (NEW COMPONENT)   |     |  (existing)        |               |
    |  +--------------------+     +--------------------+               |
    |                                                                  |
    +------------------------------------------------------------------+
```

### 2.2 Current Architecture

```
src/pybugger_mcp/
  mcp_server.py          # MCP tools (@mcp.tool() decorators)
  adapters/
    debugpy_adapter.py   # DAP communication, evaluate() method
  core/
    session.py           # Session management, delegates to adapter
  models/
    dap.py               # Variable, StackFrame, Scope models
  utils/
    tui_formatter.py     # TUI formatting (recently added)
    output_buffer.py     # Output buffering
```

### 2.3 Architecture with Data Inspector

```
src/pybugger_mcp/
  mcp_server.py          # + debug_inspect_variable tool
  adapters/
    debugpy_adapter.py   # (unchanged)
  core/
    session.py           # + inspect_variable() method
  models/
    dap.py               # (unchanged)
    inspection.py        # NEW: InspectionResult, TypeMetadata models
  utils/
    tui_formatter.py     # + format_inspection() method
    output_buffer.py     # (unchanged)
    data_inspector.py    # NEW: Type detection & introspection logic
```

---

## 3. Component Architecture

### 3.1 Component Diagram

```
+------------------------------------------------------------------+
|                          MCP Server Layer                        |
|  +------------------------------------------------------------+  |
|  |  mcp_server.py                                             |  |
|  |  +------------------------------------------------------+  |  |
|  |  | @mcp.tool()                                          |  |  |
|  |  | debug_inspect_variable(                              |  |  |
|  |  |   session_id, variable_name, frame_id?,              |  |  |
|  |  |   max_preview_rows?, include_statistics?, format?    |  |  |
|  |  | ) -> InspectionResponse                              |  |  |
|  |  +------------------------------------------------------+  |  |
|  +------------------------------------------------------------+  |
+--------------------------------|----------------------------------+
                                 |
                                 v
+------------------------------------------------------------------+
|                         Session Layer                            |
|  +------------------------------------------------------------+  |
|  |  core/session.py                                           |  |
|  |  +------------------------------------------------------+  |  |
|  |  | async def inspect_variable(                          |  |  |
|  |  |   variable_name: str,                                |  |  |
|  |  |   frame_id: int | None,                              |  |  |
|  |  |   options: InspectionOptions                         |  |  |
|  |  | ) -> InspectionResult                                |  |  |
|  |  +------------------------------------------------------+  |  |
|  +------------------------------------------------------------+  |
+--------------------------------|----------------------------------+
                                 |
                                 v
+------------------------------------------------------------------+
|                      Data Inspector Layer                        |
|  +------------------------------------------------------------+  |
|  |  utils/data_inspector.py                                   |  |
|  |  +------------------------------------------------------+  |  |
|  |  | class DataInspector:                                 |  |  |
|  |  |   async def inspect(                                 |  |  |
|  |  |     evaluator: EvaluatorProtocol,                    |  |  |
|  |  |     variable_name: str,                              |  |  |
|  |  |     frame_id: int | None,                            |  |  |
|  |  |     options: InspectionOptions                       |  |  |
|  |  |   ) -> InspectionResult                              |  |  |
|  |  |                                                      |  |  |
|  |  |   async def _detect_type(...) -> DetectedType        |  |  |
|  |  |   async def _inspect_dataframe(...) -> dict          |  |  |
|  |  |   async def _inspect_series(...) -> dict             |  |  |
|  |  |   async def _inspect_ndarray(...) -> dict            |  |  |
|  |  |   async def _inspect_dict(...) -> dict               |  |  |
|  |  |   async def _inspect_list(...) -> dict               |  |  |
|  |  |   async def _inspect_unknown(...) -> dict            |  |  |
|  |  +------------------------------------------------------+  |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
                                 |
                                 | evaluate()
                                 v
+------------------------------------------------------------------+
|                       Adapter Layer                              |
|  +------------------------------------------------------------+  |
|  |  adapters/debugpy_adapter.py                               |  |
|  |  +------------------------------------------------------+  |  |
|  |  | async def evaluate(                                  |  |  |
|  |  |   expression: str,                                   |  |  |
|  |  |   frame_id: int | None,                              |  |  |
|  |  |   context: str = "watch"                             |  |  |
|  |  | ) -> dict[str, Any]                                  |  |  |
|  |  +------------------------------------------------------+  |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

### 3.2 Class Responsibilities

| Class | Responsibility |
|-------|---------------|
| `debug_inspect_variable` (tool) | MCP endpoint, parameter validation, response formatting |
| `Session.inspect_variable()` | State validation, delegate to DataInspector |
| `DataInspector` | Type detection, introspection orchestration, result building |
| `DebugpyAdapter.evaluate()` | Execute Python expressions in debug context (existing) |
| `TUIFormatter.format_inspection()` | Generate ASCII visualization of inspection result |

### 3.3 New Models (`models/inspection.py`)

```python
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class DetectedType(str, Enum):
    """Detected data type categories."""
    DATAFRAME = "dataframe"
    SERIES = "series"
    NDARRAY = "ndarray"
    DICT = "dict"
    LIST = "list"
    PRIMITIVE = "primitive"
    UNKNOWN = "unknown"


class InspectionOptions(BaseModel):
    """Options for variable inspection."""
    max_preview_rows: int = Field(default=5, ge=1, le=100)
    max_preview_items: int = Field(default=10, ge=1, le=100)
    include_statistics: bool = True
    timeout_per_expression: float = Field(default=2.0, ge=0.1, le=10.0)


class DataFrameMetadata(BaseModel):
    """Metadata specific to pandas DataFrame."""
    shape: tuple[int, int]
    columns: list[str]
    dtypes: dict[str, str]
    index_type: str
    memory_bytes: int
    null_counts: dict[str, int] | None = None


class SeriesMetadata(BaseModel):
    """Metadata specific to pandas Series."""
    length: int
    dtype: str
    name: str | None
    index_type: str


class ArrayMetadata(BaseModel):
    """Metadata specific to NumPy ndarray."""
    shape: tuple[int, ...]
    dtype: str
    size: int
    memory_bytes: int


class CollectionMetadata(BaseModel):
    """Metadata for dict/list types."""
    length: int
    key_types: list[str] | None = None  # For dicts
    value_types: list[str] | None = None
    element_types: list[str] | None = None  # For lists
    depth: int | None = None  # Nesting depth


class Statistics(BaseModel):
    """Numerical statistics for arrays/series."""
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    std: float | None = None
    median: float | None = None
    nan_count: int | None = None
    inf_count: int | None = None


class InspectionResult(BaseModel):
    """Complete result of variable inspection."""
    name: str
    type: str  # Display type (e.g., "DataFrame", "ndarray")
    detected_type: DetectedType

    # Type-specific metadata (one will be populated)
    structure: dict[str, Any] = Field(default_factory=dict)

    # Preview data
    preview: dict[str, Any] = Field(default_factory=dict)

    # Optional statistics (numeric types)
    statistics: Statistics | None = None

    # Human-readable summary
    summary: str

    # Warnings/notes
    warnings: list[str] = Field(default_factory=list)

    # Error info (if inspection partially failed)
    error: str | None = None
    partial: bool = False
    timed_out: list[str] = Field(default_factory=list)

    # For drilling down with debug_get_variables
    variables_reference: int | None = None

    # Hint for unknown types
    hint: str | None = None
```

---

## 4. Data Flow

### 4.1 Primary Flow Diagram

```
+----------+       +-------------+       +---------+       +---------------+
|  AI      |       | MCP Server  |       | Session |       | DataInspector |
|  Agent   |       | (tool)      |       |         |       |               |
+----+-----+       +------+------+       +----+----+       +-------+-------+
     |                    |                   |                    |
     | debug_inspect_variable                 |                    |
     | (session_id, "df")                     |                    |
     |------------------->|                   |                    |
     |                    |                   |                    |
     |                    | inspect_variable  |                    |
     |                    | ("df", None, opts)|                    |
     |                    |------------------>|                    |
     |                    |                   |                    |
     |                    |                   | inspect(evaluator, |
     |                    |                   | "df", None, opts)  |
     |                    |                   |------------------>|
     |                    |                   |                    |
     |                    |                   |   +----------------+
     |                    |                   |   | 1. detect_type |
     |                    |                   |   +----------------+
     |                    |                   |            |
     |                    |                   |            v
     |                    |                   |   +-----------------+
     |                    |                   |   | 2. route to     |
     |                    |                   |   |    type handler |
     |                    |                   |   +-----------------+
     |                    |                   |            |
     |                    |                   |            v
     |                    |                   |   +-----------------+
     |                    |                   |   | 3. evaluate     |
     |                    |                   |   |    expressions  |
     |                    |                   |   |    (parallel)   |
     |                    |                   |   +-----------------+
     |                    |                   |            |
     |                    |                   |            v
     |                    |                   |   +-----------------+
     |                    |                   |   | 4. build result |
     |                    |                   |   +-----------------+
     |                    |                   |            |
     |                    |                   |<-----------+
     |                    |                   | InspectionResult
     |                    |<------------------|
     |                    | InspectionResult  |
     |                    |                   |
     |                    | [if format="tui"] |
     |                    | format_inspection |
     |                    |------------------>TUIFormatter
     |                    |<------------------+
     |                    |                   |
     |<-------------------|                   |
     | {name, type, structure, preview, ...}  |
     |                    |                   |
```

### 4.2 Type Detection Flow

```
                      +-------------------+
                      | Variable Name     |
                      | (e.g., "df")      |
                      +---------+---------+
                                |
                                v
                      +-------------------+
                      | Evaluate type()   |
                      | expression        |
                      +---------+---------+
                                |
                                v
              +----------------------------------+
              | Check type signatures            |
              +----------------------------------+
                      |         |         |
         +------------+    +----+----+    +------------+
         |                 |         |                 |
         v                 v         v                 v
+----------------+ +-------------+ +-------------+ +------------+
| DataFrame?     | | Series?     | | ndarray?    | | dict/list? |
| has columns,   | | has dtype,  | | has shape,  | | isinstance |
| dtypes, shape  | | no columns  | | dtype attr  | | check      |
+-------+--------+ +------+------+ +------+------+ +-----+------+
        |                 |               |              |
        v                 v               v              v
+----------------+ +-------------+ +-------------+ +------------+
| DATAFRAME      | | SERIES      | | NDARRAY     | | DICT/LIST  |
+----------------+ +-------------+ +-------------+ +------------+
                                          |
                                          | None matched
                                          v
                                   +-------------+
                                   | UNKNOWN     |
                                   +-------------+
```

### 4.3 Expression Evaluation Strategy

For each detected type, specific expressions are evaluated:

**DataFrame Expressions:**
```python
DATAFRAME_EXPRESSIONS = {
    "shape": "{var}.shape",
    "columns": "list({var}.columns)",
    "dtypes": "{{str(k): str(v) for k, v in {var}.dtypes.items()}}",
    "index_type": "type({var}.index).__name__",
    "memory_bytes": "int({var}.memory_usage(deep=True).sum())",
    "head": "{var}.head({n}).to_dict('records')",
}
```

**ndarray Expressions:**
```python
NDARRAY_EXPRESSIONS = {
    "shape": "{var}.shape",
    "dtype": "str({var}.dtype)",
    "size": "{var}.size",
    "memory_bytes": "{var}.nbytes",
    "sample": "{var}.flatten()[:{n}].tolist()",
    # Statistics (conditionally, if size < 10M)
    "min": "float({var}.min())",
    "max": "float({var}.max())",
    "mean": "float({var}.mean())",
    "std": "float({var}.std())",
}
```

---

## 5. API Contract

### 5.1 Tool Signature

```python
@mcp.tool()
async def debug_inspect_variable(
    session_id: str,
    variable_name: str,
    frame_id: int | None = None,
    max_preview_rows: int = 5,
    include_statistics: bool = True,
    format: str = "json",
) -> dict[str, Any]:
    """Inspect a variable with smart type-aware metadata and preview.

    Provides detailed inspection of pandas DataFrames, NumPy arrays,
    dicts, lists, and other Python objects. Returns structured metadata
    appropriate for the detected type.

    Args:
        session_id: The debug session ID
        variable_name: Name of the variable to inspect (must be in scope)
        frame_id: Stack frame to inspect in (uses topmost if not specified)
        max_preview_rows: Maximum rows/items in preview (default 5, max 100)
        include_statistics: Include statistical summary for numeric data
        format: Output format - "json" (default) or "tui" for rich terminal

    Returns:
        Structured inspection result with:
        - name: Variable name
        - type: Display type (e.g., "DataFrame", "ndarray", "dict")
        - detected_type: Category ("dataframe", "series", "ndarray", etc.)
        - structure: Type-specific metadata (shape, columns, dtypes, etc.)
        - preview: Sample data (head rows, key-value pairs, etc.)
        - statistics: Numerical stats (for numeric types, if requested)
        - summary: Human-readable one-line summary
        - warnings: Any warnings (large size, NaN values, etc.)
        - variables_reference: For drilling down with debug_get_variables
        - formatted: ASCII visualization (if format="tui")

    Example:
        >>> result = debug_inspect_variable(session_id, "df")
        >>> result
        {
            "name": "df",
            "type": "DataFrame",
            "detected_type": "dataframe",
            "structure": {
                "shape": [1000, 5],
                "columns": ["id", "name", "value", "date", "status"],
                "dtypes": {"id": "int64", "name": "object", ...},
                "memory_bytes": 80000
            },
            "preview": {
                "head": [{"id": 1, "name": "Alice", ...}, ...]
            },
            "summary": "DataFrame with 1000 rows x 5 columns, 78.1 KB"
        }
    """
```

### 5.2 Response Schema by Type

#### DataFrame Response

```json
{
    "name": "df",
    "type": "DataFrame",
    "detected_type": "dataframe",
    "structure": {
        "shape": [1000, 5],
        "columns": ["id", "name", "value", "date", "status"],
        "dtypes": {
            "id": "int64",
            "name": "object",
            "value": "float64",
            "date": "datetime64[ns]",
            "status": "object"
        },
        "index_type": "RangeIndex",
        "memory_bytes": 80000,
        "null_counts": {"name": 5, "value": 12}
    },
    "preview": {
        "head": [
            {"id": 1, "name": "Alice", "value": 100.5, "date": "2024-01-15", "status": "active"},
            {"id": 2, "name": "Bob", "value": 200.3, "date": "2024-01-16", "status": "pending"}
        ]
    },
    "summary": "DataFrame with 1000 rows x 5 columns, 78.1 KB",
    "variables_reference": 42
}
```

#### NumPy Array Response

```json
{
    "name": "weights",
    "type": "ndarray",
    "detected_type": "ndarray",
    "structure": {
        "shape": [128, 256],
        "dtype": "float32",
        "size": 32768,
        "memory_bytes": 131072
    },
    "statistics": {
        "min": -0.982,
        "max": 0.971,
        "mean": 0.002,
        "std": 0.453,
        "nan_count": 0,
        "inf_count": 0
    },
    "preview": {
        "sample": [0.123, -0.456, 0.789, -0.012, 0.345]
    },
    "summary": "ndarray float32 [128, 256], 128 KB, mean=0.002"
}
```

#### Dict Response

```json
{
    "name": "config",
    "type": "dict",
    "detected_type": "dict",
    "structure": {
        "length": 45,
        "key_types": ["str"],
        "value_types": ["str", "int", "bool", "list"]
    },
    "preview": {
        "keys": ["host", "port", "database", "pool_size", "..."],
        "sample": {
            "host": "localhost",
            "port": 5432,
            "database": "production"
        }
    },
    "summary": "dict with 45 string keys (mixed value types)"
}
```

#### Error Response

```json
{
    "error": "Variable 'data' not found in current scope",
    "code": "VARIABLE_NOT_FOUND",
    "available_variables": ["df", "config", "result"],
    "hint": "Check variable name spelling or verify the variable is in scope"
}
```

### 5.3 TUI Format Output

When `format="tui"`, the response includes a `formatted` field:

```
+------------------------------------------------------------------+
| VARIABLE INSPECTION: df                                          |
+------------------------------------------------------------------+
| Type:     DataFrame                                              |
| Shape:    1000 rows x 5 columns                                  |
| Memory:   78.1 KB                                                |
+------------------------------------------------------------------+
| COLUMNS                                                          |
+------------------+------------------+-----------------------------+
| Name             | Type             | Nulls                       |
+------------------+------------------+-----------------------------+
| id               | int64            | 0                           |
| name             | object           | 5                           |
| value            | float64          | 12                          |
| date             | datetime64[ns]   | 0                           |
| status           | object           | 0                           |
+------------------+------------------+-----------------------------+
| PREVIEW (first 5 rows)                                           |
+------+----------+--------+------------+---------+
| id   | name     | value  | date       | status  |
+------+----------+--------+------------+---------+
| 1    | Alice    | 100.5  | 2024-01-15 | active  |
| 2    | Bob      | 200.3  | 2024-01-16 | pending |
| ...  | ...      | ...    | ...        | ...     |
+------+----------+--------+------------+---------+
```

---

## 6. Technology Decisions

### 6.1 Expression-Based Introspection

**Decision:** Use `session.evaluate()` to run Python expressions in the debug context rather than accessing data directly.

**Rationale:**
- **No New Dependencies:** Leverages existing DAP evaluate mechanism
- **Safety:** Expressions run in the debugged process, not the MCP server
- **Flexibility:** Works with any Python environment that has pandas/numpy
- **Consistency:** Same approach as existing `debug_evaluate` tool

**Trade-offs:**
- (+) No need to transfer raw data to MCP server
- (+) Works with any pandas/numpy version
- (-) Slightly slower than direct memory access
- (-) Limited by what can be expressed in single-line Python

### 6.2 Parallel Expression Evaluation

**Decision:** Evaluate multiple introspection expressions concurrently where possible.

**Rationale:**
- Many expressions are independent (shape, dtype, columns)
- Reduces total inspection time from sum of timeouts to max of timeouts
- DAP protocol supports concurrent requests

**Implementation:**
```python
async def _evaluate_expressions(
    self,
    expressions: dict[str, str],
    frame_id: int | None,
) -> dict[str, Any]:
    """Evaluate multiple expressions concurrently."""
    tasks = {
        key: self._evaluate_with_timeout(expr, frame_id)
        for key, expr in expressions.items()
    }
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    return dict(zip(tasks.keys(), results))
```

### 6.3 Graceful Degradation

**Decision:** Return partial results when some introspection expressions fail or timeout.

**Rationale:**
- Large datasets may timeout on statistics but still provide shape/dtype
- Missing pandas/numpy should not completely fail inspection
- AI agents can still provide useful information with partial data

**Implementation:**
```python
result = InspectionResult(
    name=var_name,
    type="DataFrame",
    detected_type=DetectedType.DATAFRAME,
    partial=True,
    timed_out=["statistics", "memory_bytes"],
    # ... other fields populated where successful
)
```

### 6.4 TUIFormatter Integration

**Decision:** Add `format_inspection()` method to existing `TUIFormatter` class.

**Rationale:**
- Follows established pattern from TUI-001 feature
- Reuses existing box-drawing and table utilities
- Maintains single source of truth for TUI formatting
- No new dependencies or modules needed

**Implementation Location:** `utils/tui_formatter.py`

### 6.5 No New Runtime Dependencies

**Decision:** The feature works without requiring pandas or numpy to be installed in the MCP server environment.

**Rationale:**
- MCP server is a debugging tool, not a data science tool
- Target code has pandas/numpy; MCP server doesn't need them
- All introspection happens via evaluate() in the debugged process
- Keeps pybugger-mcp lightweight and fast to install

**Testing Consideration:** pandas and numpy added as dev dependencies for integration testing only.

---

## 7. Error Handling & Edge Cases

### 7.1 Error Categories

| Error | Code | Handling |
|-------|------|----------|
| Variable not found | `VARIABLE_NOT_FOUND` | Return available variables list |
| Session not paused | `INVALID_STATE` | Return session state and hint |
| Expression timeout | (partial result) | Return what succeeded, list timeouts |
| Evaluation error | (partial result) | Skip failed expressions, continue |
| Response too large | (auto-truncate) | Limit preview, add warning |

### 7.2 Edge Case Handling

| Edge Case | Handling Strategy |
|-----------|-------------------|
| Empty DataFrame (0 rows) | Return shape, columns, dtypes; empty preview |
| Very large DataFrame (>1M rows) | Limit preview to 5 rows, skip memory-intensive stats |
| DataFrame with complex columns | Show type summaries for nested types |
| NaN/Inf in array | Compute stats with nanmean, report nan/inf counts |
| Deeply nested dict/list | Limit preview depth to 3 levels |
| pandas/numpy not installed | Return basic info with fallback flag |
| Multi-index DataFrame | Include index type info in structure |

### 7.3 Size Limits

| Limit | Value | Rationale |
|-------|-------|-----------|
| Max response size | 100 KB | Prevent MCP message overflow |
| Max preview rows | 100 | Configurable, bounded |
| Max preview items (dict/list) | 100 | Configurable, bounded |
| Max preview depth | 3 | Prevent explosion on nested structures |
| Skip stats threshold | 10M elements | Statistics on huge arrays are slow |

---

## 8. Performance Considerations

### 8.1 Performance Targets

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Type detection | <50ms | Time for detection expressions |
| DataFrame inspection (typical) | <500ms | 1K rows, 10 columns |
| Array inspection (typical) | <500ms | 1M elements |
| Dict inspection (typical) | <200ms | 1K keys |
| TUI formatting | <10ms | Post-inspection formatting |

### 8.2 Optimization Strategies

1. **Parallel Evaluation:** Independent expressions evaluated concurrently
2. **Early Termination:** Stop on first timeout, return partial results
3. **Lazy Statistics:** Skip for arrays >10M elements unless explicitly requested
4. **Bounded Preview:** Hard limits on preview size regardless of configuration
5. **String Building:** Use list joins, not concatenation for TUI output

### 8.3 Timeout Strategy

```python
class DataInspector:
    async def _evaluate_with_timeout(
        self,
        expression: str,
        frame_id: int | None,
        timeout: float = 2.0,
    ) -> Any:
        """Evaluate with per-expression timeout."""
        try:
            return await asyncio.wait_for(
                self._evaluator.evaluate(expression, frame_id),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise ExpressionTimeoutError(expression)
```

---

## 9. Security Considerations

### 9.1 Expression Safety

**Risk:** Arbitrary expression evaluation could be dangerous.

**Mitigation:**
- All expressions are constructed from templates, not user input
- Variable name is validated against identifier pattern
- No shell commands or file operations in expressions
- Expressions only read data, never modify

### 9.2 Response Size

**Risk:** Malicious or accidental large data could overwhelm clients.

**Mitigation:**
- Hard limit of 100KB on response size
- Preview data truncated before serialization
- Statistics skipped for very large arrays

### 9.3 Timeout Protection

**Risk:** Long-running expressions could block the server.

**Mitigation:**
- Per-expression timeout of 2 seconds (configurable)
- Overall inspection timeout of 10 seconds
- Partial results returned on timeout

---

## 10. Testing Strategy

### 10.1 Test Categories

| Category | Location | Coverage Target |
|----------|----------|-----------------|
| Unit Tests | `tests/unit/test_data_inspector.py` | 100% |
| Integration Tests | `tests/integration/test_inspect_variable.py` | 90% |
| E2E Tests | `tests/e2e/test_data_inspection.py` | Key scenarios |

### 10.2 Unit Test Cases

```python
class TestDataInspector:
    # Type Detection
    def test_detect_dataframe(self): ...
    def test_detect_series(self): ...
    def test_detect_ndarray(self): ...
    def test_detect_dict(self): ...
    def test_detect_list(self): ...
    def test_detect_unknown_type(self): ...
    def test_detect_primitive(self): ...

    # DataFrame Inspection
    def test_inspect_simple_dataframe(self): ...
    def test_inspect_empty_dataframe(self): ...
    def test_inspect_large_dataframe(self): ...
    def test_inspect_dataframe_complex_types(self): ...
    def test_inspect_dataframe_multiindex(self): ...

    # NumPy Inspection
    def test_inspect_1d_array(self): ...
    def test_inspect_nd_array(self): ...
    def test_inspect_array_with_nan(self): ...
    def test_inspect_huge_array_skip_stats(self): ...

    # Edge Cases
    def test_timeout_partial_result(self): ...
    def test_response_size_truncation(self): ...
    def test_missing_pandas_fallback(self): ...
```

### 10.3 Integration Test Cases

```python
class TestInspectVariableTool:
    async def test_inspect_dataframe_at_breakpoint(self): ...
    async def test_inspect_with_tui_format(self): ...
    async def test_inspect_variable_not_found(self): ...
    async def test_inspect_session_not_paused(self): ...
    async def test_inspect_nested_variable(self): ...
```

### 10.4 E2E Test Scenario

```python
async def test_full_dataframe_inspection_workflow():
    """End-to-end test of DataFrame inspection during debugging."""
    # 1. Create session
    # 2. Set breakpoint in script that creates DataFrame
    # 3. Launch script
    # 4. Wait for breakpoint
    # 5. Call debug_inspect_variable("df")
    # 6. Verify structure, preview, summary
    # 7. Call with format="tui", verify formatted output
```

---

## 11. Domains Requiring LLD

### 11.1 Backend/Python (Required)

**Scope:** Detailed low-level design needed for:

| Component | LLD Content |
|-----------|-------------|
| `DataInspector` class | Method signatures, expression templates, error handling |
| Type detection logic | Decision tree, edge cases, performance |
| Expression evaluation | Parallel execution, timeout handling, result merging |
| Response building | Size limiting, truncation strategy, summary generation |
| TUIFormatter extension | `format_inspection()` method specification |

**LLD Document:** `docs/design/data-inspector-lld.md`

### 11.2 Other Domains (Not Required)

| Domain | Status | Rationale |
|--------|--------|-----------|
| Frontend | N/A | MCP server only, no frontend |
| Database | N/A | No persistence for inspection results |
| Infrastructure | N/A | No deployment changes |
| API Gateway | N/A | Direct MCP protocol |
| External Integrations | N/A | All interaction through existing DAP |

---

## Appendix A: Expression Templates

### DataFrame Expressions

```python
DATAFRAME_EXPRESSIONS = {
    "shape": "{var}.shape",
    "columns": "list({var}.columns)",
    "dtypes": "{{str(k): str(v) for k, v in {var}.dtypes.items()}}",
    "index_type": "type({var}.index).__name__",
    "memory_bytes": "int({var}.memory_usage(deep=True).sum())",
    "null_counts": "{var}.isnull().sum().to_dict()",
    "head": "{var}.head({n}).to_dict('records')",
}
```

### Series Expressions

```python
SERIES_EXPRESSIONS = {
    "length": "len({var})",
    "dtype": "str({var}.dtype)",
    "name": "{var}.name",
    "index_type": "type({var}.index).__name__",
    "head": "{var}.head({n}).tolist()",
    "tail": "{var}.tail({n}).tolist()",
    # Statistics
    "min": "float({var}.min())",
    "max": "float({var}.max())",
    "mean": "float({var}.mean())",
    "null_count": "int({var}.isnull().sum())",
}
```

### ndarray Expressions

```python
NDARRAY_EXPRESSIONS = {
    "shape": "{var}.shape",
    "dtype": "str({var}.dtype)",
    "size": "{var}.size",
    "memory_bytes": "{var}.nbytes",
    "sample": "{var}.flatten()[:{n}].tolist()",
    # Statistics (conditional on size)
    "min": "float({var}.min())",
    "max": "float({var}.max())",
    "mean": "float({var}.mean())",
    "std": "float({var}.std())",
    "nan_count": "int(__import__('numpy').isnan({var}).sum())",
    "inf_count": "int(__import__('numpy').isinf({var}).sum())",
}
```

### Dict/List Expressions

```python
DICT_EXPRESSIONS = {
    "length": "len({var})",
    "key_types": "list(set(type(k).__name__ for k in list({var}.keys())[:{n}]))",
    "value_types": "list(set(type(v).__name__ for v in list({var}.values())[:{n}]))",
    "keys_preview": "list({var}.keys())[:{n}]",
    "sample": "dict(list({var}.items())[:{n}])",
}

LIST_EXPRESSIONS = {
    "length": "len({var})",
    "element_types": "list(set(type(x).__name__ for x in {var}[:{n}]))",
    "sample": "{var}[:{n}]",
}
```

---

## Appendix B: Type Detection Expressions

```python
TYPE_DETECTORS = {
    # Order matters - check specific types before generic
    "dataframe": (
        "hasattr({var}, 'columns') and "
        "hasattr({var}, 'dtypes') and "
        "hasattr({var}, 'shape') and "
        "len(getattr({var}, 'shape', ())) == 2"
    ),
    "series": (
        "hasattr({var}, 'dtype') and "
        "hasattr({var}, 'index') and "
        "not hasattr({var}, 'columns') and "
        "hasattr({var}, 'name')"
    ),
    "ndarray": (
        "type({var}).__module__ == 'numpy' and "
        "hasattr({var}, 'shape') and "
        "hasattr({var}, 'dtype') and "
        "hasattr({var}, 'nbytes')"
    ),
    "dict": "isinstance({var}, dict)",
    "list": "isinstance({var}, list)",
}
```

---

## Appendix C: Summary Generation Templates

```python
SUMMARY_TEMPLATES = {
    "dataframe": "DataFrame with {rows:,} rows x {cols} columns, {memory}",
    "series": "Series '{name}' with {length:,} {dtype} values",
    "ndarray": "ndarray {dtype} {shape}, {memory}, mean={mean:.3f}",
    "dict": "dict with {length:,} {key_type} keys ({value_info})",
    "list": "list of {length:,} items ({type_info})",
    "unknown": "{type} object with {attr_count} attributes",
}
```

---

*Document End*
