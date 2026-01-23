"""Container debugging models.

This module defines models for container-based debugging, supporting
Docker, Podman, and Kubernetes runtimes.
"""

from enum import Enum

from pydantic import BaseModel, Field


class ContainerRuntime(str, Enum):
    """Supported container runtimes."""

    DOCKER = "docker"
    PODMAN = "podman"
    KUBERNETES = "kubernetes"


class PathMapping(BaseModel):
    """Maps local paths to container/remote paths.

    Used for translating breakpoint locations and source file paths
    between the local development environment and the container.
    """

    local_root: str = Field(description="Local path root (e.g., /home/user/project)")
    remote_root: str = Field(description="Remote/container path root (e.g., /app)")

    def to_remote(self, local_path: str) -> str:
        """Convert a local path to the corresponding remote path."""
        if local_path.startswith(self.local_root):
            relative = local_path[len(self.local_root) :].lstrip("/")
            return f"{self.remote_root.rstrip('/')}/{relative}"
        return local_path

    def to_local(self, remote_path: str) -> str:
        """Convert a remote path to the corresponding local path."""
        if remote_path.startswith(self.remote_root):
            relative = remote_path[len(self.remote_root) :].lstrip("/")
            return f"{self.local_root.rstrip('/')}/{relative}"
        return remote_path


class SSHConfig(BaseModel):
    """SSH connection configuration for remote container access."""

    host: str = Field(description="SSH server hostname or IP")
    user: str = Field(description="SSH username")
    port: int = Field(default=22, description="SSH port")
    key_path: str | None = Field(default=None, description="Path to SSH private key file")
    password: str | None = Field(default=None, description="SSH password (key_path preferred)")
    # For jump hosts / bastion
    jump_host: str | None = Field(default=None, description="SSH jump host (bastion)")
    jump_user: str | None = Field(default=None, description="Jump host username")
    jump_key_path: str | None = Field(default=None, description="Jump host key path")


class ContainerTarget(BaseModel):
    """Identifies a container to debug.

    Supports Docker/Podman containers and Kubernetes pods.
    """

    runtime: ContainerRuntime = Field(description="Container runtime type")

    # Docker/Podman identification (use one)
    container_id: str | None = Field(default=None, description="Container ID (Docker/Podman)")
    container_name: str | None = Field(default=None, description="Container name (Docker/Podman)")

    # Kubernetes identification
    namespace: str = Field(default="default", description="Kubernetes namespace")
    pod_name: str | None = Field(default=None, description="Kubernetes pod name")
    # For multi-container pods
    pod_container: str | None = Field(
        default=None,
        description="Container name within pod (for multi-container pods)",
    )

    # Remote access
    ssh: SSHConfig | None = Field(default=None, description="SSH config for remote container hosts")

    @property
    def identifier(self) -> str:
        """Get a human-readable identifier for this target."""
        if self.runtime == ContainerRuntime.KUBERNETES:
            container_suffix = f"/{self.pod_container}" if self.pod_container else ""
            return f"{self.namespace}/{self.pod_name}{container_suffix}"
        return self.container_name or self.container_id or "unknown"


class ContainerAttachConfig(BaseModel):
    """Configuration for attaching to a container process."""

    target: ContainerTarget = Field(description="Container to attach to")

    # Process identification (use one)
    process_id: int | None = Field(default=None, description="PID of process inside container")
    process_name: str | None = Field(
        default=None,
        description="Process name filter (e.g., 'python', 'gunicorn')",
    )

    # Debugpy configuration
    debugpy_port: int = Field(default=5678, description="Port for debugpy to listen on")
    inject_debugpy: bool = Field(
        default=True,
        description="Automatically inject debugpy if not already running",
    )

    # Path mapping for source files
    path_mappings: list[PathMapping] = Field(
        default_factory=list,
        description="Local to remote path mappings",
    )

    # Connection override
    host_override: str | None = Field(
        default=None,
        description="Override auto-detected host for debugpy connection",
    )


class ContainerLaunchConfig(BaseModel):
    """Configuration for launching a debug process in a container."""

    target: ContainerTarget = Field(description="Container to launch in")

    # What to run (use one)
    program: str | None = Field(default=None, description="Script path inside container")
    module: str | None = Field(default=None, description="Python module to run (e.g., 'pytest')")

    # Execution options
    args: list[str] = Field(default_factory=list, description="Program arguments")
    cwd: str = Field(default="/app", description="Working directory inside container")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")

    # Debug options
    debugpy_port: int = Field(default=5678, description="Port for debugpy")
    stop_on_entry: bool = Field(default=False, description="Pause at first line")
    stop_on_exception: bool = Field(default=True, description="Pause on exceptions")

    # Path mapping
    path_mappings: list[PathMapping] = Field(
        default_factory=list,
        description="Local to remote path mappings",
    )
