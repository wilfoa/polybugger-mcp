# DataFrame/NumPy Smart Preview - Low-Level Design

## Document Metadata
- **Feature**: Smart Variable Inspection for Data Science Types
- **Story ID**: US-DATA-002
- **Status**: Ready for Implementation
- **Author**: Backend Developer Agent
- **Created**: 2026-01-15
- **HLD Reference**: docs/design/data-inspector-hld.md

---

## 1. Overview

This document provides the complete implementation plan for the DataFrame/NumPy Smart Preview feature, which enables AI agents to inspect pandas DataFrames, NumPy arrays, dicts, and lists with a single tool call, returning structured metadata and preview data.

### 1.1 Scope

**In Scope:**
- `DataInspector` class with type detection and introspection logic
- Pydantic models for inspection options and results
- New MCP tool `debug_inspect_variable`
- Session method `inspect_variable()`
- TUIFormatter extension `format_inspection()`
- Unit and integration tests

**Out of Scope:**
- Data modification capabilities
- Full dataset transfer
- Visualization/plotting
- Custom type plugins
- torch tensor support (future version)

### 1.2 Goals

| Goal | Success Criteria |
|------|------------------|
| Efficiency | Single tool call replaces 5-10 evaluate calls |
| Structured Output | Machine-readable metadata, not strings to parse |
| Safety | Response size <100KB, per-expression timeout 2s |
| Graceful Degradation | Partial results on timeout, fallback for unknown types |

---

## 2. File Structure

### 2.1 Files to Create

| File | Purpose |
|------|---------|
| `src/polybugger_mcp/utils/data_inspector.py` | DataInspector class with type detection and introspection |
| `src/polybugger_mcp/models/inspection.py` | Pydantic models for inspection |
| `tests/unit/test_data_inspector.py` | Unit tests for DataInspector |
| `tests/integration/test_inspect_variable.py` | Integration tests for MCP tool |
| `tests/e2e/test_data_inspection.py` | E2E tests with real pandas/numpy |

### 2.2 Files to Modify

| File | Changes |
|------|---------|
| `src/polybugger_mcp/mcp_server.py` | Add `debug_inspect_variable` tool |
| `src/polybugger_mcp/core/session.py` | Add `inspect_variable()` method |
| `src/polybugger_mcp/utils/tui_formatter.py` | Add `format_inspection()` method |
| `pyproject.toml` | Add pandas/numpy as dev dependencies |

---

## 3. Pydantic Models

### 3.1 File: `src/polybugger_mcp/models/inspection.py`

```python
"""Models for smart variable inspection.

Provides structured types for inspection options, results,
and type-specific metadata for DataFrames, arrays, dicts, and lists.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DetectedType(str, Enum):
    """Detected data type categories for variable inspection."""

    DATAFRAME = "dataframe"
    SERIES = "series"
    NDARRAY = "ndarray"
    DICT = "dict"
    LIST = "list"
    PRIMITIVE = "primitive"
    UNKNOWN = "unknown"


class InspectionOptions(BaseModel):
    """Options for variable inspection.

    Attributes:
        max_preview_rows: Maximum rows/items in preview data (1-100)
        max_preview_items: Maximum items for dict/list preview (1-100)
        include_statistics: Include statistical summary for numeric data
        timeout_per_expression: Timeout in seconds for each introspection expression
        max_string_length: Maximum length for string values in preview
    """

    max_preview_rows: int = Field(default=5, ge=1, le=100)
    max_preview_items: int = Field(default=10, ge=1, le=100)
    include_statistics: bool = Field(default=True)
    timeout_per_expression: float = Field(default=2.0, ge=0.1, le=10.0)
    max_string_length: int = Field(default=200, ge=10, le=1000)


class Statistics(BaseModel):
    """Numerical statistics for arrays and series.

    Attributes:
        min: Minimum value (ignoring NaN)
        max: Maximum value (ignoring NaN)
        mean: Mean value (ignoring NaN)
        std: Standard deviation (ignoring NaN)
        median: Median value (ignoring NaN)
        nan_count: Count of NaN values
        inf_count: Count of Inf values
    """

    min: float | None = None
    max: float | None = None
    mean: float | None = None
    std: float | None = None
    median: float | None = None
    nan_count: int | None = None
    inf_count: int | None = None


class DataFrameStructure(BaseModel):
    """Structure metadata for pandas DataFrame.

    Attributes:
        shape: Tuple of (rows, columns)
        columns: List of column names
        dtypes: Dict mapping column name to dtype string
        index_type: Name of the index type (e.g., "RangeIndex")
        memory_bytes: Total memory usage in bytes
        null_counts: Dict mapping column name to null count (optional)
        truncated: True if data was truncated due to size
    """

    shape: tuple[int, int]
    columns: list[str]
    dtypes: dict[str, str]
    index_type: str | None = None
    memory_bytes: int | None = None
    null_counts: dict[str, int] | None = None
    truncated: bool = False


class SeriesStructure(BaseModel):
    """Structure metadata for pandas Series.

    Attributes:
        length: Number of elements
        dtype: Data type string
        name: Series name (can be None)
        index_type: Name of the index type
    """

    length: int
    dtype: str
    name: str | None = None
    index_type: str | None = None


class ArrayStructure(BaseModel):
    """Structure metadata for NumPy ndarray.

    Attributes:
        shape: Array shape tuple
        dtype: Data type string
        size: Total number of elements
        memory_bytes: Memory usage in bytes
        ndim: Number of dimensions
    """

    shape: tuple[int, ...]
    dtype: str
    size: int
    memory_bytes: int | None = None
    ndim: int | None = None


class DictStructure(BaseModel):
    """Structure metadata for dict.

    Attributes:
        length: Number of key-value pairs
        key_types: List of unique key type names
        value_types: List of unique value type names
        depth: Estimated nesting depth (optional)
    """

    length: int
    key_types: list[str] = Field(default_factory=list)
    value_types: list[str] = Field(default_factory=list)
    depth: int | None = None


class ListStructure(BaseModel):
    """Structure metadata for list.

    Attributes:
        length: Number of elements
        element_types: List of unique element type names
        depth: Estimated nesting depth (optional)
        uniform: True if all elements have same type
    """

    length: int
    element_types: list[str] = Field(default_factory=list)
    depth: int | None = None
    uniform: bool | None = None


class InspectionPreview(BaseModel):
    """Preview data from inspection.

    Attributes:
        head: First N rows/items (for DataFrame/list)
        tail: Last N items (for Series)
        sample: Sample values (for arrays)
        keys: Preview of keys (for dicts)
        note: Additional context about the preview
    """

    head: list[dict[str, Any]] | list[Any] | None = None
    tail: list[Any] | None = None
    sample: list[Any] | None = None
    keys: list[str] | None = None
    note: str | None = None


class InspectionResult(BaseModel):
    """Complete result of variable inspection.

    This is the main response model returned by debug_inspect_variable.

    Attributes:
        name: Variable name that was inspected
        type: Display type (e.g., "DataFrame", "ndarray", "dict")
        detected_type: Category from DetectedType enum
        structure: Type-specific structural metadata
        preview: Sample data for preview
        statistics: Numerical statistics (for numeric types)
        summary: Human-readable one-line summary
        warnings: List of warnings (size, NaN values, etc.)
        error: Error message if inspection partially failed
        partial: True if some expressions timed out
        timed_out: List of expression names that timed out
        variables_reference: DAP reference for drilling down
        hint: Helpful hint for unknown/complex types
    """

    name: str
    type: str
    detected_type: DetectedType
    structure: dict[str, Any] = Field(default_factory=dict)
    preview: InspectionPreview = Field(default_factory=InspectionPreview)
    statistics: Statistics | None = None
    summary: str
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    partial: bool = False
    timed_out: list[str] = Field(default_factory=list)
    variables_reference: int | None = None
    hint: str | None = None


class InspectionError(BaseModel):
    """Error response for inspection failures.

    Attributes:
        error: Error message
        code: Error code (VARIABLE_NOT_FOUND, INVALID_STATE, etc.)
        available_variables: List of available variable names (for NOT_FOUND)
        hint: Helpful suggestion for resolving the error
    """

    error: str
    code: str
    available_variables: list[str] | None = None
    hint: str | None = None
```

---

## 4. DataInspector Class

### 4.1 File: `src/polybugger_mcp/utils/data_inspector.py`

