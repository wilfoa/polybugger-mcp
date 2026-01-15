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

from pybugger_mcp.models.inspection import (
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
        "type({var}).__module__ == 'pandas.core.frame' and type({var}).__name__ == 'DataFrame'"
    ),
    DetectedType.SERIES: (
        "type({var}).__module__ == 'pandas.core.series' and type({var}).__name__ == 'Series'"
    ),
    DetectedType.NDARRAY: (
        "type({var}).__module__ == 'numpy' and type({var}).__name__ == 'ndarray'"
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
    "keys_preview": "[str(k) for k in list({var}.keys())[:{keys_n}]]",
    "sample": "{{str(k): repr(v)[:100] for k, v in list({var}.items())[:{n}]}}",
}

LIST_EXPRESSIONS: dict[str, str] = {
    "length": "len({var})",
    "element_types": "list(set(type(x).__name__ for x in {var}[:{n}]))",
    "sample": "[repr(x)[:100] for x in {var}[:{n}]]",
}

UNKNOWN_EXPRESSIONS: dict[str, str] = {
    "repr": "repr({var})[:{max_len}]",
    "type_module": "type({var}).__module__",
    "type_name": "type({var}).__name__",
    "attributes": "[a for a in dir({var}) if not a.startswith('_')][:{n}]",
}

# Size thresholds
MAX_SIZE_FOR_STATISTICS = 10_000_000  # 10M elements


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
            return await self._inspect_dataframe(evaluator, variable_name, frame_id, options)
        elif detected_type == DetectedType.SERIES:
            return await self._inspect_series(evaluator, variable_name, frame_id, options)
        elif detected_type == DetectedType.NDARRAY:
            return await self._inspect_ndarray(evaluator, variable_name, frame_id, options)
        elif detected_type == DetectedType.DICT:
            return await self._inspect_dict(evaluator, variable_name, frame_id, options)
        elif detected_type == DetectedType.LIST:
            return await self._inspect_list(evaluator, variable_name, frame_id, options)
        else:
            return await self._inspect_unknown(evaluator, variable_name, frame_id, options)

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
        """Detect the type category of a variable."""
        for dtype, expr_template in TYPE_DETECTION_EXPRESSIONS.items():
            expr = expr_template.format(var=variable_name)
            try:
                result = await self._evaluate_with_timeout(evaluator, expr, frame_id, timeout)
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
        """Inspect a pandas DataFrame."""
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
        """Inspect a pandas Series."""
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
        """Inspect a NumPy ndarray."""
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
        """Inspect a Python dict."""
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
        key_types = self._parse_result(results.get("key_types"), [])
        value_types = self._parse_result(results.get("value_types"), [])
        structure = {
            "length": length,
            "key_types": key_types if key_types else [],
            "value_types": value_types if value_types else [],
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
        key_types = structure.get("key_types", []) or []
        key_type_str = key_types[0] if key_types and len(key_types) == 1 else "mixed"
        value_types = structure.get("value_types", []) or []
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
        """Inspect a Python list."""
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
        if element_types is None:
            element_types = []
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
        type_info = element_types[0] if element_types and len(element_types) == 1 else "mixed"
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
        """Inspect an unknown/custom type."""
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
        if attributes is None:
            attributes = []
        repr_str = self._parse_result(results.get("repr"), "")

        structure = {
            "type_module": type_module,
            "type_name": type_name,
            "attributes": attributes,
            "repr": repr_str,
        }

        # Build summary
        full_type = f"{type_module}.{type_name}" if type_module else type_name
        attr_count = len(attributes) if attributes else 0
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
        """Evaluate an expression with timeout."""
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
        """Evaluate multiple expressions concurrently."""
        results: dict[str, Any] = {}
        timed_out: list[str] = []

        async def evaluate_one(name: str, expr: str) -> tuple[str, Any, bool]:
            try:
                result = await self._evaluate_with_timeout(evaluator, expr, frame_id, timeout)
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
            if isinstance(item, BaseException):
                continue
            # item is guaranteed to be tuple[str, Any, bool] at this point
            assert isinstance(item, tuple)
            expr_name, result_value, did_timeout = item
            if did_timeout:
                timed_out.append(expr_name)
            elif result_value is not None:
                results[expr_name] = result_value

        return results, timed_out

    # =========================================================================
    # Helper Methods - Parsing and Formatting
    # =========================================================================

    def _parse_result(
        self,
        result: dict[str, Any] | None,
        default: Any = None,
    ) -> Any:
        """Parse an evaluation result to extract the value."""
        if result is None:
            return default

        result_str = result.get("result", "")
        if not result_str:
            return default

        try:
            # Handle common Python literal formats
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
        """Format bytes as human-readable string."""
        if num_bytes < 1024:
            return f"{num_bytes} B"
        elif num_bytes < 1024 * 1024:
            return f"{num_bytes / 1024:.1f} KB"
        elif num_bytes < 1024 * 1024 * 1024:
            return f"{num_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{num_bytes / (1024 * 1024 * 1024):.1f} GB"

    def _build_dataframe_summary(self, structure: dict[str, Any]) -> str:
        """Build a summary string for a DataFrame."""
        shape = structure.get("shape", (0, 0))
        rows, cols = shape if isinstance(shape, list | tuple) else (0, 0)
        memory = self._format_bytes(structure.get("memory_bytes", 0) or 0)
        return f"DataFrame with {rows:,} rows x {cols} columns, {memory}"

    def _is_valid_identifier(self, name: str) -> bool:
        """Check if a string is a valid Python identifier or access expression."""
        # Allow simple identifiers
        if name.isidentifier():
            return True

        # Allow attribute access patterns like "obj.attr.subattr"
        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$", name):
            return True

        # Allow indexing patterns like "items[0]" or "data['key']"
        return bool(
            re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*(\[[^\]]+\])+$", name)
        )


# =============================================================================
# Module-level Functions
# =============================================================================

_default_inspector: DataInspector | None = None


def get_inspector() -> DataInspector:
    """Get the default DataInspector instance."""
    global _default_inspector
    if _default_inspector is None:
        _default_inspector = DataInspector()
    return _default_inspector
