"""Debug adapters - DAP protocol integration for multiple languages.

This package provides:
- DebugAdapter: Abstract base class for language-specific adapters
- DAPClient: Low-level DAP protocol client
- AdapterFactory: Factory for creating language-specific adapters
- Language-specific adapters (debugpy for Python, etc.)
"""

from polybugger_mcp.adapters.base import (
    AttachConfig,
    DebugAdapter,
    Language,
    LaunchConfig,
)
from polybugger_mcp.adapters.dap_client import DAPClient
from polybugger_mcp.adapters.debugpy_adapter import DebugpyAdapter
from polybugger_mcp.adapters.factory import (
    UnsupportedLanguageError,
    create_adapter,
    get_supported_languages,
    is_language_supported,
    register_adapter,
)

__all__ = [
    # Base classes
    "DebugAdapter",
    "DAPClient",
    # Config types
    "LaunchConfig",
    "AttachConfig",
    "Language",
    # Factory
    "create_adapter",
    "register_adapter",
    "get_supported_languages",
    "is_language_supported",
    "UnsupportedLanguageError",
    # Adapters
    "DebugpyAdapter",
]
