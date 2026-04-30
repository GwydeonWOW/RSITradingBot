"""Bot execution engine — runs the RSI strategy automatically.

Fetches candle data from Hyperliquid, evaluates the strategy through
the signal detector, and places real orders when signals are confirmed.
Also manages exits (stop loss, R-targets, max holding time).
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.crypto import decrypt_private_key
from app.core.regime import Regime, detect_regime
from app.core.risk_manager import RiskManager
from app.core.rsi_engine import compute_rsi
from app.core.signal import SignalDetector, SignalStage, SignalType
from app.dependencies import get_db_ctx
from app.execution.signer import HyperliquidSigner
from app.models.bot_state import BotState
from app.models.bot_log import BotLog
from app.models.order import Order, OrderSide, OrderStatus, OrderType
from app.models.position import Position, PositionSide, PositionStatus
from app.models.user_settings import UserSettings
from app.models.wallet import Wallet

logger = logging.getLogger(__name__)

# Asset index cache: {"BTC": 0, "ETH": 1, ...}
_asset_index_cache: Dict[str, int] = {}


class BotEngine:
    """Background bot engine that runs the RSI strategy for all users."""

    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._detectors: Dict[uuid.UUID, SignalDetector] = {}
        self._running = False
        self._enabled = False  # must be explicitly started

    @property
    def running(self) -> bool:
        return self._running

    async def start(self) -> None:
        """Called on app startup — loads asset indices but doesn't auto-start the loop."""
        await _load_asset_indices()
        logger.info("BotEngine initialized (asset indices loaded)")

    async def start_bot(self) -> None:
        """Start the trading loop (user action)."""
        if self._running:
            return
        self._enabled = True
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("BotEngine trading loop started")

    async def stop_bot(self) -> None:
        """Stop the trading loop (user action)."""
        self._enabled = False
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("BotEngine trading loop stopped")

    async def shutdown(self) -> None:
        """Called on app shutdown."""
        await self.stop_bot()

    async def _run_loop(self) -> None:
        while self._running:
            try:
                async with get_db_ctx() as db:
                    await self._tick(db)
            except Exception as exc:
                logger.error("BotEngine tick error: %s", exc)
            await asyncio.sleep(60)

    async def _tick(self, db: AsyncSession) -> None:
        # Find all users with active wallets
        result = await db.execute(
            select(Wallet).where(Wallet.is_active.is_(True))
        )
        wallets = result.scalars().all()

        # Group by user_id
        users_seen: set[uuid.UUID] = set()
        for wallet in wallets:
            if wallet.user_id in users_seen:
                continue
            users_seen.add(wallet.user_id)
            try:
                await self._run_cycle(wallet.user_id, wallet, db)
            except Exception as exc:
                logger.error("BotEngine cycle error for user %s: %s", wallet.user_id, exc)
                await _save_error(db, wallet.user_id, str(exc)[:500])

    async def _run_cycle(
        self,
        user_id: uuid.UUID,
        wallet: Wallet,
        db: AsyncSession,
    ) -> None:
        # Load user settings
        settings_result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        user_settings = settings_result.scalar_one_or_none()
        if not user_settings:
            await _log(db, user_id, level="error",
                message="No user settings found — visit Settings page first", symbol="BTC")
            return

        symbol = user_settings.universe.split(",")[0].strip()

        # Load or create bot state
        state = await _load_bot_state(db, user_id)

        # Recover detector from state
        if user_id not in self._detectors:
            detector = _build_detector(user_settings)
            _restore_detector(detector, state)
            self._detectors[user_id] = detector
        detector = self._detectors[user_id]

        # Fetch candles
        closes_4h = await _fetch_candles(symbol, "4h", 120)
        closes_1h = await _fetch_candles(symbol, "1h", 48)
        closes_15m = await _fetch_candles(symbol, "15m", 4)

        if not closes_4h or not closes_1h:
            logger.warning("No candle data for %s", symbol)
            return

        price = closes_15m[-1] if closes_15m else closes_1h[-1]

        # Compute RSI
        rsi_4h_result = compute_rsi(closes_4h, user_settings.rsi_period)
        rsi_1h_result = compute_rsi(closes_1h, user_settings.rsi_period)

        if rsi_4h_result is None or rsi_1h_result is None:
            return

        rsi_4h = rsi_4h_result.rsi
        rsi_1h = rsi_1h_result.rsi
        regime = detect_regime(rsi_4h, user_settings.rsi_regime_bullish_threshold, user_settings.rsi_regime_bearish_threshold)

        # Feed 1H bars through detector (only the last bar)
        signal = detector.on_1h_bar(regime=regime, rsi_1h=rsi_1h, price=price, rsi_4h=rsi_4h)

        # Check for trigger → confirm on 15m
        if signal.stage == SignalStage.TRIGGER and closes_15m:
            is_bullish = len(closes_15m) >= 2 and closes_15m[-1] >= closes_15m[-2]
            signal = detector.confirm_on_15m_close(
                price=price, rsi_1h=rsi_1h, rsi_4h=rsi_4h, is_bullish_close=is_bullish,
            )

        # Update state
        state.last_regime = regime.value
        state.last_rsi_4h = rsi_4h
        state.last_rsi_1h = rsi_1h
        state.last_price = price
        state.last_signal_type = signal.signal_type.value
        state.last_eval_at = datetime.now(timezone.utc)

        # Persist detector state
        _save_detector_state(state, detector)

        # Log cycle decision
        await _log(
            db, user_id, level="info",
            message=f"Regime={regime.value} RSI4H={rsi_4h:.1f} RSI1H={rsi_1h:.1f} Price=${price:.0f} Stage={detector.state.stage.value} Signal={detector.state.signal_type.value}",
            symbol=symbol, regime=regime.value, rsi_4h=rsi_4h, rsi_1h=rsi_1h,
            price=price, signal_stage=detector.state.stage.value, signal_type=detector.state.signal_type.value,
        )

        # If confirmed signal → place order
        if signal.stage == SignalStage.CONFIRMED and signal.signal_type != SignalType.NONE:
            # Check no existing open position
            existing = await _get_open_position(db, user_id, symbol)
            if existing is None:
                await _log(
                    db, user_id, level="signal",
                    message=f"SIGNAL CONFIRMED: {signal.signal_type.value.upper()} at ${price:.0f} — placing order",
                    symbol=symbol, regime=regime.value, rsi_4h=rsi_4h, rsi_1h=rsi_1h,
                    price=price, signal_stage="confirmed", signal_type=signal.signal_type.value,
                )
                await self._place_entry(
                    db=db, wallet=wallet, user_settings=user_settings,
                    symbol=symbol, signal=signal, price=price,
                    rsi_4h=rsi_4h, rsi_1h=rsi_1h,
                )
            else:
                logger.info("Already have open position for %s %s, skipping signal", user_id, symbol)

        # Check exits
        await self._check_exits(db, wallet, user_id, user_settings, symbol)

        db.add(state)
        await db.flush()
        logger.info(
            "BotEngine cycle user=%s symbol=%s regime=%s rsi4h=%.1f rsi1h=%.1f stage=%s signal=%s",
            user_id, symbol, regime.value, rsi_4h, rsi_1h,
            detector.state.stage.value, detector.state.signal_type.value,
        )

    async def _place_entry(
        self,
        db: AsyncSession,
        wallet: Wallet,
        user_settings: UserSettings,
        symbol: str,
        signal: Any,
        price: float,
        rsi_4h: float,
        rsi_1h: float,
    ) -> None:
        direction = signal.signal_type
        stop_distance_pct = 0.02
        if direction == SignalType.LONG:
            stop_price = price * (1 - stop_distance_pct)
        else:
            stop_price = price * (1 + stop_distance_pct)

        # Position sizing
        rm = RiskManager(
            equity=10000.0,  # TODO: use real equity from balance
            max_leverage=user_settings.max_leverage,
        )
        sizing = rm.calculate_position_size(
            entry_price=price,
            stop_price=stop_price,
            direction=direction,
            current_exposure=0.0,
        )

        if sizing.size_notional <= 0:
            logger.warning("Position size is 0, skipping order")
            return

        side = "buy" if direction == SignalType.LONG else "sell"
        size = sizing.size_contracts if sizing.size_contracts > 0 else round(sizing.size_notional / price, 6)

        # Submit order to Hyperliquid
        result = await _submit_market_order(
            wallet=wallet,
            symbol=symbol,
            side=side,
            size=size,
            leverage=user_settings.max_leverage,
        )

        venue_order_id = result.get("response", {}).get("data", {}).get("statuses", [{}])[0].get("resting", {}).get("oid") if result.get("status") == "ok" else None

        # Save order to DB
        order = Order(
            user_id=wallet.user_id,
            symbol=symbol,
            side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
            order_type=OrderType.MARKET,
            status=OrderStatus.ACCEPTED if venue_order_id else OrderStatus.INTENT,
            venue_order_id=str(venue_order_id) if venue_order_id else None,
            price=price,
            size=size,
            leverage=user_settings.max_leverage,
            stop_loss=stop_price,
            risk_pct=sizing.risk_pct,
            signal_strength=signal.strength,
            regime=signal.regime.value,
            rsi_1h=rsi_1h,
            rsi_4h=rsi_4h,
        )
        db.add(order)

        # Save position to DB
        position = Position(
            user_id=wallet.user_id,
            order_id=order.id,
            symbol=symbol,
            side=PositionSide.LONG if direction == SignalType.LONG else PositionSide.SHORT,
            status=PositionStatus.OPEN,
            size=size,
            entry_price=price,
            stop_loss=stop_price,
            leverage=user_settings.max_leverage,
        )
        db.add(position)
        await db.flush()

        logger.info(
            "Placed %s %s order: size=%s price=%.2f stop=%.2f venue_oid=%s",
            side, symbol, size, price, stop_price, venue_order_id,
        )

    async def _check_exits(
        self,
        db: AsyncSession,
        wallet: Wallet,
        user_id: uuid.UUID,
        user_settings: UserSettings,
        symbol: str,
    ) -> None:
        position = await _get_open_position(db, user_id, symbol)
        if position is None:
            return

        # Fetch current price
        mid_prices = await _fetch_mid_price(symbol)
        if not mid_prices:
            return
        current_price = mid_prices

        entry = position.entry_price
        stop = position.stop_loss or 0
        side = position.side.value
        partial_r = user_settings.rsi_exit_partial_r
        be_r = user_settings.rsi_exit_breakeven_r
        max_hours = user_settings.rsi_exit_max_hours

        # Calculate R-multiple
        risk = abs(entry - stop) if stop > 0 else entry * 0.02
        if risk == 0:
            return

        if side == "long":
            pnl_distance = current_price - entry
        else:
            pnl_distance = entry - current_price

        r_multiple = pnl_distance / risk

        # Check stop loss hit
        stop_hit = (side == "long" and current_price <= stop) or (side == "short" and current_price >= stop)
        if stop_hit:
            await self._close_position(db, wallet, position, current_price, "stop_loss")
            return

        # Check max hours
        if position.opened_at:
            hours_held = (datetime.now(timezone.utc) - position.opened_at).total_seconds() / 3600
            if hours_held >= max_hours:
                await self._close_position(db, wallet, position, current_price, "max_hours")
                return

        # Check partial exit at partial_r
        if r_multiple >= partial_r and not position.partial_exited:
            close_size = position.size / 2
            await self._partial_close(db, wallet, position, current_price, close_size)
            # Move stop to breakeven
            position.stop_loss = entry
            position.partial_exited = True
            await db.flush()
            return

        # Check move stop to breakeven at be_r
        if r_multiple >= be_r and not position.be_moved:
            position.stop_loss = entry
            position.be_moved = True
            await db.flush()

    async def _close_position(
        self, db: AsyncSession, wallet: Wallet, position: Position, current_price: float, reason: str,
    ) -> None:
        side = "sell" if position.side == PositionSide.LONG else "buy"
        result = await _submit_market_order(
            wallet=wallet, symbol=position.symbol, side=side, size=position.size, leverage=position.leverage,
        )
        position.status = PositionStatus.CLOSED
        position.exit_price = current_price
        position.closed_at = datetime.now(timezone.utc)
        # Calculate realized PnL before logging
        if position.entry_price > 0:
            if position.side == PositionSide.LONG:
                position.realized_pnl = (current_price - position.entry_price) * position.size
            else:
                position.realized_pnl = (position.entry_price - current_price) * position.size
        await _log(db, wallet.user_id, level="exit",
            message=f"EXIT {position.symbol} {position.side.value}: reason={reason} price=${current_price:.0f} pnl=${position.realized_pnl:.2f}",
            symbol=position.symbol, price=current_price)
        await db.flush()
        logger.info("Closed %s position %s: reason=%s price=%.2f", position.symbol, position.id, reason, current_price)

    async def _partial_close(
        self, db: AsyncSession, wallet: Wallet, position: Position, current_price: float, close_size: float,
    ) -> None:
        side = "sell" if position.side == PositionSide.LONG else "buy"
        await _submit_market_order(
            wallet=wallet, symbol=position.symbol, side=side, size=close_size, leverage=position.leverage,
        )
        position.size -= close_size
        position.status = PositionStatus.PARTIALLY_CLOSED
        await db.flush()
        logger.info("Partial close %s: size=%.6f price=%.2f", position.symbol, close_size, current_price)


