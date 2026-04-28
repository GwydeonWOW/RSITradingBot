"""Application configuration via pydantic-settings."""

from __future__ import annotations

from typing import List

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration loaded from environment variables or .env file."""

    # Application
    app_name: str = "RSITradingBot"
    app_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "rsi_trading"
    postgres_user: str = "rsi_user"
    postgres_password: str = "rsi_password"
    database_url: str = Field(
        default="postgresql+asyncpg://rsi_user:rsi_password@localhost:5432/rsi_trading"
    )

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0
    redis_url: str = "redis://localhost:6379/0"

    # ClickHouse
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 9000
    clickhouse_http_port: int = 8123
    clickhouse_db: str = "market_data"
    clickhouse_user: str = "default"
    clickhouse_password: str = ""

    # Security
    secret_key: str = Field(default="", alias="SECRET_KEY")
    encryption_key: str = ""  # 32-byte hex string for AES-256-GCM wallet key encryption

    # Hyperliquid (global venue URLs only; per-user creds stored in wallets table)
    hyperliquid_api_url: str = "https://api.hyperliquid.xyz"
    hyperliquid_ws_url: str = "wss://api.hyperliquid.xyz/ws"
    hyperliquid_network: str = "mainnet"

    # RSI Strategy Parameters
    rsi_period: int = 14
    rsi_regime_timeframe: str = "4h"
    rsi_regime_bullish_threshold: float = 55.0
    rsi_regime_bearish_threshold: float = 45.0
    rsi_signal_timeframe: str = "1h"
    rsi_signal_long_pullback_low: float = 40.0
    rsi_signal_long_pullback_high: float = 48.0
    rsi_signal_long_reclaim: float = 50.0
    rsi_signal_short_bounce_low: float = 52.0
    rsi_signal_short_bounce_high: float = 60.0
    rsi_signal_short_lose: float = 50.0
    rsi_execution_timeframe: str = "15m"
    rsi_exit_partial_r: float = 1.5
    rsi_exit_breakeven_r: float = 1.0
    rsi_exit_max_hours: int = 36

    # Risk Parameters
    risk_per_trade_min: float = 0.0025
    risk_per_trade_max: float = 0.0075
    max_leverage: int = 3
    max_total_exposure_pct: float = 0.30
    universe: str = "BTC,ETH,SOL"

    # z.ai Integration
    zai_api_key: str = ""
    zai_api_url: str = "https://api.z.ai/v1"

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        if self.app_env == "production" and not self.secret_key:
            raise ValueError("SECRET_KEY must be set in production")
        return self

    @property
    def universe_list(self) -> List[str]:
        """Return the trading universe as a list of symbols."""
        return [s.strip() for s in self.universe.split(",")]

    @property
    def cors_origins_list(self) -> List[str]:
        """Return CORS origins as a list."""
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
