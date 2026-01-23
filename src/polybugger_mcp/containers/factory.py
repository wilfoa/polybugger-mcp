"""Container runtime factory.

This module provides factory functions for creating container runtime
adapters based on the runtime type (Docker, Podman, Kubernetes).
"""

from collections.abc import Callable
from typing import TypeVar

from polybugger_mcp.containers.base import ContainerError, ContainerRuntimeAdapter
from polybugger_mcp.models.container import ContainerRuntime, ContainerTarget

T = TypeVar("T", bound=ContainerRuntimeAdapter)


class UnsupportedRuntimeError(ContainerError):
    """Raised when a container runtime is not supported."""

    def __init__(self, runtime: str):
        super().__init__(
            f"Container runtime '{runtime}' is not supported",
            code="UNSUPPORTED_RUNTIME",
            details={
                "runtime": runtime,
                "supported": [r.value for r in ContainerRuntime],
            },
        )


# Registry of runtime adapters
_RUNTIME_REGISTRY: dict[ContainerRuntime, type[ContainerRuntimeAdapter]] = {}


def register_runtime(
    runtime: ContainerRuntime,
) -> Callable[[type[T]], type[T]]:
    """Decorator to register a runtime adapter class.

    Usage:
        @register_runtime(ContainerRuntime.DOCKER)
        class DockerRuntime(ContainerRuntimeAdapter):
            ...
    """

    def decorator(cls: type[T]) -> type[T]:
        _RUNTIME_REGISTRY[runtime] = cls
        return cls

    return decorator


def create_runtime(
    runtime: str | ContainerRuntime,
    **kwargs: str,
) -> ContainerRuntimeAdapter:
    """Create a container runtime adapter.

    Args:
        runtime: Runtime type (docker, podman, kubernetes)
        **kwargs: Additional arguments for the runtime constructor

    Returns:
        Container runtime adapter instance

    Raises:
        UnsupportedRuntimeError: If runtime is not supported
    """
    # Normalize to enum
    if isinstance(runtime, str):
        try:
            runtime_enum = ContainerRuntime(runtime.lower())
        except ValueError:
            raise UnsupportedRuntimeError(runtime)
    else:
        runtime_enum = runtime

    # Get adapter class
    adapter_class = _RUNTIME_REGISTRY.get(runtime_enum)
    if adapter_class is None:
        raise UnsupportedRuntimeError(runtime_enum.value)

    return adapter_class(**kwargs)


def create_runtime_for_target(target: ContainerTarget, **kwargs: str) -> ContainerRuntimeAdapter:
    """Create a runtime adapter for a specific container target.

    Args:
        target: Container target specification
        **kwargs: Additional arguments for the runtime constructor

    Returns:
        Appropriate container runtime adapter
    """
    return create_runtime(target.runtime, **kwargs)


def get_supported_runtimes() -> list[str]:
    """Get list of supported runtime identifiers.

    Returns:
        List of runtime strings that have registered adapters
    """
    return [rt.value for rt in _RUNTIME_REGISTRY]


def is_runtime_supported(runtime: str) -> bool:
    """Check if a runtime is supported.

    Args:
        runtime: Runtime identifier

    Returns:
        True if an adapter is registered for the runtime
    """
    try:
        runtime_enum = ContainerRuntime(runtime.lower())
        return runtime_enum in _RUNTIME_REGISTRY
    except ValueError:
        return False


# =============================================================================
# Auto-register runtimes on import
# =============================================================================


def _register_builtin_runtimes() -> None:
    """Register built-in runtime adapters.

    This is called automatically when the module is imported.
    """
    # Import runtime modules to trigger registration
    # pylint: disable=import-outside-toplevel,unused-import

    # Docker
    try:
        from polybugger_mcp.containers.docker import DockerRuntime

        _RUNTIME_REGISTRY[ContainerRuntime.DOCKER] = DockerRuntime
    except ImportError:
        pass

    # Podman (uses Docker adapter with CLI override)
    try:
        from polybugger_mcp.containers.podman import PodmanRuntime

        _RUNTIME_REGISTRY[ContainerRuntime.PODMAN] = PodmanRuntime
    except ImportError:
        # Podman not implemented yet, can use Docker with override
        pass

    # Kubernetes
    try:
        from polybugger_mcp.containers.kubernetes import KubernetesRuntime

        _RUNTIME_REGISTRY[ContainerRuntime.KUBERNETES] = KubernetesRuntime
    except ImportError:
        pass


_register_builtin_runtimes()
