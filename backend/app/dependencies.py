"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Generator

from app.config import settings


def get_settings():
    """Provide application settings as a dependency."""
    return settings
