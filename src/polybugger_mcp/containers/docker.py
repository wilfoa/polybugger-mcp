"""Docker container runtime adapter.

This module provides the Docker implementation of the container runtime
adapter for debugging Python processes in Docker containers.
"""

import asyncio
import json
import logging
import shutil
from datetime import datetime

from polybugger_mcp.containers.base import (
    ContainerError,
    ContainerExecError,
    ContainerNotFoundError,
    ContainerNotRunningError,
    ContainerRuntimeAdapter,
    ContainerSecurityError,
)
from polybugger_mcp.containers.models import (
    ContainerInfo,
    ContainerState,
    ExecResult,
    ProcessInfo,
)
from polybugger_mcp.models.container import ContainerRuntime, ContainerTarget

logger = logging.getLogger(__name__)


class DockerRuntime(ContainerRuntimeAdapter):
    """Docker container runtime adapter.

    Uses the Docker CLI to interact with containers. This implementation
    works with both Docker and Podman (which provides Docker CLI compatibility).
    """

    def __init__(self, cli_override: str | None = None):
        """Initialize the Docker runtime.

        Args:
            cli_override: Override the CLI command (useful for Podman)
        """
        self._cli_override = cli_override

    @property
    def runtime_type(self) -> ContainerRuntime:
        """The container runtime type."""
        return ContainerRuntime.DOCKER

    @property
    def cli_command(self) -> str:
        """The CLI command for Docker."""
        if self._cli_override:
            return self._cli_override
        return "docker"

    async def is_available(self) -> bool:
        """Check if Docker CLI is available."""
        cmd = shutil.which(self.cli_command)
        if not cmd:
            return False

        try:
            proc = await asyncio.create_subprocess_exec(
                self.cli_command,
                "version",
                "--format",
                "{{.Server.Version}}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.wait(), timeout=5.0)
            return proc.returncode == 0
        except (asyncio.TimeoutError, OSError):
            return False

    def _get_container_identifier(self, target: ContainerTarget) -> str:
        """Get the container identifier (name or ID) from target."""
        return target.container_name or target.container_id or ""

    async def _run_cli(
        self,
        *args: str,
        timeout: float = 30.0,
        check: bool = False,
    ) -> ExecResult:
        """Run a Docker CLI command.

        Args:
            *args: Command arguments
            timeout: Command timeout
            check: Raise exception on non-zero exit

        Returns:
            ExecResult with stdout, stderr, exit code
        """
        cmd = [self.cli_command, *args]
        logger.debug(f"Running: {' '.join(cmd)}")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return ExecResult(
                    exit_code=-1,
                    stdout="",
                    stderr="Command timed out",
                    timed_out=True,
                )

            result = ExecResult(
                exit_code=proc.returncode or 0,
                stdout=stdout_bytes.decode("utf-8", errors="replace"),
                stderr=stderr_bytes.decode("utf-8", errors="replace"),
            )

            if check and not result.success:
                raise ContainerExecError(
                    command=" ".join(cmd),
                    exit_code=result.exit_code,
                    stderr=result.stderr,
                )

            return result

        except ContainerExecError:
            raise
        except Exception as e:
            return ExecResult(
                exit_code=-1,
                stdout="",
                stderr=str(e),
            )

    async def get_container_info(self, target: ContainerTarget) -> ContainerInfo:
        """Get detailed container information."""
        container = self._get_container_identifier(target)
        if not container:
            raise ContainerNotFoundError("(empty)", self.cli_command)

        result = await self._run_cli(
            "inspect",
            "--format",
            "{{json .}}",
            container,
        )

        if not result.success:
            if "No such" in result.stderr or "not found" in result.stderr.lower():
                raise ContainerNotFoundError(container, self.cli_command)
            raise ContainerError(
                f"Failed to inspect container: {result.stderr}",
                details={"container": container},
            )

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            raise ContainerError(
                f"Failed to parse container info: {result.stdout[:200]}",
                details={"container": container},
            )

        # Parse state
        state_str = data.get("State", {}).get("Status", "unknown").lower()
        state_map = {
            "created": ContainerState.CREATED,
            "running": ContainerState.RUNNING,
            "paused": ContainerState.PAUSED,
            "restarting": ContainerState.RESTARTING,
            "removing": ContainerState.REMOVING,
            "exited": ContainerState.EXITED,
            "dead": ContainerState.DEAD,
        }
        state = state_map.get(state_str, ContainerState.UNKNOWN)

        # Parse network info
        networks = data.get("NetworkSettings", {}).get("Networks", {})
        ip_address = None
        for net in networks.values():
            if net.get("IPAddress"):
                ip_address = net["IPAddress"]
                break

        # Parse port mappings
        ports: dict[int, int] = {}
        port_bindings = data.get("NetworkSettings", {}).get("Ports", {})
        for container_port_str, bindings in port_bindings.items():
            if bindings:
                container_port = int(container_port_str.split("/")[0])
                host_port = int(bindings[0].get("HostPort", 0))
                if host_port:
                    ports[container_port] = host_port

        # Parse creation time
        created = None
        created_str = data.get("Created")
        if created_str:
            try:
                # Docker uses RFC3339 format
                created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        return ContainerInfo(
            id=data.get("Id", "")[:12],
            name=data.get("Name", "").lstrip("/"),
            state=state,
            image=data.get("Config", {}).get("Image", ""),
            created=created,
            ip_address=ip_address,
            ports=ports,
            labels=data.get("Config", {}).get("Labels", {}),
            runtime_data=data,
        )

    async def exec_command(
        self,
        target: ContainerTarget,
        command: list[str],
        env: dict[str, str] | None = None,
        workdir: str | None = None,
        timeout: float = 30.0,
        user: str | None = None,
    ) -> ExecResult:
        """Execute a command inside a container."""
        container = self._get_container_identifier(target)
        if not container:
            raise ContainerNotFoundError("(empty)", self.cli_command)

        # Verify container is running
        info = await self.get_container_info(target)
        if not info.is_running:
            raise ContainerNotRunningError(container, info.state.value)

        # Build exec command
        args = ["exec"]

        if env:
            for key, value in env.items():
                args.extend(["-e", f"{key}={value}"])

        if workdir:
            args.extend(["-w", workdir])

        if user:
            args.extend(["-u", user])

        args.append(container)
        args.extend(command)

        return await self._run_cli(*args, timeout=timeout)

    async def find_python_processes(self, target: ContainerTarget) -> list[ProcessInfo]:
        """Find Python processes in a container."""
        # Use ps to list processes
        result = await self.exec_command(
            target,
            ["ps", "aux"],
            timeout=10.0,
        )

        if not result.success:
            # Some containers don't have ps, try /proc
            result = await self.exec_command(
                target,
                [
                    "sh",
                    "-c",
                    "for pid in /proc/[0-9]*; do "
                    'echo "$(cat $pid/stat 2>/dev/null | cut -d" " -f1,2) '
                    '$(cat $pid/cmdline 2>/dev/null | tr "\\0" " ")"; '
                    "done",
                ],
                timeout=10.0,
            )

        if not result.success:
            logger.warning(f"Failed to list processes: {result.stderr}")
            return []

        processes: list[ProcessInfo] = []
        lines = result.stdout.strip().split("\n")

        for line in lines[1:]:  # Skip header
            proc = ProcessInfo.from_ps_line(line)
            if proc and proc.is_python:
                processes.append(proc)

        return processes

    async def check_debugpy_installed(self, target: ContainerTarget) -> bool:
        """Check if debugpy is installed in the container."""
        result = await self.exec_command(
            target,
            ["python", "-c", "import debugpy; print(debugpy.__version__)"],
            timeout=10.0,
        )
        return result.success

    async def install_debugpy(self, target: ContainerTarget) -> None:
        """Install debugpy in the container."""
        # Try pip first
        result = await self.exec_command(
            target,
            ["pip", "install", "--quiet", "debugpy"],
            timeout=60.0,
        )

        if not result.success:
            # Try pip3
            result = await self.exec_command(
                target,
                ["pip3", "install", "--quiet", "debugpy"],
                timeout=60.0,
            )

        if not result.success:
            # Try python -m pip
            result = await self.exec_command(
                target,
                ["python", "-m", "pip", "install", "--quiet", "debugpy"],
                timeout=60.0,
            )

        if not result.success:
            raise ContainerExecError(
                "pip install debugpy",
                result.exit_code,
                result.stderr,
            )

        logger.info(f"Installed debugpy in container {target.identifier}")

    async def inject_debugpy(
        self,
        target: ContainerTarget,
        process_id: int,
        port: int = 5678,
    ) -> None:
        """Inject debugpy into a running Python process."""
        # First check if debugpy is installed
        if not await self.check_debugpy_installed(target):
            await self.install_debugpy(target)

        # Try to inject using debugpy --pid
        result = await self.exec_command(
            target,
            [
                "python",
                "-m",
                "debugpy",
                "--listen",
                f"0.0.0.0:{port}",
                "--pid",
                str(process_id),
            ],
            timeout=30.0,
        )

        if not result.success:
            # Check for ptrace error
            stderr_lower = result.stderr.lower()
            if (
                "operation not permitted" in stderr_lower
                or "ptrace" in stderr_lower
                or "eperm" in stderr_lower
            ):
                raise ContainerSecurityError(
                    "Cannot inject debugpy: ptrace not permitted",
                    instructions=[
                        "Container lacks SYS_PTRACE capability required for debugger injection.",
                        "",
                        "Solutions:",
                        f"1. Restart container with: {self.cli_command} run --cap-add=SYS_PTRACE ...",
                        "2. Use debug_container_launch to start a new debuggable process",
                        "3. Pre-install debugpy and call debugpy.listen() in your code",
                        "",
                        "For docker-compose, add to your service:",
                        "  cap_add:",
                        "    - SYS_PTRACE",
                    ],
                )

            raise ContainerExecError(
                f"debugpy --pid {process_id}",
                result.exit_code,
                result.stderr,
            )

        logger.info(f"Injected debugpy into PID {process_id} in container {target.identifier}")

    async def launch_with_debugpy(
        self,
        target: ContainerTarget,
        command: list[str],
        port: int = 5678,
        wait_for_client: bool = True,
        env: dict[str, str] | None = None,
        workdir: str | None = None,
    ) -> None:
        """Launch a command with debugpy listening."""
        # Ensure debugpy is installed
        if not await self.check_debugpy_installed(target):
            await self.install_debugpy(target)

        # Build debugpy command
        debugpy_cmd = [
            "python",
            "-m",
            "debugpy",
            "--listen",
            f"0.0.0.0:{port}",
        ]

        if wait_for_client:
            debugpy_cmd.append("--wait-for-client")

        debugpy_cmd.extend(command)

        # Execute in background (detached)
        container = self._get_container_identifier(target)
        args = ["exec", "-d"]  # -d for detached

        if env:
            for key, value in env.items():
                args.extend(["-e", f"{key}={value}"])

        if workdir:
            args.extend(["-w", workdir])

        args.append(container)
        args.extend(debugpy_cmd)

        result = await self._run_cli(*args, timeout=10.0)

        if not result.success:
            raise ContainerExecError(
                " ".join(debugpy_cmd),
                result.exit_code,
                result.stderr,
            )

        logger.info(f"Launched debugpy in container {target.identifier} on port {port}")
