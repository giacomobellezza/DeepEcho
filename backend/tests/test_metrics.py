import pytest
import numpy as np
import pandas as pd
import tempfile
from pathlib import Path

from src.processing.metrics import (
    compute_jerk,
    compute_prh_metrics,
    compute_trajectory,
)


class TestComputeJerk:
    """Test suite for jerk computation."""

    def test_jerk_basic_calculation(self):
        """Test jerk calculation with simple data."""
        # Create simple acceleration data
        accel_x = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        accel_y = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        accel_z = np.array([0.0, 1.0, 2.0, 3.0, 4.0])

        jerk = compute_jerk(accel_x, accel_y, accel_z, hz=10)

        # Jerk should have same length as input (first element is 0)
        assert len(jerk) == len(accel_x)
        assert jerk.dtype == np.float64

        # First element must be 0 (per MATLAB formula)
        assert jerk[0] == 0.0

        # For constant acceleration difference (1.0), jerk should be constant
        # diff = 1.0, sqrt(3 * 1.0^2 * 10^2) = sqrt(300) ≈ 17.32
        for i in range(1, len(jerk)):
            assert jerk[i] == pytest.approx(np.sqrt(3) * 10, abs=0.1)

    def test_jerk_zero_acceleration(self):
        """Test jerk with constant (zero change) acceleration."""
        accel_x = np.array([1.0, 1.0, 1.0, 1.0])
        accel_y = np.array([2.0, 2.0, 2.0, 2.0])
        accel_z = np.array([3.0, 3.0, 3.0, 3.0])

        jerk = compute_jerk(accel_x, accel_y, accel_z, hz=10)

        assert len(jerk) == 4
        assert jerk[0] == 0.0
        # All other values should be close to 0
        for i in range(1, len(jerk)):
            assert jerk[i] == pytest.approx(0.0, abs=1e-10)

    def test_jerk_different_hz(self):
        """Test jerk with different sampling rates."""
        accel_x = np.array([0.0, 1.0, 2.0])
        accel_y = np.array([0.0, 1.0, 2.0])
        accel_z = np.array([0.0, 1.0, 2.0])

        jerk_10hz = compute_jerk(accel_x, accel_y, accel_z, hz=10)
        jerk_20hz = compute_jerk(accel_x, accel_y, accel_z, hz=20)

        # Higher hz should give higher jerk values (derivative scaling)
        assert jerk_20hz[1] > jerk_10hz[1]

    def test_jerk_single_element(self):
        """Test jerk with single element array."""
        accel_x = np.array([1.0])
        accel_y = np.array([2.0])
        accel_z = np.array([3.0])

        jerk = compute_jerk(accel_x, accel_y, accel_z, hz=10)

        assert len(jerk) == 1
        assert jerk[0] == 0.0

    def test_jerk_two_elements(self):
        """Test jerk with two element array."""
        accel_x = np.array([0.0, 1.0])
        accel_y = np.array([0.0, 1.0])
        accel_z = np.array([0.0, 1.0])

        jerk = compute_jerk(accel_x, accel_y, accel_z, hz=10)

        assert len(jerk) == 2
        assert jerk[0] == 0.0
        assert jerk[1] > 0.0

    def test_jerk_numpy_array_input(self):
        """Test jerk with numpy array input."""
        accel_x = np.array([0.0, 1.0, 2.0])
        accel_y = np.array([0.0, 1.0, 2.0])
        accel_z = np.array([0.0, 1.0, 2.0])

        jerk = compute_jerk(accel_x, accel_y, accel_z, hz=10)

        assert isinstance(jerk, np.ndarray)
        assert len(jerk) == 3


