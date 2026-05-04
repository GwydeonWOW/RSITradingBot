"""Bot execution engine — runs the RSI strategy automatically.

Fetches candle data from Hyperliquid, evaluates the strategy through
the signal detector, and places real orders when signals are confirmed.
Also manages exits (stop loss, R-targets, max holding time).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
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
_sz_decimals_cache: Dict[str, int] = {}

_PERSIST_FILE = Path("/tmp/bot_enabled.json")


def _persist_enabled(enabled: bool) -> None:
    try:
        _PERSIST_FILE.write_text(json.dumps({"enabled": enabled}))
    except Exception:
        pass


def _load_persisted_enabled() -> bool:
    try:
        return json.loads(_PERSIST_FILE.read_text()).get("enabled", False)
    except Exception:
        return False


class BotEngine:
    """Background bot engine that runs the RSI strategy for all users."""

    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._detectors: Dict[tuple, SignalDetector] = {}  # (user_id, symbol) → detector
        self._running = False

    @property
    def running(self) -> bool:
        return self._running and self._task is not None and not self._task.done()

    async def start(self) -> None:
        """Called on app startup. Resumes the bot if it was running before restart."""
        await _load_asset_indices()
        if _load_persisted_enabled():
            logger.info("BotEngine: resuming (was enabled before restart)")
            await self.start_bot()
        else:
            logger.info("BotEngine initialized (stopped)")

    async def start_bot(self) -> None:
        """Start the trading loop."""
        if self.running:
            return
        self._running = True
        _persist_enabled(True)
        self._task = asyncio.create_task(self._run_loop())
        logger.info("BotEngine trading loop started")

    async def stop_bot(self) -> None:
        """Stop the trading loop."""
        self._running = False
        _persist_enabled(False)
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
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
                try:
                    await db.rollback()
                except Exception:
                    pass
                await _save_error(wallet.user_id, str(exc)[:500])

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

        symbols = [s.strip() for s in user_settings.universe.split(",") if s.strip()]

            # Sync: detect positions closed externally on DEX
        try:
            async with get_db_ctx() as sync_db:
                await self._sync_venue_positions(sync_db, wallet, user_id)
        except Exception as exc:
            logger.error("DEX sync error for %s: %s", user_id, exc)

        # Per-symbol: compute market data, check exits, then evaluate entry
        for symbol in symbols:
            try:
                # Fetch candles once per symbol, reuse for exits and entries
                closes_4h = await _fetch_candles(symbol, "4h", 120)
                closes_1h = await _fetch_candles(symbol, "1h", 48)
                closes_15m = await _fetch_candles(symbol, "15m", 4)
                price = closes_15m[-1] if closes_15m else (closes_1h[-1] if closes_1h else None)

                rsi_4h = None
                rsi_1h = None
                regime = None
                if closes_4h:
                    r4 = compute_rsi(closes_4h, user_settings.rsi_period)
                    if r4:
                        rsi_4h = r4.rsi
                        regime = detect_regime(rsi_4h, user_settings.rsi_regime_bullish_threshold, user_settings.rsi_regime_bearish_threshold)
                if closes_1h:
                    r1 = compute_rsi(closes_1h, user_settings.rsi_period)
                    if r1:
                        rsi_1h = r1.rsi

                # Check exits for this symbol with fresh market data
                async with get_db_ctx() as exit_db:
                    await self._check_exit_for_symbol(
                        exit_db, wallet, user_id, user_settings, symbol,
                        price=price, regime=regime, rsi_4h=rsi_4h, rsi_1h=rsi_1h,
                    )

                # Evaluate entry signal
                async with get_db_ctx() as sym_db:
                    await self._evaluate_symbol(
                        sym_db, user_id, wallet, user_settings, symbol,
                        closes_4h=closes_4h, closes_1h=closes_1h, closes_15m=closes_15m,
                    )
            except Exception as exc:
                logger.error("BotEngine symbol error %s/%s: %s", user_id, symbol, exc)
                await _log(db, user_id, level="error",
                    message=f"Error on {symbol}: {str(exc)[:200]}", symbol=symbol)

    async def _sync_venue_positions(
        self,
        db: AsyncSession,
        wallet: Wallet,
        user_id: uuid.UUID,
    ) -> None:
        """Detect positions closed externally on the DEX and update DB."""
        query_address = wallet.master_address or wallet.agent_address
        venue_positions = await _fetch_venue_positions(query_address)
        if venue_positions is None:
            return

        db_positions = await _get_all_open_positions(db, user_id)
        if not db_positions:
            return

        for pos in db_positions:
            venue = venue_positions.get(pos.symbol)
            if venue is not None:
                # Position still exists on venue — sync size and price
                pos.current_price = await _fetch_mid_price(pos.symbol)
                venue_size = venue.get("size", 0)
                if venue_size > 0 and abs(venue_size - pos.size) > 0.0001:
                    logger.info("DEX sync: %s size changed %.6f → %.6f (external partial close)",
                        pos.symbol, pos.size, venue_size)
                    if venue_size < pos.size:
                        pos.status = PositionStatus.PARTIALLY_CLOSED
                    pos.size = venue_size
                continue

            # Position gone from venue — closed externally
            exit_price = await _fetch_mid_price(pos.symbol) or pos.entry_price
            pos.status = PositionStatus.CLOSED
            pos.exit_price = exit_price
            pos.closed_at = datetime.now(timezone.utc)
            if pos.entry_price > 0:
                if pos.side == PositionSide.LONG:
                    pos.realized_pnl = (exit_price - pos.entry_price) * pos.size
                else:
                    pos.realized_pnl = (pos.entry_price - exit_price) * pos.size

            # Track the external close as an order in DB
            close_side = OrderSide.SELL if pos.side == PositionSide.LONG else OrderSide.BUY
            close_order = Order(
                user_id=user_id,
                symbol=pos.symbol,
                side=close_side,
                order_type=OrderType.MARKET,
                status=OrderStatus.FILLED,
                price=exit_price,
                size=pos.size,
                leverage=pos.leverage,
            )
            db.add(close_order)

            # Cancel any orphaned exchange SL
            if pos.venue_sl_oid:
                await _cancel_exchange_order(wallet, pos.symbol, pos.venue_sl_oid)
                pos.venue_sl_oid = None

            await _log(db, user_id, level="exit",
                message=f"{pos.symbol}: detected external close on DEX at ${exit_price:.2f}, PnL=${pos.realized_pnl:.2f}",
                symbol=pos.symbol, price=exit_price)
            logger.info("DEX sync: closed %s for user %s (external close) pnl=%.2f", pos.symbol, user_id, pos.realized_pnl)

        await db.flush()

    async def _evaluate_symbol(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        wallet: Wallet,
        user_settings: UserSettings,
        symbol: str,
        closes_4h: Optional[List[float]] = None,
        closes_1h: Optional[List[float]] = None,
        closes_15m: Optional[List[float]] = None,
    ) -> None:
        # Load or create per-symbol state
        state = await _load_bot_state(db, user_id, symbol)

        # Recover detector from state
        key = (user_id, symbol)
        if key not in self._detectors:
            detector = _build_detector(user_settings)
            _restore_detector(detector, state)
            self._detectors[key] = detector
        detector = self._detectors[key]

        # Fetch candles if not provided (fallback)
        if closes_4h is None:
            closes_4h = await _fetch_candles(symbol, "4h", 120)
        if closes_1h is None:
            closes_1h = await _fetch_candles(symbol, "1h", 48)
        if closes_15m is None:
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
            message=f"{symbol}: Regime={regime.value} RSI4H={rsi_4h:.1f} RSI1H={rsi_1h:.1f} Price=${price:.0f} Stage={detector.state.stage.value} Signal={detector.state.signal_type.value}",
            symbol=symbol, regime=regime.value, rsi_4h=rsi_4h, rsi_1h=rsi_1h,
            price=price, signal_stage=detector.state.stage.value, signal_type=detector.state.signal_type.value,
        )

        # If confirmed signal → place order
        if signal.stage == SignalStage.CONFIRMED and signal.signal_type != SignalType.NONE:
            existing = await _get_open_position(db, user_id, symbol)
            if existing is None:
                await _log(
                    db, user_id, level="signal",
                    message=f"SIGNAL CONFIRMED: {symbol} {signal.signal_type.value.upper()} at ${price:.0f} — placing order",
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

        # Fetch real equity from Hyperliquid
        query_address = wallet.master_address or wallet.agent_address
        equity = await _fetch_equity(query_address)
        if equity is None or equity <= 0:
            logger.warning("Could not fetch equity for %s, skipping order", query_address)
            return

        # Position sizing
        rm = RiskManager(
            equity=equity,
            max_leverage=user_settings.max_leverage,
            risk_per_trade_min=user_settings.risk_per_trade_min,
            risk_per_trade_max=user_settings.risk_per_trade_max,
            max_total_exposure_pct=user_settings.max_total_exposure_pct,
            default_risk_pct=(user_settings.risk_per_trade_min + user_settings.risk_per_trade_max) / 2,
        )
        sizing = rm.calculate_position_size(
            entry_price=price,
            stop_price=stop_price,
            direction=direction,
            current_exposure=0.0,
        )

        MIN_NOTIONAL = 10.0  # Hyperliquid minimum order notional in USD

        if sizing.size_notional <= 0:
            logger.warning("Position size is 0, skipping order")
            return

        if sizing.size_notional < MIN_NOTIONAL:
            await _log(db, wallet.user_id, level="warning",
                message=f"{symbol}: order notional ${sizing.size_notional:.2f} below Hyperliquid minimum ${MIN_NOTIONAL:.0f} — equity=${equity:.2f} too small for risk settings",
                symbol=symbol, price=price)
            logger.warning("Order notional $%.2f below minimum $%.0f for %s (equity=$%.2f)", sizing.size_notional, MIN_NOTIONAL, symbol, equity)
            return

        side = "buy" if direction == SignalType.LONG else "sell"
        size = sizing.size_contracts if sizing.size_contracts > 0 else round(sizing.size_notional / price, 6)
        size = _round_size(symbol, size)
        if size <= 0:
            logger.warning("Position size rounds to 0 for %s, skipping", symbol)
            return

        # Submit order to Hyperliquid
        result = await _submit_market_order(
            wallet=wallet,
            symbol=symbol,
            side=side,
            size=size,
            leverage=user_settings.max_leverage,
        )

        # SDK returns {status: "ok", response: {data: {statuses: [{filled: {oid, totalSz, avgPx}}]}}}
        statuses = result.get("response", {}).get("data", {}).get("statuses", [{}])
        status0 = statuses[0] if statuses else {}
        venue_order_id = status0.get("resting", {}).get("oid") or status0.get("filled", {}).get("oid")
        fill_price = float(status0.get("filled", {}).get("avgPx", 0)) or price
        fill_size = float(status0.get("filled", {}).get("totalSz", 0)) or size

        # Save order to DB with actual fill data
        order = Order(
            user_id=wallet.user_id,
            symbol=symbol,
            side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
            order_type=OrderType.MARKET,
            status=OrderStatus.FILLED if status0.get("filled") else (OrderStatus.ACCEPTED if venue_order_id else OrderStatus.INTENT),
            venue_order_id=str(venue_order_id) if venue_order_id else None,
            price=fill_price,
            size=size,
            filled_size=fill_size,
            leverage=user_settings.max_leverage,
            stop_loss=stop_price,
            risk_pct=sizing.risk_pct,
            signal_strength=signal.strength,
            regime=signal.regime.value,
            rsi_1h=rsi_1h,
            rsi_4h=rsi_4h,
        )
        db.add(order)

        # Save position to DB with actual fill price
        position = Position(
            user_id=wallet.user_id,
            order_id=order.id,
            symbol=symbol,
            side=PositionSide.LONG if direction == SignalType.LONG else PositionSide.SHORT,
            status=PositionStatus.OPEN,
            size=fill_size,
            entry_price=fill_price,
            stop_loss=stop_price,
            leverage=user_settings.max_leverage,
        )
        db.add(position)
        await db.flush()

        # Place stop-loss on the exchange (critical — abort position if SL fails)
        sl_placed = False
        try:
            sl_venue_oid = await _place_exchange_stop_loss(
                wallet=wallet, symbol=symbol, side=side,
                size=fill_size, stop_price=stop_price, price=price,
            )
            if sl_venue_oid:
                position.venue_sl_oid = str(sl_venue_oid)
                await db.flush()
                sl_placed = True
                logger.info("Exchange SL placed for %s: trigger=%.2f size=%s oid=%s", symbol, stop_price, fill_size, sl_venue_oid)
            else:
                logger.error("Exchange SL returned no OID for %s", symbol)
        except Exception as exc:
            logger.error("Failed to place exchange SL for %s: %s", symbol, exc)

        if not sl_placed:
            await _log(db, wallet.user_id, level="error",
                message=f"CRITICAL: Exchange SL NOT placed for {symbol} {side} size={fill_size} stop={stop_price:.2f} — position is unprotected on exchange!",
                symbol=symbol, price=price)

        logger.info(
            "Placed %s %s order: size=%s price=%.2f stop=%.2f venue_oid=%s",
            side, symbol, size, price, stop_price, venue_order_id,
        )

    async def _check_exit_for_symbol(
        self,
        db: AsyncSession,
        wallet: Wallet,
        user_id: uuid.UUID,
        user_settings: UserSettings,
        symbol: str,
        price: Optional[float],
        regime: Optional[Regime],
        rsi_4h: Optional[float],
        rsi_1h: Optional[float],
    ) -> None:
        """Check exit conditions for open positions on a specific symbol."""
        position = await _get_open_position(db, user_id, symbol)
        if position is None:
            return
        try:
            await self._check_exit(
                db, wallet, user_id, user_settings, position,
                price=price, regime=regime, rsi_4h=rsi_4h, rsi_1h=rsi_1h,
            )
        except Exception as exc:
            logger.error("Exit check error %s/%s: %s", user_id, symbol, exc)

    async def _check_exit(
        self,
        db: AsyncSession,
        wallet: Wallet,
        user_id: uuid.UUID,
        user_settings: UserSettings,
        position: Position,
        price: Optional[float] = None,
        regime: Optional[Regime] = None,
        rsi_4h: Optional[float] = None,
        rsi_1h: Optional[float] = None,
    ) -> None:
        symbol = position.symbol
        current_price = price or await _fetch_mid_price(symbol)
        if not current_price:
            return

        entry = position.entry_price
        stop = position.stop_loss or 0
        side = position.side
        partial_r = user_settings.rsi_exit_partial_r
        be_r = user_settings.rsi_exit_breakeven_r
        max_hours = user_settings.rsi_exit_max_hours

        risk = abs(entry - stop) if stop > 0 else entry * 0.02
        if risk == 0:
            return

        pnl_distance = (current_price - entry) if side == "long" else (entry - current_price)
        r_multiple = pnl_distance / risk

        # ── Intelligent exits (strategy: close when 4H bias deteriorates) ──

        # Regime exit: thesis no longer valid
        if regime is not None:
            regime_against = (
                (side == "long" and regime != Regime.BULLISH) or
                (side == "short" and regime != Regime.BEARISH)
            )
            if regime_against and r_multiple > 0:
                await _log(db, wallet.user_id, level="exit",
                    message=f"{symbol}: regime changed to {regime.value} while {side} (R={r_multiple:.1f}) — closing",
                    symbol=symbol, price=current_price)
                await self._close_position(db, wallet, position, current_price, "regime_change")
                return

        # RSI extreme exit: overbought/oversold while in profit
        if rsi_1h is not None and r_multiple > 0.5:
            rsi_extreme = (
                (side == "long" and rsi_1h >= 70) or
                (side == "short" and rsi_1h <= 30)
            )
            if rsi_extreme:
                await _log(db, wallet.user_id, level="exit",
                    message=f"{symbol}: RSI1H={rsi_1h:.0f} extreme while {side} at R={r_multiple:.1f} — closing",
                    symbol=symbol, price=current_price)
                await self._close_position(db, wallet, position, current_price, "rsi_extreme")
                return

        # ── Mechanical exits ──

        # Stop loss
        stop_hit = (side == "long" and current_price <= stop) or (side == "short" and current_price >= stop)
        if stop_hit:
            await self._close_position(db, wallet, position, current_price, "stop_loss")
            return

        # Max hours
        if position.opened_at:
            hours_held = (datetime.now(timezone.utc) - position.opened_at).total_seconds() / 3600
            if hours_held >= max_hours:
                await self._close_position(db, wallet, position, current_price, "max_hours")
                return

        # Partial exit
        if r_multiple >= partial_r and not position.partial_exited:
            close_size = position.size / 2
            await self._partial_close(db, wallet, position, current_price, close_size)
            position.stop_loss = entry
            position.partial_exited = True
            await db.flush()
            return

        # Move stop to breakeven
        if r_multiple >= be_r and not position.be_moved:
            position.stop_loss = entry
            position.be_moved = True
            await _update_exchange_sl(db, wallet, position)
            await db.flush()

    async def _close_position(
        self, db: AsyncSession, wallet: Wallet, position: Position, current_price: float, reason: str,
    ) -> None:
        side = "sell" if position.side == PositionSide.LONG else "buy"
        result = await _submit_market_order(
            wallet=wallet, symbol=position.symbol, side=side, size=position.size, leverage=position.leverage,
        )

        # Verify the fill succeeded
        statuses = result.get("response", {}).get("data", {}).get("statuses", [{}])
        status0 = statuses[0] if statuses else {}
        venue_oid = status0.get("resting", {}).get("oid") or status0.get("filled", {}).get("oid")
        fill_price = float(status0.get("filled", {}).get("avgPx", 0)) or current_price

        if result.get("status") == "err" or (not venue_oid and not status0.get("filled")):
            logger.error("Close order FAILED for %s: %s — position stays open", position.symbol, str(result)[:300])
            await _log(db, wallet.user_id, level="error",
                message=f"Close order FAILED for {position.symbol}: {str(result)[:200]}",
                symbol=position.symbol, price=current_price)
            await db.flush()
            return

        # Track close order in DB
        close_order = Order(
            user_id=wallet.user_id,
            symbol=position.symbol,
            side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
            order_type=OrderType.MARKET,
            status=OrderStatus.FILLED,
            venue_order_id=str(venue_oid) if venue_oid else None,
            price=fill_price,
            size=position.size,
            leverage=position.leverage,
        )
        db.add(close_order)

        # Cancel exchange stop-loss if we placed one
        if position.venue_sl_oid:
            await _cancel_exchange_order(wallet, position.symbol, position.venue_sl_oid)

        position.status = PositionStatus.CLOSED
        position.exit_price = fill_price
        position.closed_at = datetime.now(timezone.utc)
        if position.entry_price > 0:
            if position.side == PositionSide.LONG:
                position.realized_pnl = (fill_price - position.entry_price) * position.size
            else:
                position.realized_pnl = (position.entry_price - fill_price) * position.size
        await _log(db, wallet.user_id, level="exit",
            message=f"EXIT {position.symbol} {position.side}: reason={reason} price=${fill_price:.2f} pnl=${position.realized_pnl:.2f}",
            symbol=position.symbol, price=fill_price)
        await db.flush()
        logger.info("Closed %s position %s: reason=%s fill_price=%.2f", position.symbol, position.id, reason, fill_price)

    async def _partial_close(
        self, db: AsyncSession, wallet: Wallet, position: Position, current_price: float, close_size: float,
    ) -> None:
        side = "sell" if position.side == PositionSide.LONG else "buy"
        result = await _submit_market_order(
            wallet=wallet, symbol=position.symbol, side=side, size=close_size, leverage=position.leverage,
        )

        # Verify fill
        statuses = result.get("response", {}).get("data", {}).get("statuses", [{}])
        status0 = statuses[0] if statuses else {}
        venue_oid = status0.get("resting", {}).get("oid") or status0.get("filled", {}).get("oid")
        fill_price = float(status0.get("filled", {}).get("avgPx", 0)) or current_price

        if result.get("status") == "err" or (not venue_oid and not status0.get("filled")):
            logger.error("Partial close FAILED for %s: %s", position.symbol, str(result)[:300])
            return

        # Track partial close order in DB
        close_order = Order(
            user_id=wallet.user_id,
            symbol=position.symbol,
            side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
            order_type=OrderType.MARKET,
            status=OrderStatus.FILLED,
            venue_order_id=str(venue_oid) if venue_oid else None,
            price=fill_price,
            size=close_size,
            leverage=position.leverage,
        )
        db.add(close_order)

        position.size -= close_size
        position.status = PositionStatus.PARTIALLY_CLOSED

        # Update exchange SL to match remaining size
        await _update_exchange_sl(db, wallet, position)

        await db.flush()
        logger.info("Partial close %s: size=%.6f fill=%.2f remaining=%.6f", position.symbol, close_size, fill_price, position.size)


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
    """Write a log entry using its own DB session so it survives cycle rollbacks."""
    try:
        async with get_db_ctx() as log_db:
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
            log_db.add(entry)
            await log_db.flush()
    except Exception as exc:
        logger.error("Failed to write bot log: %s", exc)


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
                _sz_decimals_cache[asset["name"]] = int(asset.get("szDecimals", 0))
            logger.info("Loaded %d asset indices", len(_asset_index_cache))
    except Exception as exc:
        logger.error("Failed to load asset indices: %s", exc)


def _get_asset_index(symbol: str) -> int:
    if symbol in _asset_index_cache:
        return _asset_index_cache[symbol]
    raise ValueError(f"Unknown symbol: {symbol}")


def _round_size(symbol: str, size: float) -> float:
    decimals = _sz_decimals_cache.get(symbol, 0)
    return round(size, decimals)


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


async def _fetch_venue_positions(address: str) -> Optional[Dict[str, Dict]]:
    """Fetch open positions from Hyperliquid clearinghouseState."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.hyperliquid_api_url}/info",
                json={"type": "clearinghouseState", "user": address},
            )
            resp.raise_for_status()
            data = resp.json()
            asset_positions = data.get("assetPositions", [])
            result = {}
            for ap in asset_positions:
                pos = ap.get("position", {})
                coin = pos.get("coin", "")
                szi = float(pos.get("szi", 0))
                if coin and abs(szi) > 0:
                    result[coin] = {
                        "size": abs(szi),
                        "entry_price": float(pos.get("entryPx", 0)),
                    }
            return result
    except Exception as exc:
        logger.error("Failed to fetch venue positions for %s: %s", address, exc)
        return None