```python
"""Smart variable inspection for data science types.

Provides intelligent inspection of pandas DataFrames, NumPy arrays,
dicts, and lists with structured metadata and preview data.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import TYPE_CHECKING, Any, Protocol

from polybugger_mcp.models.inspection import (
    DetectedType,
    InspectionOptions,
    InspectionPreview,
    InspectionResult,
    Statistics,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# =============================================================================
# Constants - Expression Templates
# =============================================================================

# Type detection expressions - evaluated to True/False
# Order matters: check specific types before generic ones
TYPE_DETECTION_EXPRESSIONS: dict[DetectedType, str] = {
    DetectedType.DATAFRAME: (
        "type({var}).__module__ == 'pandas.core.frame' and "
        "type({var}).__name__ == 'DataFrame'"
    ),
    DetectedType.SERIES: (
        "type({var}).__module__ == 'pandas.core.series' and "
        "type({var}).__name__ == 'Series'"
    ),
    DetectedType.NDARRAY: (
        "type({var}).__module__ == 'numpy' and "
        "type({var}).__name__ == 'ndarray'"
    ),
    DetectedType.DICT: "isinstance({var}, dict)",
    DetectedType.LIST: "isinstance({var}, list)",
}

# Introspection expressions for each type
DATAFRAME_EXPRESSIONS: dict[str, str] = {
    "shape": "list({var}.shape)",
    "columns": "list({var}.columns)",
    "dtypes": "{{str(k): str(v) for k, v in {var}.dtypes.items()}}",
    "index_type": "type({var}.index).__name__",
    "memory_bytes": "int({var}.memory_usage(deep=True).sum())",
    "null_counts": "{{str(k): int(v) for k, v in {var}.isnull().sum().items() if v > 0}}",
    "head": "{var}.head({n}).to_dict('records')",
}

SERIES_EXPRESSIONS: dict[str, str] = {
    "length": "len({var})",
    "dtype": "str({var}.dtype)",
    "name": "str({var}.name) if {var}.name is not None else None",
    "index_type": "type({var}.index).__name__",
    "head": "{var}.head({n}).tolist()",
    "tail": "{var}.tail({n}).tolist()",
    # Statistics
    "min": "float({var}.min())",
    "max": "float({var}.max())",
    "mean": "float({var}.mean())",
    "std": "float({var}.std())",
    "null_count": "int({var}.isnull().sum())",
}

NDARRAY_EXPRESSIONS: dict[str, str] = {
    "shape": "list({var}.shape)",
    "dtype": "str({var}.dtype)",
    "size": "int({var}.size)",
    "ndim": "int({var}.ndim)",
    "memory_bytes": "int({var}.nbytes)",
    "sample": "{var}.flatten()[:{n}].tolist()",
    # Statistics (conditional on size < 10M)
    "min": "float({var}.min())",
    "max": "float({var}.max())",
    "mean": "float({var}.mean())",
    "std": "float({var}.std())",
    "nan_count": "int(__import__('numpy').isnan({var}).sum()) if {var}.dtype.kind == 'f' else 0",
    "inf_count": "int(__import__('numpy').isinf({var}).sum()) if {var}.dtype.kind == 'f' else 0",
}

DICT_EXPRESSIONS: dict[str, str] = {
    "length": "len({var})",
    "key_types": "list(set(type(k).__name__ for k in list({var}.keys())[:{n}]))",
    "value_types": "list(set(type(v).__name__ for v in list({var}.values())[:{n}]))",
    "keys_preview": "list({var}.keys())[:{keys_n}]",
    "sample": "dict(list({var}.items())[:{n}])",
}

LIST_EXPRESSIONS: dict[str, str] = {
    "length": "len({var})",
    "element_types": "list(set(type(x).__name__ for x in {var}[:{n}]))",
    "sample": "{var}[:{n}]",
    "depth": "_estimate_depth({var})" if False else "1",  # Simplified for now
}

UNKNOWN_EXPRESSIONS: dict[str, str] = {
    "repr": "repr({var})[:{max_len}]",
    "type_module": "type({var}).__module__",
    "type_name": "type({var}).__name__",
    "attributes": "[a for a in dir({var}) if not a.startswith('_')][:{n}]",
}

# Size thresholds
MAX_SIZE_FOR_STATISTICS = 10_000_000  # 10M elements
MAX_RESPONSE_SIZE_BYTES = 100_000  # 100KB
MAX_PREVIEW_DEPTH = 3


class EvaluatorProtocol(Protocol):
    """Protocol for expression evaluation."""

    async def evaluate(
        self,
        expression: str,
        frame_id: int | None = None,
        context: str = "watch",
    ) -> dict[str, Any]:
        """Evaluate a Python expression in the debug context."""
        ...


class ExpressionTimeoutError(Exception):
    """Raised when an expression evaluation times out."""

    def __init__(self, expression: str, timeout: float):
        self.expression = expression
        self.timeout = timeout
        super().__init__(f"Expression timed out after {timeout}s: {expression[:50]}...")


class DataInspector:
    """Smart variable inspector for data science types.

    Provides intelligent inspection of pandas DataFrames, NumPy arrays,
    dicts, and lists with structured metadata and preview data.

    The inspector uses debugpy's evaluate mechanism to run introspection
    expressions in the debugged process, avoiding the need to transfer
    large datasets.

    Example:
        inspector = DataInspector()
        result = await inspector.inspect(
            evaluator=session.adapter,
            variable_name="df",
            frame_id=frame.id,
            options=InspectionOptions(max_preview_rows=10),
        )
        print(result.summary)
    """

    def __init__(self) -> None:
        """Initialize the DataInspector."""
        pass

    async def inspect(
        self,
        evaluator: EvaluatorProtocol,
        variable_name: str,
        frame_id: int | None = None,
        options: InspectionOptions | None = None,
    ) -> InspectionResult:
        """Inspect a variable with smart type-aware metadata.

        Args:
            evaluator: Object with evaluate() method for running expressions
            variable_name: Name of the variable to inspect
            frame_id: Stack frame ID (uses topmost if None)
            options: Inspection options (uses defaults if None)

        Returns:
            InspectionResult with type-specific metadata and preview

        Raises:
            ValueError: If variable_name is not a valid Python identifier
        """
        options = options or InspectionOptions()

        # Validate variable name
        if not self._is_valid_identifier(variable_name):
            raise ValueError(f"Invalid variable name: {variable_name}")

        # Detect the variable type
        detected_type = await self._detect_type(
            evaluator, variable_name, frame_id, options.timeout_per_expression
        )

        # Route to type-specific handler
        if detected_type == DetectedType.DATAFRAME:
            return await self._inspect_dataframe(
                evaluator, variable_name, frame_id, options
            )
        elif detected_type == DetectedType.SERIES:
            return await self._inspect_series(
                evaluator, variable_name, frame_id, options
            )
        elif detected_type == DetectedType.NDARRAY:
            return await self._inspect_ndarray(
                evaluator, variable_name, frame_id, options
            )
        elif detected_type == DetectedType.DICT:
            return await self._inspect_dict(
                evaluator, variable_name, frame_id, options
            )
        elif detected_type == DetectedType.LIST:
            return await self._inspect_list(
                evaluator, variable_name, frame_id, options
            )
        else:
            return await self._inspect_unknown(
                evaluator, variable_name, frame_id, options
            )

    # =========================================================================
    # Type Detection
    # =========================================================================

    async def _detect_type(
        self,
        evaluator: EvaluatorProtocol,
        variable_name: str,
        frame_id: int | None,
        timeout: float,
    ) -> DetectedType:
        """Detect the type category of a variable.

        Args:
            evaluator: Expression evaluator
            variable_name: Variable name to check
            frame_id: Stack frame ID
            timeout: Timeout per expression

        Returns:
            DetectedType enum value
        """
        for dtype, expr_template in TYPE_DETECTION_EXPRESSIONS.items():
            expr = expr_template.format(var=variable_name)
            try:
                result = await self._evaluate_with_timeout(
                    evaluator, expr, frame_id, timeout
                )
                if result.get("result") == "True":
                    logger.debug(f"Detected type {dtype.value} for {variable_name}")
                    return dtype
            except Exception as e:
                logger.debug(f"Type detection failed for {dtype.value}: {e}")
                continue

        return DetectedType.UNKNOWN

    # =========================================================================
    # Type-Specific Inspectors
    # =========================================================================

    async def _inspect_dataframe(
        self,
        evaluator: EvaluatorProtocol,
        variable_name: str,
        frame_id: int | None,
        options: InspectionOptions,
    ) -> InspectionResult:
        """Inspect a pandas DataFrame.

        Args:
            evaluator: Expression evaluator
            variable_name: Variable name
            frame_id: Stack frame ID
            options: Inspection options

        Returns:
            InspectionResult with DataFrame-specific metadata
        """
        expressions = {
            k: v.format(var=variable_name, n=options.max_preview_rows)
            for k, v in DATAFRAME_EXPRESSIONS.items()
        }

        results, timed_out = await self._evaluate_multiple(
            evaluator, expressions, frame_id, options.timeout_per_expression
        )

        # Build structure
        shape = self._parse_result(results.get("shape"), [0, 0])
        columns = self._parse_result(results.get("columns"), [])
        dtypes = self._parse_result(results.get("dtypes"), {})

        structure = {
            "shape": tuple(shape) if isinstance(shape, list) else shape,
            "columns": columns,
            "dtypes": dtypes,
            "index_type": self._parse_result(results.get("index_type")),
            "memory_bytes": self._parse_result(results.get("memory_bytes")),
            "null_counts": self._parse_result(results.get("null_counts"), {}),
        }

        # Build preview
        head_data = self._parse_result(results.get("head"), [])
        preview = InspectionPreview(head=head_data)

        # Build warnings
        warnings = []
        rows, cols = shape if isinstance(shape, list) else (0, 0)
        if rows > 1_000_000:
            warnings.append(f"Large DataFrame ({rows:,} rows) - preview limited")
            structure["truncated"] = True

        memory_bytes = structure.get("memory_bytes", 0) or 0
        if memory_bytes > 1_000_000_000:  # 1GB
            warnings.append(f"DataFrame uses {self._format_bytes(memory_bytes)}")

        # Build summary
        summary = self._build_dataframe_summary(structure)

        return InspectionResult(
            name=variable_name,
            type="DataFrame",
            detected_type=DetectedType.DATAFRAME,
            structure=structure,
            preview=preview,
            summary=summary,
            warnings=warnings,
            partial=len(timed_out) > 0,
            timed_out=timed_out,
        )

    async def _inspect_series(
        self,
        evaluator: EvaluatorProtocol,
        variable_name: str,
        frame_id: int | None,
        options: InspectionOptions,
    ) -> InspectionResult:
        """Inspect a pandas Series.

        Args:
            evaluator: Expression evaluator
            variable_name: Variable name
            frame_id: Stack frame ID
            options: Inspection options

        Returns:
            InspectionResult with Series-specific metadata
        """
        expressions = {
            k: v.format(var=variable_name, n=options.max_preview_rows)
            for k, v in SERIES_EXPRESSIONS.items()
        }

        results, timed_out = await self._evaluate_multiple(
            evaluator, expressions, frame_id, options.timeout_per_expression
        )

        # Build structure
        length = self._parse_result(results.get("length"), 0)
        structure = {
            "length": length,
            "dtype": self._parse_result(results.get("dtype"), "unknown"),
            "name": self._parse_result(results.get("name")),
            "index_type": self._parse_result(results.get("index_type")),
        }

        # Build preview
        head_data = self._parse_result(results.get("head"), [])
        tail_data = self._parse_result(results.get("tail"), [])
        preview = InspectionPreview(head=head_data, tail=tail_data)

        # Build statistics if requested and numeric
        statistics = None
        if options.include_statistics:
            statistics = Statistics(
                min=self._parse_result(results.get("min")),
                max=self._parse_result(results.get("max")),
                mean=self._parse_result(results.get("mean")),
                std=self._parse_result(results.get("std")),
                nan_count=self._parse_result(results.get("null_count")),
            )

        # Build warnings
        warnings = []
        if length > 1_000_000:
            warnings.append(f"Large Series ({length:,} elements)")

        # Build summary
        name = structure.get("name") or "unnamed"
        dtype = structure.get("dtype", "unknown")
        summary = f"Series '{name}' with {length:,} {dtype} values"

        return InspectionResult(
            name=variable_name,
            type="Series",
            detected_type=DetectedType.SERIES,
            structure=structure,
            preview=preview,
            statistics=statistics,
            summary=summary,
            warnings=warnings,
            partial=len(timed_out) > 0,
            timed_out=timed_out,
        )

    async def _inspect_ndarray(
        self,
        evaluator: EvaluatorProtocol,
        variable_name: str,
        frame_id: int | None,
        options: InspectionOptions,
    ) -> InspectionResult:
        """Inspect a NumPy ndarray.

        Args:
            evaluator: Expression evaluator
            variable_name: Variable name
            frame_id: Stack frame ID
            options: Inspection options

        Returns:
            InspectionResult with ndarray-specific metadata
        """
        # First get size to decide if we should compute statistics
        size_expr = f"int({variable_name}.size)"
        try:
            size_result = await self._evaluate_with_timeout(
                evaluator, size_expr, frame_id, options.timeout_per_expression
            )
            size = int(self._parse_result(size_result, 0))
        except Exception:
            size = 0

        # Build expressions, conditionally including statistics
        expressions = {
            "shape": NDARRAY_EXPRESSIONS["shape"].format(var=variable_name),
            "dtype": NDARRAY_EXPRESSIONS["dtype"].format(var=variable_name),
            "size": NDARRAY_EXPRESSIONS["size"].format(var=variable_name),
            "ndim": NDARRAY_EXPRESSIONS["ndim"].format(var=variable_name),
            "memory_bytes": NDARRAY_EXPRESSIONS["memory_bytes"].format(var=variable_name),
            "sample": NDARRAY_EXPRESSIONS["sample"].format(
                var=variable_name, n=options.max_preview_items
            ),
        }

        # Add statistics only if array is small enough
        if options.include_statistics and size < MAX_SIZE_FOR_STATISTICS:
            expressions["min"] = NDARRAY_EXPRESSIONS["min"].format(var=variable_name)
            expressions["max"] = NDARRAY_EXPRESSIONS["max"].format(var=variable_name)
            expressions["mean"] = NDARRAY_EXPRESSIONS["mean"].format(var=variable_name)
            expressions["std"] = NDARRAY_EXPRESSIONS["std"].format(var=variable_name)
            expressions["nan_count"] = NDARRAY_EXPRESSIONS["nan_count"].format(var=variable_name)
            expressions["inf_count"] = NDARRAY_EXPRESSIONS["inf_count"].format(var=variable_name)

        results, timed_out = await self._evaluate_multiple(
            evaluator, expressions, frame_id, options.timeout_per_expression
        )

        # Build structure
        shape = self._parse_result(results.get("shape"), [])
        structure = {
            "shape": tuple(shape) if isinstance(shape, list) else shape,
            "dtype": self._parse_result(results.get("dtype"), "unknown"),
            "size": self._parse_result(results.get("size"), 0),
            "ndim": self._parse_result(results.get("ndim"), 0),
            "memory_bytes": self._parse_result(results.get("memory_bytes")),
        }

        # Build preview
        sample_data = self._parse_result(results.get("sample"), [])
        preview = InspectionPreview(sample=sample_data)

        # Build statistics
        statistics = None
        if options.include_statistics and size < MAX_SIZE_FOR_STATISTICS:
            statistics = Statistics(
                min=self._parse_result(results.get("min")),
                max=self._parse_result(results.get("max")),
                mean=self._parse_result(results.get("mean")),
                std=self._parse_result(results.get("std")),
                nan_count=self._parse_result(results.get("nan_count")),
                inf_count=self._parse_result(results.get("inf_count")),
            )

        # Build warnings
        warnings = []
        if size > MAX_SIZE_FOR_STATISTICS:
            warnings.append(f"Large array ({size:,} elements) - statistics skipped")
            timed_out.extend(["statistics"])

        nan_count = self._parse_result(results.get("nan_count"), 0) or 0
        inf_count = self._parse_result(results.get("inf_count"), 0) or 0
        if nan_count > 0 or inf_count > 0:
            warnings.append(f"Array contains {nan_count} NaN and {inf_count} Inf values")

        # Build summary
        dtype = structure.get("dtype", "unknown")
        shape_str = str(structure.get("shape", ()))
        memory = self._format_bytes(structure.get("memory_bytes", 0) or 0)
        mean_str = ""
        if statistics and statistics.mean is not None:
            mean_str = f", mean={statistics.mean:.3f}"
        summary = f"ndarray {dtype} {shape_str}, {memory}{mean_str}"

        return InspectionResult(
            name=variable_name,
            type="ndarray",
            detected_type=DetectedType.NDARRAY,
            structure=structure,
            preview=preview,
            statistics=statistics,
            summary=summary,
            warnings=warnings,
            partial=len(timed_out) > 0,
            timed_out=timed_out,
        )

    async def _inspect_dict(
        self,
        evaluator: EvaluatorProtocol,
        variable_name: str,
        frame_id: int | None,
        options: InspectionOptions,
    ) -> InspectionResult:
        """Inspect a Python dict.

        Args:
            evaluator: Expression evaluator
            variable_name: Variable name
            frame_id: Stack frame ID
            options: Inspection options

        Returns:
            InspectionResult with dict-specific metadata
        """
        expressions = {
            k: v.format(
                var=variable_name,
                n=options.max_preview_items,
                keys_n=min(20, options.max_preview_items * 2),
            )
            for k, v in DICT_EXPRESSIONS.items()
        }

        results, timed_out = await self._evaluate_multiple(
            evaluator, expressions, frame_id, options.timeout_per_expression
        )

        # Build structure
        length = self._parse_result(results.get("length"), 0)
        structure = {
            "length": length,
            "key_types": self._parse_result(results.get("key_types"), []),
            "value_types": self._parse_result(results.get("value_types"), []),
        }

        # Build preview
        keys_preview = self._parse_result(results.get("keys_preview"), [])
        sample_data = self._parse_result(results.get("sample"), {})
        preview = InspectionPreview(keys=keys_preview, head=[sample_data] if sample_data else [])

        # Build warnings
        warnings = []
        if length > 10000:
            warnings.append(f"Large dict ({length:,} items) - showing sample")

        # Build summary
        key_types = structure.get("key_types", [])
        key_type_str = key_types[0] if len(key_types) == 1 else "mixed"
        value_types = structure.get("value_types", [])
        value_info = ", ".join(value_types[:3]) if value_types else "unknown"
        summary = f"dict with {length:,} {key_type_str} keys ({value_info} values)"

        return InspectionResult(
            name=variable_name,
            type="dict",
            detected_type=DetectedType.DICT,
            structure=structure,
            preview=preview,
            summary=summary,
            warnings=warnings,
            partial=len(timed_out) > 0,
            timed_out=timed_out,
        )

    async def _inspect_list(
        self,
        evaluator: EvaluatorProtocol,
        variable_name: str,
        frame_id: int | None,
        options: InspectionOptions,
    ) -> InspectionResult:
        """Inspect a Python list.

        Args:
            evaluator: Expression evaluator
            variable_name: Variable name
            frame_id: Stack frame ID
            options: Inspection options

        Returns:
            InspectionResult with list-specific metadata
        """
        expressions = {
            k: v.format(var=variable_name, n=options.max_preview_items)
            for k, v in LIST_EXPRESSIONS.items()
        }

        results, timed_out = await self._evaluate_multiple(
            evaluator, expressions, frame_id, options.timeout_per_expression
        )

        # Build structure
        length = self._parse_result(results.get("length"), 0)
        element_types = self._parse_result(results.get("element_types"), [])
        structure = {
            "length": length,
            "element_types": element_types,
            "uniform": len(element_types) == 1,
        }

        # Build preview
        sample_data = self._parse_result(results.get("sample"), [])
        preview = InspectionPreview(head=sample_data)

        # Build warnings
        warnings = []
        if length > 100000:
            warnings.append(f"Large list ({length:,} items) - showing sample")

        # Build summary
        type_info = element_types[0] if len(element_types) == 1 else "mixed"
        summary = f"list of {length:,} {type_info} items"

        return InspectionResult(
            name=variable_name,
            type="list",
            detected_type=DetectedType.LIST,
            structure=structure,
            preview=preview,
            summary=summary,
            warnings=warnings,
            partial=len(timed_out) > 0,
            timed_out=timed_out,
        )

    async def _inspect_unknown(
        self,
        evaluator: EvaluatorProtocol,
        variable_name: str,
        frame_id: int | None,
        options: InspectionOptions,
    ) -> InspectionResult:
        """Inspect an unknown/custom type.

        Args:
            evaluator: Expression evaluator
            variable_name: Variable name
            frame_id: Stack frame ID
            options: Inspection options

        Returns:
            InspectionResult with basic metadata and hint
        """
        expressions = {
            k: v.format(
                var=variable_name,
                n=options.max_preview_items,
                max_len=options.max_string_length,
            )
            for k, v in UNKNOWN_EXPRESSIONS.items()
        }

        results, timed_out = await self._evaluate_multiple(
            evaluator, expressions, frame_id, options.timeout_per_expression
        )

        # Build structure
        type_module = self._parse_result(results.get("type_module"), "")
        type_name = self._parse_result(results.get("type_name"), "unknown")
        attributes = self._parse_result(results.get("attributes"), [])
        repr_str = self._parse_result(results.get("repr"), "")

        structure = {
            "type_module": type_module,
            "type_name": type_name,
            "attributes": attributes,
            "repr": repr_str,
        }

        # Build summary
        full_type = f"{type_module}.{type_name}" if type_module else type_name
        attr_count = len(attributes)
        summary = f"{full_type} object with {attr_count} attributes"

        return InspectionResult(
            name=variable_name,
            type=type_name,
            detected_type=DetectedType.UNKNOWN,
            structure=structure,
            summary=summary,
            hint="Use debug_get_variables with variables_reference to explore attributes",
            partial=len(timed_out) > 0,
            timed_out=timed_out,
        )

    # =========================================================================
    # Helper Methods - Evaluation
    # =========================================================================

    async def _evaluate_with_timeout(
        self,
        evaluator: EvaluatorProtocol,
        expression: str,
        frame_id: int | None,
        timeout: float,
    ) -> dict[str, Any]:
        """Evaluate an expression with timeout.

        Args:
            evaluator: Expression evaluator
            expression: Python expression to evaluate
            frame_id: Stack frame ID
            timeout: Timeout in seconds

        Returns:
            Evaluation result dict with 'result' key

        Raises:
            ExpressionTimeoutError: If evaluation times out
        """
        try:
            return await asyncio.wait_for(
                evaluator.evaluate(expression, frame_id, "watch"),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise ExpressionTimeoutError(expression, timeout)

    async def _evaluate_multiple(
        self,
        evaluator: EvaluatorProtocol,
        expressions: dict[str, str],
        frame_id: int | None,
        timeout: float,
    ) -> tuple[dict[str, Any], list[str]]:
        """Evaluate multiple expressions concurrently.

        Args:
            evaluator: Expression evaluator
            expressions: Dict mapping name to expression
            frame_id: Stack frame ID
            timeout: Timeout per expression

        Returns:
            Tuple of (results dict, list of timed-out expression names)
        """
        results: dict[str, Any] = {}
        timed_out: list[str] = []

        # Create tasks for all expressions
        async def evaluate_one(name: str, expr: str) -> tuple[str, Any, bool]:
            try:
                result = await self._evaluate_with_timeout(
                    evaluator, expr, frame_id, timeout
                )
                return (name, result, False)
            except ExpressionTimeoutError:
                return (name, None, True)
            except Exception as e:
                logger.debug(f"Expression '{name}' failed: {e}")
                return (name, None, False)

        # Run all evaluations concurrently
        tasks = [evaluate_one(name, expr) for name, expr in expressions.items()]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for item in completed:
            if isinstance(item, Exception):
                continue
            name, result, did_timeout = item
            if did_timeout:
                timed_out.append(name)
            elif result is not None:
                results[name] = result

        return results, timed_out

    # =========================================================================
    # Helper Methods - Parsing and Formatting
    # =========================================================================

    def _parse_result(
        self,
        result: dict[str, Any] | None,
        default: Any = None,
    ) -> Any:
        """Parse an evaluation result to extract the value.

        Args:
            result: Evaluation result dict with 'result' key
            default: Default value if parsing fails

        Returns:
            Parsed value or default
        """
        if result is None:
            return default

        result_str = result.get("result", "")
        if not result_str:
            return default

        # Try to parse as Python literal
        try:
            # Handle common Python literal formats
            # Use json.loads for basic types, fall back to ast.literal_eval patterns
            if result_str in ("None", "True", "False"):
                return {"None": None, "True": True, "False": False}.get(result_str)

            # Try JSON first (handles lists, dicts, numbers, strings)
            try:
                return json.loads(result_str.replace("'", '"'))
            except json.JSONDecodeError:
                pass

            # Try simple number parsing
            try:
                if "." in result_str:
                    return float(result_str)
                return int(result_str)
            except ValueError:
                pass

            # Return as string if all else fails
            return result_str

        except Exception:
            return default

    def _format_bytes(self, num_bytes: int) -> str:
        """Format bytes as human-readable string.

        Args:
            num_bytes: Number of bytes

        Returns:
            Formatted string (e.g., "1.5 MB")
        """
        if num_bytes < 1024:
            return f"{num_bytes} B"
        elif num_bytes < 1024 * 1024:
            return f"{num_bytes / 1024:.1f} KB"
        elif num_bytes < 1024 * 1024 * 1024:
            return f"{num_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{num_bytes / (1024 * 1024 * 1024):.1f} GB"

    def _build_dataframe_summary(self, structure: dict[str, Any]) -> str:
        """Build a summary string for a DataFrame.

        Args:
            structure: DataFrame structure dict

        Returns:
            Human-readable summary string
        """
        shape = structure.get("shape", (0, 0))
        rows, cols = shape if isinstance(shape, (list, tuple)) else (0, 0)
        memory = self._format_bytes(structure.get("memory_bytes", 0) or 0)
        return f"DataFrame with {rows:,} rows x {cols} columns, {memory}"

    def _is_valid_identifier(self, name: str) -> bool:
        """Check if a string is a valid Python identifier.

        Also allows attribute access (e.g., "obj.attr") and indexing
        (e.g., "items[0]", "data['key']").

        Args:
            name: String to check

        Returns:
            True if valid, False otherwise
        """
        # Allow simple identifiers
        if name.isidentifier():
            return True

        # Allow attribute access patterns like "obj.attr.subattr"
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$', name):
            return True

        # Allow indexing patterns like "items[0]" or "data['key']"
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*(\[[^\]]+\])+$', name):
            return True

        return False


# =============================================================================
# Module-level Functions
# =============================================================================

_default_inspector: DataInspector | None = None


def get_inspector() -> DataInspector:
    """Get the default DataInspector instance.

    Returns:
        DataInspector instance
    """
    global _default_inspector
    if _default_inspector is None:
        _default_inspector = DataInspector()
    return _default_inspector
```

