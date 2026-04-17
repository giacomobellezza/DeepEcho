"""
Test suite for session cache manager.

Tests the SessionCache class for caching pre-computed metrics per deployment.
"""

import pytest
import numpy as np
import pandas as pd

from src.cache.session_cache import SessionCache


class TestCacheInitialization:
    """Test suite for SessionCache initialization."""

    def test_cache_initialization(self):
        """Test that cache initializes empty."""
        cache = SessionCache()

        # Cache should be empty initially
        assert len(cache._cache) == 0

        # Should not have any deployments
        assert not cache.has_deployment("test_deploy_1")

    def test_load_deployment(self):
        """Test loading deployment metrics into cache."""
        cache = SessionCache()

        # Create sample data
        prh_data = pd.DataFrame({
            "pitch": [5.0, 10.0, 15.0],
            "roll": [-5.0, 0.0, 5.0],
            "heading": [180.0, 190.0, 200.0],
            "depth": [10.0, 15.0, 20.0],
            "speed": [1.0, 1.5, 2.0],
            "Gy_Filt": [0.1, 0.2, 0.3],
        })
        acceleration = np.array([[0.1, 0.2, 0.3], [0.2, 0.3, 0.4], [0.3, 0.4, 0.5]])
        jerk = np.array([0.0, 1.5, 2.5])
        hz = 10

        # Load into cache
        cache.load_deployment("deploy_1", prh_data, acceleration, jerk, hz)

        # Verify deployment is cached
        assert cache.has_deployment("deploy_1")

        # Verify we can retrieve it
        metrics = cache.get_deployment("deploy_1")
        assert metrics is not None
        assert len(metrics.prh_data) == 3
        assert metrics.acceleration.shape == (3, 3)
        assert len(metrics.jerk) == 3
        assert metrics.hz == 10

    def test_get_nonexistent_deployment(self):
        """Test that getting nonexistent deployment returns None."""
        cache = SessionCache()

        result = cache.get_deployment("nonexistent")
        assert result is None

    def test_clear_deployment(self):
        """Test clearing a specific deployment."""
        cache = SessionCache()

        # Create and load sample data
        prh_data = pd.DataFrame({
            "pitch": [5.0, 10.0],
            "roll": [-5.0, 0.0],
            "heading": [180.0, 190.0],
            "depth": [10.0, 15.0],
            "speed": [1.0, 1.5],
            "Gy_Filt": [0.1, 0.2],
        })
        acceleration = np.array([[0.1, 0.2, 0.3], [0.2, 0.3, 0.4]])
        jerk = np.array([0.0, 1.5])

        cache.load_deployment("deploy_1", prh_data, acceleration, jerk, 10)
        cache.load_deployment("deploy_2", prh_data, acceleration, jerk, 10)

        # Clear one deployment
        cache.clear_deployment("deploy_1")

        # Verify it's cleared but other remains
        assert not cache.has_deployment("deploy_1")
        assert cache.has_deployment("deploy_2")

    def test_clear_all(self):
        """Test clearing all cache."""
        cache = SessionCache()

        # Create and load sample data
        prh_data = pd.DataFrame({
            "pitch": [5.0],
            "roll": [-5.0],
            "heading": [180.0],
            "depth": [10.0],
            "speed": [1.0],
            "Gy_Filt": [0.1],
        })
        acceleration = np.array([[0.1, 0.2, 0.3]])
        jerk = np.array([0.0])

        cache.load_deployment("deploy_1", prh_data, acceleration, jerk, 10)
        cache.load_deployment("deploy_2", prh_data, acceleration, jerk, 10)

        # Clear all
        cache.clear()

        # Verify all cleared
        assert not cache.has_deployment("deploy_1")
        assert not cache.has_deployment("deploy_2")
        assert len(cache._cache) == 0


