# pybugger-mcp

[![PyPI version](https://img.shields.io/pypi/v/pybugger-mcp)](https://pypi.org/project/pybugger-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/wilfoa/pybugger-mcp/actions/workflows/tests.yml/badge.svg)](https://github.com/wilfoa/pybugger-mcp/actions/workflows/tests.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A lightweight, pure-Python MCP server for interactive debugging. Uses debugpy (VS Code's debugger) under the hood for reliable, battle-tested debugging.

[![Install in Cursor](https://img.shields.io/badge/Cursor-Install%20MCP-blue?style=for-the-badge&logo=cursor)](https://cursor.com/install-mcp?name=pybugger&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJweWJ1Z2dlci1tY3AiXX0=)
[![Install in VS Code](https://img.shields.io/badge/VS_Code-Install%20Server-0098FF?style=for-the-badge&logo=visualstudiocode)](https://insiders.vscode.dev/redirect?url=vscode%3Amcp%2Finstall%3F%7B%22name%22%3A%22pybugger%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22pybugger-mcp%22%5D%7D)

## Demo

https://github.com/wilfoa/pybugger-mcp/raw/main/docs/demo.mov

## Why pybugger-mcp?

| Feature | pybugger-mcp | Other MCP debuggers |
|---------|--------------|---------------------|
| **Session Recovery** | Resume debugging after server restart | Not available |
| **Watch Expressions** | Track values across debug steps | Planned for 2026 |
| **Pure Python** | Single `pip install`, no Node.js | Requires Node.js runtime |
| **HTTP API** | Use independently of MCP | MCP-only |
| **Lightweight** | ~50KB, minimal dependencies | ~3MB+ bundled |

## Key Features

- **Session Recovery** - Persist debug state and resume after server restart
- **Watch Expressions** - Define expressions to track across every debug step
- **Full Interactive Debugging** - Breakpoints, stepping, pause/continue
- **Variable Inspection** - View locals, globals, evaluate arbitrary expressions
- **Pure Python** - No Node.js required, just `pip install`
- **Dual Interface** - Use via MCP or standalone HTTP API
- **Multi-Client Support** - Cursor, VS Code, Claude Desktop, and more

## Installation

### Quick Install (no clone required)

**Using uvx (recommended):**
```bash
uvx pybugger-mcp
```

**Using pipx:**
```bash
pipx run pybugger-mcp
```

**Using pip:**
```bash
pip install pybugger-mcp
pybugger-mcp
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
      "args": ["pybugger-mcp"]
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
      "args": ["-m", "pybugger_mcp.mcp_server"]
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
code --add-mcp '{"name":"python-debugger","command":"uvx","args":["pybugger-mcp"]}'
```

Or add to your MCP settings manually.
</details>

<details>
<summary><b>Claude Code</b></summary>

```bash
claude mcp add python-debugger -- uvx pybugger-mcp
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
      "args": ["pybugger-mcp"]
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
      "command": ["uvx", "pybugger-mcp"],
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
      "args": ["pybugger-mcp"]
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
      "args": ["pybugger-mcp"],
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
- Command: `uvx pybugger-mcp`
</details>

<details>
<summary><b>Docker</b></summary>

```bash
docker run -i --rm ghcr.io/wilfoa/pybugger-mcp
```

Or in your MCP config:

```json
{
  "mcpServers": {
    "python-debugger": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "ghcr.io/wilfoa/pybugger-mcp"]
    }
  }
}
```
</details>

## Available Tools

| Tool | Description |
|------|-------------|
| `debug_create_session` | Create a new debug session for a project |
| `debug_list_sessions` | List all active debug sessions |
| `debug_get_session` | Get detailed session information |
| `debug_terminate_session` | End a debug session and clean up |
| `debug_set_breakpoints` | Set breakpoints in source files (with optional conditions) |
| `debug_get_breakpoints` | List all breakpoints for a session |
| `debug_clear_breakpoints` | Remove breakpoints from files |
| `debug_launch` | Launch a Python program for debugging |
| `debug_continue` | Continue execution until next breakpoint |
| `debug_step_over` | Step to the next line (skip function calls) |
| `debug_step_into` | Step into a function call |
| `debug_step_out` | Step out of the current function |
| `debug_pause` | Pause a running program |
| `debug_get_stacktrace` | Get the current call stack |
| `debug_get_scopes` | Get variable scopes (locals, globals) |
| `debug_get_variables` | Get variables in a scope |
| `debug_evaluate` | Evaluate a Python expression |
| `debug_add_watch` | Add a watch expression |
| `debug_remove_watch` | Remove a watch expression |
| `debug_evaluate_watches` | Evaluate all watch expressions |
| `debug_poll_events` | Poll for debug events (stopped, terminated, etc.) |
| `debug_get_output` | Get program stdout/stderr |
| `debug_list_recoverable` | List sessions that can be recovered |
| `debug_recover_session` | Recover a session from previous server run |

## Quick Start

1. **Install the package:**
   ```bash
   pip install pybugger-mcp
   ```

2. **Configure your MCP client** (see Installation above)

3. **Start debugging:** Ask your AI assistant:
   > "Debug my script.py - set a breakpoint on line 15 and show me the variables when it stops"

## Example Workflow

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

## Configuration

Environment variables (prefix with `PYBUGGER_MCP_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `127.0.0.1` | Server bind address |
| `PORT` | `5679` | Server port (for HTTP mode) |
| `MAX_SESSIONS` | `10` | Maximum concurrent debug sessions |
| `SESSION_TIMEOUT_SECONDS` | `3600` | Session idle timeout (1 hour) |
| `DATA_DIR` | `~/.pybugger-mcp` | Data directory for persistence |
| `LOG_LEVEL` | `INFO` | Logging level |

## Development

```bash
# Clone and setup
git clone https://github.com/wilfoa/pybugger-mcp.git
cd pybugger-mcp
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
