# User Story: DataFrame/NumPy Smart Preview

**Story ID:** US-DATA-002
**Epic:** Data Science Debugging Enhancement
**Priority:** P2 - High Value
**Story Points:** 5
**Created:** 2026-01-15
**Status:** Ready for Development

---

## Problem Statement

### Current State

When AI agents debug Python code using polybugger-mcp, they call `debug_get_variables` to inspect the current state. For common data science objects like pandas DataFrames, NumPy arrays, and large collections, the debugger returns truncated string representations that are not actionable:

```json
{
  "name": "df",
  "value": "<DataFrame 1000x5>",
  "type": "DataFrame",
  "variables_reference": 42,
  "has_children": true
}
```

To understand the DataFrame, the AI agent must:
1. Manually evaluate expressions like `df.shape`, `df.columns`, `df.dtypes`
2. Call `debug_evaluate` multiple times with various introspection commands
3. Parse string outputs back into structured data
4. Guess which expressions are valid for different data types

This process is:
- **Token-expensive:** Multiple round trips and parsing overhead
- **Error-prone:** AI may use wrong introspection methods for each type
- **Inconsistent:** Different AI agents implement different inspection strategies
- **Incomplete:** Important context (memory usage, statistical summary) often missed

### Pain Points

| Stakeholder | Pain Point | Impact |
|-------------|------------|--------|
| AI Agents | Must issue 5-10 `debug_evaluate` calls to understand one DataFrame | Increased latency, token cost, conversation complexity |
| AI Agents | Cannot determine appropriate introspection method for unknown types | Wrong expressions cause errors, wasted attempts |
| Developers | AI provides incomplete data structure context | Poor debugging guidance, missing critical details |
| Developers | Large datasets shown as unhelpful truncated strings | Cannot understand data shape, types, or sample values |
| AI Agents | No standardized format for data structure metadata | Each conversation reinvents the inspection pattern |

### Example: Current vs. Desired Workflow

**Current Workflow (5+ tool calls):**
```
AI: debug_get_variables(ref=locals_ref)
    -> sees df: "<DataFrame 1000x5>"

AI: debug_evaluate("df.shape")
    -> (1000, 5)

AI: debug_evaluate("list(df.columns)")
    -> ['id', 'name', 'value', 'date', 'status']

AI: debug_evaluate("df.dtypes.to_dict()")
    -> {'id': 'int64', 'name': 'object', ...}

AI: debug_evaluate("df.head(3).to_dict('records')")
    -> [{'id': 1, 'name': 'Alice', ...}, ...]

AI: debug_evaluate("df.memory_usage(deep=True).sum()")
    -> 80000
```

**Desired Workflow (1 tool call):**
```
AI: debug_inspect_variable(variable_name="df")
    -> {
         "name": "df",
         "type": "DataFrame",
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
```

### Business Case

- **5x Reduction in Tool Calls:** Single call replaces 5-10 evaluate calls for data inspection
- **Faster Debugging Sessions:** Reduced latency and token usage per data inspection
- **Higher AI Accuracy:** Structured metadata prevents expression guessing errors
- **Better Developer Experience:** AI can provide richer context about data structures
- **Differentiation:** Positions polybugger-mcp as the premier debugging tool for data science workflows

---

## User Personas

### Primary: AI Coding Assistants Debugging Data Science Code

**Representative Users:** Claude (Anthropic), GPT-4 (OpenAI), GitHub Copilot, Cursor AI, Cline

**Characteristics:**
- Debug Python code involving pandas, NumPy, and data processing
- Need to understand data shapes and types to diagnose issues
- Must provide meaningful feedback to developers about data state
- Operate under token/cost constraints - efficiency matters
- Cannot render visual plots - need text-based data summaries

**Goals:**
- Inspect data structures with minimal tool calls
- Receive structured, machine-readable metadata (not strings to parse)
- Provide developers with actionable data context quickly
- Understand data types to suggest appropriate debugging strategies

**Frustrations:**
- Multiple round trips to understand one variable
- Parsing string outputs from evaluate calls
- Guessing correct introspection expressions for each type
- Missing context like memory usage or value distributions