class TestIntervalExtraction:
    """Test suite for interval extraction from cached metrics."""

    def test_extract_interval_basic(self):
        """Test extracting a basic interval from cached metrics."""
        cache = SessionCache()

        # Create sample data with 10 samples
        prh_data = pd.DataFrame({
            "pitch": np.arange(10) * 1.0,
            "roll": np.arange(10) * 2.0,
            "heading": np.arange(10) * 3.0,
            "depth": np.arange(10) * 4.0,
            "speed": np.arange(10) * 0.5,
            "Gy_Filt": np.arange(10) * 0.1,
        })
        acceleration = np.random.randn(10, 3)
        jerk = np.arange(10) * 0.5

        cache.load_deployment("deploy_1", prh_data, acceleration, jerk, 10)

        # Extract interval [2, 5)
        prh_slice, accel_slice, jerk_slice = cache.extract_interval("deploy_1", 2, 5)

        # Verify shapes
        assert len(prh_slice) == 3
        assert accel_slice.shape == (3, 3)
        assert len(jerk_slice) == 3

        # Verify content
        assert prh_slice["pitch"].values[0] == pytest.approx(2.0)
        assert prh_slice["pitch"].values[2] == pytest.approx(4.0)
        np.testing.assert_array_almost_equal(jerk_slice, np.array([1.0, 1.5, 2.0]))

    def test_extract_interval_full_range(self):
        """Test extracting full interval."""
        cache = SessionCache()

        # Create sample data
        prh_data = pd.DataFrame({
            "pitch": [1.0, 2.0, 3.0, 4.0, 5.0],
            "roll": [10.0, 20.0, 30.0, 40.0, 50.0],
            "heading": [100.0, 200.0, 300.0, 400.0, 500.0],
            "depth": [10.0, 20.0, 30.0, 40.0, 50.0],
            "speed": [1.0, 2.0, 3.0, 4.0, 5.0],
            "Gy_Filt": [0.1, 0.2, 0.3, 0.4, 0.5],
        })
        acceleration = np.ones((5, 3))
        jerk = np.array([0.0, 1.0, 2.0, 3.0, 4.0])

        cache.load_deployment("deploy_1", prh_data, acceleration, jerk, 10)

        # Extract full range
        prh_slice, accel_slice, jerk_slice = cache.extract_interval("deploy_1", 0, 5)

        assert len(prh_slice) == 5
        assert accel_slice.shape == (5, 3)
        assert len(jerk_slice) == 5

    def test_extract_interval_clamping(self):
        """Test that indices are clamped to valid range."""
        cache = SessionCache()

        # Create sample data with 5 samples
        prh_data = pd.DataFrame({
            "pitch": [1.0, 2.0, 3.0, 4.0, 5.0],
            "roll": [10.0, 20.0, 30.0, 40.0, 50.0],
            "heading": [100.0, 200.0, 300.0, 400.0, 500.0],
            "depth": [10.0, 20.0, 30.0, 40.0, 50.0],
            "speed": [1.0, 2.0, 3.0, 4.0, 5.0],
            "Gy_Filt": [0.1, 0.2, 0.3, 0.4, 0.5],
        })
        acceleration = np.ones((5, 3))
        jerk = np.array([0.0, 1.0, 2.0, 3.0, 4.0])

        cache.load_deployment("deploy_1", prh_data, acceleration, jerk, 10)

        # Request interval beyond bounds
        prh_slice, accel_slice, jerk_slice = cache.extract_interval("deploy_1", -5, 100)

        # Should clamp to [0, 5)
        assert len(prh_slice) == 5
        assert accel_slice.shape == (5, 3)
        assert len(jerk_slice) == 5

    def test_extract_interval_nonexistent_deployment(self):
        """Test extracting from nonexistent deployment returns None."""
        cache = SessionCache()

        result = cache.extract_interval("nonexistent", 0, 5)
        assert result is None

    def test_extract_interval_prh_indices_reset(self):
        """Test that extracted PRH dataframe has reset indices."""
        cache = SessionCache()

        # Create sample data
        prh_data = pd.DataFrame({
            "pitch": [1.0, 2.0, 3.0, 4.0, 5.0],
            "roll": [10.0, 20.0, 30.0, 40.0, 50.0],
            "heading": [100.0, 200.0, 300.0, 400.0, 500.0],
            "depth": [10.0, 20.0, 30.0, 40.0, 50.0],
            "speed": [1.0, 2.0, 3.0, 4.0, 5.0],
            "Gy_Filt": [0.1, 0.2, 0.3, 0.4, 0.5],
        })
        acceleration = np.ones((5, 3))
        jerk = np.array([0.0, 1.0, 2.0, 3.0, 4.0])

        cache.load_deployment("deploy_1", prh_data, acceleration, jerk, 10)

        # Extract interval [1, 4)
        prh_slice, _, _ = cache.extract_interval("deploy_1", 1, 4)

        # Verify indices are reset to 0, 1, 2
        assert list(prh_slice.index) == [0, 1, 2]
        assert prh_slice["pitch"].iloc[0] == pytest.approx(2.0)
