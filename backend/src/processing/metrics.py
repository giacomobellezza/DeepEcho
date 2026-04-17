"""
Metric computation module for DeepEcho cetacean analysis.

Implements functions for calculating jerk, PRH metrics, and 3D trajectory
based on acceleration, gyro, and PRH data.

Formulas are based on the MATLAB plot_dynamic_creak() function.
"""

import numpy as np
import pandas as pd
from typing import Dict, List


def compute_jerk(
    accel_x: np.ndarray,
    accel_y: np.ndarray,
    accel_z: np.ndarray,
    hz: int = 10,
) -> np.ndarray:
    """
    Compute jerk (rate of change of acceleration) from acceleration data.

    Implements the MATLAB formula:
        jerk = [0; sqrt(sum(diff(Aw_raw).^2, 2)) * hz]

    The first element is always 0 (no previous sample to compare).
    Subsequent elements are the magnitude of acceleration change multiplied by hz.

    Args:
        accel_x: Acceleration in X direction (m/s^2)
        accel_y: Acceleration in Y direction (m/s^2)
        accel_z: Acceleration in Z direction (m/s^2)
        hz: Sampling rate in Hz (default: 10)

    Returns:
        numpy array of jerk values (g/s) with same length as input acceleration arrays.
        First element is always 0.

    Raises:
        ValueError: If input arrays have different lengths or are empty
    """
    # Convert inputs to numpy arrays
    accel_x = np.asarray(accel_x, dtype=np.float64)
    accel_y = np.asarray(accel_y, dtype=np.float64)
    accel_z = np.asarray(accel_z, dtype=np.float64)

    # Validate inputs
    if len(accel_x) != len(accel_y) or len(accel_x) != len(accel_z):
        raise ValueError("Input acceleration arrays must have the same length")

    if len(accel_x) == 0:
        raise ValueError("Input acceleration arrays cannot be empty")

    # Stack accelerations into matrix for vectorized computation
    # Shape: (n_samples, 3)
    Aw = np.column_stack([accel_x, accel_y, accel_z])

    # Compute differences between consecutive samples
    diff_Aw = np.diff(Aw, axis=0)

    # Compute jerk magnitude: sqrt(sum of squared differences) * hz
    jerk_magnitude = np.sqrt(np.sum(diff_Aw**2, axis=1)) * hz

    # Prepend 0 for the first element (no previous sample)
    jerk = np.concatenate([[0.0], jerk_magnitude])

    return jerk


def compute_prh_metrics(prh_df: pd.DataFrame) -> Dict[str, np.ndarray]:
    """
    Extract PRH (Pitch, Roll, Heading) metrics from a DataFrame.

    Extracts smoothed PRH values and gyro data from the DataFrame.
    These values are typically already filtered/smoothed by the PRH processing pipeline.

    Args:
        prh_df: pandas DataFrame containing PRH data with columns:
            - pitch_smoothed: Pitch angle in degrees
            - roll_smoothed_wrapped: Roll angle in degrees (wrapped)
            - heading_smoothed_wrapped: Heading angle in degrees (wrapped)
            - depth_smoothed: Depth in meters
            - speed_smoothed: Speed in m/s
            - Gy_Filt: Gyro Y-axis filtered angular velocity (rad/s)

    Returns:
        Dictionary with keys: pitch_smoothed, roll_smoothed_wrapped, heading_smoothed_wrapped,
                             depth_smoothed, speed_smoothed, Gy_Filt
        Each value is a numpy array of the corresponding column data

    Raises:
        KeyError: If required columns are missing from the DataFrame
    """
    required_columns = {
        "pitch_smoothed",
        "roll_smoothed_wrapped",
        "heading_smoothed_wrapped",
        "depth_smoothed",
        "speed_smoothed",
        "Gy_Filt",
    }

    # Check all required columns are present
    missing = required_columns - set(prh_df.columns)
    if missing:
        raise KeyError(
            f"Missing columns: {missing}. Available columns: {set(prh_df.columns)}"
        )

    # Extract metrics as numpy arrays
    metrics = {
        "pitch_smoothed": prh_df["pitch_smoothed"].values.astype(np.float64),
        "roll_smoothed_wrapped": prh_df["roll_smoothed_wrapped"].values.astype(np.float64),
        "heading_smoothed_wrapped": prh_df["heading_smoothed_wrapped"].values.astype(np.float64),
        "depth_smoothed": prh_df["depth_smoothed"].values.astype(np.float64),
        "speed_smoothed": prh_df["speed_smoothed"].values.astype(np.float64),
        "Gy_Filt": prh_df["Gy_Filt"].values.astype(np.float64),
    }

    return metrics


def compute_trajectory(
    speed_smoothed: np.ndarray,
    heading_smoothed_wrapped: np.ndarray,
    pitch_smoothed: np.ndarray,
    depth_smoothed: np.ndarray,
    hz: int = 10,
) -> Dict[str, np.ndarray]:
    """
    Compute 3D trajectory (dx, dy, dz) from motion parameters.

    Implements the MATLAB trajectory formulas:
        d_s = speed * (1/hz)  # Time step distance
        p_r = pitch in radians
        h_r = -heading in radians (negative because heading is opposite to x-axis rotation)
        dx = cumsum(d_s .* cos(h_r) .* cos(p_r))
        dy = cumsum(d_s .* sin(h_r) .* cos(p_r))
        dz = depth

    The negative heading is used to align with standard coordinate systems.

    Args:
        speed_smoothed: Speed in m/s
        heading_smoothed_wrapped: Heading angle in degrees (wrapped to [-180, 180] or [0, 360])
        pitch_smoothed: Pitch angle in degrees (positive = down)
        depth_smoothed: Depth in meters (positive = down)
        hz: Sampling rate in Hz (default: 10)

    Returns:
        Dictionary with keys: dx, dy, dz
        - dx: Cumulative distance in X direction (m)
        - dy: Cumulative distance in Y direction (m)
        - dz: Depth (same as input depth_smoothed)

    Raises:
        ValueError: If input arrays have different lengths or are empty
    """
    # Convert inputs to numpy arrays
    speed_smoothed = np.asarray(speed_smoothed, dtype=np.float64)
    heading_smoothed_wrapped = np.asarray(heading_smoothed_wrapped, dtype=np.float64)
    pitch_smoothed = np.asarray(pitch_smoothed, dtype=np.float64)
    depth_smoothed = np.asarray(depth_smoothed, dtype=np.float64)

    # Validate inputs
    if not (len(speed_smoothed) == len(heading_smoothed_wrapped) == len(pitch_smoothed) == len(depth_smoothed)):
        raise ValueError("All input arrays must have the same length")

    if len(speed_smoothed) == 0:
        raise ValueError("Input arrays cannot be empty")

    # Convert angles from degrees to radians
    # Heading is negated to align with standard coordinate system (East = 0°, North = 90°)
    heading_rad = -np.deg2rad(heading_smoothed_wrapped)
    pitch_rad = np.deg2rad(pitch_smoothed)

    # Compute time step distance: speed * (1/hz)
    dt = 1.0 / hz
    d_s = speed_smoothed * dt

    # Compute horizontal displacement components
    # These account for both heading and pitch (pitch reduces horizontal component)
    dx_step = d_s * np.cos(heading_rad) * np.cos(pitch_rad)
    dy_step = d_s * np.sin(heading_rad) * np.cos(pitch_rad)

    # Compute cumulative position
    dx = np.cumsum(dx_step)
    dy = np.cumsum(dy_step)
    dz = depth_smoothed.copy()

    return {
        "dx": dx,
        "dy": dy,
        "dz": dz,
    }
