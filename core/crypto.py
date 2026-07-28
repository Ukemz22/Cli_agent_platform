"""
Encrypt/decrypt BYOK LLM keys before storing them (Rule 3: never
hand-roll crypto — uses the vetted `cryptography` library's Fernet,
which is symmetric authenticated encryption).
"""
from cryptography.fernet import Fernet

from core.config import settings


def _get_fernet() -> Fernet:
    # settings.secret_key must be a valid Fernet key (32 url-safe base64 bytes).
    return Fernet(settings.secret_key.encode("utf-8"))


def encrypt_key(raw_key: str) -> str:
    return _get_fernet().encrypt(raw_key.encode("utf-8")).decode("utf-8")


def decrypt_key(encrypted_key: str) -> str:
    return _get_fernet().decrypt(encrypted_key.encode("utf-8")).decode("utf-8")