**Example Scenario:**
> "I'm debugging a pandas pipeline and hit a breakpoint. I see `df` in the variables but just get `<DataFrame 1000x5>`. I need to know the column names, types, and some sample values to understand if the data transformation is correct. Currently I have to call `debug_evaluate` 5 times to get this information."

### Secondary: Developers Debugging Data Pipelines

**Representative Users:** Data engineers, ML engineers, backend developers working with pandas/NumPy

**Characteristics:**
- Work with DataFrames, arrays, and large collections daily
- Need to verify data shapes at various pipeline stages
- Debug data type mismatches and missing values
- Use AI assistants to accelerate debugging

**Goals:**
- Quickly verify DataFrame shapes match expectations
- See sample values without printing entire datasets
- Understand memory footprint of data structures
- Identify dtype issues early

**Frustrations:**
- AI assistant can't tell them column names without multiple queries
- No quick way to see if data looks correct
- Memory issues are invisible until they cause crashes
- Type information requires manual inspection

**Example Scenario:**
> "My ETL job is failing silently. I stopped at a breakpoint and asked my AI assistant what `results_df` looks like. It told me 'it's a DataFrame with 1000 rows' but couldn't tell me the columns or if there are nulls until I asked multiple follow-up questions."

---

## User Flows

### Flow 1: AI Inspects DataFrame at Breakpoint (Happy Path)

```
+---------------------------------------------------------------------------+
|                       DATAFRAME INSPECTION FLOW                           |
+---------------------------------------------------------------------------+

Developer                    AI Agent                     polybugger-mcp
    |                            |                              |
    |  "What does df look like?" |                              |
    | -------------------------> |                              |
    |                            |                              |
    |                            |  1. debug_get_scopes(...)    |
    |                            |  2. debug_get_variables(     |
    |                            |       ref=locals_ref         |
    |                            |     )                        |
    |                            | ---------------------------> |
    |                            |                              |
    |                            |  variables: [                |
    |                            |    {name: "df",              |
    |                            |     type: "DataFrame",       |
    |                            |     value: "<DataFrame>"}    |
    |                            |  ]                           |
    |                            | <--------------------------- |
    |                            |                              |
    |                            |  // AI detects DataFrame     |
    |                            |  debug_inspect_variable(     |
    |                            |    session_id="abc",         |
    |                            |    variable_name="df",       |
    |                            |    max_preview_rows=5        |
    |                            |  )                           |
    |                            | ---------------------------> |
    |                            |                              |
    |                            |  {                           |
    |                            |    name: "df",               |
    |                            |    type: "DataFrame",        |
    |                            |    structure: {              |
    |                            |      shape: [1000, 5],       |
    |                            |      columns: [...],         |
    |                            |      dtypes: {...},          |
    |                            |      memory_bytes: 80000     |
    |                            |    },                        |
    |                            |    preview: {                |
    |                            |      head: [{...}, ...]      |
    |                            |    },                        |
    |                            |    summary: "DataFrame..."   |
    |                            |  }                           |
    |                            | <--------------------------- |
    |                            |                              |
    |  "df is a DataFrame with   |                              |
    |   1000 rows x 5 columns    |                              |
    |   (78 KB):                 |                              |
    |                            |                              |
    |   Columns:                 |                              |
    |   - id (int64)             |                              |
    |   - name (object)          |                              |
    |   - value (float64)        |                              |
    |   - date (datetime64)      |                              |
    |   - status (object)        |                              |
    |                            |                              |
    |   First 3 rows:            |                              |
    |   | id | name  | value |   |                              |
    |   | 1  | Alice | 100.5 |   |                              |
    |   | 2  | Bob   | 200.3 |"  |                              |
    | <------------------------- |                              |
```

**Steps:**
1. Developer asks AI about a variable
2. AI calls `debug_get_variables` and sees `df` with type `DataFrame`
3. AI calls `debug_inspect_variable` for detailed metadata
4. polybugger-mcp returns structured metadata with shape, columns, dtypes, preview
5. AI formats and presents comprehensive DataFrame summary to developer

### Flow 2: AI Inspects NumPy Array

