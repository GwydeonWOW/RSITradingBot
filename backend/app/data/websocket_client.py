"""Hyperliquid WebSocket client for real-time market data.

Connects to the Hyperliquid WebSocket API and subscribes to:
- candle: OHLCV candle updates
- l2Book: Level 2 order book snapshots
- allMids: Mid-price updates for all assets
- orderUpdates: Status updates for placed orders
- userEvents: User account events
- userFills: Fill notifications

Features:
- Auto-reconnect with exponential backoff.
- Ping every 50 seconds (server closes at 60s idle).
- Message routing to registered handler callbacks.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

import websockets
from websockets.client import WebSocketClientProtocol

logger = logging.getLogger(__name__)

# Type alias for async handler callbacks
Handler = Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]


class SubscriptionType(str, Enum):
    """Hyperliquid WebSocket subscription channels."""

    CANDLE = "candle"
    L2_BOOK = "l2Book"
    ALL_MIDS = "allMids"
    ORDER_UPDATES = "orderUpdates"
    USER_EVENTS = "userEvents"
    USER_FILLS = "userFills"


class ConnectionState(str, Enum):
    """WebSocket connection state."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"


@dataclass
class Subscription:
    """A WebSocket channel subscription."""

    channel: SubscriptionType
    params: Dict[str, Any] = field(default_factory=dict)

    def to_message(self) -> Dict[str, Any]:
        """Convert to the Hyperliquid subscription message format."""
        msg: Dict[str, Any] = {"method": "subscribe", "subscription": {"type": self.channel.value}}
        msg["subscription"].update(self.params)
        return msg


@dataclass
class ReconnectConfig:
    """Configuration for auto-reconnect behavior."""

    max_attempts: int = 20
    base_delay_ms: int = 1000
    max_delay_ms: int = 30000
    backoff_factor: float = 2.0