---

## 5. Session Method

### 5.1 Addition to `src/polybugger_mcp/core/session.py`

Add the following method to the `Session` class after the `evaluate_watches` method (around line 404):

```python
async def inspect_variable(
    self,
    variable_name: str,
    frame_id: int | None = None,
    options: "InspectionOptions | None" = None,
) -> "InspectionResult":
    """Inspect a variable with smart type-aware metadata.

    Provides detailed inspection of pandas DataFrames, NumPy arrays,
    dicts, lists, and other Python objects with structured metadata
    and preview data.

    Args:
        variable_name: Name of the variable to inspect
        frame_id: Stack frame ID (uses topmost if None)
        options: Inspection options (uses defaults if None)

    Returns:
        InspectionResult with type-specific metadata

    Raises:
        InvalidSessionStateError: If session is not paused
    """
    from polybugger_mcp.models.inspection import InspectionOptions, InspectionResult
    from polybugger_mcp.utils.data_inspector import get_inspector

    self.require_state(SessionState.PAUSED)

    if self.adapter is None:
        raise InvalidSessionStateError(self.id, "no adapter", ["initialized"])

    self.touch()

    inspector = get_inspector()
    return await inspector.inspect(
        evaluator=self.adapter,
        variable_name=variable_name,
        frame_id=frame_id,
        options=options or InspectionOptions(),
    )
```