```
+---------------------------------------------------------------------------+
|                       NUMPY ARRAY INSPECTION FLOW                         |
+---------------------------------------------------------------------------+

Developer                    AI Agent                     polybugger-mcp
    |                            |                              |
    |  "What's in the weights    |                              |
    |   array?"                  |                              |
    | -------------------------> |                              |
    |                            |                              |
    |                            |  debug_inspect_variable(     |
    |                            |    variable_name="weights"   |
    |                            |  )                           |
    |                            | ---------------------------> |
    |                            |                              |
    |                            |  {                           |
    |                            |    name: "weights",          |
    |                            |    type: "ndarray",          |
    |                            |    structure: {              |
    |                            |      shape: [128, 256],      |
    |                            |      dtype: "float32",       |
    |                            |      size: 32768,            |
    |                            |      memory_bytes: 131072    |
    |                            |    },                        |
    |                            |    statistics: {             |
    |                            |      min: -0.98,             |
    |                            |      max: 0.97,              |
    |                            |      mean: 0.002,            |
    |                            |      std: 0.45               |
    |                            |    },                        |
    |                            |    preview: {                |
    |                            |      sample: [0.1, -0.3, ...]|
    |                            |    },                        |
    |                            |    summary: "ndarray..."     |
    |                            |  }                           |
    |                            | <--------------------------- |
    |                            |                              |
    |  "weights is a 2D float32  |                              |
    |   array [128, 256] (128KB) |                              |
    |                            |                              |
    |   Stats: mean=0.002,       |                              |
    |          std=0.45,         |                              |
    |          range=[-0.98,0.97]|                              |
    |                            |                              |
    |   Sample: [0.1, -0.3, ...]"|                              |
    | <------------------------- |                              |
```

**Steps:**
1. Developer asks about NumPy array
2. AI calls `debug_inspect_variable` with variable name
3. polybugger-mcp detects ndarray type, returns shape, dtype, statistics
4. AI presents array summary with statistical context

### Flow 3: AI Inspects Large Dictionary

```
+---------------------------------------------------------------------------+
|                       DICTIONARY INSPECTION FLOW                          |
+---------------------------------------------------------------------------+

Developer                    AI Agent                     polybugger-mcp
    |                            |                              |
    |  "What's in config?"       |                              |
    | -------------------------> |                              |
    |                            |                              |
    |                            |  debug_inspect_variable(     |
    |                            |    variable_name="config"    |
    |                            |  )                           |
    |                            | ---------------------------> |
    |                            |                              |
    |                            |  {                           |
    |                            |    name: "config",           |
    |                            |    type: "dict",             |
    |                            |    structure: {              |
    |                            |      length: 45,             |
    |                            |      key_types: ["str"],     |
    |                            |      value_types: ["str",    |
    |                            |        "int", "list"]        |
    |                            |    },                        |
    |                            |    preview: {                |
    |                            |      keys: ["host", "port",  |
    |                            |        "database", ...],     |
    |                            |      sample: {               |
    |                            |        "host": "localhost",  |
    |                            |        "port": 5432,         |
    |                            |        "database": "mydb"    |
    |                            |      }                       |
    |                            |    },                        |
    |                            |    summary: "dict with 45    |
    |                            |              string keys"    |
    |                            |  }                           |
    |                            | <--------------------------- |
    |                            |                              |
    |  "config is a dict with    |                              |
    |   45 entries (all string   |                              |
    |   keys)                    |                              |
    |                            |                              |
    |   Sample entries:          |                              |
    |   - host: 'localhost'      |                              |
    |   - port: 5432             |                              |
    |   - database: 'mydb'"      |                              |
    | <------------------------- |                              |
```

### Flow 4: AI Inspects Unknown/Primitive Type (Fallback)

