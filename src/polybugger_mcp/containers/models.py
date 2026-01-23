"""Container runtime models.

Data models for container information, process discovery, and command execution.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ContainerState(str, Enum):
    """Container runtime state."""

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    RESTARTING = "restarting"
    REMOVING = "removing"
    EXITED = "exited"
    DEAD = "dead"
    UNKNOWN = "unknown"


@dataclass
class ContainerInfo:
    """Information about a container."""

    id: str
    name: str
    state: ContainerState
    image: str
    created: datetime | None = None

    # Network info
    ip_address: str | None = None
    ports: dict[int, int] = field(default_factory=dict)  # container_port -> host_port

    # Labels and metadata
    labels: dict[str, str] = field(default_factory=dict)

    # Runtime-specific info
    runtime_data: dict = field(default_factory=dict)

    @property
    def is_running(self) -> bool:
        """Check if container is running."""
        return self.state == ContainerState.RUNNING


@dataclass
class ProcessInfo:
    """Information about a process inside a container."""

    pid: int
    name: str
    cmdline: str
    user: str = ""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0

    # For Python processes
    is_python: bool = False
    python_version: str | None = None

    @classmethod
    def from_ps_line(cls, line: str) -> "ProcessInfo | None":
        """Parse a process from ps aux output line.

        Expected format: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
        """
        parts = line.split(None, 10)  # Split into max 11 parts
        if len(parts) < 11:
            return None

        try:
            user = parts[0]
            pid = int(parts[1])
            cpu = float(parts[2])
            mem = float(parts[3])
            # Parts 4-9 are VSZ, RSS, TTY, STAT, START, TIME
            cmdline = parts[10]
            name = cmdline.split()[0].split("/")[-1] if cmdline else ""

            # Check if it's a Python process
            is_python = "python" in name.lower() or cmdline.startswith("python")

            return cls(
                pid=pid,
                name=name,
                cmdline=cmdline,
                user=user,
                cpu_percent=cpu,
                memory_percent=mem,
                is_python=is_python,
            )
        except (ValueError, IndexError):
            return None


@dataclass
class ExecResult:
    """Result of executing a command in a container."""

    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def success(self) -> bool:
        """Check if command succeeded."""
        return self.exit_code == 0 and not self.timed_out


@dataclass
class PortForward:
    """Represents an active port forward (for Kubernetes)."""

    local_port: int
    remote_port: int
    process: object | None = None  # asyncio.subprocess.Process
    _closed: bool = field(default=False, repr=False)

    @property
    def is_active(self) -> bool:
        """Check if port forward is active."""
        if self._closed:
            return False
        if self.process is None:
            return False
        # Check if process has returncode (None means still running)
        return getattr(self.process, "returncode", None) is None

    async def close(self) -> None:
        """Close the port forward."""
        import asyncio

        if self._closed:
            return

        self._closed = True

        if self.process:
            try:
                self.process.terminate()  # type: ignore
                await asyncio.wait_for(self.process.wait(), timeout=5.0)  # type: ignore
            except asyncio.TimeoutError:
                self.process.kill()  # type: ignore
                await self.process.wait()  # type: ignore
            except (ProcessLookupError, AttributeError):
                pass