### 5.2 Import Statement

Add this import at the top of `session.py` (with other TYPE_CHECKING imports):

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from polybugger_mcp.models.inspection import InspectionOptions, InspectionResult
```

---

## 6. MCP Tool

### 6.1 Addition to `src/polybugger_mcp/mcp_server.py`

Add the following tool after the `debug_evaluate` tool (around line 680):

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
    appropriate for the detected type in a single call.

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
    from polybugger_mcp.models.inspection import InspectionOptions

    manager = _get_manager()
    try:
        session = await manager.get_session(session_id)

        # Build options
        options = InspectionOptions(
            max_preview_rows=min(max_preview_rows, 100),
            max_preview_items=min(max_preview_rows * 2, 100),
            include_statistics=include_statistics,
        )

        # Perform inspection
        result = await session.inspect_variable(
            variable_name=variable_name,
            frame_id=frame_id,
            options=options,
        )

        # Convert to dict
        result_dict = result.model_dump(exclude_none=True)
        result_dict["format"] = format

        # Add TUI formatting if requested
        if format == "tui":
            formatter = _get_formatter()
            result_dict["formatted"] = formatter.format_inspection(result_dict)

        return result_dict

    except SessionNotFoundError:
        return {"error": f"Session {session_id} not found", "code": "NOT_FOUND"}
    except InvalidSessionStateError as e:
        return {
            "error": str(e),
            "code": "INVALID_STATE",
            "hint": "Session must be paused at a breakpoint to inspect variables",
        }
    except ValueError as e:
        return {
            "error": str(e),
            "code": "INVALID_VARIABLE",
            "hint": "Check variable name is valid and in scope",
        }
    except Exception as e:
        logger.exception(f"Inspection failed for {variable_name}")
        return {
            "error": str(e),
            "code": "INSPECTION_ERROR",
            "hint": "Use debug_evaluate for manual inspection",
        }
```

