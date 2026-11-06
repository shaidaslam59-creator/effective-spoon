"""Constant-time verification of configured API keys."""
import hmac
from hashlib import sha256

class APIKeyAuthenticator:
    def __init__(self, keys: list[str]) -> None:
        self._digests = tuple(sha256(key.encode()).digest() for key in keys if key)

    def verify(self, candidate: str | None) -> bool:
        if not candidate:
            return False
        digest = sha256(candidate.encode()).digest()
        matched = False
        for expected in self._digests:
            matched = hmac.compare_digest(digest, expected) or matched
        return matched
