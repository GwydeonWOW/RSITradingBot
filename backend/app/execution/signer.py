"""Hyperliquid signing service using the official SDK.

Uses the hyperliquid-python-sdk for correct EIP-712 signing with msgpack
hashing, proper nonce handling, and correct domain configuration.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

import eth_account
from eth_account.signers.local import LocalAccount

from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL

logger = logging.getLogger(__name__)


class HyperliquidSigner:
    """Signs orders and actions for Hyperliquid using the official SDK.

    Wraps the SDK's Exchange class to provide signing + submission
    compatible with our async bot engine.
    """

    def __init__(
        self,
        private_key: str,
        account_address: Optional[str] = None,
        vault_address: Optional[str] = None,
        network: str = "mainnet",
    ) -> None:
        self._wallet: LocalAccount = eth_account.Account.from_key(private_key)
        base_url = MAINNET_API_URL if network == "mainnet" else TESTNET_API_URL
        self._account_address = account_address
        self._network = network

        self._exchange = Exchange(
            self._wallet,
            base_url=base_url,
            vault_address=vault_address,
            account_address=account_address,
            timeout=15,
        )

    @property
    def wallet_address(self) -> str:
        return self._wallet.address

    async def update_leverage(self, symbol: str, leverage: int, is_cross: bool = True) -> Dict[str, Any]:
        result = await asyncio.to_thread(
            self._exchange.update_leverage, leverage, symbol, is_cross
        )
        logger.info("update_leverage %s %s cross=%s: %s", leverage, symbol, is_cross, str(result)[:300])
        return result

    async def market_open(
        self,
        symbol: str,
        is_buy: bool,
        size: float,
        slippage: float = 0.03,
    ) -> Dict[str, Any]:
        result = await asyncio.to_thread(
            self._exchange.market_open, symbol, is_buy, size, None, slippage
        )
        return result

    async def market_close(
        self,
        symbol: str,
        size: Optional[float] = None,
        slippage: float = 0.03,
    ) -> Dict[str, Any]:
        result = await asyncio.to_thread(
            self._exchange.market_close, symbol, size, None, slippage
        )
        return result

    async def cancel(self, symbol: str, oid: int) -> Dict[str, Any]:
        result = await asyncio.to_thread(
            self._exchange.cancel, symbol, oid
        )
        return result

    async def order(
        self,
        symbol: str,
        is_buy: bool,
        size: float,
        price: float,
        order_type: Optional[Dict] = None,
        reduce_only: bool = False,
    ) -> Dict[str, Any]:
        if order_type is None:
            order_type = {"limit": {"tif": "Ioc"}}
        result = await asyncio.to_thread(
            self._exchange.order, symbol, is_buy, size, price, order_type, reduce_only
        )
        return result

    async def place_stop_loss(
        self,
        symbol: str,
        is_buy: bool,
        size: float,
        trigger_price: float,
        worst_price: float,
    ) -> Dict[str, Any]:
        """Place a stop-loss trigger order on the exchange.

        Args:
            symbol: Trading pair (e.g. "SOL").
            is_buy: True to buy on trigger (close SHORT), False to sell (close LONG).
            size: Position size to close.
            trigger_price: Price that activates the stop.
            worst_price: Worst acceptable fill price (slippage limit).
        """
        order_type = {
            "trigger": {
                "triggerPx": trigger_price,
                "isMarket": True,
                "tpsl": "sl",
            }
        }
        result = await asyncio.to_thread(
            self._exchange.order,
            symbol, is_buy, size, worst_price, order_type, True,
        )
        logger.info("SL order %s %s size=%s trigger=%.2f: %s",
            "buy" if is_buy else "sell", symbol, size, trigger_price, str(result)[:300])
        return result
