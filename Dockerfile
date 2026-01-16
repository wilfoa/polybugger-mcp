FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/wilfoa/polybugger-mcp"
LABEL org.opencontainers.image.description="Python Debugger MCP Server"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Install the package from PyPI
RUN pip install --no-cache-dir polybugger-mcp

# Run the MCP server
ENTRYPOINT ["python", "-m", "polybugger_mcp.mcp_server"]
