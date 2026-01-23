# polybugger-mcp

[![PyPI version](https://img.shields.io/pypi/v/polybugger-mcp)](https://pypi.org/project/polybugger-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/wilfoa/polybugger-mcp/actions/workflows/tests.yml/badge.svg)](https://github.com/wilfoa/polybugger-mcp/actions/workflows/tests.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**Multi-language MCP debugger** for AI agents. Debug Python, JavaScript/TypeScript, Go, and Rust with a single tool.

[![Install in Cursor](https://img.shields.io/badge/Cursor-Install%20MCP-blue?style=for-the-badge&logo=cursor)](https://cursor.com/install-mcp?name=polybugger&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJwb2x5YnVnZ2VyLW1jcCJdfQ==)
[![Install in VS Code](https://img.shields.io/badge/VS_Code-Install%20Server-0098FF?style=for-the-badge&logo=visualstudiocode)](https://insiders.vscode.dev/redirect?url=vscode%3Amcp%2Finstall%3F%7B%22name%22%3A%22polybugger%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22polybugger-mcp%22%5D%7D)

## Supported Languages

| Language | Debugger | Status |
|----------|----------|--------|
| **Python** | debugpy (VS Code) | Stable |
| **JavaScript/TypeScript** | Node.js Debug Adapter | Stable |
| **Go** | Delve | Stable |
| **Rust** | CodeLLDB | Stable |
| **C/C++** | CodeLLDB | Stable |

## Demo

### AI Debugging a Crashing Script

The AI uses polybugger to find a division-by-zero bug in a Python script:

![polybugger debugging demo](docs/debug_full_demo.gif)

### Available Debug Tools

![polybugger tools overview](docs/debug_demo.gif)

### Session Continuity

Debug sessions persist across multiple interactions - no need to reconfigure breakpoints or restart:

![session continuity demo](docs/session_continuity_demo.gif)

### Call Chain Visualization

See the complete call stack with source context at each frame:

![call chain demo](docs/call_chain_demo.gif)

### Watch Expressions

Track variable values as they change through execution:

![watch expressions demo](docs/watch_expressions_demo.gif)

## Why polybugger-mcp?

| Feature | polybugger-mcp | Other MCP debuggers |
|---------|--------------|---------------------|
| **Multi-Language** | Python, JS/TS, Go, Rust, C/C++ | Python only |
| **Container Debugging** | Docker, Podman, Kubernetes | Not available |
| **Session Recovery** | Resume debugging after server restart | Not available |
| **Watch Expressions** | Track values across debug steps | Planned for 2026 |
| **Pure Python** | Single `pip install`, no Node.js | Requires Node.js runtime |
| **HTTP API** | Use independently of MCP | MCP-only |

## Key Features

- **Multi-Language Debugging** - Python, JavaScript/TypeScript, Go, Rust, and C/C++
- **Container Debugging** - Debug processes inside Docker, Podman, and Kubernetes
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
    "polybugger": {
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
    "polybugger": {
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
code --add-mcp '{"name":"polybugger","command":"uvx","args":["polybugger-mcp"]}'
```

Or add to your MCP settings manually.
</details>

<details>
<summary><b>Claude Code</b></summary>

```bash
claude mcp add polybugger -- uvx polybugger-mcp
```
</details>

<details>
<summary><b>Claude Desktop</b></summary>

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "polybugger": {
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
    "polybugger": {
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
    "polybugger": {
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
    "polybugger": {
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
    "polybugger": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "ghcr.io/wilfoa/polybugger-mcp"]
    }
  }
}
```
</details>

## Available Tools (28 tools)

### Session Management
| Tool | Description |
|------|-------------|
| `debug_create_session` | Create a new debug session (supports `language` parameter) |
| `debug_list_sessions` | List all active debug sessions |
| `debug_get_session` | Get detailed session information |
| `debug_terminate_session` | End a debug session and clean up |
| `debug_list_languages` | List supported programming languages |

### Breakpoints
| Tool | Description |
|------|-------------|
| `debug_set_breakpoints` | Set breakpoints in source files (with optional conditions) |
| `debug_get_breakpoints` | List all breakpoints for a session |
| `debug_clear_breakpoints` | Remove breakpoints from files |

### Execution Control
| Tool | Description |
|------|-------------|
| `debug_launch` | Launch a program for debugging |
| `debug_continue` | Continue execution until next breakpoint |
| `debug_step` | Step execution: `mode="over"` (next line), `"into"` (enter function), `"out"` (exit function) |
| `debug_pause` | Pause a running program |
| `debug_attach` | Attach to a running debugpy server |

### Inspection
| Tool | Description |
|------|-------------|
| `debug_get_stacktrace` | Get the current call stack (supports TUI format) |
| `debug_get_scopes` | Get variable scopes (locals, globals) |
| `debug_get_variables` | Get variables in a scope (supports TUI format) |
| `debug_evaluate` | Evaluate an expression in the current context |
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

### Container Debugging
| Tool | Description |
|------|-------------|
| `debug_container_list_processes` | List Python processes in a container |
| `debug_container_attach` | Attach to a process in a container (auto-injects debugpy) |
| `debug_container_launch` | Launch a program with debugging in a container |

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

### Container Debugging
```
You: Debug the Python process running in my Docker container "api-server"

AI: I'll list the Python processes in that container and attach the debugger.
    [Lists processes, finds PID 1234, injects debugpy, attaches]

    Successfully attached to process 1234 in container "api-server".
    The program is paused at the entry point. Here's the current state:
    - File: /app/server.py
    - Function: handle_request
    - Line: 45

    I can see the request object contains invalid JSON. The 'data' field is None.
```

### Multi-Language Debugging
```
You: Debug my Go server - it's crashing on startup

AI: I'll create a Go debug session using Delve.
    [Creates session with language="go", sets breakpoints, launches]

    The program stopped at main.go:23. The config variable is nil
    because the environment variable CONFIG_PATH is not set.
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

### Recording Demo GIFs

Demo GIFs are created using [VHS](https://github.com/charmbracelet/vhs) with OpenCode as the MCP client. To regenerate them:

```bash
# Install VHS
brew install charmbracelet/tap/vhs

# Configure OpenCode with polybugger MCP (in ~/.config/opencode/opencode.json)
# Add: "mcp": { "polybugger": { "type": "local", "command": ["uvx", "polybugger-mcp"], "enabled": true } }

# Generate the GIFs
vhs docs/tapes/debug_demo.tape              # Shows available debug tools
vhs docs/tapes/debug_full_demo.tape         # Full debugging workflow
vhs docs/tapes/session_continuity_demo.tape # Session persistence across interactions
vhs docs/tapes/call_chain_demo.tape         # Call stack visualization
vhs docs/tapes/watch_expressions_demo.tape  # Watch expressions feature
vhs docs/tapes/container_debug_demo.tape    # Container debugging
```

## Architecture

```
                              ┌─────────────────┐
                              │  debugpy        │──▶ Python
                              ├─────────────────┤
AI Agent  ◀──▶  MCP Server  ◀─┤  Node Debug     │──▶ JavaScript/TypeScript
                              ├─────────────────┤
                              │  Delve          │──▶ Go
                              ├─────────────────┤
                              │  CodeLLDB       │──▶ Rust/C/C++
                              └─────────────────┘
                                     │
                              ┌──────┴──────┐
                              │  Container  │
                              │  Runtimes   │
                              ├─────────────┤
                              │ Docker      │
                              │ Podman      │
                              │ Kubernetes  │
                              └─────────────┘
```

The MCP server translates tool calls to Debug Adapter Protocol (DAP) messages for each language's debugger, enabling full debugging capabilities through natural language.

## Requirements

- Python 3.10 or higher
- Works on macOS, Linux, and Windows

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.