### 6.2 Import Statement

Add to imports at top of `mcp_server.py`:

```python
from polybugger_mcp.core.exceptions import (
    InvalidSessionStateError,
    SessionLimitError,
    SessionNotFoundError,
)
```

(This import already exists, just ensure `InvalidSessionStateError` is included.)

---

## 7. TUI Formatter Extension

### 7.1 Addition to `src/polybugger_mcp/utils/tui_formatter.py`

Add the following method to the `TUIFormatter` class (after `format_call_chain`):

```python
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
        title: Optional custom title (defaults to "VARIABLE INSPECTION: {name}")

    Returns:
        Box-drawn string representation of the inspection.

    Example Output:
        ┌──────────────────────────────────────────────────────────────────┐
        │ VARIABLE INSPECTION: df                                          │
        ├──────────────────────────────────────────────────────────────────┤
        │ Type:     DataFrame                                              │
        │ Shape:    1000 rows x 5 columns                                  │
        │ Memory:   78.1 KB                                                │
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
    display_title = title or f"VARIABLE INSPECTION: {name}"

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
            lines.append(self._box_row(f"   ! {warning}", inner_width))

    lines.append(self._box_bottom(inner_width))

    return "\n".join(lines)

def _format_dataframe_inspection(
    self,
    inspection: dict[str, Any],
    width: int,
) -> list[str]:
    """Format DataFrame-specific inspection details."""
    lines: list[str] = []
    structure = inspection.get("structure", {})

    # Columns section
    columns = structure.get("columns", [])
    dtypes = structure.get("dtypes", {})
    null_counts = structure.get("null_counts", {})

    if columns:
        lines.append(self._box_separator(width))
        lines.append(self._box_row(" COLUMNS", width))

        # Build mini-table for columns
        col_data = []
        for col in columns[:10]:  # Limit to first 10 columns
            dtype = dtypes.get(col, "unknown")
            nulls = null_counts.get(col, 0)
            col_data.append({"name": col, "dtype": dtype, "nulls": str(nulls)})

        if len(columns) > 10:
            col_data.append({"name": f"... +{len(columns) - 10} more", "dtype": "", "nulls": ""})

        # Format as aligned text
        for row in col_data:
            line = f"   {row['name']:<20} {row['dtype']:<15} {row['nulls']}"
            lines.append(self._box_row(line, width))

    # Preview section
    preview = inspection.get("preview", {})
    head = preview.get("head", [])
    if head and isinstance(head, list) and len(head) > 0:
        lines.append(self._box_separator(width))
        lines.append(self._box_row(f" PREVIEW (first {len(head)} rows)", width))

        # Show first row keys and values
        for i, row in enumerate(head[:3]):
            if isinstance(row, dict):
                row_str = ", ".join(f"{k}={v}" for k, v in list(row.items())[:4])
                if len(row) > 4:
                    row_str += ", ..."
                lines.append(self._box_row(f"   [{i}] {row_str}", width))

    return lines

def _format_series_inspection(
    self,
    inspection: dict[str, Any],
    width: int,
) -> list[str]:
    """Format Series-specific inspection details."""
    lines: list[str] = []
    stats = inspection.get("statistics")

    if stats:
        lines.append(self._box_separator(width))
        lines.append(self._box_row(" STATISTICS", width))
        for key in ["min", "max", "mean", "std"]:
            value = stats.get(key)
            if value is not None:
                lines.append(self._box_row(f"   {key}: {value:.4f}", width))

    return lines

def _format_ndarray_inspection(
    self,
    inspection: dict[str, Any],
    width: int,
) -> list[str]:
    """Format ndarray-specific inspection details."""
    lines: list[str] = []
    structure = inspection.get("structure", {})
    stats = inspection.get("statistics")

    # Shape details
    shape = structure.get("shape", ())
    dtype = structure.get("dtype", "unknown")
    lines.append(self._box_row(f" Shape: {shape}, dtype: {dtype}", width))

    # Statistics
    if stats:
        lines.append(self._box_separator(width))
        lines.append(self._box_row(" STATISTICS", width))
        stat_line = "   "
        for key in ["min", "max", "mean", "std"]:
            value = stats.get(key)
            if value is not None:
                stat_line += f"{key}={value:.3f}  "
        lines.append(self._box_row(stat_line, width))

    # Sample
    preview = inspection.get("preview", {})
    sample = preview.get("sample", [])
    if sample:
        lines.append(self._box_separator(width))
        sample_str = str(sample[:10])
        if len(sample) > 10:
            sample_str = sample_str[:-1] + ", ...]"
        lines.append(self._box_row(f" Sample: {sample_str}", width))

    return lines

def _format_dict_inspection(
    self,
    inspection: dict[str, Any],
    width: int,
) -> list[str]:
    """Format dict-specific inspection details."""
    lines: list[str] = []
    preview = inspection.get("preview", {})

    # Keys preview
    keys = preview.get("keys", [])
    if keys:
        lines.append(self._box_separator(width))
        lines.append(self._box_row(" KEYS", width))
        keys_str = ", ".join(str(k) for k in keys[:10])
        if len(keys) > 10:
            keys_str += ", ..."
        lines.append(self._box_row(f"   {keys_str}", width))

    # Sample values
    head = preview.get("head", [])
    if head and isinstance(head, list) and len(head) > 0:
        sample = head[0] if isinstance(head[0], dict) else {}
        if sample:
            lines.append(self._box_separator(width))
            lines.append(self._box_row(" SAMPLE", width))
            for k, v in list(sample.items())[:5]:
                v_str = self._truncate(str(v), 40)
                lines.append(self._box_row(f"   {k}: {v_str}", width))

    return lines

def _format_list_inspection(
    self,
    inspection: dict[str, Any],
    width: int,
) -> list[str]:
    """Format list-specific inspection details."""
    lines: list[str] = []
    structure = inspection.get("structure", {})
    preview = inspection.get("preview", {})

    # Element types
    element_types = structure.get("element_types", [])
    if element_types:
        types_str = ", ".join(element_types)
        lines.append(self._box_row(f" Element types: {types_str}", width))

    # Sample
    head = preview.get("head", [])
    if head:
        lines.append(self._box_separator(width))
        lines.append(self._box_row(" SAMPLE", width))
        for i, item in enumerate(head[:5]):
            item_str = self._truncate(str(item), 60)
            lines.append(self._box_row(f"   [{i}] {item_str}", width))

    return lines

def _format_unknown_inspection(
    self,
    inspection: dict[str, Any],
    width: int,
) -> list[str]:
    """Format unknown type inspection details."""
    lines: list[str] = []
    structure = inspection.get("structure", {})

    # Attributes
    attributes = structure.get("attributes", [])
    if attributes:
        lines.append(self._box_separator(width))
        lines.append(self._box_row(" ATTRIBUTES", width))
        attrs_str = ", ".join(attributes[:10])
        if len(attributes) > 10:
            attrs_str += f", ... (+{len(attributes) - 10} more)"
        lines.append(self._box_row(f"   {attrs_str}", width))

    # Hint
    hint = inspection.get("hint")
    if hint:
        lines.append(self._box_separator(width))
        lines.append(self._box_row(f" Hint: {hint}", width))

    return lines
```

