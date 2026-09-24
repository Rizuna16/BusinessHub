"""
Process-local in-memory rate limiter for Feature #67.

Limits per-email and per-IP request rates.
State is lost on process restart — acceptable for single-worker deployment.
"""
import time
from collections import defaultdict


class RateLimiter:
    """Sliding-window rate limiter with per-key limits."""

    def __init__(self):
        self._store: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Check if request is allowed. Returns True if under limit."""
        now = time.time()
        window_start = now - window_seconds
        self._store[key] = [t for t in self._store[key] if t > window_start]
        if len(self._store[key]) >= max_requests:
            return False
        self._store[key].append(now)
        return True


# Global singleton
_rate_limiter = RateLimiter()

EMAIL_LIMIT = 5
EMAIL_WINDOW = 3600  # 1 hour
IP_LIMIT = 20
IP_WINDOW = 3600     # 1 hour


def is_rate_limited(email: str, ip_address: str) -> bool:
    """Returns True if request should be rejected (rate limited)."""
    email_key = f"forgot:{email.lower().strip()}"
    ip_key = f"forgot_ip:{ip_address}"
    return (
        not _rate_limiter.is_allowed(email_key, EMAIL_LIMIT, EMAIL_WINDOW)
        or not _rate_limiter.is_allowed(ip_key, IP_LIMIT, IP_WINDOW)
    )
