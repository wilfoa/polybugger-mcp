"""Application configuration using Pydantic Settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="PYTHON_DEBUGGER_MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Server settings
    host: str = "127.0.0.1"
    port: int = 5679
    debug: bool = False
    log_level: str = "INFO"

    # Session limits
    max_sessions: int = Field(default=10, ge=1, le=100)
    session_timeout_seconds: int = Field(default=3600, ge=60)  # 1 hour default
    session_max_lifetime_seconds: int = Field(default=14400, ge=300)  # 4 hours max

    # Output buffer
    output_buffer_max_bytes: int = Field(
        default=50 * 1024 * 1024,  # 50MB
        ge=1024 * 1024,  # Min 1MB
        le=500 * 1024 * 1024,  # Max 500MB
    )

    # Persistence
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".python-debugger-mcp")

    # DAP settings
    dap_timeout_seconds: float = Field(default=30.0, ge=1.0, le=300.0)
    dap_launch_timeout_seconds: float = Field(default=60.0, ge=5.0, le=600.0)

    # Python settings
    default_python_path: str | None = None

    @property
    def breakpoints_dir(self) -> Path:
        """Directory for breakpoint storage."""
        return self.data_dir / "breakpoints"

    @property
    def sessions_dir(self) -> Path:
        """Directory for session recovery data."""
        return self.data_dir / "sessions"

    @property
    def config_file(self) -> Path:
        """Path to config file."""
        return self.data_dir / "config.json"

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.breakpoints_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
