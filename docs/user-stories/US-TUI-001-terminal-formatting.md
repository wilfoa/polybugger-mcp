# User Story: TUI/Terminal Formatting for Rich Output

**Story ID:** US-TUI-001
**Epic:** Developer Experience Enhancement
**Priority:** P2 - High Value
**Story Points:** 8
**Created:** 2026-01-14
**Status:** Ready for Development

---

## Problem Statement

### Current State

pybugger-mcp currently returns all debugging information as raw JSON responses. When AI agents (Claude, GPT, Copilot) present this information to developers in terminal/CLI interfaces, they must:

1. Parse nested JSON structures manually
2. Generate their own text formatting for each response type
3. Recreate similar formatting logic repeatedly across conversations
4. Often produce inconsistent or suboptimal visual presentations

### Pain Points

| Stakeholder | Pain Point | Impact |
|-------------|------------|--------|
| AI Agents | Must implement formatting logic for every debug response | Increased token usage, slower responses |
| Developers | Receive inconsistent debug output presentation | Reduced readability, harder to scan information |
| AI Agents | Cannot leverage terminal graphics (boxes, trees) | Missing visual hierarchy, harder to parse complex data |
| Developers | Large stack traces become walls of text | Critical information gets buried |

### Example: Current vs. Desired Output

**Current JSON Output:**
```json
{
  "frames": [
    {"id": 1, "name": "process_data", "file": "/app/processor.py", "line": 45},
    {"id": 2, "name": "validate_input", "file": "/app/validator.py", "line": 23},
    {"id": 3, "name": "main", "file": "/app/main.py", "line": 12}
  ],
  "total": 3
}
```

**Desired TUI Output:**
```
Stack Trace (3 frames)
=======================

 #  Function          File                  Line
------------------------------------------------------
 0  process_data      /app/processor.py       45  <-- current
 1  validate_input    /app/validator.py       23
 2  main              /app/main.py            12
```

### Business Case

- **Reduced Token Usage:** Pre-formatted output eliminates AI agents needing to generate formatting (est. 30-50% fewer tokens for display)
- **Faster Time-to-Insight:** Developers can scan formatted tables/trees faster than parsing JSON
- **Consistency:** All AI clients get identical, well-designed formatting
- **Differentiation:** Positions pybugger-mcp as the most developer-friendly debugging MCP server

---

## User Personas

### Primary: AI Coding Assistants

**Representative Users:** Claude (Anthropic), GPT-4 (OpenAI), Copilot (GitHub), Cline, Cursor AI

**Characteristics:**
- Consume pybugger-mcp tools via MCP protocol
- Present debugging information to human developers
- Operate in terminal/CLI environments (VS Code terminal, macOS Terminal, Windows Terminal)
- Need to minimize token usage while maximizing information clarity
- Cannot render rich HTML or graphics - limited to monospace text

**Goals:**
- Receive pre-formatted output ready for display
- Maintain structured data access when needed (JSON still available)
- Present professional, readable debug information to users

**Frustrations:**
- Spending tokens formatting JSON into readable text
- Inconsistent output quality depending on prompt engineering
- Cannot create visual elements like box drawings or aligned tables

### Secondary: Developers in Terminal

**Representative Users:** Backend developers, DevOps engineers, CLI-first developers

**Characteristics:**
- View AI-presented debug output in terminal windows
- Familiar with CLI tools like `top`, `htop`, `git log --graph`
- Expect information hierarchy and visual organization
- May have varying terminal widths (80-200+ columns)
- Some use non-standard terminals or SSH sessions

**Goals:**
- Quickly identify current execution location
- Scan variable names and values efficiently
- Understand call hierarchy at a glance
- Copy/paste relevant information easily

**Frustrations:**
- Dense JSON output requires mental parsing
- Important details hidden in data structures
- Inconsistent presentation across AI interactions

---

## User Flows

### Flow 1: AI Requests Formatted Stack Trace (Happy Path)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FORMATTED STACK TRACE FLOW                          │
└─────────────────────────────────────────────────────────────────────────────┘

Developer                    AI Agent                     pybugger-mcp
    │                            │                              │
    │  "Show me the call stack"  │                              │
    │ ─────────────────────────> │                              │
    │                            │                              │
    │                            │  debug_get_stacktrace(       │
    │                            │    session_id="abc123",      │
    │                            │    format="tui"              │
    │                            │  )                           │
    │                            │ ──────────────────────────> │
    │                            │                              │
    │                            │  {                           │
    │                            │    "formatted": "...",       │
    │                            │    "frames": [...],          │
    │                            │    "total": 5                │
    │                            │  }                           │
    │                            │ <────────────────────────── │
    │                            │                              │
    │  ┌─────────────────────┐   │                              │
    │  │ Stack Trace         │   │                              │
    │  │ ==================  │   │                              │
    │  │ #0 calculate  :45   │   │                              │
    │  │ #1 process    :23   │   │                              │
    │  │ #2 main       :12   │   │                              │
    │  └─────────────────────┘   │                              │
    │ <───────────────────────── │                              │
    │                            │                              │