async def _fetch_equity(address: str) -> Optional[float]:
    """Fetch real account equity from Hyperliquid.

    Queries both perp clearinghouse and spot clearinghouse because unified
    accounts hold USDC in spot (auto-used as margin) and clearinghouseState
    returns accountValue=0 for them.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            perp_resp = await client.post(
                f"{settings.hyperliquid_api_url}/info",
                json={"type": "clearinghouseState", "user": address},
            )
            perp_resp.raise_for_status()
            perp_data = perp_resp.json()

            spot_resp = await client.post(
                f"{settings.hyperliquid_api_url}/info",
                json={"type": "spotClearinghouseState", "user": address},
            )
            spot_resp.raise_for_status()
            spot_data = spot_resp.json()

        margin_summary = perp_data.get("marginSummary", {})
        perp_equity = float(margin_summary.get("accountValue", 0))

        spot_usdc = 0.0
        for bal in spot_data.get("balances", []):
            if bal.get("coin") == "USDC":
                spot_usdc += float(bal.get("total", 0))

        # For unified accounts, USDC lives in spot; for legacy, in perps
        equity = perp_equity if perp_equity > 0 else spot_usdc
        logger.info("Fetched equity for %s: $%.2f (perp=$%.2f spot_usdc=$%.2f)", address, equity, perp_equity, spot_usdc)
        return equity if equity > 0 else None
    except Exception as exc:
        logger.error("Failed to fetch equity for %s: %s", address, exc)
        return None


async def _submit_market_order(
    wallet: Wallet,
    symbol: str,
    side: str,
    size: float,
    leverage: int = 3,
) -> Dict[str, Any]:
    private_key = decrypt_private_key(wallet.encrypted_private_key, settings.encryption_key)

    size = _round_size(symbol, size)
    if size <= 0:
        raise ValueError(f"Order size rounds to 0 for {symbol}")

    # Use master_address as account_address so the SDK knows who the user is
    account_addr = wallet.master_address or wallet.agent_address

    signer = HyperliquidSigner(
        private_key=private_key,
        account_address=account_addr,
        network=settings.hyperliquid_network,
    )

    logger.info(
        "Submitting %s %s size=%s — wallet=%s account=%s derived=%s",
        side, symbol, size, wallet.agent_address, account_addr, signer.wallet_address,
    )

    # Set leverage (idempotent)
    try:
        await signer.update_leverage(symbol, leverage, is_cross=True)
    except Exception as exc:
        logger.warning("Leverage setting failed (non-fatal): %s", exc)

    # Place market order (SDK handles slippage-adjusted price + signing)
    is_buy = side == "buy"
    result = await signer.market_open(symbol, is_buy, size, slippage=0.03)

    logger.info("Hyperliquid order response for %s %s size=%s: %s", side, symbol, size, str(result)[:500])

    if result.get("status") == "err":
        raise RuntimeError(f"Hyperliquid error for {symbol} {side} size={size}: {str(result)[:300]}")

    return result


async def _place_exchange_stop_loss(
    wallet: Wallet,
    symbol: str,
    side: str,
    size: float,
    stop_price: float,
    price: float,
) -> Optional[int]:
    """Place a real stop-loss trigger order on Hyperliquid."""
    private_key = decrypt_private_key(wallet.encrypted_private_key, settings.encryption_key)
    account_addr = wallet.master_address or wallet.agent_address
    signer = HyperliquidSigner(
        private_key=private_key,
        account_address=account_addr,
        network=settings.hyperliquid_network,
    )

    # SL is opposite direction from entry: LONG entry → sell SL, SHORT entry → buy SL
    is_buy_sl = side == "sell"
    # BUY SL → limit above trigger (pay up to), SELL SL → limit below trigger (accept less)
    slippage = 0.05
    worst_price = stop_price * (1 + slippage) if is_buy_sl else stop_price * (1 - slippage)

    result = await signer.place_stop_loss(
        symbol=symbol,
        is_buy=is_buy_sl,
        size=size,
        trigger_price=stop_price,
        worst_price=worst_price,
    )

    if result.get("status") == "err":
        logger.warning("SL order rejected for %s: %s", symbol, str(result)[:300])
        return None

    statuses = result.get("response", {}).get("data", {}).get("statuses", [{}])
    status0 = statuses[0] if statuses else {}
    return status0.get("resting", {}).get("oid") or status0.get("triggered", {}).get("oid")


async def _cancel_exchange_order(wallet: Wallet, symbol: str, venue_oid: str) -> None:
    """Cancel an order on Hyperliquid by venue OID."""
    try:
        private_key = decrypt_private_key(wallet.encrypted_private_key, settings.encryption_key)
        account_addr = wallet.master_address or wallet.agent_address
        signer = HyperliquidSigner(
            private_key=private_key,
            account_address=account_addr,
            network=settings.hyperliquid_network,
        )
        await signer.cancel(symbol, int(venue_oid))
        logger.info("Cancelled exchange order %s for %s", venue_oid, symbol)
    except Exception as exc:
        logger.warning("Failed to cancel exchange order %s for %s: %s", venue_oid, symbol, exc)


async def _update_exchange_sl(db: AsyncSession, wallet: Wallet, position: Position) -> None:
    """Cancel old exchange SL and place a new one with updated size/price."""
    if not position.stop_loss or position.stop_loss <= 0:
        return

    # Cancel existing exchange SL
    if position.venue_sl_oid:
        await _cancel_exchange_order(wallet, position.symbol, position.venue_sl_oid)
        position.venue_sl_oid = None

    # Pass ENTRY direction — _place_exchange_stop_loss flips it internally
    entry_side = "buy" if position.side == "long" else "sell"

    try:
        new_oid = await _place_exchange_stop_loss(
            wallet=wallet,
            symbol=position.symbol,
            side=entry_side,
            size=position.size,
            stop_price=position.stop_loss,
            price=position.stop_loss,
        )
        if new_oid:
            position.venue_sl_oid = str(new_oid)
            logger.info("Updated exchange SL for %s: trigger=%.2f size=%.6f oid=%s",
                position.symbol, position.stop_loss, position.size, new_oid)
    except Exception as exc:
        logger.warning("Failed to update exchange SL for %s: %s", position.symbol, exc)


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


async def _load_bot_state(db: AsyncSession, user_id: uuid.UUID, symbol: str = "BTC") -> BotState:
    result = await db.execute(select(BotState).where(BotState.user_id == user_id, BotState.symbol == symbol))
    state = result.scalar_one_or_none()
    if state is None:
        state = BotState(user_id=user_id, symbol=symbol)
        db.add(state)
        await db.flush()
    return state


async def _save_error(user_id: uuid.UUID, error: str, symbol: str = "BTC") -> None:
    """Save error to bot state using its own DB session."""
    try:
        async with get_db_ctx() as db:
            state = await _load_bot_state(db, user_id, symbol)
            state.last_error = error
            state.last_eval_at = datetime.now(timezone.utc)
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


async def _get_all_open_positions(db: AsyncSession, user_id: uuid.UUID) -> List[Position]:
    result = await db.execute(
        select(Position).where(
            Position.user_id == user_id,
            Position.status.in_([PositionStatus.OPEN, PositionStatus.PARTIALLY_CLOSED]),
        )
    )
    return list(result.scalars().all())
