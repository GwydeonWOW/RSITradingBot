"""AES-256-GCM encryption for wallet private keys at rest."""

from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def encrypt_private_key(plaintext_key: str, encryption_key_hex: str) -> str:
    """Encrypt a private key using AES-256-GCM.

    Args:
        plaintext_key: The raw private key string.
        encryption_key_hex: 64-char hex string (32 bytes) used as the AES key.

    Returns:
        Base64-encoded string containing nonce + ciphertext + tag.
    """
    if not encryption_key_hex:
        raise ValueError("ENCRYPTION_KEY not configured")

    key_bytes = bytes.fromhex(encryption_key_hex)
    nonce = os.urandom(12)
    aesgcm = AESGCM(key_bytes)
    ciphertext = aesgcm.encrypt(nonce, plaintext_key.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def decrypt_private_key(encrypted: str, encryption_key_hex: str) -> str:
    """Decrypt a private key previously encrypted with encrypt_private_key.

    Args:
        encrypted: Base64-encoded nonce + ciphertext + tag.
        encryption_key_hex: 64-char hex string (32 bytes) used as the AES key.

    Returns:
        The original plaintext private key.
    """
    if not encryption_key_hex:
        raise ValueError("ENCRYPTION_KEY not configured")

    key_bytes = bytes.fromhex(encryption_key_hex)
    raw = base64.b64decode(encrypted)
    nonce = raw[:12]
    ciphertext = raw[12:]
    aesgcm = AESGCM(key_bytes)
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
