# Python Debugger MCP

## Project Overview

This is a Python MCP (Model Context Protocol) server that enables AI agents to debug Python code interactively. It translates MCP tool calls to DAP (Debug Adapter Protocol) messages for debugpy.

## Tech Stack

- **Language:** Python 3.10+
- **Framework:** FastAPI with uvicorn, MCP SDK
- **Debugger:** debugpy (Python debugger)
- **Testing:** pytest with pytest-asyncio
- **Package Manager:** pip with pyproject.toml

## Project Structure

```
src/python_debugger_mcp/
  api/           # FastAPI routers (sessions, breakpoints, execution, inspection, output)
  adapters/      # DAP client and debugpy adapter
  core/          # Session management, events, exceptions
  models/        # Pydantic models (DAP, requests, responses)
  persistence/   # Breakpoint storage
  utils/         # Output buffer
  config.py      # Pydantic Settings configuration
  main.py        # FastAPI app entry point
  mcp_server.py  # MCP server with debug_* tools

tests/
  unit/          # Unit tests for buffer and persistence
  integration/   # API integration tests
  e2e/           # End-to-end debug session tests
```

## Running the Project

```bash
# Activate virtual environment
source .venv/bin/activate

# Start the HTTP server
python -m python_debugger_mcp.main

# Start the MCP server (stdio)
python -m python_debugger_mcp.mcp_server

# Run tests
pytest tests/ -v
```

## Debugging This Project

This project includes its own debugging tools as MCP tools.

### Using the Debug Tools

1. **Start the MCP server** - Configure your MCP client to use:
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

2. **Use the debug_* tools** to debug Python code in this project:
   - `debug_create_session` - Create a session with project_root
   - `debug_set_breakpoints` - Set breakpoints in source files
   - `debug_launch` - Launch test scripts or the server itself
   - `debug_get_stacktrace`, `debug_get_variables`, `debug_evaluate` - Inspect state

### Debugging Tests

To debug a failing test:
1. Create a debug session for this project
2. Set breakpoints in the test file or source code
3. Launch with: `program="path/to/test.py"` or `module="pytest"` with `args=["-xvs", "tests/path/to/test.py::test_name"]`

## Code Patterns

- **Async/await:** All I/O operations are async
- **Pydantic models:** Used for all API request/response validation
- **DAP protocol:** Communication with debugpy follows DAP specification
- **State machine:** Sessions have defined state transitions (created -> launching -> running/paused -> terminated)

## Key Files

- `src/python_debugger_mcp/adapters/debugpy_adapter.py` - Core debugpy communication
- `src/python_debugger_mcp/core/session.py` - Session management and state machine
- `src/python_debugger_mcp/mcp_server.py` - MCP server with all debug tools
- `src/python_debugger_mcp/api/sessions.py` - REST API session endpoints
- `tests/e2e/test_debug_session.py` - End-to-end debugging tests