# ─── Helper functions ───────────────────────────────────────────


async def _log(
    db: AsyncSession,
    user_id: uuid.UUID,
    level: str,
    message: str,
    symbol: str = "BTC",
    regime: Optional[str] = None,
    rsi_4h: Optional[float] = None,
    rsi_1h: Optional[float] = None,
    price: Optional[float] = None,
    signal_stage: Optional[str] = None,
    signal_type: Optional[str] = None,
) -> None:
    entry = BotLog(
        user_id=user_id,
        level=level,
        message=message,
        symbol=symbol,
        regime=regime,
        rsi_4h=rsi_4h,
        rsi_1h=rsi_1h,
        price=price,
        signal_stage=signal_stage,
        signal_type=signal_type,
    )
    db.add(entry)
    try:
        await db.flush()
    except Exception:
        pass


async def _load_asset_indices() -> None:
    global _asset_index_cache
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.hyperliquid_api_url}/info",
                json={"type": "meta"},
            )
            resp.raise_for_status()
            data = resp.json()
            universe = data.get("universe", [])
            for i, asset in enumerate(universe):
                _asset_index_cache[asset["name"]] = i
            logger.info("Loaded %d asset indices", len(_asset_index_cache))
    except Exception as exc:
        logger.error("Failed to load asset indices: %s", exc)


