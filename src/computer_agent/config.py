"""Portable user configuration for Interly."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Values the agent can read from environment variables or .env."""

    model_config = SettingsConfigDict(extra="ignore")

    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-20b"


def config_file() -> Path:
    """Return the per-user configuration path, with a test/development override."""
    override = os.environ.get("INTERLY_CONFIG_DIR")
    if override:
        return Path(override) / ".env"
    app_data = os.environ.get("APPDATA")
    base = Path(app_data) if app_data else Path.home() / ".config"
    return base / "Interly" / ".env"


def load_settings() -> Settings:
    """Load user configuration, while retaining local .env support for development."""
    return Settings(_env_file=(config_file(), Path.cwd() / ".env"))


def memory_file() -> Path:
    """Return the per-user memory storage path."""
    return config_file().parent / "memory.json"


def save_api_key(api_key: str) -> Path:
    """Store the Groq key in the current user's private Interly configuration directory."""
    path = config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"GROQ_API_KEY={api_key}\n", encoding="utf-8")
    return path
