"""Tests for container debugging support."""

import pytest

from polybugger_mcp.containers.base import (
    ContainerNotFoundError,
    ContainerSecurityError,
)
from polybugger_mcp.containers.factory import (
    create_runtime,
    get_supported_runtimes,
    is_runtime_supported,
)
from polybugger_mcp.containers.models import (
    ContainerInfo,
    ContainerState,
    ExecResult,
    ProcessInfo,
)
from polybugger_mcp.models.container import (
    ContainerRuntime,
    ContainerTarget,
    PathMapping,
    SSHConfig,
)


class TestContainerModels:
    """Tests for container models."""

    def test_path_mapping_to_remote(self):
        """Test path mapping local to remote conversion."""
        mapping = PathMapping(
            local_root="/home/user/project",
            remote_root="/app",
        )
        assert mapping.to_remote("/home/user/project/src/main.py") == "/app/src/main.py"
        assert mapping.to_remote("/other/path") == "/other/path"

    def test_path_mapping_to_local(self):
        """Test path mapping remote to local conversion."""
        mapping = PathMapping(
            local_root="/home/user/project",
            remote_root="/app",
        )
        assert mapping.to_local("/app/src/main.py") == "/home/user/project/src/main.py"
        assert mapping.to_local("/other/path") == "/other/path"

    def test_container_target_identifier(self):
        """Test container target identifier property."""
        # Docker target
        docker_target = ContainerTarget(
            runtime=ContainerRuntime.DOCKER,
            container_name="my-container",
        )
        assert docker_target.identifier == "my-container"

        # Kubernetes target
        k8s_target = ContainerTarget(
            runtime=ContainerRuntime.KUBERNETES,
            namespace="production",
            pod_name="my-pod",
        )
        assert k8s_target.identifier == "production/my-pod"

        # Kubernetes target with container
        k8s_target_with_container = ContainerTarget(
            runtime=ContainerRuntime.KUBERNETES,
            namespace="production",
            pod_name="my-pod",
            pod_container="app",
        )
        assert k8s_target_with_container.identifier == "production/my-pod/app"

    def test_ssh_config(self):
        """Test SSH configuration model."""
        config = SSHConfig(
            host="remote.example.com",
            user="deploy",
            port=22,
            key_path="~/.ssh/id_rsa",
        )
        assert config.host == "remote.example.com"
        assert config.user == "deploy"
        assert config.port == 22


class TestContainerRuntimeFactory:
    """Tests for container runtime factory."""

    def test_supported_runtimes(self):
        """Test that all expected runtimes are registered."""
        runtimes = get_supported_runtimes()
        assert "docker" in runtimes
        assert "podman" in runtimes
        assert "kubernetes" in runtimes

    def test_is_runtime_supported(self):
        """Test runtime support checking."""
        assert is_runtime_supported("docker")
        assert is_runtime_supported("podman")
        assert is_runtime_supported("kubernetes")
        assert not is_runtime_supported("invalid")

    def test_create_docker_runtime(self):
        """Test Docker runtime creation."""
        runtime = create_runtime("docker")
        assert runtime.runtime_type == ContainerRuntime.DOCKER
        assert runtime.cli_command == "docker"

    def test_create_podman_runtime(self):
        """Test Podman runtime creation."""
        runtime = create_runtime("podman")
        assert runtime.runtime_type == ContainerRuntime.PODMAN
        assert runtime.cli_command == "podman"

    def test_create_kubernetes_runtime(self):
        """Test Kubernetes runtime creation."""
        runtime = create_runtime("kubernetes")
        assert runtime.runtime_type == ContainerRuntime.KUBERNETES
        assert runtime.cli_command == "kubectl"

    def test_create_invalid_runtime(self):
        """Test error on invalid runtime."""
        from polybugger_mcp.containers.factory import UnsupportedRuntimeError

        with pytest.raises(UnsupportedRuntimeError):
            create_runtime("invalid")


class TestContainerDataModels:
    """Tests for container data models."""

    def test_container_info_is_running(self):
        """Test ContainerInfo.is_running property."""
        running = ContainerInfo(
            id="abc123",
            name="test",
            state=ContainerState.RUNNING,
            image="python:3.11",
        )
        assert running.is_running

        stopped = ContainerInfo(
            id="abc123",
            name="test",
            state=ContainerState.EXITED,
            image="python:3.11",
        )
        assert not stopped.is_running

    def test_exec_result_success(self):
        """Test ExecResult.success property."""
        success = ExecResult(exit_code=0, stdout="output", stderr="")
        assert success.success

        failure = ExecResult(exit_code=1, stdout="", stderr="error")
        assert not failure.success

        timeout = ExecResult(exit_code=0, stdout="", stderr="", timed_out=True)
        assert not timeout.success

    def test_process_info_from_ps_line(self):
        """Test ProcessInfo.from_ps_line parsing."""
        # Valid Python process
        line = "root       1  0.0  0.5 12345 67890 ?  Ss  00:00  0:00 python app.py"
        proc = ProcessInfo.from_ps_line(line)
        assert proc is not None
        assert proc.pid == 1
        assert proc.user == "root"
        assert proc.is_python

        # Non-Python process
        line = "root       2  0.0  0.1 12345 67890 ?  Ss  00:00  0:00 nginx"
        proc = ProcessInfo.from_ps_line(line)
        assert proc is not None
        assert proc.pid == 2
        assert not proc.is_python

        # Invalid line
        assert ProcessInfo.from_ps_line("invalid") is None


class TestContainerExceptions:
    """Tests for container exceptions."""

    def test_container_not_found_error(self):
        """Test ContainerNotFoundError."""
        error = ContainerNotFoundError("my-container", "docker")
        assert "my-container" in error.message
        assert error.code == "CONTAINER_NOT_FOUND"
        assert error.details["container"] == "my-container"
        assert error.details["runtime"] == "docker"

    def test_container_security_error(self):
        """Test ContainerSecurityError with instructions."""
        error = ContainerSecurityError(
            "ptrace not permitted",
            instructions=["Add SYS_PTRACE capability", "Run with --privileged"],
        )
        assert error.code == "CONTAINER_SECURITY_ERROR"
        assert len(error.instructions) == 2
