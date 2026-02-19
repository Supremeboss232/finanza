"""App-local config shim

This module re-exports the project-level `settings` object so modules
inside the `app` package can use `from .config import settings`.

Keeping the settings in the project root (`config.py`) avoids duplicating
configuration logic; this shim simply exposes it as `app.config`.
"""
try:
    from config import settings  # project-level config.py
except Exception:
    # If importing the project-level config fails (for example in some test
    # runners or packaging scenarios), create a minimal fallback so imports
    # don't crash immediately. This fallback should be overridden by the
    # real `config.settings` in normal runs.
    from pydantic_settings import BaseSettings

    class _FallbackSettings(BaseSettings):
        DATABASE_URL: str = ""
        ADMIN_EMAIL: str = "admin@example.com"
        ADMIN_PASSWORD: str = "admin"
        SECRET_KEY: str = ""
        ALGORITHM: str = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    settings = _FallbackSettings()

__all__ = ["settings"]
