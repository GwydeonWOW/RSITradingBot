"""Hyperliquid signing service.

Constructs and signs L1 actions for the Hyperliquid API using
the EIP-712 typed data standard. Signs orders, cancellations,
and other on-chain interactions.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from eth_account import Account
from eth_account.messages import encode_structured_data
from eth_hash.auto import keccak as keccak256

logger = logging.getLogger(__name__)

PHANTOM_GAS = 2_000_000
PHANTOM_GAS_PRICE = 0

EIP712_DOMAIN_TYPES = [
    {"name": "name", "type": "string"},
    {"name": "version", "type": "uint32"},
    {"name": "chainId", "type": "uint256"},
]

AGENT_TYPES = [
    {"name": "source", "type": "string"},
    {"name": "connectionId", "type": "bytes32"},
]


@dataclass(frozen=True)
class SignedOrder:
    """A signed order ready for submission to Hyperliquid."""

    signature: Dict[str, str]
    action: Dict[str, Any]
    payload: Dict[str, Any]


@dataclass(frozen=True)
class SignedAction:
    """A signed action (non-order) ready for submission."""

    signature: Dict[str, str]
    action: Dict[str, Any]
    payload: Dict[str, Any]


class HyperliquidSigner:
    """Signs orders and actions for Hyperliquid using EIP-712.

    Usage:
        signer = HyperliquidSigner(private_key="0x...")
        signed = signer.sign_order(
            symbol="BTC", side="buy", size=0.01, price=50000.0
        )
    """

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
        self._chain_id = 42161 if network == "mainnet" else 421614

    @property
    def account_address(self) -> str:
        return self._account_address

    def sign_order(
        self,
        symbol: str,
        side: str,
        size: float,
        price: Optional[float] = None,
        order_type: str = "Ioc",
        reduce_only: bool = False,
        leverage: int = 1,
    ) -> SignedOrder:
        """Sign a place-order action."""
        action = {
            "type": "order",
            "orders": [
                {
                    "a": 0,
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

        nonce = int(time.time() * 1000)
        signature = self._sign_action(action)
        payload = {"action": action, "signature": signature, "nonce": nonce}

        return SignedOrder(signature=signature, action=action, payload=payload)

    def sign_cancel(
        self,
        symbol: str,
        order_id: str,
    ) -> SignedOrder:
        """Sign a cancel-order action."""
        action = {
            "type": "cancel",
            "cancels": [
                {
                    "a": 0,
                    "o": int(order_id),
                }
            ],
        }

        if self._vault_address:
            action["vaultAddress"] = self._vault_address

        nonce = int(time.time() * 1000)
        signature = self._sign_action(action)
        payload = {"action": action, "signature": signature, "nonce": nonce}

        return SignedOrder(signature=signature, action=action, payload=payload)

    def sign_modify_leverage(
        self,
        symbol: str,
        leverage: int,
        is_cross: bool = False,
    ) -> SignedAction:
        """Sign a leverage modification action."""
        action = {
            "type": "updateLeverage",
            "asset": 0,
            "isCross": is_cross,
            "leverage": leverage,
        }

        if self._vault_address:
            action["vaultAddress"] = self._vault_address

        nonce = int(time.time() * 1000)
        signature = self._sign_action(action)
        payload = {"action": action, "signature": signature, "nonce": nonce}

        return SignedAction(signature=signature, action=action, payload=payload)

    def _sign_action(self, action: Dict[str, Any]) -> Dict[str, str]:
        """Sign an action using EIP-712 typed data for Hyperliquid.

        The action is hashed with phantom gas fields, wrapped in an
        Agent EIP-712 struct, and signed with secp256k1.
        """
        action_with_gas = dict(action)
        action_with_gas["gas"] = PHANTOM_GAS
        action_with_gas["gasPrice"] = PHANTOM_GAS_PRICE

        action_json = json.dumps(action_with_gas, separators=(",", ":")).encode()
        action_hash = keccak256(action_json)

        structured_data = {
            "domain": {
                "name": "Exchange",
                "version": 1,
                "chainId": self._chain_id,
            },
            "types": {
                "EIP712Domain": EIP712_DOMAIN_TYPES,
                "Agent": AGENT_TYPES,
            },
            "primaryType": "Agent",
            "message": {
                "source": "a",
                "connectionId": action_hash,
            },
        }

        encoded = encode_structured_data(structured_data)
        signed = Account.sign_message(encoded, self._private_key)

        return {"r": hex(signed.r), "s": hex(signed.s), "v": signed.v}