class HyperliquidWebSocketClient:
    """Async WebSocket client for Hyperliquid market data.

    Usage:
        client = HyperliquidWebSocketClient(ws_url="wss://api.hyperliquid.xyz/ws")
        client.on(SubscriptionType.CANDLE, my_candle_handler)
        client.on(SubscriptionType.L2_BOOK, my_book_handler)

        await client.connect()
        await client.subscribe(Subscription(
            channel=SubscriptionType.CANDLE,
            params={"coin": "BTC", "interval": "15m"}
        ))
        # ... runs until disconnect
        await client.disconnect()
    """

    PING_INTERVAL_S = 50  # seconds between pings
    IDLE_TIMEOUT_S = 60  # server timeout

    def __init__(
        self,
        ws_url: str = "wss://api.hyperliquid.xyz/ws",
        reconnect_config: Optional[ReconnectConfig] = None,
        ping_interval: float = 50.0,
    ) -> None:
        self._ws_url = ws_url
        self._reconnect_config = reconnect_config or ReconnectConfig()
        self._ping_interval = ping_interval
        self._connection_state = ConnectionState.DISCONNECTED
        self._ws: Optional[WebSocketClientProtocol] = None
        self._handlers: Dict[SubscriptionType, List[Handler]] = {}
        self._subscriptions: List[Subscription] = []
        self._reconnect_attempts = 0
        self._running = False
        self._last_ping = 0.0
        self._listen_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None

    @property
    def state(self) -> ConnectionState:
        return self._connection_state

    @property
    def is_connected(self) -> bool:
        return self._connection_state == ConnectionState.CONNECTED

    def on(self, channel: SubscriptionType, handler: Handler) -> None:
        """Register a handler for a subscription channel.

        Multiple handlers can be registered for the same channel.

        Args:
            channel: The subscription type to listen for.
            handler: Async callback that receives parsed message dicts.
        """
        if channel not in self._handlers:
            self._handlers[channel] = []
        self._handlers[channel].append(handler)

    def remove_handler(self, channel: SubscriptionType, handler: Handler) -> None:
        """Remove a previously registered handler."""
        if channel in self._handlers:
            self._handlers[channel] = [h for h in self._handlers[channel] if h != handler]

    async def connect(self) -> None:
        """Establish the WebSocket connection.

        Starts the listen loop and ping loop as background tasks.
        Auto-reconnects on failure.
        """
        self._running = True
        self._connection_state = ConnectionState.CONNECTING

        while self._running:
            try:
                logger.info("Connecting to %s ...", self._ws_url)
                async with websockets.connect(
                    self._ws_url,
                    ping_interval=None,  # we handle pings ourselves
                    close_timeout=5,
                ) as ws:
                    self._ws = ws
                    self._connection_state = ConnectionState.CONNECTED
                    self._reconnect_attempts = 0
                    logger.info("WebSocket connected to %s", self._ws_url)

                    # Re-subscribe to all channels
                    await self._resubscribe()

                    # Start ping and listen loops
                    self._ping_task = asyncio.create_task(self._ping_loop())
                    await self._listen_loop()

            except (
                websockets.ConnectionClosed,
                websockets.InvalidHandshake,
                ConnectionRefusedError,
                OSError,
            ) as exc:
                self._connection_state = ConnectionState.RECONNECTING
                logger.warning("WebSocket disconnected: %s", exc)

                if not self._running:
                    break

                await self._backoff()

            except Exception as exc:
                logger.error("Unexpected WebSocket error: %s", exc, exc_info=True)
                self._connection_state = ConnectionState.RECONNECTING
                if not self._running:
                    break
                await self._backoff()

        self._connection_state = ConnectionState.DISCONNECTED
        logger.info("WebSocket client stopped.")

    async def disconnect(self) -> None:
        """Gracefully disconnect from the WebSocket."""
        self._running = False
        if self._ping_task and not self._ping_task.done():
            self._ping_task.cancel()
        if self._ws and not self._ws.closed:
            await self._ws.close()
        self._connection_state = ConnectionState.DISCONNECTED
        logger.info("WebSocket disconnected.")

    async def subscribe(self, subscription: Subscription) -> None:
        """Subscribe to a channel.

        If connected, sends the subscription message immediately.
        Otherwise, queues it for when connection is established.

        Args:
            subscription: The subscription to add.
        """
        self._subscriptions.append(subscription)
        if self.is_connected and self._ws:
            msg = subscription.to_message()
            await self._ws.send(json.dumps(msg))
            logger.info("Subscribed to %s", subscription.channel.value)

    async def unsubscribe(self, subscription: Subscription) -> None:
        """Unsubscribe from a channel."""
        self._subscriptions = [
            s for s in self._subscriptions
            if not (s.channel == subscription.channel and s.params == subscription.params)
        ]
        if self.is_connected and self._ws:
            msg = subscription.to_message()
            msg["method"] = "unsubscribe"
            await self._ws.send(json.dumps(msg))
            logger.info("Unsubscribed from %s", subscription.channel.value)

    async def _listen_loop(self) -> None:
        """Main loop that reads messages and dispatches to handlers."""
        if not self._ws:
            return

        async for raw_message in self._ws:
            try:
                data = json.loads(raw_message)
                await self._dispatch(data)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON from WebSocket: %s", raw_message[:200])
            except Exception as exc:
                logger.error("Error processing message: %s", exc, exc_info=True)

    async def _ping_loop(self) -> None:
        """Send periodic pings to keep the connection alive.

        Hyperliquid closes connections idle for 60 seconds, so we
        ping every 50 seconds.
        """
        try:
            while self._running and self._ws and not self._ws.closed:
                await asyncio.sleep(self._ping_interval)
                if self._ws and not self._ws.closed:
                    await self._ws.ping()
                    self._last_ping = time.monotonic()
                    logger.debug("Ping sent")
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("Ping loop error: %s", exc)

    async def _dispatch(self, data: Dict[str, Any]) -> None:
        """Route a message to the appropriate handlers.

        Hyperliquid messages have the structure:
        {
            "channel": "<channel_type>",
            "data": { ... }
        }
        """
        channel_str = data.get("channel", "")
        try:
            channel = SubscriptionType(channel_str)
        except ValueError:
            # Response to subscription request or unknown channel
            logger.debug("Ignoring message for channel: %s", channel_str)
            return

        handlers = self._handlers.get(channel, [])
        for handler in handlers:
            try:
                await handler(data)
            except Exception as exc:
                logger.error(
                    "Handler error for %s: %s", channel.value, exc, exc_info=True
                )

    async def _resubscribe(self) -> None:
        """Re-send all queued subscriptions after a reconnect."""
        if not self._ws:
            return
        for sub in self._subscriptions:
            msg = sub.to_message()
            await self._ws.send(json.dumps(msg))
            logger.info("Re-subscribed to %s", sub.channel.value)

    async def _backoff(self) -> None:
        """Wait with exponential backoff before reconnecting."""
        config = self._reconnect_config
        self._reconnect_attempts += 1

        if self._reconnect_attempts > config.max_attempts:
            logger.error(
                "Max reconnect attempts (%d) reached. Stopping.",
                config.max_attempts,
            )
            self._running = False
            return

        delay_ms = min(
            config.base_delay_ms * (config.backoff_factor ** (self._reconnect_attempts - 1)),
            config.max_delay_ms,
        )
        delay_s = delay_ms / 1000.0
        logger.info(
            "Reconnecting in %.1f seconds (attempt %d/%d)",
            delay_s,
            self._reconnect_attempts,
            config.max_attempts,
        )
        await asyncio.sleep(delay_s)
