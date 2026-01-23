"""Abstract base class for container runtime adapters.

This module defines the interface that all container runtime implementations
(Docker, Podman, Kubernetes) must implement.
"""

from abc import ABC, abstractmethod
from typing import Any

from polybugger_mcp.containers.models import ContainerInfo, ExecResult, ProcessInfo
from polybugger_mcp.models.container import ContainerRuntime, ContainerTarget


class ContainerError(Exception):
    """Base exception for container operations."""

    def __init__(
        self,
        message: str,
        code: str = "CONTAINER_ERROR",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class ContainerNotFoundError(ContainerError):
    """Container not found."""

    def __init__(self, container: str, runtime: str):
        super().__init__(
            f"Container '{container}' not found",
            code="CONTAINER_NOT_FOUND",
            details={"container": container, "runtime": runtime},
        )


class ContainerNotRunningError(ContainerError):
    """Container is not running."""

    def __init__(self, container: str, state: str):
        super().__init__(
            f"Container '{container}' is not running (state: {state})",
            code="CONTAINER_NOT_RUNNING",
            details={"container": container, "state": state},
        )


class ContainerExecError(ContainerError):
    """Command execution failed in container."""

    def __init__(self, command: str, exit_code: int, stderr: str):
        super().__init__(
            f"Command failed with exit code {exit_code}: {stderr[:200]}",
            code="CONTAINER_EXEC_ERROR",
            details={"command": command, "exit_code": exit_code, "stderr": stderr},
        )


class ContainerSecurityError(ContainerError):
    """Security-related error (e.g., missing capabilities for ptrace)."""

    def __init__(self, message: str, instructions: list[str] | None = None):
        super().__init__(
            message,
            code="CONTAINER_SECURITY_ERROR",
            details={"instructions": instructions or []},
        )
        self.instructions = instructions or []


class ContainerRuntimeAdapter(ABC):
    """Abstract base class for container runtime adapters.

    Each runtime (Docker, Podman, Kubernetes) must implement this interface
    to provide container debugging capabilities.
    """

    @property
    @abstractmethod
    def runtime_type(self) -> ContainerRuntime:
        """The container runtime type this adapter handles."""
        ...

    @property
    @abstractmethod
    def cli_command(self) -> str:
        """The CLI command for this runtime (e.g., 'docker', 'kubectl')."""
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the runtime CLI is available on the system.

        Returns:
            True if the CLI is installed and accessible
        """
        ...

    @abstractmethod
    async def get_container_info(self, target: ContainerTarget) -> ContainerInfo:
        """Get detailed information about a container.

        Args:
            target: Container target specification

        Returns:
            ContainerInfo with state, network info, etc.

        Raises:
            ContainerNotFoundError: If container doesn't exist
        """
        ...

    @abstractmethod
    async def exec_command(
        self,
        target: ContainerTarget,
        command: list[str],
        env: dict[str, str] | None = None,
        workdir: str | None = None,
        timeout: float = 30.0,
        user: str | None = None,
    ) -> ExecResult:
        """Execute a command inside a container.

        Args:
            target: Container target specification
            command: Command and arguments to execute
            env: Environment variables to set
            workdir: Working directory inside container
            timeout: Command timeout in seconds
            user: User to run command as

        Returns:
            ExecResult with stdout, stderr, and exit code

        Raises:
            ContainerNotFoundError: If container doesn't exist
            ContainerNotRunningError: If container is not running
        """
        ...

    @abstractmethod
    async def find_python_processes(self, target: ContainerTarget) -> list[ProcessInfo]:
        """Find Python processes running in a container.

        Args:
            target: Container target specification

        Returns:
            List of Python processes with PID, cmdline, etc.

        Raises:
            ContainerNotFoundError: If container doesn't exist
            ContainerNotRunningError: If container is not running
        """
        ...

    @abstractmethod
    async def check_debugpy_installed(self, target: ContainerTarget) -> bool:
        """Check if debugpy is installed in the container.

        Args:
            target: Container target specification

        Returns:
            True if debugpy is importable in the container
        """
        ...

    @abstractmethod
    async def install_debugpy(self, target: ContainerTarget) -> None:
        """Install debugpy in the container.

        Args:
            target: Container target specification

        Raises:
            ContainerExecError: If installation fails
        """
        ...

    @abstractmethod
    async def inject_debugpy(
        self,
        target: ContainerTarget,
        process_id: int,
        port: int = 5678,
    ) -> None:
        """Inject debugpy into a running Python process.

        This uses debugpy's --pid mode to attach to an existing process.
        Requires SYS_PTRACE capability.

        Args:
            target: Container target specification
            process_id: PID of the Python process inside the container
            port: Port for debugpy to listen on

        Raises:
            ContainerSecurityError: If ptrace is not allowed
            ContainerExecError: If injection fails
        """
        ...

    @abstractmethod
    async def launch_with_debugpy(
        self,
        target: ContainerTarget,
        command: list[str],
        port: int = 5678,
        wait_for_client: bool = True,
        env: dict[str, str] | None = None,
        workdir: str | None = None,
    ) -> None:
        """Launch a command with debugpy listening.

        This starts a new process with debugpy.listen() configured.

        Args:
            target: Container target specification
            command: Command to run (e.g., ["python", "app.py"])
            port: Port for debugpy to listen on
            wait_for_client: Whether to wait for debugger to attach
            env: Additional environment variables
            workdir: Working directory

        Raises:
            ContainerExecError: If launch fails
        """
        ...

    async def get_debugpy_endpoint(
        self,
        target: ContainerTarget,
        container_port: int = 5678,
    ) -> tuple[str, int]:
        """Get the host and port to connect to debugpy.

        For local containers, this returns the container's IP or mapped port.
        Subclasses may override for special handling (e.g., Kubernetes port-forward).

        Args:
            target: Container target specification
            container_port: Port debugpy is listening on inside container

        Returns:
            Tuple of (host, port) to connect to
        """
        info = await self.get_container_info(target)

        # Check for mapped port first
        if container_port in info.ports:
            return ("127.0.0.1", info.ports[container_port])

        # Fall back to container IP
        if info.ip_address:
            return (info.ip_address, container_port)

        raise ContainerError(
            f"Cannot determine debugpy endpoint for container {target.identifier}",
            code="NO_ENDPOINT",
            details={
                "container": target.identifier,
                "port": container_port,
                "mapped_ports": info.ports,
                "ip_address": info.ip_address,
            },
        )
