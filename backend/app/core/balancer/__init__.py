"""Core load balancing and failover routing package."""
from backend.app.core.balancer.router import (
    DEFAULT_COOLDOWN_SECONDS,
    MAX_FAILOVER_ATTEMPTS,
    CascadeRouter,
)

__all__ = [
    "DEFAULT_COOLDOWN_SECONDS",
    "MAX_FAILOVER_ATTEMPTS",
    "CascadeRouter",
]