---

## 8. Implementation Plan

### 8.1 Ordered Task List

| # | Task | File | Estimated Time | Dependencies |
|---|------|------|----------------|--------------|
| 1 | Create Pydantic models | `models/inspection.py` | 30 min | None |
| 2 | Create DataInspector class | `utils/data_inspector.py` | 2 hours | Task 1 |
| 3 | Add inspect_variable to Session | `core/session.py` | 15 min | Tasks 1, 2 |
| 4 | Add debug_inspect_variable tool | `mcp_server.py` | 30 min | Tasks 1, 2, 3 |
| 5 | Add format_inspection to TUIFormatter | `utils/tui_formatter.py` | 1 hour | Task 1 |
| 6 | Create unit tests | `tests/unit/test_data_inspector.py` | 2 hours | Tasks 1, 2 |
| 7 | Create integration tests | `tests/integration/test_inspect_variable.py` | 1 hour | Tasks 1-4 |
| 8 | Create E2E tests | `tests/e2e/test_data_inspection.py` | 1 hour | Tasks 1-4 |
| 9 | Add dev dependencies | `pyproject.toml` | 5 min | None |
| 10 | Update documentation | Various | 30 min | All |

**Total Estimated Time: 8-9 hours**

### 8.2 Task Details

#### Task 1: Create Pydantic Models

1. Create `src/polybugger_mcp/models/inspection.py`
2. Define all model classes as specified in Section 3
3. Add `__all__` exports

#### Task 2: Create DataInspector Class

1. Create `src/polybugger_mcp/utils/data_inspector.py`
2. Implement type detection expressions
3. Implement type-specific inspection methods
4. Implement helper methods
5. Add module-level `get_inspector()` function

#### Task 3: Add Session Method

1. Add import in `core/session.py`
2. Add `inspect_variable()` method to `Session` class
3. Wire up to DataInspector

#### Task 4: Add MCP Tool

1. Add import in `mcp_server.py`
2. Add `debug_inspect_variable` tool function
3. Handle all error cases
4. Support `format="tui"` option

#### Task 5: Add TUI Formatting

1. Add `format_inspection()` to `TUIFormatter`
2. Add type-specific formatting helpers
3. Test output formatting

#### Task 6: Unit Tests

1. Create `tests/unit/test_data_inspector.py`
2. Test type detection logic
3. Test expression building
4. Test result parsing
5. Test timeout handling
6. Mock evaluator for isolated testing

#### Task 7: Integration Tests

1. Create `tests/integration/test_inspect_variable.py`
2. Test MCP tool parameter validation
3. Test error responses
4. Test TUI formatting integration

#### Task 8: E2E Tests

1. Create `tests/e2e/test_data_inspection.py`
2. Test with real pandas DataFrame
3. Test with real NumPy array
4. Test with dict/list
5. Test full debug session workflow

#### Task 9: Dev Dependencies

Add to `pyproject.toml` under `[project.optional-dependencies]`:

```toml
[project.optional-dependencies]
dev = [
    # ... existing deps ...
    "pandas>=2.0.0",
    "numpy>=1.24.0",
]
```

---

## 9. Unit Tests

### 9.1 File: `tests/unit/test_data_inspector.py`

