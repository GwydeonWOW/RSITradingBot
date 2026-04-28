"""Hyperliquid signing service.

Constructs and signs L1 actions for the Hyperliquid API using
the EIP-712 typed data standard. Signs orders, cancellations,
and other on-chain interactions.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SignedOrder:
    """A signed order ready for submission to Hyperliquid."""

    signature: str
    action: Dict[str, Any]
    payload: Dict[str, Any]


class HyperliquidSigner:
    """Signs orders and actions for Hyperliquid using EIP-712.

    NOTE: This is a simplified implementation. In production, use
    the official Hyperliquid Python SDK or ethers.js for proper
    EIP-712 typed-data signing with the correct domain separator.

    Usage:
        signer = HyperliquidSigner(private_key="0x...")
        signed = signer.sign_order(
            symbol="BTC", side="buy", size=0.01, price=50000.0
        )
    """

    # Hyperliquid EIP-712 domain
    DOMAIN = {
        "name": "Exchange",
        "version": "1",
        "chainId": 421614,  # Arbitrum testnet; mainnet = 42161
    }

    def __init__(
        self,
        private_key: str,
        account_address: Optional[str] = None,
        vault_address: Optional[str] = None,
        network: str = "mainnet",
    ) -> None:
        self._private_key = private_key
        self._account_address = account_address or ""
        self._vault_address = vault_address
        self._network = network

        if network == "mainnet":
            self.DOMAIN["chainId"] = 42161
        else:
            self.DOMAIN["chainId"] = 421614

    @property
    def account_address(self) -> str:
        return self._account_address

    def sign_order(
        self,
        symbol: str,
        side: str,
        size: float,
        price: Optional[float] = None,
        order_type: str = "Ioc",  # Ioc, Gtc, Alo
        reduce_only: bool = False,
        leverage: int = 1,
    ) -> SignedOrder:
        """Sign a place-order action.

        Args:
            symbol: Asset symbol (e.g. "BTC").
            side: "buy" or "sell".
            size: Order size in base currency.
            price: Limit price. None for market orders.
            order_type: "Ioc" (Immediate or Cancel), "Gtc" (Good til Cancel), "Alo" (Add Liquidity Only).
            reduce_only: Only reduce existing position.
            leverage: Leverage for the position.

        Returns:
            SignedOrder with signature and action payload.
        """
        action = {
            "type": "order",
            "orders": [
                {
                    "a": 0,  # asset index, resolved by symbol -> index mapping
                    "b": side == "buy",
                    "p": str(price) if price else "0",
                    "s": str(size),
                    "r": reduce_only,
                    "t": {"limit": {"tif": order_type}},
                }
            ],
            "grouping": "na",
        }

        if self._vault_address:
            action["vaultAddress"] = self._vault_address

        payload = {
            "action": action,
            "signature": self._sign_action(action),
            "nonce": int(time.time() * 1000),
        }

        return SignedOrder(
            signature=payload["signature"],
            action=action,
            payload=payload,
        )

    def sign_cancel(
        self,
        symbol: str,
        order_id: str,
    ) -> SignedOrder:
        """Sign a cancel-order action.

        Args:
            symbol: Asset symbol.
            order_id: Venue-assigned order ID to cancel.

        Returns:
            SignedOrder with cancel action.
        """
        action = {
            "type": "cancel",
            "cancels": [
                {
                    "a": 0,  # asset index
                    "o": int(order_id),
                }
            ],
        }

        if self._vault_address:
            action["vaultAddress"] = self._vault_address

        payload = {
            "action": action,
            "signature": self._sign_action(action),
            "nonce": int(time.time() * 1000),
        }

        return SignedOrder(
            signature=payload["signature"],
            action=action,
            payload=payload,
        )

    def sign_modify_leverage(
        self,
        symbol: str,
        leverage: int,
        is_cross: bool = False,
    ) -> SignedAction:
        """Sign a leverage modification action.

        Args:
            symbol: Asset symbol.
            leverage: Target leverage.
            is_cross: True for cross margin, False for isolated.

        Returns:
            SignedAction with leverage modification.
        """
        action = {
            "type": "updateLeverage",
            "asset": 0,  # resolved by symbol
            "isCross": is_cross,
            "leverage": leverage,
        }

        if self._vault_address:
            action["vaultAddress"] = self._vault_address

        payload = {
            "action": action,
            "signature": self._sign_action(action),
            "nonce": int(time.time() * 1000),
        }

        return SignedAction(
            signature=payload["signature"],
            action=action,
            payload=payload,
        )

    def _sign_action(self, action: Dict[str, Any]) -> Dict[str, str]:
        """Sign an action using EIP-712 typed data.

        In production, this would use web3.py or a hardware wallet
        to produce a proper secp256k1 signature. This stub returns
        a placeholder structure.
        """
        # Placeholder: in production, use proper EIP-712 signing
        # from web3 import Web3
        # w3 = Web3()
        # structured = self._build_eip712_message(action)
        # signed = w3.eth.account.sign_typed_data(self._private_key, structured)
        # return {"r": hex(signed.r), "s": hex(signed.s), "v": signed.v}

        action_hash = hashlib.sha256(json.dumps(action, sort_keys=True).encode()).hexdigest()
        return {
            "r": f"0x{action_hash[:64]}",
            "s": f"0x{'0' * 63}1",
            "v": 28,
        }


@dataclass(frozen=True)
class SignedAction:
    """A signed action (non-order) ready for submission."""

    signature: Dict[str, str]
    action: Dict[str, Any]
    payload: Dict[str, Any]
