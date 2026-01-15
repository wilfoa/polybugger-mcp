"""Debug adapter factory.

This module provides factory functions for creating language-specific
debug adapters based on the target language.
"""

from collections.abc import Callable, Coroutine
from typing import Any

from pybugger_mcp.adapters.base import DebugAdapter, Language
from pybugger_mcp.core.exceptions import DebugRelayError
from pybugger_mcp.models.events import EventType


class UnsupportedLanguageError(DebugRelayError):
    """Raised when a language is not supported."""

    def __init__(self, language: str):
        super().__init__(
            code="UNSUPPORTED_LANGUAGE",
            message=f"Language '{language}' is not supported",
            details={"language": language, "supported": [l.value for l in Language]},
        )


# Registry of adapter classes by language
_ADAPTER_REGISTRY: dict[Language, type[DebugAdapter]] = {}


def register_adapter(language: Language) -> Callable[[type[DebugAdapter]], type[DebugAdapter]]:
    """Decorator to register an adapter class for a language.

    Usage:
        @register_adapter(Language.PYTHON)
        class DebugpyAdapter(DebugAdapter):
            ...
    """

    def decorator(cls: type[DebugAdapter]) -> type[DebugAdapter]:
        _ADAPTER_REGISTRY[language] = cls
        return cls

    return decorator


def create_adapter(
    language: str | Language,
    session_id: str,
    output_callback: Callable[[str, str], Any] | None = None,
    event_callback: Callable[[EventType, dict[str, Any]], Coroutine[Any, Any, None]] | None = None,
) -> DebugAdapter:
    """Create a debug adapter for the specified language.

    Args:
        language: Target programming language
        session_id: Unique session identifier
        output_callback: Callback for program output
        event_callback: Async callback for debug events

    Returns:
        Language-specific debug adapter instance

    Raises:
        UnsupportedLanguageError: If language is not supported
    """
    # Normalize language to enum
    if isinstance(language, str):
        try:
            lang = Language(language.lower())
        except ValueError:
            raise UnsupportedLanguageError(language)
    else:
        lang = language

    # Get adapter class from registry
    adapter_class = _ADAPTER_REGISTRY.get(lang)
    if adapter_class is None:
        raise UnsupportedLanguageError(lang.value)

    return adapter_class(
        session_id=session_id,
        output_callback=output_callback,
        event_callback=event_callback,
    )


def get_supported_languages() -> list[str]:
    """Get list of supported language identifiers.

    Returns:
        List of language strings that have registered adapters
    """
    return [lang.value for lang in _ADAPTER_REGISTRY.keys()]


def is_language_supported(language: str) -> bool:
    """Check if a language is supported.

    Args:
        language: Language identifier

    Returns:
        True if an adapter is registered for the language
    """
    try:
        lang = Language(language.lower())
        return lang in _ADAPTER_REGISTRY
    except ValueError:
        return False


# =============================================================================
# Auto-register adapters on import
# =============================================================================


def _register_builtin_adapters() -> None:
    """Register built-in adapters.

    This is called automatically when the module is imported.
    Each adapter module should use the @register_adapter decorator.
    """
    # Import adapter modules to trigger registration
    # pylint: disable=import-outside-toplevel,unused-import
    try:
        from pybugger_mcp.adapters import debugpy_adapter  # noqa: F401
    except ImportError:
        pass

    try:
        from pybugger_mcp.adapters import node_adapter  # noqa: F401
    except ImportError:
        pass

    # Future adapters:
    # from pybugger_mcp.adapters import delve_adapter  # noqa: F401
    # from pybugger_mcp.adapters import lldb_adapter  # noqa: F401


_register_builtin_adapters()
