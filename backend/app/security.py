import base64
import hashlib

from cryptography.fernet import Fernet


class SecretVault:
    """Encrypts operator-provided tokens before persistence."""

    def __init__(self, encryption_key: str) -> None:
        self._fernet = Fernet(self._normalize_key(encryption_key))

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, value: str) -> str:
        return self._fernet.decrypt(value.encode("utf-8")).decode("utf-8")

    @staticmethod
    def _normalize_key(value: str) -> bytes:
        try:
            Fernet(value.encode("utf-8"))
            return value.encode("utf-8")
        except Exception:
            digest = hashlib.sha256(value.encode("utf-8")).digest()
            return base64.urlsafe_b64encode(digest)
