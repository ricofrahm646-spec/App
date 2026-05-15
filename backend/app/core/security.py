from cryptography.fernet import Fernet, InvalidToken


class SecretVault:
    """Encrypts API tokens before persistence.

    The key is provided through TOKEN_ENCRYPTION_KEY. In development we can
    generate a key, but production deployments should inject a stable key.
    """

    def __init__(self, key: str | None) -> None:
        self.key = key or Fernet.generate_key().decode("utf-8")
        self._fernet = Fernet(self.key.encode("utf-8"))

    @staticmethod
    def generate_key() -> str:
        return Fernet.generate_key().decode("utf-8")

    def encrypt(self, value: str) -> str:
        if not value:
            raise ValueError("Cannot encrypt empty secrets")
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Secret could not be decrypted with the active key") from exc
