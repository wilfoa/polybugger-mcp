# polybugger-mcp

[![PyPI version](https://img.shields.io/pypi/v/polybugger-mcp)](https://pypi.org/project/polybugger-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/wilfoa/polybugger-mcp/actions/workflows/tests.yml/badge.svg)](https://github.com/wilfoa/polybugger-mcp/actions/workflows/tests.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A lightweight, pure-Python MCP server for interactive debugging. Uses debugpy (VS Code's debugger) under the hood for reliable, battle-tested debugging.

[![Install in Cursor](https://img.shields.io/badge/Cursor-Install%20MCP-blue?style=for-the-badge&logo=cursor)](https://cursor.com/install-mcp?name=polybugger&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJwb2x5YnVnZ2VyLW1jcCJdfQ==)
[![Install in VS Code](https://img.shields.io/badge/VS_Code-Install%20Server-0098FF?style=for-the-badge&logo=visualstudiocode)](https://insiders.vscode.dev/redirect?url=vscode%3Amcp%2Finstall%3F%7B%22name%22%3A%22polybugger%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22polybugger-mcp%22%5D%7D)

## Demo

![polybugger-mcp demo](docs/demo.gif)

## Why polybugger-mcp?

| Feature | polybugger-mcp | Other MCP debuggers |
|---------|--------------|---------------------|
| **Session Recovery** | Resume debugging after server restart | Not available |
| **Watch Expressions** | Track values across debug steps | Planned for 2026 |
| **Pure Python** | Single `pip install`, no Node.js | Requires Node.js runtime |
| **HTTP API** | Use independently of MCP | MCP-only |
| **Lightweight** | ~50KB, minimal dependencies | ~3MB+ bundled |

## Key Features

- **Session Recovery** - Persist debug state and resume after server restart
- **Watch Expressions** - Define expressions to track across every debug step
- **Smart Data Inspection** - Intelligent preview of DataFrames, NumPy arrays, dicts, and lists
- **Call Hierarchy** - Visualize the complete call chain with source context
- **Full Interactive Debugging** - Breakpoints, stepping, pause/continue
- **Variable Inspection** - View locals, globals, evaluate arbitrary expressions
- **Rich TUI Output** - ASCII box-drawn tables and diagrams for better visualization
- **Pure Python** - No Node.js required, just `pip install`
- **Dual Interface** - Use via MCP or standalone HTTP API
- **Multi-Client Support** - Cursor, VS Code, Claude Desktop, and more

## Installation

### Quick Install (no clone required)

**Using uvx (recommended):**
```bash
uvx polybugger-mcp
```

**Using pipx:**
```bash
pipx run polybugger-mcp
```

**Using pip:**
```bash
pip install polybugger-mcp
polybugger-mcp
```

### MCP Client Configuration

Configure your MCP client to use one of these commands:

<details>
<summary><b>Cursor</b></summary>

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "python-debugger": {
      "command": "uvx",
      "args": ["polybugger-mcp"]
    }
  }
}
```

<details>
<summary>Alternative: using pip install</summary>

```json
{
  "mcpServers": {
    "python-debugger": {
      "command": "python",
      "args": ["-m", "polybugger_mcp.mcp_server"]
    }
  }
}
```
</details>
</details>

<details>
<summary><b>VS Code</b></summary>

Use the VS Code CLI:

```bash
code --add-mcp '{"name":"python-debugger","command":"uvx","args":["polybugger-mcp"]}'
```

Or add to your MCP settings manually.
</details>

<details>
<summary><b>Claude Code</b></summary>

```bash
claude mcp add python-debugger -- uvx polybugger-mcp
```
</details>

<details>
<summary><b>Claude Desktop</b></summary>

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "python-debugger": {
      "command": "uvx",
      "args": ["polybugger-mcp"]
    }
  }
}
```
</details>

<details>
<summary><b>OpenCode</b></summary>

Add to `~/.config/opencode/opencode.json`:

```json
{
  "mcp": {
    "python-debugger": {
      "type": "local",
      "command": ["uvx", "polybugger-mcp"],
      "enabled": true
    }
  }
}
```
</details>

<details>
<summary><b>Windsurf</b></summary>

Add to your Windsurf MCP config:

```json
{
  "mcpServers": {
    "python-debugger": {
      "command": "uvx",
      "args": ["polybugger-mcp"]
    }
  }
}
```
</details>

<details>
<summary><b>Cline</b></summary>

Add to your `cline_mcp_settings.json`:

```json
{
  "mcpServers": {
    "python-debugger": {
      "command": "uvx",
      "args": ["polybugger-mcp"],
      "disabled": false
    }
  }
}
```
</details>

<details>
<summary><b>Goose</b></summary>

Go to Settings > Extensions > Add custom extension:
- Type: STDIO
- Command: `uvx polybugger-mcp`
</details>

<details>
<summary><b>Docker</b></summary>

```bash
docker run -i --rm ghcr.io/wilfoa/polybugger-mcp
```

Or in your MCP config:

```json
{
  "mcpServers": {
    "python-debugger": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "ghcr.io/wilfoa/polybugger-mcp"]
    }
  }
}
```
</details>

## Available Tools (23 tools)

### Session Management
| Tool | Description |
|------|-------------|
| `debug_create_session` | Create a new debug session for a project |
| `debug_list_sessions` | List all active debug sessions |
| `debug_get_session` | Get detailed session information |
| `debug_terminate_session` | End a debug session and clean up |

### Breakpoints
| Tool | Description |
|------|-------------|
| `debug_set_breakpoints` | Set breakpoints in source files (with optional conditions) |
| `debug_get_breakpoints` | List all breakpoints for a session |
| `debug_clear_breakpoints` | Remove breakpoints from files |

### Execution Control
| Tool | Description |
|------|-------------|
| `debug_launch` | Launch a Python program for debugging |
| `debug_continue` | Continue execution until next breakpoint |
| `debug_step` | Step execution: `mode="over"` (next line), `"into"` (enter function), `"out"` (exit function) |
| `debug_pause` | Pause a running program |

### Inspection
| Tool | Description |
|------|-------------|
| `debug_get_stacktrace` | Get the current call stack (supports TUI format) |
| `debug_get_scopes` | Get variable scopes (locals, globals) |
| `debug_get_variables` | Get variables in a scope (supports TUI format) |
| `debug_evaluate` | Evaluate a Python expression |
| `debug_inspect_variable` | **Smart inspection** of DataFrames, arrays, dicts with metadata |
| `debug_get_call_chain` | **Call hierarchy** with source context for each frame |

### Watch Expressions
| Tool | Description |
|------|-------------|
| `debug_watch` | Manage watches: `action="add"`, `"remove"`, or `"list"` |
| `debug_evaluate_watches` | Evaluate all watch expressions |

### Events & Output
| Tool | Description |
|------|-------------|
| `debug_poll_events` | Poll for debug events (stopped, terminated, etc.) |
| `debug_get_output` | Get program stdout/stderr |

### Recovery
| Tool | Description |
|------|-------------|
| `debug_list_recoverable` | List sessions that can be recovered |
| `debug_recover_session` | Recover a session from previous server run |

## Quick Start

1. **Install the package:**
   ```bash
   pip install polybugger-mcp
   ```

2. **Configure your MCP client** (see Installation above)

3. **Start debugging:** Ask your AI assistant:
   > "Debug my script.py - set a breakpoint on line 15 and show me the variables when it stops"

## Example Workflows

### Basic Debugging
```
You: Debug tests/test_example.py - I want to see why the calculate function returns wrong results

AI: I'll create a debug session and set breakpoints in the calculate function.
    [Creates session, sets breakpoints, launches program]

    The program stopped at line 23. Here are the local variables:
    - x = 10
    - y = 5
    - result = 50  # This should be 15!

    I see the issue - you're using multiplication instead of addition on line 24.
```

### Data Science Debugging
```
You: Debug my data pipeline and inspect the DataFrame at line 45

AI: [Sets breakpoint, launches program]

    The DataFrame `df` has 1000 rows x 5 columns (78.1 KB):

    ┌────────────┬────────────────┬────────┐
    │ Name       │ Type           │ Nulls  │
    ├────────────┼────────────────┼────────┤
    │ id         │ int64          │ -      │
    │ name       │ object         │ 5      │
    │ value      │ float64        │ 12     │
    └────────────┴────────────────┴────────┘

    I found 17 null values. The `value` column has NaN entries that may cause issues.
```

### Call Hierarchy Visualization
```
You: Show me how we got to this breakpoint

AI: [Uses debug_get_call_chain with format="tui"]

    CALL CHAIN (4 frames)
    ════════════════════════════════════════════════════════════

    main (app.py:50)
    │ >> 50 │     result = process_order(order)
    │
    └─▶ process_order (orders.py:76)
        │ >> 76 │     pricing = apply_pricing(items, tier)
        │
        └─▶ apply_pricing (pricing.py:58)
            │ >> 58 │     discount = calculate_discount(subtotal)
            │
            └─▶ calculate_discount (pricing.py:23)  ◀── YOU ARE HERE
                │ >> 23 │     return base * rate
```

## Configuration

Environment variables (prefix with `PYBUGGER_MCP_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `127.0.0.1` | Server bind address |
| `PORT` | `5679` | Server port (for HTTP mode) |
| `MAX_SESSIONS` | `10` | Maximum concurrent debug sessions |
| `SESSION_TIMEOUT_SECONDS` | `3600` | Session idle timeout (1 hour) |
| `DATA_DIR` | `~/.polybugger-mcp` | Data directory for persistence |
| `LOG_LEVEL` | `INFO` | Logging level |

## Development

```bash
# Clone and setup
git clone https://github.com/wilfoa/polybugger-mcp.git
cd polybugger-mcp
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
make test

# Run linter
make lint

# Run type checker
make typecheck
```

## Architecture

```
AI Agent  <-->  MCP Server  <-->  debugpy (DAP)  <-->  Python Process
```

The MCP server translates tool calls to Debug Adapter Protocol (DAP) messages, enabling full debugging capabilities through natural language.

## Requirements

- Python 3.10 or higher
- Works on macOS, Linux, and Windows

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.