```
+---------------------------------------------------------------------------+
|                       FALLBACK INSPECTION FLOW                            |
+---------------------------------------------------------------------------+

Developer                    AI Agent                     polybugger-mcp
    |                            |                              |
    |  "What is my_object?"      |                              |
    | -------------------------> |                              |
    |                            |                              |
    |                            |  debug_inspect_variable(     |
    |                            |    variable_name="my_object" |
    |                            |  )                           |
    |                            | ---------------------------> |
    |                            |                              |
    |                            |  {                           |
    |                            |    name: "my_object",        |
    |                            |    type: "CustomClass",      |
    |                            |    detected_type: "unknown", |
    |                            |    basic_info: {             |
    |                            |      repr: "<CustomClass     |
    |                            |              at 0x7f...>",   |
    |                            |      type_module: "myapp",   |
    |                            |      attributes: ["name",    |
    |                            |        "value", "process"]   |
    |                            |    },                        |
    |                            |    variables_reference: 42,  |
    |                            |    hint: "Use debug_get_     |
    |                            |           variables to       |
    |                            |           explore attributes"|
    |                            |  }                           |
    |                            | <--------------------------- |
    |                            |                              |
    |  "my_object is a           |                              |
    |   CustomClass instance     |                              |
    |   with attributes: name,   |                              |
    |   value, process.          |                              |
    |                            |                              |
    |   Would you like me to     |                              |
    |   inspect its attributes?" |                              |
    | <------------------------- |                              |
```

---

## Edge Cases and Error Scenarios

### EC-1: Variable Not Found

**Scenario:** AI requests inspection of a variable that doesn't exist in current scope.

**Expected Behavior:**
```json
{
  "error": "Variable 'nonexistent' not found in current scope",
  "code": "VARIABLE_NOT_FOUND",
  "available_variables": ["df", "config", "result"]
}
```

**Rules:**
- Return helpful error with list of available variables
- Do not raise exception - return structured error
- Include variable names from current locals scope

### EC-2: Session Not Paused

**Scenario:** AI calls `debug_inspect_variable` when program is running (not at breakpoint).

**Expected Behavior:**
```json
{
  "error": "Cannot inspect variables while program is running",
  "code": "INVALID_STATE",
  "session_state": "running",
  "hint": "Set a breakpoint and wait for the program to pause"
}
```

**Rules:**
- Check session state before attempting inspection
- Provide clear guidance on required state

### EC-3: Very Large DataFrame (>1M rows)

**Scenario:** DataFrame has millions of rows, inspection could be slow/expensive.

**Expected Behavior:**
```json
{
  "name": "huge_df",
  "type": "DataFrame",
  "structure": {
    "shape": [10000000, 50],
    "columns": ["col1", "col2", "..."],
    "dtypes": {"col1": "int64", "...": "..."},
    "memory_bytes": 4000000000,
    "truncated": true
  },
  "preview": {
    "head": [{"col1": 1, "...": "..."}],
    "warning": "Large DataFrame - showing first 5 rows only"
  },
  "summary": "DataFrame with 10M rows x 50 columns, 3.7 GB (LARGE)",
  "warnings": ["DataFrame exceeds 1GB - inspection limited for performance"]
}
```

**Rules:**
- Never transfer entire large datasets
- Limit preview to max 5-10 rows regardless of `max_preview_rows`
- Include memory warning in summary
- Add `truncated: true` flag
- Add explicit warning about performance considerations

### EC-4: DataFrame with Complex Types (nested objects, etc.)

**Scenario:** DataFrame columns contain lists, dicts, or custom objects.

**Expected Behavior:**
```json
{
  "name": "complex_df",
  "type": "DataFrame",
  "structure": {
    "shape": [100, 4],
    "columns": ["id", "tags", "metadata", "embedding"],
    "dtypes": {
      "id": "int64",
      "tags": "object",
      "metadata": "object",
      "embedding": "object"
    },
    "complex_columns": ["tags", "metadata", "embedding"]
  },
  "preview": {
    "head": [
      {
        "id": 1,
        "tags": "[3 items]",
        "metadata": "{dict with 5 keys}",
        "embedding": "[ndarray 128]"
      }
    ],
    "note": "Complex columns show type summaries - use debug_evaluate for full values"
  }
}
```

**Rules:**
- Detect columns with non-primitive types
- Show type summary instead of full nested values
- Flag complex columns in structure metadata
- Suggest `debug_evaluate` for detailed inspection

### EC-5: NumPy Array with NaN/Inf Values

**Scenario:** Array contains NaN or Inf values that affect statistics.

