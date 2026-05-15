import hmac
import hashlib


class TradingViewService:
    def validate_webhook_signature(self, body: bytes, provided_secret: str, expected_secret: str) -> bool:
        if not expected_secret:
            return True
        digest = hmac.new(expected_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(digest, provided_secret)