def _get_asset_index(symbol: str) -> int:
    if symbol in _asset_index_cache:
        return _asset_index_cache[symbol]
    raise ValueError(f"Unknown symbol: {symbol}")


async def _fetch_candles(coin: str, interval: str, hours_back: int) -> List[float]:
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - (hours_back * 60 * 60 * 1000)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.hyperliquid_api_url}/info",
                json={"type": "candleSnapshot", "req": {"coin": coin, "interval": interval, "startTime": start_ms, "endTime": now_ms}},
            )
            resp.raise_for_status()
            candles = resp.json()
        return [float(c["c"]) for c in candles]
    except Exception as exc:
        logger.error("Failed to fetch %s %s candles: %s", coin, interval, exc)
        return []


async def _fetch_mid_price(symbol: str) -> Optional[float]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.hyperliquid_api_url}/info",
                json={"type": "allMids"},
            )
            resp.raise_for_status()
            mids = resp.json()
            price_str = mids.get(symbol)
            return float(price_str) if price_str else None
    except Exception as exc:
        logger.error("Failed to fetch mid price for %s: %s", symbol, exc)
        return None


async def _submit_market_order(
    wallet: Wallet,
    symbol: str,
    side: str,
    size: float,
    leverage: int = 3,
) -> Dict[str, Any]:
    private_key = decrypt_private_key(wallet.encrypted_private_key, settings.encryption_key)
    signer = HyperliquidSigner(
        private_key=private_key,
        account_address=wallet.agent_address,
        network=settings.hyperliquid_network,
    )

    # Set leverage first
    leverage_action = signer.sign_modify_leverage(symbol, leverage, is_cross=True)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{settings.hyperliquid_api_url}/exchange",
                json=leverage_action.payload,
            )
    except Exception:
        pass  # leverage setting is idempotent, ignore errors

    # Sign and submit order
    asset_idx = _get_asset_index(symbol)
    signed = signer.sign_order(
        symbol=symbol, side=side, size=size, price=None, order_type="Ioc",
    )

    # Override asset index in the action
    signed.action["orders"][0]["a"] = asset_idx

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{settings.hyperliquid_api_url}/exchange",
            json=signed.payload,
        )
        resp.raise_for_status()
        result = resp.json()

    logger.info("Hyperliquid order response: %s", str(result)[:500])
    return result


