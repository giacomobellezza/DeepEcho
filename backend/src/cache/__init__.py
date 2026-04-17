"""
Cache module for DeepEcho application.

Provides session-based caching of pre-computed deployment metrics.
"""

from .session_cache import (
    SessionCache,
    DeploymentMetrics,
    SpectrogramCache,
    get_session_cache,
)


def get_cache():
    """
    Get the global session cache instance.

    Alias for get_session_cache() for backward compatibility.

    Returns:
        The global SessionCache instance
    """
    return get_session_cache()


__all__ = [
    "SessionCache",
    "DeploymentMetrics",
    "SpectrogramCache",
    "get_session_cache",
    "get_cache",
]
