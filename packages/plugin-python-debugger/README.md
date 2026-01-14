# Python Debugger MCP Python Debugger Plugin

An Python Debugger MCP plugin that provides custom tools for interactive Python debugging via the Python Debugger MCP.

## Installation

### From npm (when published)
Add to your `opencode.json`:

```json
{
  "plugin": ["opencode-python-debugger"]
}
```

### Local installation
Copy `index.ts` to your Python Debugger MCP plugin directory:

```bash
# Project-level
mkdir -p .opencode/plugin
cp index.ts .opencode/plugin/python-debugger.ts

# Global
mkdir -p ~/.config/opencode/plugin
cp index.ts ~/.config/opencode/plugin/python-debugger.ts
```

## Prerequisites

The Python Debugger MCP must be running:

```bash
# Install the debug server
pip install python-debugger-mcp

# Start the server
python -m python_debugger_mcp.main
```

By default, the plugin connects to `http://127.0.0.1:5679`. Configure via environment variables:
- `OPENCODE_DEBUG_HOST` - Server host (default: 127.0.0.1)
- `OPENCODE_DEBUG_PORT` - Server port (default: 5679)

## Available Tools

The plugin provides the following tools to Python Debugger MCP agents:

### Session Management
- **debug-session-create** - Create a new debug session for a project
- **debug-sessions** - List all active debug sessions
- **debug-terminate** - Terminate a debug session

### Program Control
- **debug-launch** - Launch a Python program in debug mode
- **debug-continue** - Continue execution to next breakpoint
- **debug-step-over** - Execute current line, stop at next line
- **debug-step-into** - Step into a function call
- **debug-step-out** - Run until current function returns

### Breakpoints
- **debug-breakpoints** - Set breakpoints in a source file (supports conditional breakpoints)

### Inspection
- **debug-status** - Get session state and poll for events
- **debug-stacktrace** - Get the call stack
- **debug-variables** - Get variables in scope
- **debug-evaluate** - Evaluate a Python expression
- **debug-output** - Get captured program output

## Example Usage

The agent can use these tools like this:

```
1. Create a session: debug-session-create project_root="/path/to/project"
2. Set a breakpoint: debug-breakpoints session_id="sess_xxx" source="/path/to/file.py" breakpoints=[{line: 10}]
3. Launch: debug-launch session_id="sess_xxx" program="/path/to/file.py"
4. Check status: debug-status session_id="sess_xxx"
5. Get stack: debug-stacktrace session_id="sess_xxx"
6. Inspect variables: debug-variables session_id="sess_xxx" frame_id=1
7. Evaluate: debug-evaluate session_id="sess_xxx" expression="len(my_list)"
8. Continue: debug-continue session_id="sess_xxx"
```

## Configuration

### Permissions

Configure tool permissions in `opencode.json`:

```json
{
  "permission": {
    "tool": {
      "debug-*": "allow"
    }
  }
}
```

Or require confirmation:

```json
{
  "permission": {
    "tool": {
      "debug-launch": "ask",
      "debug-terminate": "ask",
      "debug-*": "allow"
    }
  }
}
```

## License

MIT
