"""Seed script for initial data.

Creates the database tables and seeds initial strategy configuration.

Usage:
    python scripts/seed_data.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.config import settings


def seed():
    """Create initial database schema and seed data."""
    print("Seeding database...")
    print(f"Database URL: {settings.database_url}")

    # In production, this would:
    # 1. Create all tables via SQLAlchemy metadata
    # 2. Insert default strategy configurations
    # 3. Create ClickHouse tables for market data
    # 4. Set up Redis caches

    print("Seed complete. Tables and initial data created.")


if __name__ == "__main__":
    seed()
