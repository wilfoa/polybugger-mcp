# Python Debugger MCP

[![PyPI version](https://img.shields.io/pypi/v/python-debugger-mcp)](https://pypi.org/project/python-debugger-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/wilfoa/python-debugger-mcp/actions/workflows/tests.yml/badge.svg)](https://github.com/wilfoa/python-debugger-mcp/actions/workflows/tests.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A Model Context Protocol (MCP) server that enables AI agents to debug Python code interactively. Set breakpoints, step through code, inspect variables, and evaluate expressions - all through natural conversation with your AI assistant.

[![Install in Cursor](https://img.shields.io/badge/Cursor-Install%20MCP-blue?style=for-the-badge&logo=cursor)](https://cursor.com/install-mcp?name=python-debugger&config=eyJjb21tYW5kIjoicHl0aG9uIiwiYXJncyI6WyItbSIsInB5dGhvbl9kZWJ1Z2dlcl9tY3AubWNwX3NlcnZlciJdfQ==)
[![Install in VS Code](https://img.shields.io/badge/VS_Code-Install%20Server-0098FF?style=for-the-badge&logo=visualstudiocode)](https://insiders.vscode.dev/redirect?url=vscode%3Amcp%2Finstall%3F%257B%2522name%2522%253A%2522python-debugger%2522%252C%2522command%2522%253A%2522python%2522%252C%2522args%2522%253A%255B%2522-m%2522%252C%2522python_debugger_mcp.mcp_server%2522%255D%257D)

## Demo

https://github.com/wilfoa/python-debugger-mcp/raw/main/docs/demo.mov

## Key Features

- **Full Interactive Debugging** - Set breakpoints, step over/into/out, pause, and continue
- **Variable Inspection** - View locals, globals, and evaluate arbitrary expressions
- **Watch Expressions** - Track values across debug steps
- **Session Recovery** - Resume debugging after server restart
- **Multi-Client Support** - Works with Cursor, VS Code, Claude Desktop, and more

## Installation

First, install the package:

```bash
pip install python-debugger-mcp
```

Then configure your MCP client:

<details>
<summary><b>Cursor</b></summary>

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "python-debugger": {
      "command": "python",
      "args": ["-m", "python_debugger_mcp.mcp_server"]
    }
  }
}
```
</details>

<details>
<summary><b>VS Code</b></summary>

Use the VS Code CLI:

```bash
code --add-mcp '{"name":"python-debugger","command":"python","args":["-m","python_debugger_mcp.mcp_server"]}'
```

Or add to your MCP settings manually.
</details>

<details>
<summary><b>Claude Code</b></summary>

```bash
claude mcp add python-debugger -- python -m python_debugger_mcp.mcp_server
```
</details>

<details>
<summary><b>Claude Desktop</b></summary>

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "python-debugger": {
      "command": "python",
      "args": ["-m", "python_debugger_mcp.mcp_server"]
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
      "command": ["python", "-m", "python_debugger_mcp.mcp_server"],
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
      "command": "python",
      "args": ["-m", "python_debugger_mcp.mcp_server"]
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
      "command": "python",
      "args": ["-m", "python_debugger_mcp.mcp_server"],
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
- Command: `python -m python_debugger_mcp.mcp_server`
</details>

<details>
<summary><b>Docker</b></summary>

```bash
docker run -i --rm ghcr.io/wilfoa/python-debugger-mcp
```

Or in your MCP config:

```json
{
  "mcpServers": {
    "python-debugger": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "ghcr.io/wilfoa/python-debugger-mcp"]
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
   pip install python-debugger-mcp
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

Environment variables (prefix with `PYTHON_DEBUGGER_MCP_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `127.0.0.1` | Server bind address |
| `PORT` | `5679` | Server port (for HTTP mode) |
| `MAX_SESSIONS` | `10` | Maximum concurrent debug sessions |
| `SESSION_TIMEOUT_SECONDS` | `3600` | Session idle timeout (1 hour) |
| `DATA_DIR` | `~/.python-debugger-mcp` | Data directory for persistence |
| `LOG_LEVEL` | `INFO` | Logging level |

## Development

```bash
# Clone and setup
git clone https://github.com/wilfoa/python-debugger-mcp.git
cd python-debugger-mcp
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