**Expected Behavior:**
```json
{
  "name": "data",
  "type": "ndarray",
  "structure": {
    "shape": [1000],
    "dtype": "float64"
  },
  "statistics": {
    "min": -100.5,
    "max": 200.3,
    "mean": 45.2,
    "std": 30.1,
    "nan_count": 15,
    "inf_count": 2
  },
  "warnings": ["Array contains 15 NaN and 2 Inf values"]
}
```

**Rules:**
- Compute statistics ignoring NaN/Inf (use `np.nanmean`, etc.)
- Report NaN and Inf counts separately
- Include warning when special values present

### EC-6: pandas/NumPy Not Installed

**Scenario:** Debugged code imports pandas/numpy but evaluation fails because library introspection is unavailable.

**Expected Behavior:**
```json
{
  "name": "df",
  "type": "DataFrame",
  "detected_type": "pandas_unavailable",
  "basic_info": {
    "repr": "<pandas.core.frame.DataFrame>",
    "type_str": "pandas.core.frame.DataFrame"
  },
  "error": "pandas introspection failed - library may not be fully loaded",
  "fallback": true,
  "hint": "Try debug_evaluate('df.shape') directly"
}
```

**Rules:**
- Gracefully degrade when introspection expressions fail
- Return basic repr and type information
- Suggest manual `debug_evaluate` as fallback
- Set `fallback: true` flag

### EC-7: Empty DataFrame/Array

**Scenario:** DataFrame or array has zero rows/elements.

**Expected Behavior:**
```json
{
  "name": "empty_df",
  "type": "DataFrame",
  "structure": {
    "shape": [0, 5],
    "columns": ["id", "name", "value", "date", "status"],
    "dtypes": {"id": "int64", "name": "object", "...": "..."},
    "empty": true
  },
  "preview": {
    "head": [],
    "note": "DataFrame is empty (0 rows)"
  },
  "summary": "Empty DataFrame with 5 columns defined"
}
```

**Rules:**
- Handle empty structures without error
- Show column definitions even when no data
- Set `empty: true` flag
- Provide helpful summary noting empty state

### EC-8: pandas Series (not DataFrame)

**Scenario:** Variable is a pandas Series, not DataFrame.

**Expected Behavior:**
```json
{
  "name": "prices",
  "type": "Series",
  "structure": {
    "length": 1000,
    "dtype": "float64",
    "name": "price",
    "index_type": "RangeIndex"
  },
  "statistics": {
    "min": 9.99,
    "max": 999.99,
    "mean": 150.50,
    "median": 125.00,
    "null_count": 5
  },
  "preview": {
    "head": [9.99, 15.50, 22.00, 45.99, 50.00],
    "tail": [875.00, 899.99, 925.00, 950.00, 999.99]
  },
  "summary": "Series 'price' with 1000 float64 values"
}
```

**Rules:**
- Detect Series vs DataFrame
- Provide Series-specific metadata (single dtype, name, index)
- Include statistical summary appropriate for 1D data
- Show both head and tail preview

### EC-9: Nested List/Dict Structures

**Scenario:** Variable is a deeply nested list of dicts.

**Expected Behavior:**
```json
{
  "name": "records",
  "type": "list",
  "structure": {
    "length": 500,
    "element_types": ["dict"],
    "depth": 3,
    "uniform": true
  },
  "preview": {
    "sample": [
      {"id": 1, "data": {"value": 100, "tags": ["a", "b"]}},
      {"id": 2, "data": {"value": 200, "tags": ["c"]}}
    ],
    "truncated_at_depth": 3
  },
  "summary": "list of 500 dicts (3 levels deep, uniform structure)"
}
```

**Rules:**
- Detect nested structures and estimate depth
- Limit preview depth to prevent massive responses
- Note if structure appears uniform (consistent schema)
- Indicate where truncation occurred

### EC-10: Evaluation Timeout

**Scenario:** Introspection expression takes too long (e.g., huge dataset statistics).

**Expected Behavior:**
```json
{
  "name": "huge_array",
  "type": "ndarray",
  "structure": {
    "shape": [100000000],
    "dtype": "float64"
  },
  "partial": true,
  "computed": ["shape", "dtype"],
  "timed_out": ["statistics", "preview"],
  "warning": "Some inspections timed out - data may be too large",
  "hint": "Use debug_evaluate with specific expressions for large data"
}
```