class TestComputePRHMetrics:
    """Test suite for PRH metrics extraction."""

    def test_prh_metrics_basic(self):
        """Test basic PRH metrics extraction."""
        # Create a simple DataFrame with required columns
        data = {
            "pitch_smoothed": np.array([5.0, 10.0, 15.0, 20.0]),
            "roll_smoothed_wrapped": np.array([-5.0, 0.0, 5.0, 10.0]),
            "heading_smoothed_wrapped": np.array([180.0, 190.0, 200.0, 210.0]),
            "depth_smoothed": np.array([10.0, 15.0, 20.0, 25.0]),
            "speed_smoothed": np.array([1.0, 1.5, 2.0, 2.5]),
            "Gy_Filt": np.array([0.1, 0.2, 0.3, 0.4]),
        }
        prh_df = pd.DataFrame(data)

        metrics = compute_prh_metrics(prh_df)

        # Check all required keys are present
        assert set(metrics.keys()) == {
            "pitch_smoothed",
            "roll_smoothed_wrapped",
            "heading_smoothed_wrapped",
            "depth_smoothed",
            "speed_smoothed",
            "Gy_Filt",
        }

        # Check all values match input
        np.testing.assert_array_equal(metrics["pitch_smoothed"], data["pitch_smoothed"])
        np.testing.assert_array_equal(
            metrics["roll_smoothed_wrapped"], data["roll_smoothed_wrapped"]
        )
        np.testing.assert_array_equal(
            metrics["heading_smoothed_wrapped"], data["heading_smoothed_wrapped"]
        )
        np.testing.assert_array_equal(metrics["depth_smoothed"], data["depth_smoothed"])
        np.testing.assert_array_equal(metrics["speed_smoothed"], data["speed_smoothed"])
        np.testing.assert_array_equal(metrics["Gy_Filt"], data["Gy_Filt"])

    def test_prh_metrics_empty_dataframe(self):
        """Test PRH metrics with empty DataFrame."""
        data = {
            "pitch_smoothed": np.array([]),
            "roll_smoothed_wrapped": np.array([]),
            "heading_smoothed_wrapped": np.array([]),
            "depth_smoothed": np.array([]),
            "speed_smoothed": np.array([]),
            "Gy_Filt": np.array([]),
        }
        prh_df = pd.DataFrame(data)

        metrics = compute_prh_metrics(prh_df)

        assert len(metrics["pitch_smoothed"]) == 0

    def test_prh_metrics_missing_column(self):
        """Test that KeyError is raised for missing columns."""
        prh_df = pd.DataFrame({"pitch_smoothed": [1.0, 2.0, 3.0]})

        with pytest.raises(KeyError):
            compute_prh_metrics(prh_df)

    def test_prh_metrics_large_dataset(self):
        """Test PRH metrics with larger dataset."""
        n = 1000
        data = {
            "pitch_smoothed": np.random.randn(n) * 20,
            "roll_smoothed_wrapped": np.random.randn(n) * 20,
            "heading_smoothed_wrapped": np.random.randn(n) * 180 + 180,
            "depth_smoothed": np.random.randn(n) * 50 + 100,
            "speed_smoothed": np.abs(np.random.randn(n)) + 1.0,
            "Gy_Filt": np.random.randn(n),
        }
        prh_df = pd.DataFrame(data)

        metrics = compute_prh_metrics(prh_df)

        assert len(metrics["pitch_smoothed"]) == n


