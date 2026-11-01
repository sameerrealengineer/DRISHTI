"""Password/PIN hashing and phone-number protection (PRD §14, §16.4).

Phones are stored as `phone_hash` (SHA-256 with a server pepper, for lookup) and
`phone_enc` (AES-GCM, for sending). Never log raw numbers; use `mask_phone`.
"""

from __future__ import annotations

import base64
import hashlib
import os
import re

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from passlib.context import CryptContext

from app.config import get_settings

_pwd = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_secret(secret: str) -> str:
    return _pwd.hash(secret)


def verify_secret(secret: str, hashed: str | None) -> bool:
    return bool(hashed) and _pwd.verify(secret, hashed)


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 10:
        digits = "91" + digits
    return "+" + digits


def phone_hash(phone: str) -> str:
    pepper = get_settings().phone_pepper
    return hashlib.sha256((pepper + normalize_phone(phone)).encode()).hexdigest()


def _key() -> bytes:
    s = get_settings()
    if s.phone_enc_key:
        return base64.b64decode(s.phone_enc_key)
    return hashlib.sha256(("phone-enc:" + s.jwt_secret).encode()).digest()


def encrypt_phone(phone: str) -> str:
    nonce = os.urandom(12)
    ct = AESGCM(_key()).encrypt(nonce, normalize_phone(phone).encode(), None)
    return base64.b64encode(nonce + ct).decode()


def decrypt_phone(token: str) -> str:
    raw = base64.b64decode(token)
    return AESGCM(_key()).decrypt(raw[:12], raw[12:], None).decode()


def mask_phone(phone: str) -> str:
    """'+919876543321' -> '98xxxxx321'."""
    d = re.sub(r"\D", "", phone)[-10:]
    return d[:2] + "x" * 5 + d[-3:] if len(d) == 10 else "x" * len(d)