**Rules:**
- Set reasonable timeout per introspection expression (e.g., 2 seconds)
- Return partial results when some expressions succeed
- Track which computations timed out
- Provide actionable guidance

---

## Success KPIs

### Efficiency Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Tool calls per data inspection | <2 (down from 5-10) | Track tool call patterns in debug sessions |
| Time to full data understanding | <3 seconds | End-to-end timing from request to response |
| Token reduction | >60% vs. multiple evaluate calls | Compare token counts for equivalent information |
| Cache hit rate for type detection | >80% after first call | Track type detection per session |

### Adoption Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| `debug_inspect_variable` usage | >30% of sessions within 2 months | Track tool usage in logs |
| Replaced `debug_evaluate` patterns | >50% of data introspection | Identify evaluate patterns replaced |
| AI agent integration | 3+ major AI assistants using feature | Partner feedback, usage analytics |

### Quality Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Type detection accuracy | >95% for supported types | Unit test coverage, error tracking |
| Graceful fallback rate | 100% (no crashes) | Exception monitoring |
| Response size for large data | <50KB always | Response size tracking |
| P95 response latency | <500ms | Performance monitoring |

### User Satisfaction Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Developer debugging speed | 2x faster for data issues | User survey, A/B comparison |
| AI agent accuracy | >90% correct data descriptions | Spot-check AI outputs |
| Feature satisfaction | >4.0/5.0 | User survey |
| Support tickets for data inspection | <2/month | Support ticket analysis |

---

## Acceptance Criteria

### Functional Requirements

#### Type Detection
- [ ] **AC-1:** `debug_inspect_variable` tool exists and accepts `session_id`, `variable_name`, optional `frame_id`, and optional `max_preview_rows` parameters
- [ ] **AC-2:** Detects `pandas.DataFrame` and returns shape, columns list, dtypes dict, and memory_bytes
- [ ] **AC-3:** Detects `pandas.Series` and returns length, dtype, name, and statistics
- [ ] **AC-4:** Detects `numpy.ndarray` and returns shape, dtype, and basic statistics (min, max, mean)
- [ ] **AC-5:** Detects `dict` and returns length, key sample (up to 20), and value sample (up to 5 items)
- [ ] **AC-6:** Detects `list` and returns length, element type summary, and sample values
- [ ] **AC-7:** Returns `detected_type: "unknown"` for unsupported types with basic repr and attribute list

#### Preview Data
- [ ] **AC-8:** DataFrame preview includes `head` rows (default 5, configurable via `max_preview_rows`)
- [ ] **AC-9:** NumPy array preview includes flattened sample values (first 10 elements)
- [ ] **AC-10:** Dict preview includes sample key-value pairs (first 5)
- [ ] **AC-11:** List preview includes sample values (first 10)
- [ ] **AC-12:** All previews respect `max_preview_rows` parameter

#### Summaries
- [ ] **AC-13:** Every response includes human-readable `summary` string
- [ ] **AC-14:** Summary includes type, dimensions/length, and memory estimate
- [ ] **AC-15:** Summary flags warnings (large size, NaN values, empty)

#### Safety & Performance
- [ ] **AC-16:** Response size never exceeds 100KB regardless of input data size
- [ ] **AC-17:** Individual introspection expressions timeout after 2 seconds
- [ ] **AC-18:** Large datasets (>1M elements) automatically limit preview
- [ ] **AC-19:** Memory-intensive statistics skipped for arrays >10M elements
- [ ] **AC-20:** Partial results returned when some expressions timeout

#### Error Handling
- [ ] **AC-21:** Returns structured error when variable not found (includes available variables)
- [ ] **AC-22:** Returns structured error when session not paused (includes session state)
- [ ] **AC-23:** Graceful fallback when introspection expressions fail
- [ ] **AC-24:** Never raises exceptions - always returns structured response

### Non-Functional Requirements