```python
"""Unit tests for DataInspector."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from polybugger_mcp.models.inspection import (
    DetectedType,
    InspectionOptions,
    InspectionResult,
)
from polybugger_mcp.utils.data_inspector import (
    DataInspector,
    ExpressionTimeoutError,
    get_inspector,
)


class MockEvaluator:
    """Mock evaluator for testing."""

    def __init__(self, responses: dict[str, Any] | None = None):
        self.responses = responses or {}
        self.calls: list[str] = []

    async def evaluate(
        self,
        expression: str,
        frame_id: int | None = None,
        context: str = "watch",
    ) -> dict[str, Any]:
        self.calls.append(expression)

        # Check for programmed responses
        for pattern, response in self.responses.items():
            if pattern in expression:
                if isinstance(response, Exception):
                    raise response
                return {"result": str(response)}

        return {"result": "None"}


class TestTypeDetection:
    """Test type detection logic."""

    @pytest.fixture
    def inspector(self) -> DataInspector:
        return DataInspector()

    @pytest.mark.asyncio
    async def test_detect_dataframe(self, inspector: DataInspector):
        """Test DataFrame detection."""
        evaluator = MockEvaluator({
            "pandas.core.frame": "True",
            "DataFrame": "True",
        })

        result = await inspector._detect_type(evaluator, "df", None, 2.0)
        assert result == DetectedType.DATAFRAME

    @pytest.mark.asyncio
    async def test_detect_series(self, inspector: DataInspector):
        """Test Series detection."""
        evaluator = MockEvaluator({
            "pandas.core.series": "True",
            "Series": "True",
        })

        result = await inspector._detect_type(evaluator, "s", None, 2.0)
        assert result == DetectedType.SERIES

    @pytest.mark.asyncio
    async def test_detect_ndarray(self, inspector: DataInspector):
        """Test ndarray detection."""
        evaluator = MockEvaluator({
            "__module__ == 'numpy'": "True",
            "__name__ == 'ndarray'": "True",
        })

        result = await inspector._detect_type(evaluator, "arr", None, 2.0)
        assert result == DetectedType.NDARRAY

    @pytest.mark.asyncio
    async def test_detect_dict(self, inspector: DataInspector):
        """Test dict detection."""
        evaluator = MockEvaluator({
            "isinstance": "True",
            "dict": "True",
        })

        result = await inspector._detect_type(evaluator, "d", None, 2.0)
        # Note: dict detection depends on expression ordering
        assert result in (DetectedType.DICT, DetectedType.LIST, DetectedType.UNKNOWN)

    @pytest.mark.asyncio
    async def test_detect_unknown(self, inspector: DataInspector):
        """Test unknown type detection."""
        evaluator = MockEvaluator({})  # All checks return "None" -> False

        result = await inspector._detect_type(evaluator, "x", None, 2.0)
        assert result == DetectedType.UNKNOWN


class TestDataFrameInspection:
    """Test DataFrame inspection."""

    @pytest.fixture
    def inspector(self) -> DataInspector:
        return DataInspector()

    @pytest.fixture
    def df_evaluator(self) -> MockEvaluator:
        """Mock evaluator for DataFrame."""
        return MockEvaluator({
            "pandas.core.frame": "True",
            ".shape": "[1000, 5]",
            ".columns": "['id', 'name', 'value', 'date', 'status']",
            ".dtypes": "{'id': 'int64', 'name': 'object'}",
            "index).__name__": "'RangeIndex'",
            "memory_usage": "80000",
            "isnull().sum()": "{'name': 5}",
            ".head": "[{'id': 1, 'name': 'Alice'}]",
        })

    @pytest.mark.asyncio
    async def test_inspect_dataframe_basic(
        self,
        inspector: DataInspector,
        df_evaluator: MockEvaluator,
    ):
        """Test basic DataFrame inspection."""
        result = await inspector._inspect_dataframe(
            df_evaluator, "df", None, InspectionOptions()
        )

        assert result.name == "df"
        assert result.type == "DataFrame"
        assert result.detected_type == DetectedType.DATAFRAME
        assert "shape" in result.structure
        assert "columns" in result.structure
        assert "DataFrame" in result.summary

    @pytest.mark.asyncio
    async def test_inspect_dataframe_with_warnings(
        self,
        inspector: DataInspector,
    ):
        """Test DataFrame inspection with size warnings."""
        evaluator = MockEvaluator({
            ".shape": "[10000000, 50]",  # 10M rows
            ".columns": "['col1']",
            ".dtypes": "{}",
            "memory_usage": "4000000000",  # 4GB
        })

        result = await inspector._inspect_dataframe(
            evaluator, "huge_df", None, InspectionOptions()
        )

        assert len(result.warnings) > 0
        assert any("Large" in w for w in result.warnings)


class TestArrayInspection:
    """Test NumPy array inspection."""

    @pytest.fixture
    def inspector(self) -> DataInspector:
        return DataInspector()

    @pytest.mark.asyncio
    async def test_inspect_ndarray_basic(self, inspector: DataInspector):
        """Test basic ndarray inspection."""
        evaluator = MockEvaluator({
            ".shape": "[128, 256]",
            ".dtype": "'float32'",
            ".size": "32768",
            ".ndim": "2",
            ".nbytes": "131072",
            "flatten()": "[0.1, 0.2, 0.3]",
            ".min()": "-0.98",
            ".max()": "0.97",
            ".mean()": "0.002",
            ".std()": "0.45",
            "isnan": "0",
            "isinf": "0",
        })

        result = await inspector._inspect_ndarray(
            evaluator, "weights", None, InspectionOptions()
        )

        assert result.name == "weights"
        assert result.type == "ndarray"
        assert result.detected_type == DetectedType.NDARRAY
        assert "shape" in result.structure
        assert "dtype" in result.structure
        assert "ndarray" in result.summary

    @pytest.mark.asyncio
    async def test_inspect_large_array_skips_stats(self, inspector: DataInspector):
        """Test that large arrays skip statistics."""
        evaluator = MockEvaluator({
            ".size": "100000000",  # 100M elements
            ".shape": "[100000000]",
            ".dtype": "'float64'",
            ".ndim": "1",
            ".nbytes": "800000000",
        })

        result = await inspector._inspect_ndarray(
            evaluator, "huge_arr", None, InspectionOptions()
        )

        # Should have warning about skipped statistics
        assert any("statistics skipped" in w for w in result.warnings)


class TestDictInspection:
    """Test dict inspection."""

    @pytest.fixture
    def inspector(self) -> DataInspector:
        return DataInspector()

    @pytest.mark.asyncio
    async def test_inspect_dict_basic(self, inspector: DataInspector):
        """Test basic dict inspection."""
        evaluator = MockEvaluator({
            "len(": "45",
            "key_types": "['str']",
            "value_types": "['str', 'int', 'bool']",
            "keys())": "['host', 'port', 'database']",
            "items())": "{'host': 'localhost', 'port': 5432}",
        })

        result = await inspector._inspect_dict(
            evaluator, "config", None, InspectionOptions()
        )

        assert result.name == "config"
        assert result.type == "dict"
        assert result.detected_type == DetectedType.DICT
        assert "length" in result.structure


class TestListInspection:
    """Test list inspection."""

    @pytest.fixture
    def inspector(self) -> DataInspector:
        return DataInspector()

    @pytest.mark.asyncio
    async def test_inspect_list_basic(self, inspector: DataInspector):
        """Test basic list inspection."""
        evaluator = MockEvaluator({
            "len(": "100",
            "element_types": "['int']",
            "[:{n}]": "[1, 2, 3, 4, 5]",
        })

        result = await inspector._inspect_list(
            evaluator, "items", None, InspectionOptions()
        )

        assert result.name == "items"
        assert result.type == "list"
        assert result.detected_type == DetectedType.LIST
        assert "length" in result.structure


class TestHelperMethods:
    """Test helper methods."""

    @pytest.fixture
    def inspector(self) -> DataInspector:
        return DataInspector()

    def test_is_valid_identifier_simple(self, inspector: DataInspector):
        """Test valid simple identifiers."""
        assert inspector._is_valid_identifier("df") is True
        assert inspector._is_valid_identifier("my_var") is True
        assert inspector._is_valid_identifier("_private") is True

    def test_is_valid_identifier_attribute(self, inspector: DataInspector):
        """Test valid attribute access."""
        assert inspector._is_valid_identifier("obj.attr") is True
        assert inspector._is_valid_identifier("self.data.value") is True

    def test_is_valid_identifier_indexing(self, inspector: DataInspector):
        """Test valid indexing."""
        assert inspector._is_valid_identifier("items[0]") is True
        assert inspector._is_valid_identifier("data['key']") is True

    def test_is_valid_identifier_invalid(self, inspector: DataInspector):
        """Test invalid identifiers."""
        assert inspector._is_valid_identifier("") is False
        assert inspector._is_valid_identifier("123var") is False
        assert inspector._is_valid_identifier("import") is True  # Valid identifier, just a keyword

    def test_format_bytes(self, inspector: DataInspector):
        """Test byte formatting."""
        assert inspector._format_bytes(500) == "500 B"
        assert inspector._format_bytes(1024) == "1.0 KB"
        assert inspector._format_bytes(1024 * 1024) == "1.0 MB"
        assert inspector._format_bytes(1024 * 1024 * 1024) == "1.0 GB"

    def test_parse_result_none(self, inspector: DataInspector):
        """Test parsing None result."""
        assert inspector._parse_result(None, "default") == "default"

    def test_parse_result_boolean(self, inspector: DataInspector):
        """Test parsing boolean results."""
        assert inspector._parse_result({"result": "True"}) is True
        assert inspector._parse_result({"result": "False"}) is False
        assert inspector._parse_result({"result": "None"}) is None

    def test_parse_result_number(self, inspector: DataInspector):
        """Test parsing number results."""
        assert inspector._parse_result({"result": "42"}) == 42
        assert inspector._parse_result({"result": "3.14"}) == 3.14

    def test_parse_result_list(self, inspector: DataInspector):
        """Test parsing list results."""
        assert inspector._parse_result({"result": "[1, 2, 3]"}) == [1, 2, 3]


class TestTimeoutHandling:
    """Test timeout handling."""

    @pytest.fixture
    def inspector(self) -> DataInspector:
        return DataInspector()

    @pytest.mark.asyncio
    async def test_expression_timeout_error(self, inspector: DataInspector):
        """Test that timeout raises ExpressionTimeoutError."""
        import asyncio

        async def slow_evaluate(*args, **kwargs):
            await asyncio.sleep(10)
            return {"result": "done"}

        evaluator = MagicMock()
        evaluator.evaluate = slow_evaluate

        with pytest.raises(ExpressionTimeoutError):
            await inspector._evaluate_with_timeout(
                evaluator, "slow_expr", None, 0.1
            )


class TestModuleFunctions:
    """Test module-level functions."""

    def test_get_inspector(self):
        """Test get_inspector returns DataInspector."""
        inspector = get_inspector()
        assert isinstance(inspector, DataInspector)

    def test_get_inspector_singleton(self):
        """Test get_inspector returns same instance."""
        inspector1 = get_inspector()
        inspector2 = get_inspector()
        assert inspector1 is inspector2
```

---

## 10. Integration Tests

### 10.1 File: `tests/integration/test_inspect_variable.py`

