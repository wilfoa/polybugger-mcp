"""SSH tunnel management for remote container debugging.

This module provides utilities for creating and managing SSH tunnels
to access containers running on remote hosts.
"""

import asyncio
import logging
import os
import shutil
import socket
from dataclasses import dataclass, field
from pathlib import Path

from polybugger_mcp.models.container import SSHConfig

logger = logging.getLogger(__name__)


class SSHTunnelError(Exception):
    """Raised when SSH tunnel operations fail."""

    def __init__(self, message: str, details: dict[str, object] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


def _get_free_port() -> int:
    """Get an available local port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port: int = s.getsockname()[1]
        return port


@dataclass
class SSHTunnel:
    """Represents an active SSH tunnel."""

    local_port: int
    remote_host: str
    remote_port: int
    ssh_host: str
    ssh_user: str
    process: asyncio.subprocess.Process | None = None
    _closed: bool = field(default=False, repr=False)

    @property
    def is_active(self) -> bool:
        """Check if the tunnel is still active."""
        if self._closed:
            return False
        if self.process is None:
            return False
        return self.process.returncode is None

    @property
    def local_endpoint(self) -> str:
        """Get the local endpoint to connect to."""
        return f"127.0.0.1:{self.local_port}"

    async def wait_ready(self, timeout: float = 10.0) -> bool:
        """Wait for the tunnel to be ready for connections.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if tunnel is ready, False if timeout reached
        """
        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < timeout:
            try:
                # Try to connect to the local port
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection("127.0.0.1", self.local_port),
                    timeout=1.0,
                )
                writer.close()
                await writer.wait_closed()
                return True
            except (ConnectionRefusedError, asyncio.TimeoutError, OSError):
                await asyncio.sleep(0.2)

        return False

    async def close(self) -> None:
        """Close the SSH tunnel."""
        if self._closed:
            return

        self._closed = True

        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            except ProcessLookupError:
                pass  # Already terminated

            logger.info(
                f"SSH tunnel closed: localhost:{self.local_port} -> "
                f"{self.ssh_user}@{self.ssh_host} -> {self.remote_host}:{self.remote_port}"
            )


class SSHTunnelManager:
    """Manages SSH tunnels for remote debugging."""

    def __init__(self) -> None:
        self._tunnels: dict[str, SSHTunnel] = {}
        self._lock = asyncio.Lock()

    def _get_ssh_command(self) -> str | None:
        """Find the SSH command on the system."""
        return shutil.which("ssh")

    def _tunnel_key(self, ssh_host: str, remote_host: str, remote_port: int) -> str:
        """Generate a unique key for a tunnel."""
        return f"{ssh_host}:{remote_host}:{remote_port}"

    async def create_tunnel(
        self,
        ssh_config: SSHConfig,
        remote_host: str = "127.0.0.1",
        remote_port: int = 5678,
        local_port: int | None = None,
    ) -> SSHTunnel:
        """Create an SSH tunnel for port forwarding.

        Args:
            ssh_config: SSH connection configuration
            remote_host: Target host from SSH server's perspective (default 127.0.0.1)
            remote_port: Target port to forward
            local_port: Local port to bind (auto-assigned if None)

        Returns:
            SSHTunnel instance

        Raises:
            SSHTunnelError: If tunnel creation fails
        """
        ssh_cmd = self._get_ssh_command()
        if not ssh_cmd:
            raise SSHTunnelError(
                "SSH client not found",
                {"hint": "Install OpenSSH client (e.g., 'apt install openssh-client')"},
            )

        # Check if we already have a tunnel for this target
        key = self._tunnel_key(ssh_config.host, remote_host, remote_port)
        async with self._lock:
            if key in self._tunnels and self._tunnels[key].is_active:
                return self._tunnels[key]

        # Get a free local port if not specified
        if local_port is None:
            local_port = _get_free_port()

        # Build SSH command
        cmd = [
            ssh_cmd,
            "-N",  # Don't execute remote command
            "-L",
            f"{local_port}:{remote_host}:{remote_port}",  # Local port forward
            "-o",
            "StrictHostKeyChecking=accept-new",  # Accept new host keys
            "-o",
            "BatchMode=yes",  # Non-interactive mode
            "-o",
            "ConnectTimeout=10",
            "-o",
            "ServerAliveInterval=30",
            "-o",
            "ServerAliveCountMax=3",
            "-p",
            str(ssh_config.port),
        ]

        # Add key file if specified
        if ssh_config.key_path:
            key_path = Path(ssh_config.key_path).expanduser()
            if not key_path.exists():
                raise SSHTunnelError(
                    f"SSH key file not found: {key_path}",
                    {"key_path": str(key_path)},
                )
            cmd.extend(["-i", str(key_path)])

        # Add jump host if specified
        if ssh_config.jump_host:
            jump_str = ssh_config.jump_host
            if ssh_config.jump_user:
                jump_str = f"{ssh_config.jump_user}@{jump_str}"
            if ssh_config.jump_key_path:
                jump_key = Path(ssh_config.jump_key_path).expanduser()
                cmd.extend(["-J", jump_str, "-i", str(jump_key)])
            else:
                cmd.extend(["-J", jump_str])

        # Add target
        cmd.append(f"{ssh_config.user}@{ssh_config.host}")

        # Start SSH process
        logger.info(
            f"Creating SSH tunnel: localhost:{local_port} -> "
            f"{ssh_config.user}@{ssh_config.host} -> {remote_host}:{remote_port}"
        )

        try:
            env = os.environ.copy()
            # Disable SSH password prompt if no key is provided
            if not ssh_config.key_path and not ssh_config.password:
                env["SSH_ASKPASS"] = ""
                env["SSH_ASKPASS_REQUIRE"] = "never"

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            tunnel = SSHTunnel(
                local_port=local_port,
                remote_host=remote_host,
                remote_port=remote_port,
                ssh_host=ssh_config.host,
                ssh_user=ssh_config.user,
                process=process,
            )

            # Wait for tunnel to be ready
            ready = await tunnel.wait_ready(timeout=15.0)
            if not ready:
                # Check if process died
                if process.returncode is not None:
                    stderr = ""
                    if process.stderr:
                        stderr_bytes = await process.stderr.read()
                        stderr = stderr_bytes.decode()[:500]
                    raise SSHTunnelError(
                        f"SSH tunnel failed to start: {stderr}",
                        {
                            "exit_code": process.returncode,
                            "stderr": stderr,
                            "cmd": " ".join(cmd),
                        },
                    )
                raise SSHTunnelError(
                    "SSH tunnel connection timeout",
                    {"timeout": 15.0, "local_port": local_port},
                )

            # Store tunnel
            async with self._lock:
                self._tunnels[key] = tunnel

            logger.info(f"SSH tunnel ready: localhost:{local_port}")
            return tunnel

        except SSHTunnelError:
            raise
        except Exception as e:
            raise SSHTunnelError(
                f"Failed to create SSH tunnel: {e}",
                {"error": str(e)},
            )

    async def get_tunnel(
        self, ssh_host: str, remote_host: str, remote_port: int
    ) -> SSHTunnel | None:
        """Get an existing active tunnel.

        Args:
            ssh_host: SSH server hostname
            remote_host: Target host from SSH server's perspective
            remote_port: Target port

        Returns:
            SSHTunnel if exists and active, None otherwise
        """
        key = self._tunnel_key(ssh_host, remote_host, remote_port)
        async with self._lock:
            tunnel = self._tunnels.get(key)
            if tunnel and tunnel.is_active:
                return tunnel
            return None

    async def close_tunnel(self, ssh_host: str, remote_host: str, remote_port: int) -> bool:
        """Close a specific tunnel.

        Args:
            ssh_host: SSH server hostname
            remote_host: Target host from SSH server's perspective
            remote_port: Target port

        Returns:
            True if tunnel was closed, False if not found
        """
        key = self._tunnel_key(ssh_host, remote_host, remote_port)
        async with self._lock:
            tunnel = self._tunnels.pop(key, None)
            if tunnel:
                await tunnel.close()
                return True
            return False

    async def close_all(self) -> int:
        """Close all active tunnels.

        Returns:
            Number of tunnels closed
        """
        async with self._lock:
            count = 0
            for tunnel in self._tunnels.values():
                await tunnel.close()
                count += 1
            self._tunnels.clear()
            return count

    @property
    def active_count(self) -> int:
        """Get number of active tunnels."""
        return sum(1 for t in self._tunnels.values() if t.is_active)


# Global tunnel manager instance
_tunnel_manager: SSHTunnelManager | None = None


def get_tunnel_manager() -> SSHTunnelManager:
    """Get the global tunnel manager instance."""
    global _tunnel_manager
    if _tunnel_manager is None:
        _tunnel_manager = SSHTunnelManager()
    return _tunnel_manager