```

**Steps:**
1. Developer asks AI to show the call stack
2. AI calls `debug_get_stacktrace` with `format="tui"` parameter
3. pybugger-mcp returns response with `formatted` field containing ASCII table
4. AI displays the `formatted` string directly to developer
5. Developer sees clean, aligned stack trace

### Flow 2: AI Requests Variables Table

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FORMATTED VARIABLES FLOW                            │
└─────────────────────────────────────────────────────────────────────────────┘

Developer                    AI Agent                     pybugger-mcp
    │                            │                              │
    │  "What are the local       │                              │
    │   variables?"              │                              │
    │ ─────────────────────────> │                              │
    │                            │                              │
    │                            │  1. debug_get_scopes(...)    │
    │                            │  2. debug_get_variables(     │
    │                            │       ref=locals_ref,        │
    │                            │       format="tui"           │
    │                            │     )                        │
    │                            │ ──────────────────────────> │
    │                            │                              │
    │                            │  {                           │
    │                            │    "formatted": "...",       │
    │                            │    "variables": [...]        │
    │                            │  }                           │
    │                            │ <────────────────────────── │
    │                            │                              │
    │  ┌───────────────────────────────────────────┐            │
    │  │ Local Variables                           │            │
    │  │ ========================================= │            │
    │  │ Name          Type        Value          │            │
    │  │ ----------------------------------------- │            │
    │  │ user_id       int         42             │            │
    │  │ username      str         "alice"        │            │
    │  │ settings      dict        {3 items}      │            │
    │  │ is_active     bool        True           │            │
    │  └───────────────────────────────────────────┘            │
    │ <───────────────────────────────────────────────────────  │
```

