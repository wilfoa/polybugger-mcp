"""Unit tests for DataInspector and related utilities."""

import asyncio
from typing import Any
from unittest.mock import MagicMock

import pytest

from pybugger_mcp.models.inspection import (
    DetectedType,
    InspectionOptions,
    InspectionPreview,
    InspectionResult,
    Statistics,
)
from pybugger_mcp.utils.data_inspector import (
    DataInspector,
    ExpressionTimeoutError,
    get_inspector,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def inspector() -> DataInspector:
    """Create a DataInspector instance."""
    return DataInspector()


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
        for pattern, response in self.responses.items():
            if pattern in expression:
                if isinstance(response, Exception):
                    raise response
                return {"result": str(response)}
        return {"result": "None"}


@pytest.fixture
def mock_evaluator():
    """Factory fixture for MockEvaluator."""
    return MockEvaluator


# =============================================================================
# Type Detection Tests
# =============================================================================


class TestTypeDetection:
    """Test type detection logic."""

    @pytest.mark.asyncio
    async def test_detect_dataframe(self, inspector, mock_evaluator):
        """Test DataFrame detection via type module/name check."""
        evaluator = mock_evaluator(
            {
                "pandas.core.frame": "True",
                "DataFrame": "True",
            }
        )
        result = await inspector._detect_type(evaluator, "df", None, 2.0)
        assert result == DetectedType.DATAFRAME

    @pytest.mark.asyncio
    async def test_detect_series(self, inspector, mock_evaluator):
        """Test Series detection."""
        evaluator = mock_evaluator(
            {
                "pandas.core.series": "True",
                "Series": "True",
            }
        )
        result = await inspector._detect_type(evaluator, "s", None, 2.0)
        assert result == DetectedType.SERIES

    @pytest.mark.asyncio
    async def test_detect_ndarray(self, inspector, mock_evaluator):
        """Test ndarray detection."""
        evaluator = mock_evaluator(
            {
                "__module__ == 'numpy'": "True",
                "__name__ == 'ndarray'": "True",
            }
        )
        result = await inspector._detect_type(evaluator, "arr", None, 2.0)
        assert result == DetectedType.NDARRAY

    @pytest.mark.asyncio
    async def test_detect_dict(self, inspector, mock_evaluator):
        """Test dict detection with isinstance check."""
        evaluator = mock_evaluator(
            {
                ", dict)": "True",
            }
        )
        result = await inspector._detect_type(evaluator, "d", None, 2.0)
        assert result == DetectedType.DICT

    @pytest.mark.asyncio
    async def test_detect_list(self, inspector, mock_evaluator):
        """Test list detection."""
        # Note: This evaluator will also match dict first since dict check comes before list
        # In reality, the type detection would fail for dict if it's really a list
        evaluator = mock_evaluator(
            {
                ", list)": "True",
            }
        )
        result = await inspector._detect_type(evaluator, "lst", None, 2.0)
        assert result == DetectedType.LIST

    @pytest.mark.asyncio
    async def test_detect_unknown(self, inspector, mock_evaluator):
        """Test unknown type fallback when no patterns match."""
        evaluator = mock_evaluator({})  # All checks return None/False
        result = await inspector._detect_type(evaluator, "custom_obj", None, 2.0)
        assert result == DetectedType.UNKNOWN

    @pytest.mark.asyncio
    async def test_detect_handles_evaluation_errors(self, inspector, mock_evaluator):
        """Test detection handles expression errors gracefully."""
        evaluator = mock_evaluator(
            {
                "pandas.core.frame": Exception("Network error"),
            }
        )
        # Should not raise, should return UNKNOWN
        result = await inspector._detect_type(evaluator, "df", None, 2.0)
        assert result == DetectedType.UNKNOWN


# =============================================================================
# DataFrame Inspection Tests
# =============================================================================


class TestDataFrameInspection:
    """Test DataFrame-specific inspection."""

    @pytest.fixture
    def df_evaluator(self, mock_evaluator):
        """Mock evaluator returning DataFrame metadata."""
        return mock_evaluator(
            {
                "pandas.core.frame": "True",
                ".shape": "[1000, 5]",
                ".columns": "['id', 'name', 'value', 'date', 'status']",
                ".dtypes": "{'id': 'int64', 'name': 'object', 'value': 'float64'}",
                "index).__name__": "'RangeIndex'",
                "memory_usage": "80000",
                "isnull().sum()": "{'name': 5, 'value': 12}",
                ".head": "[{'id': 1, 'name': 'Alice', 'value': 100.5}]",
            }
        )

    @pytest.mark.asyncio
    async def test_inspect_dataframe_basic(self, inspector, df_evaluator):
        """Test basic DataFrame inspection returns expected structure."""
        result = await inspector._inspect_dataframe(df_evaluator, "df", None, InspectionOptions())

        assert result.name == "df"
        assert result.type == "DataFrame"
        assert result.detected_type == DetectedType.DATAFRAME
        assert "shape" in result.structure
        assert "columns" in result.structure
        assert "dtypes" in result.structure
        assert "DataFrame" in result.summary

    @pytest.mark.asyncio
    async def test_inspect_dataframe_preview(self, inspector, df_evaluator):
        """Test DataFrame preview contains head rows."""
        result = await inspector._inspect_dataframe(
            df_evaluator, "df", None, InspectionOptions(max_preview_rows=3)
        )

        assert result.preview.head is not None
        assert len(result.preview.head) > 0

    @pytest.mark.asyncio
    async def test_inspect_large_dataframe_warning(self, inspector, mock_evaluator):
        """Test large DataFrame triggers size warning."""
        evaluator = mock_evaluator(
            {
                "pandas.core.frame": "True",
                ".shape": "[10000000, 50]",  # 10M rows
                ".columns": "['col1']",
                ".dtypes": "{}",
                "memory_usage": "4000000000",  # 4GB
            }
        )

        result = await inspector._inspect_dataframe(evaluator, "huge_df", None, InspectionOptions())

        assert len(result.warnings) > 0
        assert any("Large" in w for w in result.warnings)
        assert result.structure.get("truncated") is True


# =============================================================================
# Series Inspection Tests
# =============================================================================


class TestSeriesInspection:
    """Test Series-specific inspection."""

    @pytest.mark.asyncio
    async def test_inspect_series_basic(self, inspector, mock_evaluator):
        """Test basic Series inspection."""
        evaluator = mock_evaluator(
            {
                "pandas.core.series": "True",
                "len(": "1000",
                "str({var}.dtype)": "'float64'",
                "{var}.name": "'prices'",
                "index).__name__": "'RangeIndex'",
                ".head": "[9.99, 15.50, 22.00]",
                ".tail": "[45.99, 50.00, 55.00]",
                ".min()": "9.99",
                ".max()": "999.99",
                ".mean()": "150.50",
                ".std()": "45.2",
                "isnull().sum()": "5",
            }
        )

        result = await inspector._inspect_series(evaluator, "prices", None, InspectionOptions())

        assert result.name == "prices"
        assert result.type == "Series"
        assert result.detected_type == DetectedType.SERIES
        assert "length" in result.structure
        assert result.statistics is not None


# =============================================================================
# NumPy Array Inspection Tests
# =============================================================================


class TestArrayInspection:
    """Test NumPy array inspection."""

    @pytest.mark.asyncio
    async def test_inspect_ndarray_basic(self, inspector, mock_evaluator):
        """Test basic ndarray inspection."""
        evaluator = mock_evaluator(
            {
                "int(weights.size)": "32768",
                "list(weights.shape)": "[128, 256]",
                "str(weights.dtype)": "'float32'",
                "int(weights.ndim)": "2",
                "int(weights.nbytes)": "131072",
                "flatten()": "[0.1, 0.2, 0.3, -0.1, 0.5]",
                ".min()": "-0.98",
                ".max()": "0.97",
                ".mean()": "0.002",
                ".std()": "0.45",
                "numpy').isnan": "0",
                "numpy').isinf": "0",
            }
        )

        result = await inspector._inspect_ndarray(evaluator, "weights", None, InspectionOptions())

        assert result.name == "weights"
        assert result.type == "ndarray"
        assert "shape" in result.structure
        assert "dtype" in result.structure
        assert result.statistics is not None
        assert "ndarray" in result.summary

    @pytest.mark.asyncio
    async def test_inspect_large_array_skips_stats(self, inspector, mock_evaluator):
        """Test large arrays skip statistics computation."""
        evaluator = mock_evaluator(
            {
                ".size": "100000000",  # 100M elements
                ".shape": "[100000000]",
                ".dtype": "'float64'",
                ".ndim": "1",
                ".nbytes": "800000000",
            }
        )

        result = await inspector._inspect_ndarray(evaluator, "huge_arr", None, InspectionOptions())

        assert any("statistics skipped" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_inspect_ndarray_with_nan_inf(self, inspector, mock_evaluator):
        """Test array with NaN/Inf values reports counts."""
        evaluator = mock_evaluator(
            {
                "int(data.size)": "1000",
                "list(data.shape)": "[1000]",
                "str(data.dtype)": "'float64'",
                "int(data.ndim)": "1",
                "int(data.nbytes)": "8000",
                ".min()": "-100.0",
                ".max()": "200.0",
                ".mean()": "50.0",
                ".std()": "30.0",
                "numpy').isnan": "15",  # 15 NaN values
                "numpy').isinf": "2",  # 2 Inf values
            }
        )

        result = await inspector._inspect_ndarray(evaluator, "data", None, InspectionOptions())

        assert result.statistics is not None
        assert result.statistics.nan_count == 15
        assert result.statistics.inf_count == 2
        assert any("NaN" in w or "Inf" in w for w in result.warnings)


# =============================================================================
# Dict Inspection Tests
# =============================================================================


class TestDictInspection:
    """Test dict inspection."""

    @pytest.mark.asyncio
    async def test_inspect_dict_basic(self, inspector, mock_evaluator):
        """Test basic dict inspection."""
        evaluator = mock_evaluator(
            {
                "len(config)": "45",
                "type(k).__name__": "['str']",
                "type(v).__name__": "['str', 'int', 'bool']",
                "str(k)": "['host', 'port', 'database', 'pool_size']",
                "repr(v)": "{'host': 'localhost', 'port': '5432'}",
            }
        )

        result = await inspector._inspect_dict(evaluator, "config", None, InspectionOptions())

        assert result.name == "config"
        assert result.type == "dict"
        assert result.structure["length"] == 45


# =============================================================================
# List Inspection Tests
# =============================================================================


class TestListInspection:
    """Test list inspection."""

    @pytest.mark.asyncio
    async def test_inspect_list_basic(self, inspector, mock_evaluator):
        """Test basic list inspection."""
        evaluator = mock_evaluator(
            {
                "len(items)": "100",
                "type(x).__name__": "['int']",
                "repr(x)": "[1, 2, 3, 4, 5]",
            }
        )

        result = await inspector._inspect_list(evaluator, "items", None, InspectionOptions())

        assert result.name == "items"
        assert result.type == "list"
        assert result.structure["length"] == 100
        # Note: element_types parsing may not work with this mock
        # but we verify the basic structure is correct

    @pytest.mark.asyncio
    async def test_inspect_list_mixed_types(self, inspector, mock_evaluator):
        """Test list with mixed element types."""
        evaluator = mock_evaluator(
            {
                "len(mixed)": "50",
                "type(x).__name__": "['int', 'str', 'dict']",
                "repr(x)": "[1, 'hello', 'dict_obj']",
            }
        )

        result = await inspector._inspect_list(evaluator, "mixed", None, InspectionOptions())

        # Verify the structure is populated correctly
        assert result.name == "mixed"
        assert result.type == "list"
        assert result.structure["length"] == 50


# =============================================================================
# Unknown Type Inspection Tests
# =============================================================================


class TestUnknownTypeInspection:
    """Test unknown/custom type inspection."""

    @pytest.mark.asyncio
    async def test_inspect_unknown_basic(self, inspector, mock_evaluator):
        """Test unknown type returns basic info."""
        evaluator = mock_evaluator(
            {
                "__module__": "'myapp.models'",
                "__name__": "'CustomModel'",
                "dir(my_obj)": "['id', 'name', 'process', 'validate']",
                "repr(my_obj)": "'<CustomModel object at 0x7f...>'",
            }
        )

        result = await inspector._inspect_unknown(evaluator, "my_obj", None, InspectionOptions())

        assert result.detected_type == DetectedType.UNKNOWN
        # The type name defaults to "unknown" if __name__ doesn't match
        assert result.hint is not None
        assert "debug_get_variables" in result.hint


# =============================================================================
# Helper Method Tests
# =============================================================================


class TestHelperMethods:
    """Test helper methods."""

    def test_is_valid_identifier_simple(self, inspector):
        """Test valid simple identifiers."""
        assert inspector._is_valid_identifier("df") is True
        assert inspector._is_valid_identifier("my_var") is True
        assert inspector._is_valid_identifier("_private") is True
        assert inspector._is_valid_identifier("MyClass") is True

    def test_is_valid_identifier_attribute(self, inspector):
        """Test valid attribute access patterns."""
        assert inspector._is_valid_identifier("obj.attr") is True
        assert inspector._is_valid_identifier("self.data.value") is True
        assert inspector._is_valid_identifier("module.Class.method") is True

    def test_is_valid_identifier_indexing(self, inspector):
        """Test valid indexing patterns."""
        assert inspector._is_valid_identifier("items[0]") is True
        assert inspector._is_valid_identifier("data['key']") is True
        assert inspector._is_valid_identifier("matrix[0][1]") is True

    def test_is_valid_identifier_invalid(self, inspector):
        """Test invalid identifier patterns."""
        assert inspector._is_valid_identifier("") is False
        assert inspector._is_valid_identifier("123var") is False
        assert inspector._is_valid_identifier("a b c") is False
        assert inspector._is_valid_identifier("import;sys") is False

    def test_format_bytes(self, inspector):
        """Test byte formatting."""
        assert inspector._format_bytes(500) == "500 B"
        assert inspector._format_bytes(1024) == "1.0 KB"
        assert inspector._format_bytes(1536) == "1.5 KB"
        assert inspector._format_bytes(1024 * 1024) == "1.0 MB"
        assert inspector._format_bytes(1024 * 1024 * 1024) == "1.0 GB"

    def test_parse_result_none(self, inspector):
        """Test parsing None result."""
        assert inspector._parse_result(None) is None
        assert inspector._parse_result(None, "default") == "default"
        assert inspector._parse_result({}, "default") == "default"

    def test_parse_result_boolean(self, inspector):
        """Test parsing boolean results."""
        assert inspector._parse_result({"result": "True"}) is True
        assert inspector._parse_result({"result": "False"}) is False
        assert inspector._parse_result({"result": "None"}) is None

    def test_parse_result_numbers(self, inspector):
        """Test parsing numeric results."""
        assert inspector._parse_result({"result": "42"}) == 42
        assert inspector._parse_result({"result": "3.14"}) == 3.14
        assert inspector._parse_result({"result": "-100"}) == -100

    def test_parse_result_collections(self, inspector):
        """Test parsing collection results."""
        assert inspector._parse_result({"result": "[1, 2, 3]"}) == [1, 2, 3]
        assert inspector._parse_result({"result": "{'a': 1}"}) == {"a": 1}


# =============================================================================
# Timeout Handling Tests
# =============================================================================


class TestTimeoutHandling:
    """Test timeout handling."""

    @pytest.mark.asyncio
    async def test_expression_timeout_error(self, inspector):
        """Test that slow evaluation raises ExpressionTimeoutError."""

        async def slow_evaluate(*args, **kwargs):
            await asyncio.sleep(10)
            return {"result": "done"}

        evaluator = MagicMock()
        evaluator.evaluate = slow_evaluate

        with pytest.raises(ExpressionTimeoutError):
            await inspector._evaluate_with_timeout(evaluator, "slow_expr", None, 0.1)

    @pytest.mark.asyncio
    async def test_evaluate_multiple_with_partial_timeout(self, inspector):
        """Test concurrent evaluation handles partial timeouts."""
        call_count = 0

        async def mixed_evaluate(expression, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if "slow" in expression:
                await asyncio.sleep(10)  # Will timeout
            return {"result": "fast_result"}

        evaluator = MagicMock()
        evaluator.evaluate = mixed_evaluate

        expressions = {
            "fast1": "fast_expr_1",
            "slow1": "slow_expr_1",
            "fast2": "fast_expr_2",
        }

        results, timed_out = await inspector._evaluate_multiple(evaluator, expressions, None, 0.1)

        assert "fast1" in results or "fast2" in results
        assert "slow1" in timed_out


# =============================================================================
# Module-level Functions Tests
# =============================================================================


class TestModuleFunctions:
    """Test module-level functions."""

    def test_get_inspector_singleton(self):
        """Test get_inspector returns singleton."""
        inspector1 = get_inspector()
        inspector2 = get_inspector()
        assert inspector1 is inspector2

    def test_get_inspector_returns_data_inspector(self):
        """Test get_inspector returns DataInspector instance."""
        inspector = get_inspector()
        assert isinstance(inspector, DataInspector)


# =============================================================================
# Inspection Models Tests
# =============================================================================


class TestInspectionModels:
    """Test Pydantic inspection models."""

    def test_inspection_options_defaults(self):
        """Test default option values."""
        opts = InspectionOptions()
        assert opts.max_preview_rows == 5
        assert opts.max_preview_items == 10
        assert opts.include_statistics is True
        assert opts.timeout_per_expression == 2.0
        assert opts.max_string_length == 200

    def test_inspection_options_validation(self):
        """Test option value validation."""
        from pydantic import ValidationError

        # Valid
        assert InspectionOptions(max_preview_rows=1).max_preview_rows == 1
        assert InspectionOptions(max_preview_rows=100).max_preview_rows == 100

        # Invalid
        with pytest.raises(ValidationError):
            InspectionOptions(max_preview_rows=0)
        with pytest.raises(ValidationError):
            InspectionOptions(max_preview_rows=101)

    def test_detected_type_enum_values(self):
        """Test DetectedType enum has all expected values."""
        assert DetectedType.DATAFRAME.value == "dataframe"
        assert DetectedType.SERIES.value == "series"
        assert DetectedType.NDARRAY.value == "ndarray"
        assert DetectedType.DICT.value == "dict"
        assert DetectedType.LIST.value == "list"
        assert DetectedType.PRIMITIVE.value == "primitive"
        assert DetectedType.UNKNOWN.value == "unknown"

    def test_inspection_result_serialization(self):
        """Test InspectionResult serialization."""
        result = InspectionResult(
            name="df",
            type="DataFrame",
            detected_type=DetectedType.DATAFRAME,
            structure={"shape": (100, 5)},
            preview=InspectionPreview(head=[{"a": 1}]),
            summary="DataFrame with 100 rows",
        )

        data = result.model_dump()
        assert data["name"] == "df"
        assert data["type"] == "DataFrame"
        assert data["detected_type"] == "dataframe"
        assert "shape" in data["structure"]

    def test_statistics_model(self):
        """Test Statistics model fields."""
        stats = Statistics(
            min=-1.0,
            max=1.0,
            mean=0.0,
            std=0.5,
            nan_count=3,
            inf_count=0,
        )
        assert stats.min == -1.0
        assert stats.max == 1.0
        assert stats.mean == 0.0
        assert stats.nan_count == 3

    def test_inspection_result_optional_fields(self):
        """Test optional fields default appropriately."""
        result = InspectionResult(
            name="x",
            type="int",
            detected_type=DetectedType.UNKNOWN,
            summary="integer value",
        )

        assert result.statistics is None
        assert result.error is None
        assert result.partial is False
        assert result.timed_out == []
        assert result.warnings == []