class TestComputeTrajectory:
    """Test suite for 3D trajectory computation."""

    def test_trajectory_basic(self):
        """Test basic trajectory computation."""
        speed_smoothed = np.array([1.0, 1.0, 1.0, 1.0])
        heading_smoothed_wrapped = np.array([0.0, 0.0, 0.0, 0.0])  # degrees
        pitch_smoothed = np.array([0.0, 0.0, 0.0, 0.0])  # degrees
        depth_smoothed = np.array([10.0, 11.0, 12.0, 13.0])

        trajectory = compute_trajectory(
            speed_smoothed,
            heading_smoothed_wrapped,
            pitch_smoothed,
            depth_smoothed,
            hz=10,
        )

        # Check all keys are present
        assert set(trajectory.keys()) == {"dx", "dy", "dz"}

        # Check all arrays have correct length
        assert len(trajectory["dx"]) == 4
        assert len(trajectory["dy"]) == 4
        assert len(trajectory["dz"]) == 4

        # Check dx, dy, dz are numpy arrays
        assert isinstance(trajectory["dx"], np.ndarray)
        assert isinstance(trajectory["dy"], np.ndarray)
        assert isinstance(trajectory["dz"], np.ndarray)

        # dz should match input depth
        np.testing.assert_array_equal(trajectory["dz"], depth_smoothed)

        # With heading=0 and pitch=0, movement should be mostly in +X direction
        # dx should be cumulative and increasing
        assert trajectory["dx"][1] > trajectory["dx"][0]
        assert trajectory["dx"][-1] > trajectory["dx"][0]

    def test_trajectory_circular_motion(self):
        """Test trajectory with circular heading change."""
        speed_smoothed = np.array([1.0] * 360)
        # Heading changes from 0 to 359 degrees (full circle)
        heading_smoothed_wrapped = np.linspace(0, 359, 360)
        pitch_smoothed = np.array([0.0] * 360)
        depth_smoothed = np.array([10.0] * 360)

        trajectory = compute_trajectory(
            speed_smoothed,
            heading_smoothed_wrapped,
            pitch_smoothed,
            depth_smoothed,
            hz=10,
        )

        # For a complete circle with constant speed and pitch, dx and dy should
        # return approximately to their starting position
        assert trajectory["dx"][-1] == pytest.approx(trajectory["dx"][0], abs=1.0)
        assert trajectory["dy"][-1] == pytest.approx(trajectory["dy"][0], abs=1.0)

    def test_trajectory_pitch_variation(self):
        """Test trajectory with varying pitch."""
        speed_smoothed = np.array([1.0, 1.0, 1.0, 1.0])
        heading_smoothed_wrapped = np.array([0.0, 0.0, 0.0, 0.0])
        pitch_smoothed = np.array([0.0, 10.0, 20.0, 30.0])  # Pitching down
        depth_smoothed = np.array([10.0, 11.0, 12.0, 13.0])

        trajectory = compute_trajectory(
            speed_smoothed,
            heading_smoothed_wrapped,
            pitch_smoothed,
            depth_smoothed,
            hz=10,
        )

        # With increasing positive pitch (downward), horizontal distance (dx) should decrease
        assert trajectory["dx"][3] < trajectory["dx"][0] + (1.0 / 10) * 4

    def test_trajectory_different_hz(self):
        """Test trajectory with different sampling rates."""
        speed_smoothed = np.array([1.0, 1.0, 1.0])
        heading_smoothed_wrapped = np.array([0.0, 0.0, 0.0])
        pitch_smoothed = np.array([0.0, 0.0, 0.0])
        depth_smoothed = np.array([10.0, 10.0, 10.0])

        traj_10hz = compute_trajectory(
            speed_smoothed,
            heading_smoothed_wrapped,
            pitch_smoothed,
            depth_smoothed,
            hz=10,
        )

        traj_5hz = compute_trajectory(
            speed_smoothed,
            heading_smoothed_wrapped,
            pitch_smoothed,
            depth_smoothed,
            hz=5,
        )

        # Higher hz means shorter time steps, so distances should be smaller
        assert np.abs(traj_10hz["dx"][-1]) < np.abs(traj_5hz["dx"][-1])

    def test_trajectory_zero_speed(self):
        """Test trajectory with zero speed."""
        speed_smoothed = np.array([0.0, 0.0, 0.0, 0.0])
        heading_smoothed_wrapped = np.array([0.0, 0.0, 0.0, 0.0])
        pitch_smoothed = np.array([0.0, 0.0, 0.0, 0.0])
        depth_smoothed = np.array([10.0, 10.0, 10.0, 10.0])

        trajectory = compute_trajectory(
            speed_smoothed,
            heading_smoothed_wrapped,
            pitch_smoothed,
            depth_smoothed,
            hz=10,
        )

        # With zero speed, dx and dy should be all zeros or very close
        np.testing.assert_array_almost_equal(trajectory["dx"], 0.0)
        np.testing.assert_array_almost_equal(trajectory["dy"], 0.0)

    def test_trajectory_single_element(self):
        """Test trajectory with single element array."""
        speed_smoothed = np.array([1.0])
        heading_smoothed_wrapped = np.array([0.0])
        pitch_smoothed = np.array([0.0])
        depth_smoothed = np.array([10.0])

        trajectory = compute_trajectory(
            speed_smoothed,
            heading_smoothed_wrapped,
            pitch_smoothed,
            depth_smoothed,
            hz=10,
        )

        assert len(trajectory["dx"]) == 1
        assert len(trajectory["dy"]) == 1
        assert len(trajectory["dz"]) == 1
        # Single element: cumsum produces one value = speed * (1/hz) = 1.0 * 0.1 = 0.1
        assert trajectory["dx"][0] == pytest.approx(0.1, abs=1e-10)
        assert trajectory["dy"][0] == pytest.approx(0.0, abs=1e-10)

    def test_trajectory_negative_heading(self):
        """Test trajectory with negative heading values."""
        speed_smoothed = np.array([1.0, 1.0])
        heading_smoothed_wrapped = np.array([-45.0, -45.0])  # Southwest
        pitch_smoothed = np.array([0.0, 0.0])
        depth_smoothed = np.array([10.0, 10.0])

        trajectory = compute_trajectory(
            speed_smoothed,
            heading_smoothed_wrapped,
            pitch_smoothed,
            depth_smoothed,
            hz=10,
        )

        # With heading=-45 (negated to +45 rad), cos(heading) is positive, sin(heading) is positive
        # So dx and dy should both be positive but cumsum is always increasing
        assert trajectory["dx"][1] > trajectory["dx"][0]
        assert trajectory["dy"][1] > trajectory["dy"][0]
        # Verify that with equal speed and heading, displacement is equal in both axes
        dx_step = trajectory["dx"][1] - trajectory["dx"][0]
        dy_step = trajectory["dy"][1] - trajectory["dy"][0]
        assert dx_step == pytest.approx(dy_step, abs=1e-10)