**Steps:**
1. Developer asks about local variables
2. AI calls `debug_get_scopes` to get scope references (format doesn't apply here)
3. AI calls `debug_get_variables` with `format="tui"`
4. pybugger-mcp returns formatted table with type alignment
5. Developer sees organized variable table with truncated complex values

### Flow 3: AI Requests Call Hierarchy Visualization

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       CALL HIERARCHY TREE FLOW                              │
└─────────────────────────────────────────────────────────────────────────────┘

Developer                    AI Agent                     pybugger-mcp
    │                            │                              │
    │  "Show me how we got here" │                              │
    │ ─────────────────────────> │                              │
    │                            │                              │
    │                            │  debug_get_stacktrace(       │
    │                            │    session_id="abc123",      │
    │                            │    format="tui",             │
    │                            │    style="tree"              │
    │                            │  )                           │
    │                            │ ──────────────────────────> │
    │                            │                              │
    │                            │  { "formatted": "..." }      │
    │                            │ <────────────────────────── │
    │                            │                              │
    │  Call Hierarchy                                           │
    │  ===============                                          │
    │                                                           │
    │  main() ─────────────────────────── main.py:12            │
    │  └── process_request() ──────────── handlers.py:45       │
    │      └── validate_data() ────────── validator.py:23      │
    │          └── check_field() ──────── validator.py:67 ←    │
    │                                                           │
    │ <───────────────────────────────────────────────────────  │
```

**Steps:**
1. Developer asks for call hierarchy context
2. AI requests stack trace with `format="tui"` and `style="tree"`
3. pybugger-mcp returns tree-structured visualization
4. Developer sees visual call flow with current position marked

---

## Edge Cases

### EC-1: Very Deep Stack Traces (>20 frames)

**Scenario:** Recursive function or deep library call creates 50+ stack frames

**Behavior:**
```
Stack Trace (47 frames, showing top 20)
=======================================

 #  Function              File                      Line
----------------------------------------------------------
 0  recursive_process     /app/core.py                89  <-- current
 1  recursive_process     /app/core.py                87
 2  recursive_process     /app/core.py                87
    ... (24 frames hidden) ...
 46 main                  /app/main.py                12

Hint: Use max_frames parameter to see more frames
```

**Rules:**
- Default to showing top 20 frames
- Show count of hidden frames
- Always show bottom frame (entry point)
- Include hint about `max_frames` parameter

### EC-2: Very Long Variable Names or Values

**Scenario:** Variable name is 50+ characters, or value is a large string/structure

**Behavior:**
```
Local Variables
================

Name                          Type        Value
------------------------------------------------------------------
user_authentication_token...  str         "eyJhbGciOiJIUzI1NiIsInR..."
cfg                           dict        {12 items}
very_long_variable_name_f...  list        [1, 2, 3, ... +47 items]
```

**Rules:**
- Truncate names > 28 characters with "..."
- Truncate string values > 30 characters with "..."
- Show collection summary for large collections: `{N items}`, `[... +N items]`
- Preserve enough characters to be identifiable
- Full values always available in JSON `variables` array

### EC-3: Unicode/Special Characters in Values

**Scenario:** Variable contains emoji, non-Latin scripts, or control characters

**Behavior:**
```
Local Variables
================

Name        Type    Value
-----------------------------------
greeting    str     "Hello"
emoji_test  str     "<unicode: 4 chars>"
japanese    str     "<unicode: 6 chars>"
binary_dat  bytes   <binary: 128 bytes>
```

**Rules:**
- ASCII-safe rendering by default
- Replace non-ASCII strings with `<unicode: N chars>`
- Replace binary data with `<binary: N bytes>`
- Escape control characters
- Original values preserved in JSON response

### EC-4: Empty Results

**Scenario:** No stack frames, no variables in scope, empty watch list

**Empty Stack Trace:**
```
Stack Trace
===========

(No frames available - program may not be paused)
```

**Empty Variables:**
```
Local Variables
===============

(No variables in this scope)
```

**Empty Scopes:**
```
Scopes
======

(No scopes available for this frame)
```

**Rules:**
- Always show the header/title
- Provide contextual hint about why empty
- Never return empty `formatted` string

### EC-5: Non-Standard Terminal Widths

**Scenario:** Terminal is 60 chars wide (narrow) or 200 chars wide

**Behavior:**
- Design for 80-character baseline
- Graceful degradation at 60 chars (tighter truncation)
- Do not expand beyond 120 chars (avoid horizontal scroll)
- Optional `width` parameter for explicit control (future)

**Narrow Terminal (60 chars):**
```
Stack Trace (3 frames)
========================

#  Function       File              Ln
-----------------------------------------
0  process_data   .../processor.py  45
1  validate       .../validator.py  23
2  main           .../main.py       12
```

**Rules:**
- Abbreviate column headers
- Shorten file paths (show `...` prefix)
- Reduce column widths proportionally
- Maintain readability over completeness

---

## Success KPIs

### Adoption Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| TUI format adoption rate | >50% of inspection calls within 3 months | Track `format` parameter usage in logs |
| AI agent preference | >70% switch to TUI after trying | A/B comparison of repeat users |
| Time-to-feature-use | <1 week after discovery | Track first TUI call per session |

### Quality Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Rendering issues reported | 0 critical, <5 minor | GitHub issues tagged `tui-formatting` |
| Character encoding issues | 0 reported | GitHub issues |
| Terminal compatibility | Works in 95% of reported terminals | Compatibility testing matrix |

### User Satisfaction Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Readability rating | >4.2/5.0 | User survey |
| "Would recommend" (NPS proxy) | >60 NPS | User survey |
| Support tickets for output formatting | <2/month | Support ticket analysis |

### Efficiency Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| AI token reduction | >30% for formatted responses | Compare token counts JSON vs TUI |
| Developer scan time | <3 seconds to find key info | Usability testing |

---

## Acceptance Criteria

### Functional Requirements

- [ ] **AC-1:** `debug_get_stacktrace` accepts `format` parameter with values `"json"` (default) and `"tui"`
- [ ] **AC-2:** `debug_get_variables` accepts `format` parameter with values `"json"` (default) and `"tui"`
- [ ] **AC-3:** `debug_get_scopes` accepts `format` parameter with values `"json"` (default) and `"tui"`
- [ ] **AC-4:** When `format="tui"`, response includes `formatted` field with ASCII-rendered output
- [ ] **AC-5:** When `format="tui"`, response still includes original structured data fields
- [ ] **AC-6:** Default `format` is `"json"` - no breaking changes to existing behavior
- [ ] **AC-7:** Stack trace TUI displays: frame number, function name, file path, line number
- [ ] **AC-8:** Variables TUI displays: variable name, type, value (truncated if needed)
- [ ] **AC-9:** Values longer than 30 characters are truncated with "..."
- [ ] **AC-10:** Names longer than 28 characters are truncated with "..."
- [ ] **AC-11:** Output fits within 80 characters width by default
- [ ] **AC-12:** Output fits within 120 characters width maximum
- [ ] **AC-13:** Empty results show appropriate placeholder message
- [ ] **AC-14:** Deep stacks (>20 frames) show summary with hidden frame count

### Non-Functional Requirements

- [ ] **AC-15:** TUI formatting adds <10ms latency to response time
- [ ] **AC-16:** No external dependencies added for formatting (pure Python)
- [ ] **AC-17:** Works with Python 3.10+ (project minimum)
- [ ] **AC-18:** Unit tests cover all formatters with >90% coverage
- [ ] **AC-19:** Integration tests verify TUI output in MCP tool responses

### Documentation Requirements

- [ ] **AC-20:** README updated with `format` parameter documentation
- [ ] **AC-21:** Example TUI outputs shown in documentation
- [ ] **AC-22:** MCP tool docstrings updated to document `format` parameter

---

## Out of Scope

The following are explicitly **NOT** included in this feature:

### Colors/ANSI Codes
- No color output (keep monochrome for maximum compatibility)
- No bold/underline/italic text styling
- Rationale: Many terminals, SSH sessions, and log viewers don't support ANSI

### Interactive TUI
- No cursor movement or screen manipulation
- No real-time updating displays
- No keyboard input handling
- Rationale: MCP tools return static responses; interactivity requires different architecture

### Custom Themes
- No user-configurable formatting styles
- No custom box-drawing character sets
- No configurable column widths
- Rationale: Keep initial implementation simple; can add in v2 based on demand

### Rich/Complex Graphics
- No syntax highlighting for code
- No sparklines or mini-charts
- No image rendering (e.g., Sixel)
- Rationale: Complexity vs. value tradeoff; focus on tables and trees

### HTML/Markdown Output
- No `format="html"` or `format="markdown"` option
- Rationale: TUI format targets terminal display; other formats are different features

---

## Technical Notes

### Suggested Implementation Approach

1. **Create Formatter Module:** `src/pybugger_mcp/formatters/`
   - `tui.py` - TUI formatting functions
   - `__init__.py` - Format dispatcher

2. **Formatter Functions:**
   ```python
   def format_stacktrace_tui(frames: list[StackFrame], total: int) -> str
   def format_variables_tui(variables: list[Variable]) -> str
   def format_scopes_tui(scopes: list[Scope]) -> str
   ```

3. **Integration Points:**
   - Add `format: Literal["json", "tui"] = "json"` parameter to relevant MCP tools
   - Call formatter when `format="tui"`
   - Include `formatted` key in response dict

### Box Drawing Characters (Reference)

Use standard ASCII for maximum compatibility:
```
Horizontal: -
Vertical:   |
Corners:    +
Headers:    =
```

Avoid Unicode box drawing (┌ ┐ └ ┘ │ ─) unless we add a `style` parameter later.

### Response Structure

```python
# format="json" (default, unchanged)
{
    "frames": [...],
    "total": 5
}

# format="tui" (new)
{
    "formatted": "Stack Trace (5 frames)\n...",
    "frames": [...],
    "total": 5
}
```

---

## Open Questions

1. **Q:** Should we add a `width` parameter for explicit terminal width control?
   - **Recommendation:** Defer to v2, use 80-char default for now

2. **Q:** Should `debug_evaluate` also support TUI formatting?
   - **Recommendation:** Yes, but low priority - single values don't benefit as much

3. **Q:** Should we add `format="tui"` to `debug_poll_events` or `debug_get_output`?
   - **Recommendation:** Consider for events (nice for stopped event summary), skip for output (already text)

---

## Appendix: Example TUI Outputs

### Stack Trace (Table Style)
```
Stack Trace (5 frames)
=======================

 #  Function          File                        Line
--------------------------------------------------------
 0  calculate_tax     /app/finance/calc.py          67  <--
 1  process_invoice   /app/billing/invoice.py       45
 2  handle_request    /app/api/handlers.py          23
 3  dispatch          /app/api/router.py           102
 4  main              /app/main.py                  15
```

### Stack Trace (Tree Style)
```
Call Hierarchy
===============

main() ─────────────────────────────── /app/main.py:15
└── dispatch() ─────────────────────── /app/api/router.py:102
    └── handle_request() ───────────── /app/api/handlers.py:23
        └── process_invoice() ──────── /app/billing/invoice.py:45
            └── calculate_tax() ────── /app/finance/calc.py:67 <-- current
```

### Variables Table
```
Local Variables (Locals scope)
===============================

Name              Type          Value
------------------------------------------------
invoice_id        int           12345
customer_name     str           "Acme Corporation"
line_items        list          [5 items]
subtotal          Decimal       "1234.56"
tax_rate          float         0.0825
config            dict          {8 items}
is_taxable        bool          True
```

### Scopes List
```
Available Scopes
=================

  #  Scope Name    Variables    Expensive
-------------------------------------------
  1  Locals              7      No
  2  Globals           142      Yes
  3  Builtins          152      Yes

Use debug_get_variables with scope's variables_reference to inspect.
```

### Empty State Examples
```
Stack Trace
===========

(No frames available - program may not be paused)

---

Local Variables
===============

(No variables in this scope)

---

Available Scopes
=================

(No scopes available - ensure program is paused at a breakpoint)
```
