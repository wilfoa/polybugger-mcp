"""Container debugging support.

This package provides container runtime adapters and utilities for
debugging Python processes running inside containers.

Supported runtimes:
- Docker
- Podman
- Kubernetes
"""

from polybugger_mcp.containers.base import ContainerRuntimeAdapter
from polybugger_mcp.containers.factory import create_runtime, get_supported_runtimes
from polybugger_mcp.containers.ssh_tunnel import SSHTunnel, SSHTunnelManager

__all__ = [
    "ContainerRuntimeAdapter",
    "SSHTunnel",
    "SSHTunnelManager",
    "create_runtime",
    "get_supported_runtimes",
]
