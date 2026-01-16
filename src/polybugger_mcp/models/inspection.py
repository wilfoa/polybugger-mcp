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
        formatted: TUI-formatted output (when format="tui")
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
    formatted: str | None = None


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