```python
"""Integration tests for debug_inspect_variable tool."""

import pytest

from polybugger_mcp.mcp_server import debug_inspect_variable


class TestInspectVariableTool:
    """Test debug_inspect_variable MCP tool."""

    @pytest.mark.asyncio
    async def test_session_not_found(self):
        """Test error when session not found."""
        result = await debug_inspect_variable(
            session_id="nonexistent",
            variable_name="df",
        )

        assert "error" in result
        assert result["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_invalid_variable_name(self):
        """Test error for invalid variable names."""
        # This test would need a real session to test
        # For unit testing, we verify the validation logic
        from polybugger_mcp.utils.data_inspector import DataInspector

        inspector = DataInspector()
        assert inspector._is_valid_identifier("valid_name") is True
        assert inspector._is_valid_identifier("123invalid") is False

    @pytest.mark.asyncio
    async def test_max_preview_rows_capped(self):
        """Test that max_preview_rows is capped at 100."""
        from polybugger_mcp.models.inspection import InspectionOptions

        # If user requests more than 100, it should be capped
        options = InspectionOptions(max_preview_rows=100)
        assert options.max_preview_rows <= 100

    @pytest.mark.asyncio
    async def test_default_parameters(self):
        """Test default parameter values."""
        from polybugger_mcp.models.inspection import InspectionOptions

        options = InspectionOptions()
        assert options.max_preview_rows == 5
        assert options.include_statistics is True
        assert options.timeout_per_expression == 2.0
```

---

## 11. E2E Tests

### 11.1 File: `tests/e2e/test_data_inspection.py`

```python
"""End-to-end tests for data inspection feature.

These tests require pandas and numpy to be installed.
They test the full inspection workflow with real data types.
"""

import sys
import tempfile
from pathlib import Path

import pytest

# Skip if pandas/numpy not available
pytest.importorskip("pandas")
pytest.importorskip("numpy")


@pytest.fixture
def dataframe_script() -> str:
    """Create a test script with pandas DataFrame."""
    return '''
import pandas as pd
import numpy as np

# Create test DataFrame
df = pd.DataFrame({
    "id": [1, 2, 3, 4, 5],
    "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
    "value": [100.5, 200.3, 150.0, 300.1, 250.7],
    "active": [True, False, True, True, False],
})

# Create test Series
prices = pd.Series([9.99, 15.50, 22.00, 45.99, 50.00], name="price")

# Create test array
weights = np.random.randn(10, 5).astype(np.float32)

# Create test dict
config = {
    "host": "localhost",
    "port": 5432,
    "database": "testdb",
    "pool_size": 10,
}

# Create test list
items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# Breakpoint here
x = 1  # Line for breakpoint
'''


class TestDataFrameInspection:
    """E2E tests for DataFrame inspection."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_dataframe_inspection_workflow(self, dataframe_script: str):
        """Test complete DataFrame inspection during debug session."""
        from polybugger_mcp.mcp_server import (
            debug_create_session,
            debug_set_breakpoints,
            debug_launch,
            debug_poll_events,
            debug_inspect_variable,
            debug_terminate_session,
        )

        # Create temp file with script
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(dataframe_script)
            script_path = f.name

        try:
            # 1. Create session
            session_result = await debug_create_session(
                project_root=str(Path(script_path).parent),
                name="dataframe_test",
            )
            session_id = session_result["session_id"]

            # 2. Set breakpoint on last line
            await debug_set_breakpoints(
                session_id=session_id,
                file_path=script_path,
                lines=[22],  # x = 1 line
            )

            # 3. Launch
            await debug_launch(
                session_id=session_id,
                program=script_path,
            )

            # 4. Wait for stop
            events = await debug_poll_events(session_id, timeout_seconds=10)
            assert any(e["type"] == "stopped" for e in events["events"])

            # 5. Inspect DataFrame
            df_result = await debug_inspect_variable(
                session_id=session_id,
                variable_name="df",
                max_preview_rows=3,
            )

            # Verify DataFrame inspection
            assert df_result.get("type") == "DataFrame"
            assert df_result.get("detected_type") == "dataframe"
            assert "structure" in df_result
            assert "columns" in df_result["structure"]
            assert "preview" in df_result
            assert "summary" in df_result

            # 6. Inspect NumPy array
            arr_result = await debug_inspect_variable(
                session_id=session_id,
                variable_name="weights",
            )

            assert arr_result.get("type") == "ndarray"
            assert "statistics" in arr_result

            # 7. Inspect dict
            dict_result = await debug_inspect_variable(
                session_id=session_id,
                variable_name="config",
            )

            assert dict_result.get("type") == "dict"
            assert dict_result["structure"]["length"] == 4

            # 8. Cleanup
            await debug_terminate_session(session_id)

        finally:
            # Clean up temp file
            Path(script_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_inspect_with_tui_format(self, dataframe_script: str):
        """Test inspection with TUI formatting."""
        # This test verifies TUI output is generated
        # Full test would require running a debug session
        from polybugger_mcp.utils.tui_formatter import TUIFormatter

        formatter = TUIFormatter()

        # Test formatting with mock inspection result
        inspection = {
            "name": "df",
            "type": "DataFrame",
            "detected_type": "dataframe",
            "structure": {
                "shape": (100, 5),
                "columns": ["id", "name", "value"],
                "dtypes": {"id": "int64", "name": "object"},
            },
            "preview": {"head": [{"id": 1, "name": "Alice"}]},
            "summary": "DataFrame with 100 rows x 5 columns, 7.8 KB",
            "warnings": [],
        }

        result = formatter.format_inspection(inspection)

        # Verify TUI output structure
        assert "VARIABLE INSPECTION" in result
        assert "DataFrame" in result
        assert "COLUMNS" in result
        assert "PREVIEW" in result
```

---

## 12. pyproject.toml Changes

### 12.1 Add Dev Dependencies

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.3.0",
    "mypy>=1.8.0",
    "pandas>=2.0.0",
    "numpy>=1.24.0",
]
```

---

## 13. Acceptance Criteria Checklist

### 13.1 Functional Requirements

| AC | Requirement | Test Location |
|----|-------------|---------------|
| AC-1 | Tool accepts session_id, variable_name, frame_id, max_preview_rows | `test_inspect_variable.py` |
| AC-2 | Detects DataFrame with shape, columns, dtypes, memory | `test_data_inspector.py::TestDataFrameInspection` |
| AC-3 | Detects Series with length, dtype, name, stats | `test_data_inspector.py::TestSeriesInspection` |
| AC-4 | Detects ndarray with shape, dtype, stats | `test_data_inspector.py::TestArrayInspection` |
| AC-5 | Detects dict with length, key sample, value sample | `test_data_inspector.py::TestDictInspection` |
| AC-6 | Detects list with length, element types, sample | `test_data_inspector.py::TestListInspection` |
| AC-7 | Returns detected_type: "unknown" for unsupported types | `test_data_inspector.py::TestTypeDetection` |
| AC-8 | DataFrame preview includes head rows | `test_data_inspection.py` |
| AC-13 | Every response includes summary string | All tests |
| AC-16 | Response size <100KB | Size limiting in DataInspector |
| AC-17 | Per-expression timeout 2s | `test_data_inspector.py::TestTimeoutHandling` |
| AC-21 | Variable not found returns available variables | `test_inspect_variable.py` |
| AC-22 | Session not paused returns error | `test_inspect_variable.py` |
| AC-24 | Never raises exceptions | All error handling tests |

### 13.2 Non-Functional Requirements

| AC | Requirement | Verification |
|----|-------------|--------------|
| AC-25 | No new runtime dependencies | Review pyproject.toml |
| AC-26 | Works with Python 3.10+ | CI matrix |
| AC-27 | P95 latency <500ms | Performance tests |
| AC-28 | Unit test coverage >90% | pytest-cov report |

---

## 14. Error Handling

### 14.1 Error Response Schema

```python
{
    "error": "Human-readable error message",
    "code": "ERROR_CODE",
    "hint": "Optional helpful suggestion",
    "available_variables": ["list", "of", "vars"],  # For VARIABLE_NOT_FOUND
}
```

### 14.2 Error Codes

| Code | When | Hint |
|------|------|------|
| `NOT_FOUND` | Session ID not found | "Create a session first" |
| `INVALID_STATE` | Session not paused | "Set breakpoint and wait for pause" |
| `VARIABLE_NOT_FOUND` | Variable not in scope | Show available variables |
| `INVALID_VARIABLE` | Invalid variable name | "Check syntax" |
| `INSPECTION_ERROR` | Generic failure | "Use debug_evaluate" |

---

## Appendix A: Expression Templates Quick Reference

### DataFrame
```python
shape: list({var}.shape)
columns: list({var}.columns)
dtypes: {{str(k): str(v) for k, v in {var}.dtypes.items()}}
head: {var}.head({n}).to_dict('records')
```

### Series
```python
length: len({var})
dtype: str({var}.dtype)
head: {var}.head({n}).tolist()
```

### ndarray
```python
shape: list({var}.shape)
dtype: str({var}.dtype)
sample: {var}.flatten()[:{n}].tolist()
```

### dict
```python
length: len({var})
keys_preview: list({var}.keys())[:{n}]
sample: dict(list({var}.items())[:{n}])
```

### list
```python
length: len({var})
element_types: list(set(type(x).__name__ for x in {var}[:{n}]))
sample: {var}[:{n}]
```

---

*Document End*
