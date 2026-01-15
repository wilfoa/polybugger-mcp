# DataFrame/NumPy Smart Preview - Test Plan

## Document Metadata
- **Feature**: Smart Variable Inspection for Data Science Types
- **Story ID**: US-DATA-002
- **Version**: 1.0
- **Created**: 2026-01-15
- **Status**: Ready for Implementation
- **Author**: QA Expert Agent
- **HLD Reference**: docs/design/data-inspector-hld.md
- **LLD Reference**: docs/plans/data-inspector-lld.md

---

## Table of Contents

1. [Test Strategy Overview](#1-test-strategy-overview)
2. [Test Environment & Prerequisites](#2-test-environment--prerequisites)
3. [Unit Test Specifications](#3-unit-test-specifications)
4. [Integration Test Specifications](#4-integration-test-specifications)
5. [E2E Test Specifications](#5-e2e-test-specifications)
6. [Edge Case Test Scenarios](#6-edge-case-test-scenarios)
7. [Test Data Requirements](#7-test-data-requirements)
8. [Coverage Matrix](#8-coverage-matrix)
9. [Quality Metrics & Acceptance](#9-quality-metrics--acceptance)

---

## 1. Test Strategy Overview

### 1.1 Objectives

| Objective | Description |
|-----------|-------------|
| **Functional Correctness** | Verify all data types (DataFrame, Series, ndarray, dict, list) are correctly detected and inspected |
| **Error Handling** | Ensure graceful handling of all error conditions without exceptions |
| **Performance** | Validate response times meet <500ms P95 requirement |
| **Safety** | Confirm response sizes stay under 100KB and timeouts prevent hanging |
| **Compatibility** | Test with Python 3.10+ and various pandas/numpy versions |

### 1.2 Testing Pyramid

```
                    ┌─────────────────┐
                    │    E2E Tests    │  (~10%)
                    │  Real debugger  │  Full workflow validation
                    ├─────────────────┤
                    │  Integration    │  (~20%)
                    │   MCP tool &    │  API contract verification
                    │   Session API   │
                    ├─────────────────┤
                    │   Unit Tests    │  (~70%)
                    │  DataInspector  │  Type detection, parsing,
                    │  TUIFormatter   │  expression building
                    └─────────────────┘
```

### 1.3 Test Scope

**In Scope:**
- DataInspector class methods (type detection, inspection, parsing)
- MCP tool `debug_inspect_variable` parameter handling
- Session `inspect_variable()` method
- TUIFormatter `format_inspection()` method
- All 10 edge cases (EC-1 to EC-10)
- Error response formats
- Timeout behavior
- Response size limiting

**Out of Scope:**
- debugpy internals (covered by existing tests)
- DAP protocol validation (covered by existing tests)
- HTTP API endpoints (feature uses MCP only)

### 1.4 Quality Gates

| Gate | Requirement | Verification |
|------|-------------|--------------|
| Unit Test Coverage | >90% for data_inspector.py | pytest-cov report |
| Unit Test Coverage | >80% for models/inspection.py | pytest-cov report |
| All Tests Pass | 100% pass rate | CI pipeline |
| No Regressions | Existing tests pass | CI pipeline |
| P95 Latency | <500ms for typical data | Performance tests |

---

## 2. Test Environment & Prerequisites

### 2.1 Dependencies

```toml
# Add to pyproject.toml [project.optional-dependencies]
dev = [
    # Existing...
    "pandas>=2.0.0",
    "numpy>=1.24.0",
]
```

### 2.2 Test Fixtures (tests/conftest.py additions)

```python
# Add to existing conftest.py

@pytest.fixture
def mock_evaluator():
    """Create a mock evaluator for unit testing."""
    class MockEvaluator:
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

    return MockEvaluator


@pytest.fixture
def dataframe_script(tmp_path) -> Path:
    """Create test script with pandas DataFrame."""
    script = tmp_path / "dataframe_test.py"
    script.write_text('''
import pandas as pd
import numpy as np

# Test DataFrame
df = pd.DataFrame({
    "id": [1, 2, 3, 4, 5],
    "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
    "value": [100.5, 200.3, 150.0, 300.1, 250.7],
    "active": [True, False, True, True, False],
})

# Test Series
prices = pd.Series([9.99, 15.50, 22.00, 45.99, 50.00], name="price")

# Test NumPy array
weights = np.random.randn(10, 5).astype(np.float32)

# Test dict
config = {
    "host": "localhost",
    "port": 5432,
    "database": "testdb",
    "pool_size": 10,
}

# Test list
items = list(range(100))

# Breakpoint target
x = 1  # Line for breakpoint
''')
    return script


@pytest.fixture
def empty_dataframe_script(tmp_path) -> Path:
    """Create script with empty DataFrame."""
    script = tmp_path / "empty_df_test.py"
    script.write_text('''
import pandas as pd
import numpy as np

empty_df = pd.DataFrame(columns=["a", "b", "c"])
empty_array = np.array([])
empty_dict = {}
empty_list = []

x = 1
''')
    return script


@pytest.fixture
def large_data_script(tmp_path) -> Path:
    """Create script with large data structures."""
    script = tmp_path / "large_data_test.py"
    script.write_text('''
import pandas as pd
import numpy as np

# Large DataFrame (will trigger warnings)
large_df = pd.DataFrame({
    f"col_{i}": range(100000) for i in range(50)
})

# Large array
large_array = np.random.randn(1000000)

# Large dict
large_dict = {f"key_{i}": f"value_{i}" for i in range(10000)}

x = 1
''')
    return script
```

### 2.3 Test File Structure

```
tests/
├── conftest.py                    # Add new fixtures
├── unit/
│   ├── test_data_inspector.py     # NEW - Core inspection logic
│   ├── test_inspection_models.py  # NEW - Pydantic models
│   └── test_tui_formatter.py      # Existing + format_inspection
├── integration/
│   ├── test_api_inspection.py     # NEW - MCP tool tests
│   └── ...existing...
└── e2e/
    ├── test_data_inspection.py    # NEW - Full debug workflows
    └── ...existing...
```

---

## 3. Unit Test Specifications

### 3.1 File: `tests/unit/test_data_inspector.py`

#### 3.1.1 Type Detection Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| UT-DET-001 | `test_detect_dataframe` | Verify DataFrame type detection | Returns `DetectedType.DATAFRAME` |
| UT-DET-002 | `test_detect_series` | Verify Series type detection | Returns `DetectedType.SERIES` |
| UT-DET-003 | `test_detect_ndarray` | Verify ndarray type detection | Returns `DetectedType.NDARRAY` |
| UT-DET-004 | `test_detect_dict` | Verify dict type detection | Returns `DetectedType.DICT` |
| UT-DET-005 | `test_detect_list` | Verify list type detection | Returns `DetectedType.LIST` |
| UT-DET-006 | `test_detect_unknown` | Verify unknown type fallback | Returns `DetectedType.UNKNOWN` |
| UT-DET-007 | `test_detect_primitive_int` | Verify primitive types fallback | Returns `DetectedType.UNKNOWN` |
| UT-DET-008 | `test_detect_type_detection_order` | Verify detection checks specific types first | DataFrame detected before dict |

```python
class TestTypeDetection:
    """Test type detection logic."""

    @pytest.fixture
    def inspector(self) -> DataInspector:
        return DataInspector()

    @pytest.mark.asyncio
    async def test_detect_dataframe(self, inspector, mock_evaluator):
        """Test DataFrame detection via type module/name check."""
        evaluator = mock_evaluator({
            "pandas.core.frame": "True",
            "DataFrame": "True",
        })
        result = await inspector._detect_type(evaluator, "df", None, 2.0)
        assert result == DetectedType.DATAFRAME

    @pytest.mark.asyncio
    async def test_detect_series(self, inspector, mock_evaluator):
        """Test Series detection."""
        evaluator = mock_evaluator({
            "pandas.core.series": "True",
            "Series": "True",
        })
        result = await inspector._detect_type(evaluator, "s", None, 2.0)
        assert result == DetectedType.SERIES

    @pytest.mark.asyncio
    async def test_detect_ndarray(self, inspector, mock_evaluator):
        """Test ndarray detection."""
        evaluator = mock_evaluator({
            "__module__ == 'numpy'": "True",
            "__name__ == 'ndarray'": "True",
        })
        result = await inspector._detect_type(evaluator, "arr", None, 2.0)
        assert result == DetectedType.NDARRAY

    @pytest.mark.asyncio
    async def test_detect_dict(self, inspector, mock_evaluator):
        """Test dict detection with isinstance check."""
        # All non-dict checks should fail, dict check should succeed
        evaluator = mock_evaluator({
            "isinstance({var}, dict)": "True",
        })
        result = await inspector._detect_type(evaluator, "d", None, 2.0)
        assert result == DetectedType.DICT

    @pytest.mark.asyncio
    async def test_detect_list(self, inspector, mock_evaluator):
        """Test list detection."""
        evaluator = mock_evaluator({
            "isinstance({var}, list)": "True",
        })
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
        evaluator = mock_evaluator({
            "pandas.core.frame": Exception("Network error"),
        })
        # Should not raise, should return UNKNOWN
        result = await inspector._detect_type(evaluator, "df", None, 2.0)
        assert result == DetectedType.UNKNOWN
```

#### 3.1.2 DataFrame Inspection Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| UT-DF-001 | `test_inspect_dataframe_basic` | Inspect simple DataFrame | Returns shape, columns, dtypes |
| UT-DF-002 | `test_inspect_dataframe_with_nulls` | Inspect DataFrame with null values | Includes null_counts |
| UT-DF-003 | `test_inspect_dataframe_large_triggers_warning` | Inspect >1M row DataFrame | Includes size warning |
| UT-DF-004 | `test_inspect_dataframe_preview_data` | Verify head() data extraction | preview.head contains rows |
| UT-DF-005 | `test_inspect_dataframe_memory_bytes` | Verify memory calculation | structure.memory_bytes present |
| UT-DF-006 | `test_inspect_dataframe_summary_format` | Verify summary string format | Contains rows, columns, memory |

```python
class TestDataFrameInspection:
    """Test DataFrame-specific inspection."""

    @pytest.fixture
    def inspector(self) -> DataInspector:
        return DataInspector()

    @pytest.fixture
    def df_evaluator(self, mock_evaluator):
        """Mock evaluator returning DataFrame metadata."""
        return mock_evaluator({
            "pandas.core.frame": "True",
            ".shape": "[1000, 5]",
            ".columns": "['id', 'name', 'value', 'date', 'status']",
            ".dtypes": "{'id': 'int64', 'name': 'object', 'value': 'float64'}",
            "index).__name__": "'RangeIndex'",
            "memory_usage": "80000",
            "isnull().sum()": "{'name': 5, 'value': 12}",
            ".head": "[{'id': 1, 'name': 'Alice', 'value': 100.5}]",
        })

    @pytest.mark.asyncio
    async def test_inspect_dataframe_basic(self, inspector, df_evaluator):
        """Test basic DataFrame inspection returns expected structure."""
        result = await inspector._inspect_dataframe(
            df_evaluator, "df", None, InspectionOptions()
        )

        assert result.name == "df"
        assert result.type == "DataFrame"
        assert result.detected_type == DetectedType.DATAFRAME
        assert "shape" in result.structure
        assert "columns" in result.structure
        assert "dtypes" in result.structure
        assert "DataFrame" in result.summary
        assert "1,000 rows" in result.summary or "1000 rows" in result.summary

    @pytest.mark.asyncio
    async def test_inspect_dataframe_preview(self, inspector, df_evaluator):
        """Test DataFrame preview contains head rows."""
        result = await inspector._inspect_dataframe(
            df_evaluator, "df", None, InspectionOptions(max_preview_rows=3)
        )

        assert result.preview.head is not None
        assert len(result.preview.head) > 0
        assert isinstance(result.preview.head[0], dict)

    @pytest.mark.asyncio
    async def test_inspect_large_dataframe_warning(self, inspector, mock_evaluator):
        """Test large DataFrame triggers size warning."""
        evaluator = mock_evaluator({
            "pandas.core.frame": "True",
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
        assert result.structure.get("truncated") is True
```

#### 3.1.3 Series Inspection Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| UT-SER-001 | `test_inspect_series_basic` | Inspect simple Series | Returns length, dtype, name |
| UT-SER-002 | `test_inspect_series_statistics` | Inspect Series with stats | Includes min, max, mean, std |
| UT-SER-003 | `test_inspect_series_head_tail` | Verify head/tail preview | Both head and tail present |
| UT-SER-004 | `test_inspect_series_null_count` | Verify null count reporting | nan_count in statistics |

```python
class TestSeriesInspection:
    """Test Series-specific inspection."""

    @pytest.fixture
    def inspector(self) -> DataInspector:
        return DataInspector()

    @pytest.mark.asyncio
    async def test_inspect_series_basic(self, inspector, mock_evaluator):
        """Test basic Series inspection."""
        evaluator = mock_evaluator({
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
        })

        result = await inspector._inspect_series(
            evaluator, "prices", None, InspectionOptions()
        )

        assert result.name == "prices"
        assert result.type == "Series"
        assert result.detected_type == DetectedType.SERIES
        assert "length" in result.structure
        assert result.statistics is not None
        assert result.statistics.min is not None
```

#### 3.1.4 NumPy Array Inspection Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| UT-ARR-001 | `test_inspect_ndarray_basic` | Inspect simple 1D array | Returns shape, dtype, size |
| UT-ARR-002 | `test_inspect_ndarray_multidim` | Inspect multi-dimensional array | Returns correct shape tuple |
| UT-ARR-003 | `test_inspect_ndarray_statistics` | Verify stats for small arrays | Includes min, max, mean, std |
| UT-ARR-004 | `test_inspect_ndarray_large_skips_stats` | Verify >10M elements skips stats | Warning present, no stats |
| UT-ARR-005 | `test_inspect_ndarray_nan_inf_counts` | Verify NaN/Inf detection | nan_count and inf_count present |
| UT-ARR-006 | `test_inspect_ndarray_sample_preview` | Verify sample values | preview.sample contains values |

```python
class TestArrayInspection:
    """Test NumPy array inspection."""

    @pytest.fixture
    def inspector(self) -> DataInspector:
        return DataInspector()

    @pytest.mark.asyncio
    async def test_inspect_ndarray_basic(self, inspector, mock_evaluator):
        """Test basic ndarray inspection."""
        evaluator = mock_evaluator({
            ".size": "32768",
            ".shape": "[128, 256]",
            ".dtype": "'float32'",
            ".ndim": "2",
            ".nbytes": "131072",
            "flatten()": "[0.1, 0.2, 0.3, -0.1, 0.5]",
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
        assert "shape" in result.structure
        assert "dtype" in result.structure
        assert result.statistics is not None
        assert "ndarray" in result.summary

    @pytest.mark.asyncio
    async def test_inspect_large_array_skips_stats(self, inspector, mock_evaluator):
        """Test large arrays skip statistics computation."""
        evaluator = mock_evaluator({
            ".size": "100000000",  # 100M elements
            ".shape": "[100000000]",
            ".dtype": "'float64'",
            ".ndim": "1",
            ".nbytes": "800000000",
        })

        result = await inspector._inspect_ndarray(
            evaluator, "huge_arr", None, InspectionOptions()
        )

        assert any("statistics skipped" in w for w in result.warnings)
        assert "statistics" in result.timed_out or result.statistics is None

    @pytest.mark.asyncio
    async def test_inspect_ndarray_with_nan_inf(self, inspector, mock_evaluator):
        """Test array with NaN/Inf values reports counts."""
        evaluator = mock_evaluator({
            ".size": "1000",
            ".shape": "[1000]",
            ".dtype": "'float64'",
            ".ndim": "1",
            ".nbytes": "8000",
            ".min()": "-100.0",
            ".max()": "200.0",
            ".mean()": "50.0",
            ".std()": "30.0",
            "isnan": "15",  # 15 NaN values
            "isinf": "2",   # 2 Inf values
        })

        result = await inspector._inspect_ndarray(
            evaluator, "data", None, InspectionOptions()
        )

        assert result.statistics is not None
        assert result.statistics.nan_count == 15
        assert result.statistics.inf_count == 2
        assert any("NaN" in w or "Inf" in w for w in result.warnings)
```

#### 3.1.5 Dict/List Inspection Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| UT-DICT-001 | `test_inspect_dict_basic` | Inspect simple dict | Returns length, key_types, value_types |
| UT-DICT-002 | `test_inspect_dict_preview` | Verify key/value preview | keys and sample present |
| UT-DICT-003 | `test_inspect_large_dict_warning` | Inspect >10K keys | Warning present |
| UT-LIST-001 | `test_inspect_list_basic` | Inspect simple list | Returns length, element_types |
| UT-LIST-002 | `test_inspect_list_uniform` | Verify uniform type detection | uniform=True for same types |
| UT-LIST-003 | `test_inspect_list_mixed` | Verify mixed type detection | element_types has multiple |

```python
class TestDictInspection:
    """Test dict inspection."""

    @pytest.fixture
    def inspector(self) -> DataInspector:
        return DataInspector()

    @pytest.mark.asyncio
    async def test_inspect_dict_basic(self, inspector, mock_evaluator):
        """Test basic dict inspection."""
        evaluator = mock_evaluator({
            "len(": "45",
            "key_types": "['str']",
            "value_types": "['str', 'int', 'bool']",
            "keys())": "['host', 'port', 'database', 'pool_size']",
            "items())": "{'host': 'localhost', 'port': 5432}",
        })

        result = await inspector._inspect_dict(
            evaluator, "config", None, InspectionOptions()
        )

        assert result.name == "config"
        assert result.type == "dict"
        assert result.structure["length"] == 45
        assert "str" in result.structure.get("key_types", [])


class TestListInspection:
    """Test list inspection."""

    @pytest.fixture
    def inspector(self) -> DataInspector:
        return DataInspector()

    @pytest.mark.asyncio
    async def test_inspect_list_basic(self, inspector, mock_evaluator):
        """Test basic list inspection."""
        evaluator = mock_evaluator({
            "len(": "100",
            "element_types": "['int']",
            "[:{n}]": "[1, 2, 3, 4, 5]",
        })

        result = await inspector._inspect_list(
            evaluator, "items", None, InspectionOptions()
        )

        assert result.name == "items"
        assert result.type == "list"
        assert result.structure["length"] == 100
        assert result.structure["uniform"] is True

    @pytest.mark.asyncio
    async def test_inspect_list_mixed_types(self, inspector, mock_evaluator):
        """Test list with mixed element types."""
        evaluator = mock_evaluator({
            "len(": "50",
            "element_types": "['int', 'str', 'dict']",
            "[:{n}]": "[1, 'hello', {'key': 'value'}]",
        })

        result = await inspector._inspect_list(
            evaluator, "mixed", None, InspectionOptions()
        )

        assert result.structure["uniform"] is False
        assert len(result.structure["element_types"]) > 1
```

#### 3.1.6 Unknown Type Inspection Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| UT-UNK-001 | `test_inspect_unknown_basic` | Inspect custom class | Returns type_name, attributes |
| UT-UNK-002 | `test_inspect_unknown_repr` | Verify repr truncation | repr present, truncated if long |
| UT-UNK-003 | `test_inspect_unknown_hint` | Verify hint for exploration | hint present |

```python
class TestUnknownTypeInspection:
    """Test unknown/custom type inspection."""

    @pytest.fixture
    def inspector(self) -> DataInspector:
        return DataInspector()

    @pytest.mark.asyncio
    async def test_inspect_unknown_basic(self, inspector, mock_evaluator):
        """Test unknown type returns basic info."""
        evaluator = mock_evaluator({
            "type_module": "'myapp.models'",
            "type_name": "'CustomModel'",
            "attributes": "['id', 'name', 'process', 'validate']",
            "repr": "'<CustomModel object at 0x7f...>'",
        })

        result = await inspector._inspect_unknown(
            evaluator, "my_obj", None, InspectionOptions()
        )

        assert result.detected_type == DetectedType.UNKNOWN
        assert "CustomModel" in result.type
        assert result.hint is not None
        assert "debug_get_variables" in result.hint
```

#### 3.1.7 Helper Method Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| UT-HLP-001 | `test_is_valid_identifier_simple` | Simple variable names | True for valid identifiers |
| UT-HLP-002 | `test_is_valid_identifier_attribute` | Attribute access patterns | True for obj.attr |
| UT-HLP-003 | `test_is_valid_identifier_indexing` | Indexing patterns | True for items[0] |
| UT-HLP-004 | `test_is_valid_identifier_invalid` | Invalid patterns | False for invalid |
| UT-HLP-005 | `test_format_bytes_kb` | Format KB values | "1.0 KB" for 1024 |
| UT-HLP-006 | `test_format_bytes_mb` | Format MB values | "1.0 MB" for 1048576 |
| UT-HLP-007 | `test_format_bytes_gb` | Format GB values | "1.0 GB" for 1073741824 |
| UT-HLP-008 | `test_parse_result_none` | Parse None result | Returns default |
| UT-HLP-009 | `test_parse_result_boolean` | Parse boolean strings | True/False/None |
| UT-HLP-010 | `test_parse_result_number` | Parse numeric strings | int/float |
| UT-HLP-011 | `test_parse_result_list` | Parse list strings | Python list |
| UT-HLP-012 | `test_parse_result_dict` | Parse dict strings | Python dict |

```python
class TestHelperMethods:
    """Test helper methods."""

    @pytest.fixture
    def inspector(self) -> DataInspector:
        return DataInspector()

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
```

#### 3.1.8 Timeout Handling Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| UT-TMT-001 | `test_expression_timeout_error` | Expression exceeds timeout | ExpressionTimeoutError raised |
| UT-TMT-002 | `test_evaluate_multiple_partial_timeout` | Some expressions timeout | Returns partial results + timed_out list |
| UT-TMT-003 | `test_inspect_partial_result` | Inspection with timeouts | result.partial=True, timed_out populated |

```python
class TestTimeoutHandling:
    """Test timeout handling."""

    @pytest.fixture
    def inspector(self) -> DataInspector:
        return DataInspector()

    @pytest.mark.asyncio
    async def test_expression_timeout_error(self, inspector):
        """Test that slow evaluation raises ExpressionTimeoutError."""
        async def slow_evaluate(*args, **kwargs):
            await asyncio.sleep(10)
            return {"result": "done"}

        from unittest.mock import MagicMock
        evaluator = MagicMock()
        evaluator.evaluate = slow_evaluate

        with pytest.raises(ExpressionTimeoutError):
            await inspector._evaluate_with_timeout(
                evaluator, "slow_expr", None, 0.1
            )

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

        from unittest.mock import MagicMock
        evaluator = MagicMock()
        evaluator.evaluate = mixed_evaluate

        expressions = {
            "fast1": "fast_expr_1",
            "slow1": "slow_expr_1",
            "fast2": "fast_expr_2",
        }

        results, timed_out = await inspector._evaluate_multiple(
            evaluator, expressions, None, 0.1
        )

        assert "fast1" in results or "fast2" in results
        assert "slow1" in timed_out
```

### 3.2 File: `tests/unit/test_inspection_models.py`

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| UT-MOD-001 | `test_inspection_options_defaults` | Default option values | Correct defaults |
| UT-MOD-002 | `test_inspection_options_validation` | Value range validation | Raises for invalid |
| UT-MOD-003 | `test_inspection_result_serialization` | Model to dict conversion | Valid JSON-serializable dict |
| UT-MOD-004 | `test_statistics_model` | Statistics model fields | All fields nullable |
| UT-MOD-005 | `test_detected_type_enum` | DetectedType enum values | All expected values present |

```python
"""Tests for inspection models."""

import pytest
from pydantic import ValidationError

from pybugger_mcp.models.inspection import (
    DetectedType,
    InspectionOptions,
    InspectionPreview,
    InspectionResult,
    Statistics,
)


class TestInspectionOptions:
    """Test InspectionOptions model."""

    def test_defaults(self):
        """Test default values."""
        opts = InspectionOptions()
        assert opts.max_preview_rows == 5
        assert opts.max_preview_items == 10
        assert opts.include_statistics is True
        assert opts.timeout_per_expression == 2.0

    def test_validation_max_preview_rows(self):
        """Test max_preview_rows validation."""
        # Valid
        assert InspectionOptions(max_preview_rows=1).max_preview_rows == 1
        assert InspectionOptions(max_preview_rows=100).max_preview_rows == 100

        # Invalid
        with pytest.raises(ValidationError):
            InspectionOptions(max_preview_rows=0)
        with pytest.raises(ValidationError):
            InspectionOptions(max_preview_rows=101)

    def test_validation_timeout(self):
        """Test timeout validation."""
        assert InspectionOptions(timeout_per_expression=0.1).timeout_per_expression == 0.1
        assert InspectionOptions(timeout_per_expression=10.0).timeout_per_expression == 10.0

        with pytest.raises(ValidationError):
            InspectionOptions(timeout_per_expression=0.05)
        with pytest.raises(ValidationError):
            InspectionOptions(timeout_per_expression=11.0)


class TestDetectedType:
    """Test DetectedType enum."""

    def test_all_values(self):
        """Test all expected values exist."""
        assert DetectedType.DATAFRAME.value == "dataframe"
        assert DetectedType.SERIES.value == "series"
        assert DetectedType.NDARRAY.value == "ndarray"
        assert DetectedType.DICT.value == "dict"
        assert DetectedType.LIST.value == "list"
        assert DetectedType.PRIMITIVE.value == "primitive"
        assert DetectedType.UNKNOWN.value == "unknown"


class TestInspectionResult:
    """Test InspectionResult model."""

    def test_serialization(self):
        """Test model serialization."""
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

    def test_optional_fields(self):
        """Test optional fields default to appropriate values."""
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
```

---

## 4. Integration Test Specifications

### 4.1 File: `tests/integration/test_api_inspection.py`

#### 4.1.1 MCP Tool Parameter Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| IT-PAR-001 | `test_session_not_found_error` | Call with invalid session ID | Error with code NOT_FOUND |
| IT-PAR-002 | `test_session_not_paused_error` | Call when session running | Error with code INVALID_STATE |
| IT-PAR-003 | `test_invalid_variable_name_error` | Call with invalid var name | Error with code INVALID_VARIABLE |
| IT-PAR-004 | `test_max_preview_rows_capped` | Request >100 rows | Capped at 100 |
| IT-PAR-005 | `test_default_parameters` | Call with minimal params | Defaults applied |
| IT-PAR-006 | `test_format_json_default` | No format specified | JSON format returned |
| IT-PAR-007 | `test_format_tui` | format="tui" | Includes "formatted" field |

```python
"""Integration tests for debug_inspect_variable MCP tool."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from pybugger_mcp.core.session import SessionManager
from pybugger_mcp.main import create_app
from pybugger_mcp.persistence.breakpoints import BreakpointStore


@pytest_asyncio.fixture
async def test_client(tmp_path):
    """Create test client with session manager."""
    app = create_app()
    breakpoint_store = BreakpointStore(base_dir=tmp_path / "breakpoints")
    session_manager = SessionManager(breakpoint_store=breakpoint_store)
    await session_manager.start()
    app.state.session_manager = session_manager

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    await session_manager.stop()


class TestInspectVariableTool:
    """Test debug_inspect_variable MCP tool."""

    @pytest.mark.asyncio
    async def test_session_not_found(self):
        """Test error response when session doesn't exist."""
        from pybugger_mcp.mcp_server import debug_inspect_variable

        result = await debug_inspect_variable(
            session_id="nonexistent_session",
            variable_name="df",
        )

        assert "error" in result
        assert result["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_default_parameters(self):
        """Test default parameter values are applied correctly."""
        from pybugger_mcp.models.inspection import InspectionOptions

        options = InspectionOptions()
        assert options.max_preview_rows == 5
        assert options.include_statistics is True
        assert options.timeout_per_expression == 2.0

    @pytest.mark.asyncio
    async def test_max_preview_rows_capped(self):
        """Test that max_preview_rows is capped at 100."""
        from pybugger_mcp.models.inspection import InspectionOptions

        # Valid max
        options = InspectionOptions(max_preview_rows=100)
        assert options.max_preview_rows == 100

        # Would be invalid if >100
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            InspectionOptions(max_preview_rows=101)


class TestInspectVariableValidation:
    """Test parameter validation."""

    def test_variable_name_validation(self):
        """Test variable name validation patterns."""
        from pybugger_mcp.utils.data_inspector import DataInspector

        inspector = DataInspector()

        # Valid names
        assert inspector._is_valid_identifier("df") is True
        assert inspector._is_valid_identifier("my_var") is True
        assert inspector._is_valid_identifier("obj.attr") is True
        assert inspector._is_valid_identifier("items[0]") is True

        # Invalid names
        assert inspector._is_valid_identifier("") is False
        assert inspector._is_valid_identifier("123") is False
        assert inspector._is_valid_identifier("a b") is False
```

#### 4.1.2 Response Format Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| IT-RSP-001 | `test_response_structure_dataframe` | DataFrame response | Has all required fields |
| IT-RSP-002 | `test_response_structure_error` | Error response | Has error, code, hint |
| IT-RSP-003 | `test_response_size_limit` | Large data response | <100KB |

```python
class TestResponseFormat:
    """Test response format compliance."""

    def test_response_fields_present(self):
        """Test required fields are present in responses."""
        from pybugger_mcp.models.inspection import (
            InspectionResult,
            DetectedType,
        )

        result = InspectionResult(
            name="test",
            type="DataFrame",
            detected_type=DetectedType.DATAFRAME,
            structure={"shape": (100, 5)},
            summary="Test summary",
        )

        data = result.model_dump()

        # Required fields
        assert "name" in data
        assert "type" in data
        assert "detected_type" in data
        assert "structure" in data
        assert "summary" in data

        # Optional fields should be present with defaults
        assert "warnings" in data
        assert "partial" in data
        assert "timed_out" in data

    def test_error_response_format(self):
        """Test error response has required fields."""
        from pybugger_mcp.models.inspection import InspectionError

        error = InspectionError(
            error="Variable not found",
            code="VARIABLE_NOT_FOUND",
            available_variables=["df", "config"],
            hint="Check variable name",
        )

        data = error.model_dump()
        assert data["error"] == "Variable not found"
        assert data["code"] == "VARIABLE_NOT_FOUND"
        assert "df" in data["available_variables"]
```

---

## 5. E2E Test Specifications

### 5.1 File: `tests/e2e/test_data_inspection.py`

#### 5.1.1 Full Workflow Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| E2E-WF-001 | `test_full_dataframe_inspection_workflow` | Complete DataFrame debug flow | All fields populated correctly |
| E2E-WF-002 | `test_full_ndarray_inspection_workflow` | Complete ndarray debug flow | Shape, dtype, statistics present |
| E2E-WF-003 | `test_full_dict_inspection_workflow` | Complete dict debug flow | Keys, values, length present |
| E2E-WF-004 | `test_full_list_inspection_workflow` | Complete list debug flow | Length, types, sample present |
| E2E-WF-005 | `test_multiple_inspections_same_session` | Inspect multiple vars | Each returns correct data |

```python
"""End-to-end tests for data inspection feature.

These tests require pandas and numpy to be installed.
They test the full inspection workflow with real data types.
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

# Skip if pandas/numpy not available
pytest.importorskip("pandas")
pytest.importorskip("numpy")


class TestDataFrameInspectionE2E:
    """E2E tests for DataFrame inspection."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_dataframe_inspection_workflow(self, dataframe_script):
        """Test complete DataFrame inspection during debug session."""
        from pybugger_mcp.mcp_server import (
            debug_create_session,
            debug_set_breakpoints,
            debug_launch,
            debug_poll_events,
            debug_inspect_variable,
            debug_terminate_session,
        )

        script_path = str(dataframe_script)
        project_root = str(dataframe_script.parent)

        try:
            # 1. Create session
            session_result = await debug_create_session(
                project_root=project_root,
                name="dataframe_test",
            )
            session_id = session_result["session_id"]

            # 2. Set breakpoint on last line (x = 1)
            await debug_set_breakpoints(
                session_id=session_id,
                file_path=script_path,
                lines=[24],  # x = 1 line
            )

            # 3. Launch
            await debug_launch(
                session_id=session_id,
                program=script_path,
            )

            # 4. Wait for stop event
            for _ in range(50):  # 10 second timeout
                events = await debug_poll_events(session_id, timeout_seconds=0.2)
                if any(e["type"] == "stopped" for e in events.get("events", [])):
                    break
                await asyncio.sleep(0.2)

            # 5. Inspect DataFrame
            df_result = await debug_inspect_variable(
                session_id=session_id,
                variable_name="df",
                max_preview_rows=3,
            )

            # Verify DataFrame inspection result
            assert df_result.get("type") == "DataFrame"
            assert df_result.get("detected_type") == "dataframe"
            assert "structure" in df_result
            assert "columns" in df_result["structure"]
            assert "preview" in df_result
            assert "summary" in df_result

            # Verify structure details
            structure = df_result["structure"]
            assert structure["shape"][0] == 5  # 5 rows
            assert structure["shape"][1] == 4  # 4 columns
            assert "id" in structure["columns"]
            assert "name" in structure["columns"]

            # 6. Cleanup
            await debug_terminate_session(session_id)

        except Exception as e:
            # Ensure cleanup even on failure
            try:
                await debug_terminate_session(session_id)
            except Exception:
                pass
            raise e

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_ndarray_inspection_workflow(self, dataframe_script):
        """Test complete NumPy array inspection."""
        from pybugger_mcp.mcp_server import (
            debug_create_session,
            debug_set_breakpoints,
            debug_launch,
            debug_poll_events,
            debug_inspect_variable,
            debug_terminate_session,
        )

        script_path = str(dataframe_script)
        project_root = str(dataframe_script.parent)

        try:
            session_result = await debug_create_session(
                project_root=project_root,
                name="ndarray_test",
            )
            session_id = session_result["session_id"]

            await debug_set_breakpoints(
                session_id=session_id,
                file_path=script_path,
                lines=[24],
            )

            await debug_launch(
                session_id=session_id,
                program=script_path,
            )

            # Wait for stop
            for _ in range(50):
                events = await debug_poll_events(session_id, timeout_seconds=0.2)
                if any(e["type"] == "stopped" for e in events.get("events", [])):
                    break
                await asyncio.sleep(0.2)

            # Inspect NumPy array
            arr_result = await debug_inspect_variable(
                session_id=session_id,
                variable_name="weights",
                include_statistics=True,
            )

            # Verify array inspection
            assert arr_result.get("type") == "ndarray"
            assert arr_result.get("detected_type") == "ndarray"
            assert "structure" in arr_result

            structure = arr_result["structure"]
            assert structure["shape"] == [10, 5] or structure["shape"] == (10, 5)
            assert structure["dtype"] == "float32"

            # Statistics should be present for small array
            assert "statistics" in arr_result
            if arr_result["statistics"]:
                assert "mean" in arr_result["statistics"] or arr_result["statistics"].get("mean") is not None

            await debug_terminate_session(session_id)

        except Exception as e:
            try:
                await debug_terminate_session(session_id)
            except Exception:
                pass
            raise e

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_inspect_multiple_variables(self, dataframe_script):
        """Test inspecting multiple variables in same session."""
        from pybugger_mcp.mcp_server import (
            debug_create_session,
            debug_set_breakpoints,
            debug_launch,
            debug_poll_events,
            debug_inspect_variable,
            debug_terminate_session,
        )

        script_path = str(dataframe_script)
        project_root = str(dataframe_script.parent)

        try:
            session_result = await debug_create_session(
                project_root=project_root,
            )
            session_id = session_result["session_id"]

            await debug_set_breakpoints(
                session_id=session_id,
                file_path=script_path,
                lines=[24],
            )

            await debug_launch(
                session_id=session_id,
                program=script_path,
            )

            # Wait for stop
            for _ in range(50):
                events = await debug_poll_events(session_id, timeout_seconds=0.2)
                if any(e["type"] == "stopped" for e in events.get("events", [])):
                    break
                await asyncio.sleep(0.2)

            # Inspect all variable types
            df_result = await debug_inspect_variable(session_id=session_id, variable_name="df")
            assert df_result.get("type") == "DataFrame"

            arr_result = await debug_inspect_variable(session_id=session_id, variable_name="weights")
            assert arr_result.get("type") == "ndarray"

            dict_result = await debug_inspect_variable(session_id=session_id, variable_name="config")
            assert dict_result.get("type") == "dict"

            list_result = await debug_inspect_variable(session_id=session_id, variable_name="items")
            assert list_result.get("type") == "list"

            await debug_terminate_session(session_id)

        except Exception as e:
            try:
                await debug_terminate_session(session_id)
            except Exception:
                pass
            raise e
```

#### 5.1.2 TUI Format Tests

| Test ID | Test Name | Description | Expected Result |
|---------|-----------|-------------|-----------------|
| E2E-TUI-001 | `test_inspect_with_tui_format` | Request format="tui" | "formatted" field present |
| E2E-TUI-002 | `test_tui_format_dataframe` | TUI format for DataFrame | Contains COLUMNS, PREVIEW sections |
| E2E-TUI-003 | `test_tui_format_array` | TUI format for ndarray | Contains STATISTICS section |

```python
class TestTUIFormattingE2E:
    """E2E tests for TUI formatting."""

    @pytest.mark.asyncio
    async def test_tui_formatter_integration(self):
        """Test TUI formatter produces expected output."""
        from pybugger_mcp.utils.tui_formatter import TUIFormatter

        formatter = TUIFormatter()

        # Test DataFrame inspection formatting
        inspection = {
            "name": "df",
            "type": "DataFrame",
            "detected_type": "dataframe",
            "structure": {
                "shape": (100, 5),
                "columns": ["id", "name", "value", "date", "status"],
                "dtypes": {"id": "int64", "name": "object", "value": "float64"},
                "null_counts": {"name": 5},
            },
            "preview": {"head": [{"id": 1, "name": "Alice", "value": 100.5}]},
            "summary": "DataFrame with 100 rows x 5 columns, 7.8 KB",
            "warnings": [],
        }

        result = formatter.format_inspection(inspection)

        # Verify TUI output structure
        assert "VARIABLE INSPECTION" in result
        assert "df" in result
        assert "DataFrame" in result
        assert "COLUMNS" in result
        assert "PREVIEW" in result

    @pytest.mark.asyncio
    async def test_tui_formatter_ndarray(self):
        """Test TUI formatter for ndarray inspection."""
        from pybugger_mcp.utils.tui_formatter import TUIFormatter

        formatter = TUIFormatter()

        inspection = {
            "name": "weights",
            "type": "ndarray",
            "detected_type": "ndarray",
            "structure": {
                "shape": (128, 256),
                "dtype": "float32",
                "size": 32768,
                "memory_bytes": 131072,
            },
            "statistics": {
                "min": -0.98,
                "max": 0.97,
                "mean": 0.002,
                "std": 0.45,
            },
            "preview": {"sample": [0.1, -0.2, 0.3]},
            "summary": "ndarray float32 [128, 256], 128 KB",
            "warnings": [],
        }

        result = formatter.format_inspection(inspection)

        assert "VARIABLE INSPECTION" in result
        assert "weights" in result
        assert "ndarray" in result
        assert "STATISTICS" in result
```

---

## 6. Edge Case Test Scenarios

### 6.1 Mapping to User Story Edge Cases

| Edge Case ID | User Story Reference | Test ID | Test Name |
|--------------|---------------------|---------|-----------|
| EC-1 | Variable Not Found | EC-001 | `test_variable_not_found_returns_available_vars` |
| EC-2 | Session Not Paused | EC-002 | `test_session_not_paused_error` |
| EC-3 | Very Large DataFrame | EC-003 | `test_large_dataframe_truncates_preview` |
| EC-4 | DataFrame with Complex Types | EC-004 | `test_dataframe_complex_columns` |
| EC-5 | NumPy Array with NaN/Inf | EC-005 | `test_array_nan_inf_handling` |
| EC-6 | pandas/NumPy Not Installed | EC-006 | `test_pandas_unavailable_fallback` |
| EC-7 | Empty DataFrame/Array | EC-007 | `test_empty_structures` |
| EC-8 | pandas Series | EC-008 | `test_series_vs_dataframe` |
| EC-9 | Nested List/Dict | EC-009 | `test_nested_structures_depth_limit` |
| EC-10 | Evaluation Timeout | EC-010 | `test_timeout_partial_result` |

### 6.2 Edge Case Test Implementations

```python
"""Edge case tests for data inspection (EC-1 through EC-10)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from pybugger_mcp.models.inspection import (
    DetectedType,
    InspectionOptions,
)
from pybugger_mcp.utils.data_inspector import DataInspector


class TestEdgeCases:
    """Tests for edge cases EC-1 through EC-10."""

    @pytest.fixture
    def inspector(self) -> DataInspector:
        return DataInspector()

    # EC-1: Variable Not Found
    @pytest.mark.asyncio
    async def test_ec1_variable_not_found(self):
        """EC-1: Variable not found returns available variables list."""
        # This is handled at the session/tool level
        # The DataInspector assumes variable exists
        # Test at integration level with full session

        from pybugger_mcp.models.inspection import InspectionError

        error = InspectionError(
            error="Variable 'nonexistent' not found in current scope",
            code="VARIABLE_NOT_FOUND",
            available_variables=["df", "config", "result"],
            hint="Check variable name spelling",
        )

        assert error.code == "VARIABLE_NOT_FOUND"
        assert "df" in error.available_variables

    # EC-2: Session Not Paused
    @pytest.mark.asyncio
    async def test_ec2_session_not_paused(self):
        """EC-2: Session not paused returns INVALID_STATE error."""
        # Handled at MCP tool level
        # Test expects error response with session state info

        expected_error = {
            "error": "Cannot inspect variables while program is running",
            "code": "INVALID_STATE",
            "session_state": "running",
            "hint": "Set a breakpoint and wait for the program to pause",
        }

        assert expected_error["code"] == "INVALID_STATE"

    # EC-3: Very Large DataFrame
    @pytest.mark.asyncio
    async def test_ec3_large_dataframe(self, inspector, mock_evaluator):
        """EC-3: Very large DataFrame (>1M rows) triggers warnings."""
        evaluator = mock_evaluator({
            "pandas.core.frame": "True",
            ".shape": "[10000000, 50]",  # 10M rows
            ".columns": "['col1', 'col2']",
            ".dtypes": "{}",
            "memory_usage": "4000000000",  # 4GB
            ".head": "[{'col1': 1}]",
        })

        result = await inspector._inspect_dataframe(
            evaluator, "huge_df", None, InspectionOptions()
        )

        assert result.structure.get("truncated") is True
        assert len(result.warnings) > 0
        assert any("Large" in w or "limited" in w.lower() for w in result.warnings)

    # EC-4: DataFrame with Complex Types
    @pytest.mark.asyncio
    async def test_ec4_complex_column_types(self, inspector, mock_evaluator):
        """EC-4: DataFrame with complex column types (lists, dicts)."""
        evaluator = mock_evaluator({
            "pandas.core.frame": "True",
            ".shape": "[100, 4]",
            ".columns": "['id', 'tags', 'metadata', 'embedding']",
            ".dtypes": "{'id': 'int64', 'tags': 'object', 'metadata': 'object', 'embedding': 'object'}",
            ".head": "[{'id': 1, 'tags': '[3 items]', 'metadata': '{dict}', 'embedding': '[ndarray]'}]",
        })

        result = await inspector._inspect_dataframe(
            evaluator, "complex_df", None, InspectionOptions()
        )

        # Should have columns with object dtype
        assert "object" in str(result.structure.get("dtypes", {}))

    # EC-5: NumPy Array with NaN/Inf
    @pytest.mark.asyncio
    async def test_ec5_nan_inf_values(self, inspector, mock_evaluator):
        """EC-5: NumPy array with NaN/Inf values reports counts."""
        evaluator = mock_evaluator({
            ".size": "1000",
            ".shape": "[1000]",
            ".dtype": "'float64'",
            ".ndim": "1",
            ".nbytes": "8000",
            ".min()": "-100.5",
            ".max()": "200.3",
            ".mean()": "45.2",
            ".std()": "30.1",
            "isnan": "15",
            "isinf": "2",
        })

        result = await inspector._inspect_ndarray(
            evaluator, "data", None, InspectionOptions()
        )

        assert result.statistics is not None
        assert result.statistics.nan_count == 15
        assert result.statistics.inf_count == 2
        assert any("NaN" in w or "Inf" in w for w in result.warnings)

    # EC-6: pandas/NumPy Not Installed (fallback)
    @pytest.mark.asyncio
    async def test_ec6_pandas_unavailable_fallback(self, inspector, mock_evaluator):
        """EC-6: Graceful fallback when pandas introspection fails."""
        # All detection fails -> unknown type with basic info
        evaluator = mock_evaluator({
            "type_module": "'pandas.core.frame'",
            "type_name": "'DataFrame'",
            "repr": "'<DataFrame object>'",
            "attributes": "['shape', 'columns']",
        })

        result = await inspector._inspect_unknown(
            evaluator, "df", None, InspectionOptions()
        )

        assert result.detected_type == DetectedType.UNKNOWN
        assert result.hint is not None
        assert "debug_get_variables" in result.hint or "evaluate" in result.hint.lower()

    # EC-7: Empty DataFrame/Array
    @pytest.mark.asyncio
    async def test_ec7_empty_dataframe(self, inspector, mock_evaluator):
        """EC-7: Empty DataFrame (0 rows) handled correctly."""
        evaluator = mock_evaluator({
            "pandas.core.frame": "True",
            ".shape": "[0, 5]",
            ".columns": "['id', 'name', 'value', 'date', 'status']",
            ".dtypes": "{'id': 'int64', 'name': 'object'}",
            ".head": "[]",
            "memory_usage": "1000",
        })

        result = await inspector._inspect_dataframe(
            evaluator, "empty_df", None, InspectionOptions()
        )

        assert result.structure["shape"] == (0, 5) or result.structure["shape"] == [0, 5]
        assert len(result.structure["columns"]) == 5
        assert result.preview.head == []
        assert "Empty" in result.summary or "0 rows" in result.summary

    @pytest.mark.asyncio
    async def test_ec7_empty_array(self, inspector, mock_evaluator):
        """EC-7: Empty ndarray handled correctly."""
        evaluator = mock_evaluator({
            ".size": "0",
            ".shape": "[0]",
            ".dtype": "'float64'",
            ".ndim": "1",
            ".nbytes": "0",
        })

        result = await inspector._inspect_ndarray(
            evaluator, "empty_arr", None, InspectionOptions()
        )

        assert result.structure["size"] == 0

    # EC-8: pandas Series (not DataFrame)
    @pytest.mark.asyncio
    async def test_ec8_series_detection(self, inspector, mock_evaluator):
        """EC-8: Series detected and handled differently from DataFrame."""
        evaluator = mock_evaluator({
            "pandas.core.series": "True",
            "len(": "1000",
            "str({var}.dtype)": "'float64'",
            "{var}.name": "'price'",
            ".head": "[9.99, 15.50, 22.00]",
            ".tail": "[45.99, 50.00, 55.00]",
            ".min()": "9.99",
            ".max()": "999.99",
            ".mean()": "150.50",
            ".std()": "45.2",
            "isnull": "5",
        })

        result = await inspector._inspect_series(
            evaluator, "prices", None, InspectionOptions()
        )

        assert result.type == "Series"
        assert result.detected_type == DetectedType.SERIES
        assert "length" in result.structure
        assert result.preview.head is not None
        assert result.preview.tail is not None

    # EC-9: Nested List/Dict Structures
    @pytest.mark.asyncio
    async def test_ec9_nested_dict(self, inspector, mock_evaluator):
        """EC-9: Deeply nested dict shows limited depth."""
        evaluator = mock_evaluator({
            "len(": "500",
            "key_types": "['str']",
            "value_types": "['dict']",
            "keys())": "['level1', 'level2']",
            "items())": "{'level1': {'nested': {'deep': 'value'}}}",
        })

        result = await inspector._inspect_dict(
            evaluator, "nested", None, InspectionOptions()
        )

        assert result.type == "dict"
        assert result.structure["length"] == 500

    # EC-10: Evaluation Timeout
    @pytest.mark.asyncio
    async def test_ec10_timeout_partial_result(self, inspector):
        """EC-10: Timeout returns partial results."""
        import asyncio

        call_count = 0

        async def slow_evaluate(expression, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if "statistics" in expression or "mean" in expression:
                await asyncio.sleep(10)  # Will timeout
            return {"result": "[100, 5]" if "shape" in expression else "None"}

        evaluator = MagicMock()
        evaluator.evaluate = slow_evaluate

        # Use very short timeout
        options = InspectionOptions(timeout_per_expression=0.05)

        expressions = {
            "shape": "{var}.shape",
            "mean": "{var}.mean()",  # Will timeout
        }

        results, timed_out = await inspector._evaluate_multiple(
            evaluator, expressions, None, options.timeout_per_expression
        )

        # Should have partial results
        assert len(timed_out) > 0 or len(results) < len(expressions)
```

---

## 7. Test Data Requirements

### 7.1 Mock Data Fixtures

| Fixture | Purpose | Data Characteristics |
|---------|---------|---------------------|
| `mock_evaluator` | Unit test evaluator | Configurable responses |
| `dataframe_script` | E2E DataFrame test | 5 rows, 4 columns, mixed types |
| `empty_dataframe_script` | Empty structure tests | 0 rows, empty collections |
| `large_data_script` | Performance/size tests | 100K rows, 1M array |

### 7.2 Test Script Templates

```python
# Standard DataFrame test script
DATAFRAME_SCRIPT = '''
import pandas as pd
import numpy as np

df = pd.DataFrame({
    "id": [1, 2, 3, 4, 5],
    "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
    "value": [100.5, 200.3, 150.0, 300.1, 250.7],
    "active": [True, False, True, True, False],
})

prices = pd.Series([9.99, 15.50, 22.00, 45.99, 50.00], name="price")
weights = np.random.randn(10, 5).astype(np.float32)
config = {"host": "localhost", "port": 5432, "database": "testdb"}
items = list(range(100))

x = 1  # Breakpoint line
'''

# Empty structures test script
EMPTY_SCRIPT = '''
import pandas as pd
import numpy as np

empty_df = pd.DataFrame(columns=["a", "b", "c"])
empty_array = np.array([])
empty_dict = {}
empty_list = []

x = 1
'''

# Large data test script
LARGE_DATA_SCRIPT = '''
import pandas as pd
import numpy as np

large_df = pd.DataFrame({f"col_{i}": range(100000) for i in range(50)})
large_array = np.random.randn(1000000)
large_dict = {f"key_{i}": f"value_{i}" for i in range(10000)}

x = 1
'''

# NaN/Inf test script
NAN_INF_SCRIPT = '''
import numpy as np

data = np.array([1.0, 2.0, np.nan, 4.0, np.inf, 6.0, -np.inf, 8.0, np.nan, 10.0])
clean_data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

x = 1
'''
```

### 7.3 Mock Evaluator Response Configurations

```python
# DataFrame mock responses
DATAFRAME_RESPONSES = {
    "pandas.core.frame": "True",
    ".shape": "[1000, 5]",
    ".columns": "['id', 'name', 'value', 'date', 'status']",
    ".dtypes": "{'id': 'int64', 'name': 'object', 'value': 'float64'}",
    "index).__name__": "'RangeIndex'",
    "memory_usage": "80000",
    "isnull().sum()": "{'name': 5, 'value': 12}",
    ".head": "[{'id': 1, 'name': 'Alice', 'value': 100.5}]",
}

# Series mock responses
SERIES_RESPONSES = {
    "pandas.core.series": "True",
    "len(": "1000",
    "str({var}.dtype)": "'float64'",
    "{var}.name": "'prices'",
    ".head": "[9.99, 15.50, 22.00]",
    ".tail": "[45.99, 50.00]",
    ".min()": "9.99",
    ".max()": "999.99",
    ".mean()": "150.50",
}

# ndarray mock responses
NDARRAY_RESPONSES = {
    ".size": "32768",
    ".shape": "[128, 256]",
    ".dtype": "'float32'",
    ".ndim": "2",
    ".nbytes": "131072",
    "flatten()": "[0.1, 0.2, 0.3]",
    ".min()": "-0.98",
    ".max()": "0.97",
    ".mean()": "0.002",
    ".std()": "0.45",
}
```

---

## 8. Coverage Matrix

### 8.1 Acceptance Criteria to Test Mapping

| AC ID | Acceptance Criteria | Test ID(s) | Test Type |
|-------|---------------------|------------|-----------|
| AC-1 | Tool accepts session_id, variable_name, frame_id, max_preview_rows | IT-PAR-005, IT-PAR-004 | Integration |
| AC-2 | Detects DataFrame with shape, columns, dtypes, memory | UT-DF-001, E2E-WF-001 | Unit, E2E |
| AC-3 | Detects Series with length, dtype, name, stats | UT-SER-001, UT-SER-002 | Unit |
| AC-4 | Detects ndarray with shape, dtype, stats | UT-ARR-001, E2E-WF-002 | Unit, E2E |
| AC-5 | Detects dict with length, key sample, value sample | UT-DICT-001, E2E-WF-003 | Unit, E2E |
| AC-6 | Detects list with length, element types, sample | UT-LIST-001, E2E-WF-004 | Unit, E2E |
| AC-7 | Returns detected_type: "unknown" for unsupported | UT-DET-006, UT-UNK-001 | Unit |
| AC-8 | DataFrame preview includes head rows | UT-DF-004, E2E-WF-001 | Unit, E2E |
| AC-9 | NumPy preview includes sample values | UT-ARR-006, E2E-WF-002 | Unit, E2E |
| AC-10 | Dict preview includes sample pairs | UT-DICT-002 | Unit |
| AC-11 | List preview includes sample values | UT-LIST-001 | Unit |
| AC-12 | Previews respect max_preview_rows | IT-PAR-004 | Integration |
| AC-13 | Response includes summary string | UT-DF-006, UT-MOD-003 | Unit |
| AC-14 | Summary includes type, dimensions, memory | UT-DF-006 | Unit |
| AC-15 | Summary flags warnings | UT-DF-003, EC-003 | Unit, Edge |
| AC-16 | Response size <100KB | IT-RSP-003 | Integration |
| AC-17 | Expression timeout 2s | UT-TMT-001, EC-010 | Unit, Edge |
| AC-18 | Large datasets limit preview | EC-003 | Edge |
| AC-19 | Skip stats for >10M elements | UT-ARR-004, EC-003 | Unit, Edge |
| AC-20 | Partial results on timeout | UT-TMT-002, EC-010 | Unit, Edge |
| AC-21 | Variable not found error | EC-001 | Edge |
| AC-22 | Session not paused error | EC-002 | Edge |
| AC-23 | Graceful fallback on failure | EC-006 | Edge |
| AC-24 | Never raises exceptions | All tests | All |
| AC-25 | No new runtime dependencies | (Manual review) | - |
| AC-26 | Works with Python 3.10+ | CI matrix | - |
| AC-27 | P95 latency <500ms | Performance tests | - |
| AC-28 | Unit tests >90% coverage | pytest-cov | - |
| AC-29 | Integration tests all contracts | IT-* | Integration |
| AC-30 | E2E demonstrates workflow | E2E-WF-001 | E2E |

### 8.2 Edge Case to Test Mapping

| EC ID | Edge Case | Test ID | Status |
|-------|-----------|---------|--------|
| EC-1 | Variable Not Found | EC-001 | Planned |
| EC-2 | Session Not Paused | EC-002 | Planned |
| EC-3 | Very Large DataFrame | EC-003 | Planned |
| EC-4 | Complex Column Types | EC-004 | Planned |
| EC-5 | NaN/Inf Values | EC-005 | Planned |
| EC-6 | pandas Not Available | EC-006 | Planned |
| EC-7 | Empty Structures | EC-007 | Planned |
| EC-8 | Series vs DataFrame | EC-008 | Planned |
| EC-9 | Nested Structures | EC-009 | Planned |
| EC-10 | Evaluation Timeout | EC-010 | Planned |

---

## 9. Quality Metrics & Acceptance

### 9.1 Test Execution Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Unit Test Pass Rate | 100% | pytest exit code |
| Integration Test Pass Rate | 100% | pytest exit code |
| E2E Test Pass Rate | 100% | pytest exit code |
| Code Coverage (data_inspector.py) | >90% | pytest-cov |
| Code Coverage (models/inspection.py) | >80% | pytest-cov |

### 9.2 Performance Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Average inspection time | <200ms | pytest timing |
| P95 inspection time | <500ms | pytest timing |
| Max response size | <100KB | Response size check |
| Timeout handling | 2s per expression | Timeout tests |

### 9.3 Definition of Done

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All E2E tests pass
- [ ] All edge case tests pass
- [ ] Code coverage >90% for data_inspector.py
- [ ] Code coverage >80% for models/inspection.py
- [ ] No regressions in existing test suite
- [ ] Performance targets met
- [ ] Test plan document complete

### 9.4 CI/CD Integration

```yaml
# Add to existing CI workflow
test-data-inspection:
  runs-on: ubuntu-latest
  strategy:
    matrix:
      python-version: ['3.10', '3.11', '3.12']
  steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      run: |
        pip install -e ".[dev]"
    - name: Run tests with coverage
      run: |
        pytest tests/unit/test_data_inspector.py \
               tests/unit/test_inspection_models.py \
               tests/integration/test_api_inspection.py \
               tests/e2e/test_data_inspection.py \
               --cov=src/pybugger_mcp/utils/data_inspector \
               --cov=src/pybugger_mcp/models/inspection \
               --cov-report=xml \
               --cov-fail-under=90 \
               -v
```

---

## Appendix A: Test Execution Commands

```bash
# Run all data inspection tests
pytest tests/unit/test_data_inspector.py \
       tests/unit/test_inspection_models.py \
       tests/integration/test_api_inspection.py \
       tests/e2e/test_data_inspection.py \
       -v

# Run unit tests only
pytest tests/unit/test_data_inspector.py -v

# Run with coverage
pytest tests/unit/test_data_inspector.py \
       --cov=src/pybugger_mcp/utils/data_inspector \
       --cov-report=html

# Run specific test class
pytest tests/unit/test_data_inspector.py::TestTypeDetection -v

# Run edge case tests
pytest tests/unit/test_data_inspector.py -k "ec" -v

# Run E2E tests (slow, requires pandas/numpy)
pytest tests/e2e/test_data_inspection.py -v --slow
```

---

## Appendix B: Test File Templates

### tests/unit/test_data_inspector.py Template

```python
"""Unit tests for DataInspector."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pybugger_mcp.models.inspection import (
    DetectedType,
    InspectionOptions,
    InspectionResult,
)
from pybugger_mcp.utils.data_inspector import (
    DataInspector,
    ExpressionTimeoutError,
    get_inspector,
)


# MockEvaluator class here...

# Test classes here...
```

### tests/e2e/test_data_inspection.py Template

```python
"""End-to-end tests for data inspection feature."""

import asyncio
from pathlib import Path

import pytest

pytest.importorskip("pandas")
pytest.importorskip("numpy")

# Test classes here...
```

---

*Document End*

*Last Updated: 2026-01-15*
*Version: 1.0*