def _build_detector(user_settings: UserSettings) -> SignalDetector:
    return SignalDetector(
        long_pullback_low=user_settings.rsi_signal_long_pullback_low,
        long_pullback_high=user_settings.rsi_signal_long_pullback_high,
        long_reclaim=user_settings.rsi_signal_long_reclaim,
        short_bounce_low=user_settings.rsi_signal_short_bounce_low,
        short_bounce_high=user_settings.rsi_signal_short_bounce_high,
        short_lose=user_settings.rsi_signal_short_lose,
    )


def _restore_detector(detector: SignalDetector, state: BotState) -> None:
    s = detector.state
    s.regime = Regime(state.regime) if state.regime else Regime.NEUTRAL
    s.stage = SignalStage(state.signal_stage) if state.signal_stage else SignalStage.INACTIVE
    s.signal_type = SignalType(state.signal_type) if state.signal_type else SignalType.NONE
    s.rsi_at_setup = state.rsi_at_setup
    s.bars_in_setup = state.bars_in_setup
    s.rsi_extreme_in_zone = state.rsi_extreme_in_zone


def _save_detector_state(state: BotState, detector: SignalDetector) -> None:
    s = detector.state
    state.regime = s.regime.value
    state.signal_stage = s.stage.value
    state.signal_type = s.signal_type.value
    state.rsi_at_setup = s.rsi_at_setup
    state.bars_in_setup = s.bars_in_setup
    state.rsi_extreme_in_zone = s.rsi_extreme_in_zone


async def _load_bot_state(db: AsyncSession, user_id: uuid.UUID) -> BotState:
    result = await db.execute(select(BotState).where(BotState.user_id == user_id))
    state = result.scalar_one_or_none()
    if state is None:
        state = BotState(user_id=user_id)
        db.add(state)
        await db.flush()
    return state


async def _save_error(db: AsyncSession, user_id: uuid.UUID, error: str) -> None:
    try:
        state = await _load_bot_state(db, user_id)
        state.last_error = error
        state.last_eval_at = datetime.now(timezone.utc)
        db.add(state)
        await db.flush()
    except Exception:
        pass


async def _get_open_position(db: AsyncSession, user_id: uuid.UUID, symbol: str) -> Optional[Position]:
    result = await db.execute(
        select(Position).where(
            Position.user_id == user_id,
            Position.symbol == symbol,
            Position.status.in_([PositionStatus.OPEN, PositionStatus.PARTIALLY_CLOSED]),
        )
    )
    return result.scalar_one_or_none()


def get_bot_status() -> Dict[str, Any]:
    return {
        "running": BotEngine._instance._running if hasattr(BotEngine, "_instance") else False,
        "asset_indices_loaded": len(_asset_index_cache),
    }
