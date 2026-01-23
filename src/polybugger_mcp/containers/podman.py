"""Podman container runtime adapter.

Podman is Docker CLI-compatible, so this adapter extends DockerRuntime
with the CLI command changed to 'podman'.
"""

from polybugger_mcp.containers.docker import DockerRuntime
from polybugger_mcp.models.container import ContainerRuntime


class PodmanRuntime(DockerRuntime):
    """Podman container runtime adapter.

    Podman provides Docker CLI compatibility, so this adapter inherits
    all functionality from DockerRuntime with the CLI command changed.
    """

    def __init__(self) -> None:
        """Initialize the Podman runtime."""
        super().__init__(cli_override="podman")

    @property
    def runtime_type(self) -> ContainerRuntime:
        """The container runtime type."""
        return ContainerRuntime.PODMAN
