# Multi-Language Debug Support Architecture

## Overview

This document outlines the architecture changes needed to support debugging multiple languages (Python, Node.js, Go, Rust, etc.) using the Debug Adapter Protocol (DAP).

## Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     MCP Tools Layer                         │
│            (debug_* tools - AI interface)                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Session Manager                          │
│              (state, recovery, lifecycle)                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   DebugpyAdapter                            │
│                 (Python-specific)                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     DAPClient                               │
│              (protocol-generic ✓)                           │
└─────────────────────────────────────────────────────────────┘
```

## Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     MCP Tools Layer                         │
│            (debug_* tools - AI interface)                   │
│         + language parameter on create_session              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Session Manager                          │
│              (state, recovery, lifecycle)                   │
│            + AdapterFactory for language selection          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   DebugAdapter (ABC)                        │
│              (abstract interface)                           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │  Debugpy    │ │    Node     │ │   Delve     │  ...      │
│  │  Adapter    │ │   Adapter   │ │  Adapter    │           │
│  │  (Python)   │ │ (JS/TS)     │ │   (Go)      │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     DAPClient                               │
│              (protocol-generic ✓)                           │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Plan

### Phase 1: Abstract Base Class

Create `adapters/base.py` with the `DebugAdapter` ABC.

### Phase 2: Refactor DebugpyAdapter

Make `DebugpyAdapter` inherit from `DebugAdapter`.

### Phase 3: Adapter Factory

Create factory for language-based adapter selection.

### Phase 4: New Language Adapters

Add adapters for Node.js, Go, etc.

## File Structure

```
src/polybugger_mcp/
  adapters/
    __init__.py
    base.py              # NEW: DebugAdapter ABC
    factory.py           # NEW: AdapterFactory
    dap_client.py        # Existing (no changes)
    debugpy_adapter.py   # Refactor to inherit from base
    node_adapter.py      # NEW: Node.js/vscode-js-debug
    delve_adapter.py     # NEW: Go/delve
    lldb_adapter.py      # NEW: C/C++/Rust via LLDB
```

## Supported Debug Adapters by Language

| Language   | Debug Adapter          | DAP Server Command                    |
|------------|------------------------|---------------------------------------|
| Python     | debugpy                | `python -m debugpy --listen`          |
| JavaScript | vscode-js-debug        | `js-debug-adapter`                    |
| TypeScript | vscode-js-debug        | `js-debug-adapter`                    |
| Go         | delve                  | `dlv dap`                             |
| Rust       | CodeLLDB / lldb-vscode | `lldb-vscode` or `codelldb`           |
| C/C++      | CodeLLDB / cpptools    | `lldb-vscode` or `cppvsdbg`           |
| Java       | java-debug             | `java -jar java-debug-adapter.jar`    |
| Ruby       | debug                  | `rdbg --open`                         |
| PHP        | vscode-php-debug       | `php-debug-adapter`                   |

## API Changes

### debug_create_session

```python
# Before
async def debug_create_session(
    project_root: str,
    name: str | None = None,
) -> dict[str, Any]:

# After
async def debug_create_session(
    project_root: str,
    name: str | None = None,
    language: str = "python",  # NEW: "python", "javascript", "go", etc.
) -> dict[str, Any]:
```

### debug_launch

```python
# Before (Python-specific)
async def debug_launch(
    session_id: str,
    program: str | None = None,
    module: str | None = None,  # Python-specific
    args: list[str] | None = None,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:

# After (language-aware)
async def debug_launch(
    session_id: str,
    program: str | None = None,
    args: list[str] | None = None,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    # Language-specific options passed through
    **kwargs,
) -> dict[str, Any]:
```
