"""Configuration classes for PyDBA."""

from __future__ import annotations

import os
import secrets


class Config:
    """Base configuration."""

    SECRET_KEY: str = os.environ.get("PYDBA_SECRET_KEY") or secrets.token_hex(32)
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    # Limit query result pages to keep memory usage low
    PAGE_SIZE: int = int(os.environ.get("PYDBA_PAGE_SIZE", "50"))
    # Maximum rows returned from a raw SQL query
    MAX_QUERY_ROWS: int = int(os.environ.get("PYDBA_MAX_QUERY_ROWS", "1000"))


class DevelopmentConfig(Config):
    DEBUG: bool = True
    TESTING: bool = False


class TestingConfig(Config):
    TESTING: bool = True
    # Use a fixed key so tests are reproducible
    SECRET_KEY: str = "test-secret-key"
    WTF_CSRF_ENABLED: bool = False


class ProductionConfig(Config):
    DEBUG: bool = False
    TESTING: bool = False
    SESSION_COOKIE_SECURE: bool = True


_CONFIG_MAP: dict[str, type[Config]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(env: str | None = None) -> Config:
    """Return the appropriate Config instance based on *env* or FLASK_ENV."""
    env = env or os.environ.get("FLASK_ENV", "development")
    cls = _CONFIG_MAP.get(env, DevelopmentConfig)
    return cls()
