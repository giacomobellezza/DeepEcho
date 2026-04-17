"""
Session cache manager for pre-computed deployment metrics.

Provides the SessionCache class for efficiently caching and retrieving
pre-computed metrics (PRH data, acceleration, jerk) per deployment.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import numpy as np
import pandas as pd


@dataclass
class DeploymentMetrics:
    """
    Container for pre-computed metrics for a single deployment.

    Attributes:
        prh_data: DataFrame with pitch, roll, heading, depth, speed, Gy_Filt columns
        acceleration: (N, 3) numpy array of acceleration (ax, ay, az)
        jerk: (N,) numpy array of pre-computed jerk values
        hz: Sampling frequency in Hz (typically 10)
    """

    prh_data: pd.DataFrame
    acceleration: np.ndarray
    jerk: np.ndarray
    hz: int


@dataclass
class SpectrogramCache:
    """
    Container for cached spectrogram data.

    Attributes:
        freqs: Array of frequency values
        times: Array of time values
        power: 2D array of power values (sampled)
        resolution: Resolution level (64, 128, etc.)
        start_idx: Start index of the cached range
        end_idx: End index of the cached range
    """

    freqs: np.ndarray
    times: np.ndarray
    power: np.ndarray
    resolution: int
    start_idx: int
    end_idx: int


class SessionCache:
    """
    Cache manager for deployment metrics.

    Stores pre-computed metrics (PRH data, acceleration, jerk) per deployment
    for fast retrieval and interval extraction. Uses a singleton pattern via
    get_session_cache() function.

    The cache stores complete metrics per deployment and supports efficient
    extraction of intervals for specific time ranges.
    """

    def __init__(self):
        """Initialize empty cache."""
        self._cache: Dict[str, DeploymentMetrics] = {}
        self._spectrogram_cache: Dict[str, SpectrogramCache] = {}

    def load_deployment(
        self,
        deployment_id: str,
        prh_data: pd.DataFrame,
        acceleration: np.ndarray,
        jerk: np.ndarray,
        hz: int,
    ) -> None:
        """
        Load metrics for a deployment into the cache.

        Stores a DeploymentMetrics object containing all pre-computed metrics
        for a deployment. If the deployment already exists, it will be overwritten.

        Args:
            deployment_id: Unique identifier for the deployment
            prh_data: DataFrame with columns: pitch, roll, heading, depth, speed, Gy_Filt
            acceleration: (N, 3) numpy array of acceleration data (ax, ay, az)
            jerk: (N,) numpy array of pre-computed jerk values
            hz: Sampling frequency in Hz

        Returns:
            None
        """
        metrics = DeploymentMetrics(
            prh_data=prh_data,
            acceleration=acceleration,
            jerk=jerk,
            hz=hz,
        )
        self._cache[deployment_id] = metrics

    def has_deployment(self, deployment_id: str) -> bool:
        """
        Check if a deployment is cached.

        Args:
            deployment_id: Unique identifier for the deployment

        Returns:
            True if deployment is in cache, False otherwise
        """
        return deployment_id in self._cache

    def get_deployment(self, deployment_id: str) -> Optional[DeploymentMetrics]:
        """
        Retrieve a deployment's metrics from cache.

        Args:
            deployment_id: Unique identifier for the deployment

        Returns:
            DeploymentMetrics object if cached, None if not found
        """
        return self._cache.get(deployment_id)

    def extract_interval(
        self,
        deployment_id: str,
        start_idx: int,
        end_idx: int,
    ) -> Optional[Tuple[pd.DataFrame, np.ndarray, np.ndarray]]:
        """
        Extract metrics for a specific interval from cached deployment.

        Efficiently extracts a slice of metrics for a specific time interval.
        Indices are clamped to the valid range [0, length). The returned
        PRH dataframe has its indices reset so they start at 0.

        Args:
            deployment_id: Unique identifier for the deployment
            start_idx: Start index (inclusive, clamped to [0, length))
            end_idx: End index (exclusive, clamped to [0, length))

        Returns:
            Tuple of (prh_slice, accel_slice, jerk_slice) where:
            - prh_slice: pd.DataFrame with reset indices
            - accel_slice: (M, 3) numpy array
            - jerk_slice: (M,) numpy array
            Returns None if deployment not found

        Raises:
            No exceptions - indices are automatically clamped to valid range
        """
        metrics = self.get_deployment(deployment_id)
        if metrics is None:
            return None

        # Get the length of the data
        length = len(metrics.prh_data)

        # Clamp indices to valid range [0, length)
        start_idx = max(0, min(start_idx, length))
        end_idx = max(0, min(end_idx, length))

        # Ensure start <= end
        if start_idx > end_idx:
            start_idx, end_idx = end_idx, start_idx

        # Extract slices
        prh_slice = metrics.prh_data.iloc[start_idx:end_idx].reset_index(drop=True)
        accel_slice = metrics.acceleration[start_idx:end_idx]
        jerk_slice = metrics.jerk[start_idx:end_idx]

        return prh_slice, accel_slice, jerk_slice

    def clear(self) -> None:
        """
        Clear all cached deployments.

        Removes all deployment metrics from the cache.

        Returns:
            None
        """
        self._cache.clear()

    def clear_deployment(self, deployment_id: str) -> None:
        """
        Clear a specific deployment from cache.

        Args:
            deployment_id: Unique identifier for the deployment

        Returns:
            None
        """
        if deployment_id in self._cache:
            del self._cache[deployment_id]

    def get(
        self,
        deployment_id: str,
        start_idx: int,
        end_idx: int,
        resolution: int = 64,
    ) -> Optional[SpectrogramCache]:
        """
        Retrieve cached spectrogram data for a deployment.

        Args:
            deployment_id: Unique identifier for the deployment
            start_idx: Start index of the cached range
            end_idx: End index of the cached range
            resolution: Resolution level (default: 64)

        Returns:
            SpectrogramCache object if cached, None if not found
        """
        spec_cache = self._spectrogram_cache.get(deployment_id)
        if spec_cache is None:
            return None

        # Verify the cached data matches the requested range and resolution
        if (spec_cache.start_idx == start_idx and
            spec_cache.end_idx == end_idx and
            spec_cache.resolution == resolution):
            return spec_cache

        return None

    def store(
        self,
        deployment_id: str,
        start_idx: int,
        end_idx: int,
        freqs: np.ndarray,
        times: np.ndarray,
        power: np.ndarray,
        resolution: int = 64,
    ) -> None:
        """
        Store pre-computed spectrogram data for a deployment.

        Args:
            deployment_id: Unique identifier for the deployment
            start_idx: Start index of the cached range
            end_idx: End index of the cached range
            freqs: Array of frequency values
            times: Array of time values
            power: 2D array of power values (sampled)
            resolution: Resolution level (default: 64)

        Returns:
            None
        """
        spec_cache = SpectrogramCache(
            freqs=freqs,
            times=times,
            power=power,
            resolution=resolution,
            start_idx=start_idx,
            end_idx=end_idx,
        )
        self._spectrogram_cache[deployment_id] = spec_cache


# Global singleton instance
_session_cache: Optional[SessionCache] = None


def get_session_cache() -> SessionCache:
    """
    Get the global session cache instance.

    Returns a singleton SessionCache instance, creating it on first call.
    This function provides global access to the cache for use throughout
    the application.

    Returns:
        The global SessionCache instance
    """
    global _session_cache
    if _session_cache is None:
        _session_cache = SessionCache()
    return _session_cache