- [ ] **AC-25:** No new runtime dependencies (uses existing `debug_evaluate` mechanism)
- [ ] **AC-26:** Works with Python 3.10+ (project minimum)
- [ ] **AC-27:** P95 response latency <500ms for typical data structures
- [ ] **AC-28:** Unit tests cover all supported types with >90% coverage
- [ ] **AC-29:** Integration tests verify inspection with real pandas/NumPy (dev dependencies)
- [ ] **AC-30:** E2E test demonstrates full DataFrame inspection workflow

### Documentation Requirements

- [ ] **AC-31:** MCP tool docstring fully documents all parameters and return format
- [ ] **AC-32:** README updated with `debug_inspect_variable` usage example
- [ ] **AC-33:** Feature backlog entry updated to "Implemented" status

---

## Out of Scope

The following are explicitly **NOT** included in this feature:

### Data Modification
- No ability to modify DataFrame/array values through this tool
- No in-place transformations or filtering
- Rationale: Inspection tool should be read-only; modifications via `debug_evaluate`

### Full Dataset Transfer
- No option to return entire DataFrame contents
- No streaming or pagination for large data
- Rationale: Keep responses lightweight; use `debug_evaluate` for specific slices

### Visualization
- No histograms, plots, or graphical summaries
- No ASCII art data visualizations
- Rationale: Text-only responses; visualization is separate feature

### Custom Type Definitions
- No user-defined inspection patterns
- No plugin system for new types
- Rationale: Support common types first; extensibility in future version

### Statistical Analysis
- No advanced statistics (correlation, percentiles beyond basic)
- No null analysis beyond count
- No outlier detection
- Rationale: Keep inspection fast; detailed analysis via explicit evaluate calls

### Comparison Operations
- No diff between two DataFrames
- No change tracking across debug steps
- Rationale: Different feature (data diffing tool)

---

## Technical Notes

### Implementation Approach

#### Type Detection Strategy

Use debugpy's `evaluate` method to run detection expressions. Each type has a detection pattern that returns True/False:

```python
TYPE_DETECTORS = {
    "dataframe": "hasattr({var}, 'shape') and hasattr({var}, 'columns') and hasattr({var}, 'dtypes')",
    "series": "hasattr({var}, 'dtype') and hasattr({var}, 'index') and not hasattr({var}, 'columns')",
    "ndarray": "type({var}).__module__ == 'numpy' and hasattr({var}, 'shape') and hasattr({var}, 'dtype')",
    "dict": "isinstance({var}, dict)",
    "list": "isinstance({var}, list)",
}
```

#### Introspection Expressions

Each type has a set of expressions to gather metadata:

```python
DATAFRAME_EXPRESSIONS = {
    "shape": "{var}.shape",
    "columns": "list({var}.columns)",
    "dtypes": "{{str(k): str(v) for k, v in {var}.dtypes.items()}}",
    "memory_bytes": "int({var}.memory_usage(deep=True).sum())",
    "head": "{var}.head({n}).to_dict('records')",
}

NDARRAY_EXPRESSIONS = {
    "shape": "{var}.shape",
    "dtype": "str({var}.dtype)",
    "size": "{var}.size",
    "sample": "{var}.flatten()[:{n}].tolist()",
    "min": "float({var}.min())" if not "{var}.size > 10000000" else None,
    "max": "float({var}.max())" if not "{var}.size > 10000000" else None,
    "mean": "float({var}.mean())" if not "{var}.size > 10000000" else None,
}
```

#### Response Construction

Build response incrementally, catching individual expression failures:

```python
async def inspect_variable(self, var_name: str, frame_id: int | None, max_rows: int = 5):
    result = {"name": var_name}

    # Detect type
    detected_type = await self._detect_type(var_name, frame_id)
    result["type"] = detected_type

    # Get type-specific metadata
    expressions = TYPE_EXPRESSIONS.get(detected_type, {})
    structure = {}

    for key, expr in expressions.items():
        try:
            value = await self._evaluate_with_timeout(
                expr.format(var=var_name, n=max_rows),
                frame_id,
                timeout=2.0
            )
            structure[key] = value
        except TimeoutError:
            result.setdefault("timed_out", []).append(key)
        except Exception:
            pass  # Skip failed expressions

    result["structure"] = structure
    result["summary"] = self._build_summary(detected_type, structure)
    return result
```

### Files to Modify/Create

