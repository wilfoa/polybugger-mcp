FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/wilfoa/python-debugger-mcp"
LABEL org.opencontainers.image.description="Python Debugger MCP Server"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Install the package from PyPI
RUN pip install --no-cache-dir python-debugger-mcp

# Run the MCP server
ENTRYPOINT ["python", "-m", "python_debugger_mcp.mcp_server"]
