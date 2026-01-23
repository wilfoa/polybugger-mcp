"""Kubernetes container runtime adapter.

This module provides the Kubernetes implementation of the container runtime
adapter for debugging Python processes in Kubernetes pods.
"""

import asyncio
import json
import logging
import shutil

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
    PortForward,
    ProcessInfo,
)
from polybugger_mcp.models.container import ContainerRuntime, ContainerTarget

logger = logging.getLogger(__name__)


class KubernetesRuntime(ContainerRuntimeAdapter):
    """Kubernetes container runtime adapter.

    Uses kubectl to interact with pods and containers in a Kubernetes cluster.
    """

    def __init__(self, context: str | None = None, kubeconfig: str | None = None):
        """Initialize the Kubernetes runtime.

        Args:
            context: Kubernetes context to use (default: current context)
            kubeconfig: Path to kubeconfig file (default: ~/.kube/config)
        """
        self._context = context
        self._kubeconfig = kubeconfig
        self._port_forwards: dict[str, PortForward] = {}

    @property
    def runtime_type(self) -> ContainerRuntime:
        """The container runtime type."""
        return ContainerRuntime.KUBERNETES

    @property
    def cli_command(self) -> str:
        """The CLI command for Kubernetes."""
        return "kubectl"

    def _build_base_args(self) -> list[str]:
        """Build base kubectl arguments."""
        args = []
        if self._context:
            args.extend(["--context", self._context])
        if self._kubeconfig:
            args.extend(["--kubeconfig", self._kubeconfig])
        return args

    def _get_pod_identifier(self, target: ContainerTarget) -> tuple[str, str]:
        """Get namespace and pod name from target."""
        namespace = target.namespace or "default"
        pod_name = target.pod_name or target.container_name or ""
        return namespace, pod_name

    async def is_available(self) -> bool:
        """Check if kubectl is available."""
        cmd = shutil.which(self.cli_command)
        if not cmd:
            return False

        try:
            proc = await asyncio.create_subprocess_exec(
                self.cli_command,
                "version",
                "--client",
                "--output=json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.wait(), timeout=5.0)
            return proc.returncode == 0
        except (asyncio.TimeoutError, OSError):
            return False

    async def _run_kubectl(
        self,
        *args: str,
        timeout: float = 30.0,
        check: bool = False,
    ) -> ExecResult:
        """Run a kubectl command.

        Args:
            *args: Command arguments
            timeout: Command timeout
            check: Raise exception on non-zero exit

        Returns:
            ExecResult with stdout, stderr, exit code
        """
        cmd = [self.cli_command, *self._build_base_args(), *args]
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
        """Get detailed pod/container information."""
        namespace, pod_name = self._get_pod_identifier(target)
        if not pod_name:
            raise ContainerNotFoundError("(empty)", self.cli_command)

        result = await self._run_kubectl(
            "get",
            "pod",
            pod_name,
            "-n",
            namespace,
            "-o",
            "json",
        )

        if not result.success:
            if "NotFound" in result.stderr or "not found" in result.stderr.lower():
                raise ContainerNotFoundError(f"{namespace}/{pod_name}", self.cli_command)
            raise ContainerError(
                f"Failed to get pod info: {result.stderr}",
                details={"pod": pod_name, "namespace": namespace},
            )

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            raise ContainerError(
                f"Failed to parse pod info: {result.stdout[:200]}",
                details={"pod": pod_name},
            )

        # Parse phase to state
        phase = data.get("status", {}).get("phase", "Unknown").lower()
        state_map = {
            "pending": ContainerState.CREATED,
            "running": ContainerState.RUNNING,
            "succeeded": ContainerState.EXITED,
            "failed": ContainerState.DEAD,
            "unknown": ContainerState.UNKNOWN,
        }
        state = state_map.get(phase, ContainerState.UNKNOWN)

        # Get pod IP
        ip_address = data.get("status", {}).get("podIP")

        # Get container status if specific container requested
        container_name = target.pod_container
        if container_name:
            container_statuses = data.get("status", {}).get("containerStatuses", [])
            for cs in container_statuses:
                if cs.get("name") == container_name:
                    if cs.get("state", {}).get("running"):
                        state = ContainerState.RUNNING
                    elif cs.get("state", {}).get("terminated"):
                        state = ContainerState.EXITED
                    elif cs.get("state", {}).get("waiting"):
                        state = ContainerState.CREATED
                    break

        return ContainerInfo(
            id=data.get("metadata", {}).get("uid", "")[:12],
            name=pod_name,
            state=state,
            image=data.get("spec", {}).get("containers", [{}])[0].get("image", ""),
            ip_address=ip_address,
            labels=data.get("metadata", {}).get("labels", {}),
            runtime_data=data,
        )

    async def exec_command(
        self,
        target: ContainerTarget,
        command: list[str],
        env: dict[str, str] | None = None,
        workdir: str | None = None,
        timeout: float = 30.0,
        user: str | None = None,  # noqa: ARG002 - kept for API compatibility
    ) -> ExecResult:
        """Execute a command inside a pod."""
        namespace, pod_name = self._get_pod_identifier(target)
        if not pod_name:
            raise ContainerNotFoundError("(empty)", self.cli_command)

        # Verify pod is running
        info = await self.get_container_info(target)
        if not info.is_running:
            raise ContainerNotRunningError(f"{namespace}/{pod_name}", info.state.value)

        # Build exec command
        args = ["exec", pod_name, "-n", namespace]

        if target.pod_container:
            args.extend(["-c", target.pod_container])

        # kubectl exec doesn't support -w or -e directly, use sh wrapper
        shell_cmd = " ".join(command)
        if workdir:
            shell_cmd = f"cd {workdir} && {shell_cmd}"
        if env:
            env_exports = " ".join(f"{k}={v}" for k, v in env.items())
            shell_cmd = f"{env_exports} {shell_cmd}"

        args.extend(["--", "sh", "-c", shell_cmd])

        return await self._run_kubectl(*args, timeout=timeout)

    async def find_python_processes(self, target: ContainerTarget) -> list[ProcessInfo]:
        """Find Python processes in a pod."""
        result = await self.exec_command(
            target,
            ["ps", "aux"],
            timeout=10.0,
        )

        if not result.success:
            # Try alternative
            result = await self.exec_command(
                target,
                ["cat", "/proc/*/cmdline"],
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
        """Check if debugpy is installed in the pod."""
        result = await self.exec_command(
            target,
            ["python", "-c", "import debugpy; print(debugpy.__version__)"],
            timeout=10.0,
        )
        return result.success

    async def install_debugpy(self, target: ContainerTarget) -> None:
        """Install debugpy in the pod."""
        result = await self.exec_command(
            target,
            ["pip", "install", "--quiet", "debugpy"],
            timeout=60.0,
        )

        if not result.success:
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

        logger.info(f"Installed debugpy in pod {target.identifier}")

    async def inject_debugpy(
        self,
        target: ContainerTarget,
        process_id: int,
        port: int = 5678,
    ) -> None:
        """Inject debugpy into a running Python process."""
        if not await self.check_debugpy_installed(target):
            await self.install_debugpy(target)

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
            stderr_lower = result.stderr.lower()
            if (
                "operation not permitted" in stderr_lower
                or "ptrace" in stderr_lower
                or "eperm" in stderr_lower
            ):
                raise ContainerSecurityError(
                    "Cannot inject debugpy: ptrace not permitted",
                    instructions=[
                        "Pod lacks SYS_PTRACE capability required for debugger injection.",
                        "",
                        "Solutions:",
                        "1. Add SYS_PTRACE capability to your pod spec:",
                        "   securityContext:",
                        "     capabilities:",
                        "       add: ['SYS_PTRACE']",
                        "",
                        "2. Use debug_container_launch to start a new debuggable process",
                        "3. Pre-install debugpy and call debugpy.listen() in your code",
                    ],
                )

            raise ContainerExecError(
                f"debugpy --pid {process_id}",
                result.exit_code,
                result.stderr,
            )

        logger.info(f"Injected debugpy into PID {process_id} in pod {target.identifier}")

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
        if not await self.check_debugpy_installed(target):
            await self.install_debugpy(target)

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

        # Run in background using nohup
        namespace, pod_name = self._get_pod_identifier(target)
        args = ["exec", pod_name, "-n", namespace]

        if target.pod_container:
            args.extend(["-c", target.pod_container])

        # Build command with environment and workdir
        shell_cmd = " ".join(debugpy_cmd)
        if workdir:
            shell_cmd = f"cd {workdir} && {shell_cmd}"
        if env:
            env_exports = " ".join(f"export {k}={v};" for k, v in env.items())
            shell_cmd = f"{env_exports} {shell_cmd}"

        # Use nohup to run in background
        args.extend(["--", "sh", "-c", f"nohup {shell_cmd} > /dev/null 2>&1 &"])

        result = await self._run_kubectl(*args, timeout=10.0)

        if not result.success:
            raise ContainerExecError(
                " ".join(debugpy_cmd),
                result.exit_code,
                result.stderr,
            )

        logger.info(f"Launched debugpy in pod {target.identifier} on port {port}")

    async def get_debugpy_endpoint(
        self,
        target: ContainerTarget,
        container_port: int = 5678,
    ) -> tuple[str, int]:
        """Get endpoint using kubectl port-forward."""
        namespace, pod_name = self._get_pod_identifier(target)
        key = f"{namespace}/{pod_name}:{container_port}"

        # Check for existing port-forward
        if key in self._port_forwards and self._port_forwards[key].is_active:
            pf = self._port_forwards[key]
            return ("127.0.0.1", pf.local_port)

        # Create new port-forward
        import socket

        # Get a free local port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            local_port = s.getsockname()[1]

        cmd = [
            self.cli_command,
            *self._build_base_args(),
            "port-forward",
            f"pod/{pod_name}",
            "-n",
            namespace,
            f"{local_port}:{container_port}",
        ]

        logger.info(f"Starting port-forward: localhost:{local_port} -> {pod_name}:{container_port}")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        pf = PortForward(
            local_port=local_port,
            remote_port=container_port,
            process=proc,
        )

        # Wait for port-forward to be ready
        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < 10.0:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection("127.0.0.1", local_port),
                    timeout=1.0,
                )
                writer.close()
                await writer.wait_closed()
                break
            except (ConnectionRefusedError, asyncio.TimeoutError, OSError):
                if proc.returncode is not None:
                    stderr = ""
                    if proc.stderr:
                        stderr_bytes = await proc.stderr.read()
                        stderr = stderr_bytes.decode()[:500]
                    raise ContainerError(
                        f"Port-forward failed: {stderr}",
                        details={"pod": pod_name, "port": container_port},
                    )
                await asyncio.sleep(0.2)
        else:
            proc.kill()
            raise ContainerError(
                "Port-forward timeout",
                details={"pod": pod_name, "port": container_port},
            )

        self._port_forwards[key] = pf
        return ("127.0.0.1", local_port)

    async def cleanup_port_forwards(self) -> None:
        """Close all active port-forwards."""
        for pf in self._port_forwards.values():
            await pf.close()
        self._port_forwards.clear()