| File | Changes |
|------|---------|
| `src/polybugger_mcp/utils/data_inspector.py` | **New** - Type detection and introspection logic |
| `src/polybugger_mcp/core/session.py` | Add `inspect_variable()` method delegating to adapter |
| `src/polybugger_mcp/mcp_server.py` | Add `debug_inspect_variable` tool |
| `tests/unit/test_data_inspector.py` | **New** - Unit tests for type detection and expression building |
| `tests/e2e/test_data_inspection.py` | **New** - E2E tests with real pandas/numpy |
| `pyproject.toml` | Add pandas/numpy as dev dependencies for testing |

### Response Schema

```python
class InspectionResult(TypedDict):
    name: str
    type: str  # "DataFrame", "Series", "ndarray", "dict", "list", "unknown"
    detected_type: str  # Same as type, or "unknown" for fallback
    structure: dict[str, Any]  # Type-specific metadata
    preview: dict[str, Any]  # Sample data
    statistics: dict[str, float] | None  # For numeric types
    summary: str  # Human-readable summary
    warnings: list[str] | None  # Size warnings, NaN warnings, etc.
    error: str | None  # If inspection failed
    partial: bool | None  # True if some expressions timed out
    variables_reference: int | None  # For drilling down with debug_get_variables
```

### Performance Considerations

1. **Timeout per expression:** 2 seconds max to prevent hanging on large data
2. **Size limits:** Skip statistics for arrays >10M elements
3. **Response size:** Truncate preview data to stay under 100KB
4. **Caching:** Consider caching type detection per variable per stop

---

## Open Questions

1. **Q:** Should we add TUI formatting support (`format="tui"`) for this tool?
   - **Recommendation:** Yes, in follow-up PR. Build on US-TUI-001 formatter.

2. **Q:** Should statistics be optional via parameter?
   - **Recommendation:** Yes, add `include_statistics: bool = True` parameter for performance control.

3. **Q:** Should we support torch tensors?
   - **Recommendation:** Add in v2 based on user demand. Similar pattern to ndarray.

4. **Q:** How to handle multi-index DataFrames?
   - **Recommendation:** Include index type info in structure; full index inspection via evaluate.

---

## Appendix: Example Response Formats

### DataFrame Response

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
    "memory_bytes": 80000,
    "index_type": "RangeIndex"
  },
  "preview": {
    "head": [
      {"id": 1, "name": "Alice", "value": 100.5, "date": "2024-01-15", "status": "active"},
      {"id": 2, "name": "Bob", "value": 200.3, "date": "2024-01-16", "status": "pending"},
      {"id": 3, "name": "Charlie", "value": 150.0, "date": "2024-01-17", "status": "active"}
    ]
  },
  "summary": "DataFrame with 1000 rows x 5 columns, 78.1 KB",
  "variables_reference": 42
}
```

### NumPy Array Response

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
    "std": 0.453
  },
  "preview": {
    "sample": [0.123, -0.456, 0.789, -0.012, 0.345, -0.678, 0.901, -0.234, 0.567, -0.890]
  },
  "summary": "ndarray float32 [128, 256], 128 KB, mean=0.002, std=0.453"
}
```

### Large Dictionary Response

```json
{
  "name": "config",
  "type": "dict",
  "detected_type": "dict",
  "structure": {
    "length": 45,
    "key_types": ["str"],
    "value_types": ["str", "int", "bool", "list", "dict"]
  },
  "preview": {
    "keys": [
      "host", "port", "database", "username", "password",
      "pool_size", "timeout", "retry_count", "ssl_enabled", "ssl_cert",
      "log_level", "log_format", "cache_ttl", "cache_size", "features"
    ],
    "sample": {
      "host": "localhost",
      "port": 5432,
      "database": "production",
      "pool_size": 10,
      "ssl_enabled": true
    }
  },
  "summary": "dict with 45 string keys (mixed value types)"
}
```

### Error Response

```json
{
  "error": "Variable 'data' not found in current scope",
  "code": "VARIABLE_NOT_FOUND",
  "available_variables": ["df", "config", "result", "temp"],
  "hint": "Check variable name spelling or verify the variable is in scope at current breakpoint"
}
```

---

*Last updated: 2026-01-15*
