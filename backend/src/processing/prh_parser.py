import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List


def parse_prh_csv(filepath: str) -> pd.DataFrame:
    """
    Parse a PRH (Position, Rate, Heading) CSV file.

    Args:
        filepath: Path to the PRH CSV file

    Returns:
        pandas DataFrame containing the parsed PRH data

    Raises:
        FileNotFoundError: If the file does not exist
        ValueError: If the file is not a valid CSV file
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    try:
        prh_df = pd.read_csv(filepath)
    except Exception as e:
        raise ValueError(f"Invalid CSV file: {filepath}") from e

    return prh_df


def extract_prh_slice(
    prh_df: pd.DataFrame, start_idx: int, end_idx: int
) -> Dict[str, np.ndarray]:
    """
    Extract a slice of PRH data between two indices.

    Args:
        prh_df: pandas DataFrame containing PRH data
        start_idx: Starting index (inclusive)
        end_idx: Ending index (exclusive)

    Returns:
        Dictionary with keys: depth, speed, pitch, roll, heading, accel_x, accel_y, accel_z, gyro_y
        Each value is a numpy array of the corresponding column data

    Raises:
        KeyError: If required columns are missing from the DataFrame
        IndexError: If indices are out of bounds
    """
    # Map output keys to possible column names (handle different CSV formats)
    column_mapping = {
        "depth": ["depth", "depth_smoothed"],
        "speed": ["speed", "speed_smoothed"],
        "pitch": ["pitch", "pitch_smoothed"],
        "roll": ["roll", "roll_smoothed", "roll_smoothed_wrapped"],
        "heading": ["heading", "heading_smoothed", "heading_smoothed_wrapped"],
        "accel_x": ["accel_x", "Ax_Filt"],
        "accel_y": ["accel_y", "Ay_Filt"],
        "accel_z": ["accel_z", "Az_Filt"],
        "gyro_y": ["gyro_y", "Gy_Filt"],
    }

    # Find actual columns in DataFrame
    actual_columns = {}
    for output_key, possible_names in column_mapping.items():
        found = None
        for name in possible_names:
            if name in prh_df.columns:
                found = name
                break
        if found:
            actual_columns[output_key] = found
        else:
            actual_columns[output_key] = None

    # Check if all required columns are present
    missing = {k: v for k, v in actual_columns.items() if v is None}
    if missing:
        raise KeyError(f"Missing columns: {list(missing.keys())}. Available: {list(prh_df.columns)}")

    # Validate indices
    if start_idx < 0 or end_idx > len(prh_df) or start_idx >= end_idx:
        raise IndexError(
            f"Invalid indices: start_idx={start_idx}, end_idx={end_idx}, "
            f"DataFrame length={len(prh_df)}"
        )

    # Extract the slice
    sliced_df = prh_df.iloc[start_idx:end_idx]

    # Create the result dictionary using the found columns
    result = {output_key: sliced_df[actual_col].values for output_key, actual_col in actual_columns.items()}

    return result


def compute_jerk(
    accel_x: np.ndarray, accel_y: np.ndarray, accel_z: np.ndarray, sample_rate: int = 10
) -> List[float]:
    """
    Compute jerk (time derivative of acceleration) from acceleration data.

    Args:
        accel_x: Acceleration in X direction (numpy array or list)
        accel_y: Acceleration in Y direction (numpy array or list)
        accel_z: Acceleration in Z direction (numpy array or list)
        sample_rate: Sampling rate in Hz (default: 10)

    Returns:
        List of jerk magnitudes (m/s^3) for each time step after the first

    Raises:
        ValueError: If input arrays have different lengths or are empty
    """
    accel_x = np.asarray(accel_x)
    accel_y = np.asarray(accel_y)
    accel_z = np.asarray(accel_z)

    # Validate inputs
    if len(accel_x) != len(accel_y) or len(accel_x) != len(accel_z):
        raise ValueError("Input acceleration arrays must have the same length")

    if len(accel_x) == 0:
        raise ValueError("Input acceleration arrays cannot be empty")

    if len(accel_x) < 2:
        return []

    # Compute jerk as the difference in acceleration
    dt = 1.0 / sample_rate
    jerk_x = np.diff(accel_x) / dt
    jerk_y = np.diff(accel_y) / dt
    jerk_z = np.diff(accel_z) / dt

    # Compute jerk magnitude
    jerk_magnitude = np.sqrt(jerk_x**2 + jerk_y**2 + jerk_z**2)

    return jerk_magnitude.tolist()


def compute_fluke_stroke(gyro_y: np.ndarray) -> List[float]:
    """
    Compute fluke stroke amplitude from gyro Y-axis data.

    Args:
        gyro_y: Gyro Y-axis angular velocity data (numpy array or list)

    Returns:
        List of fluke stroke amplitudes for each time step

    Raises:
        ValueError: If input array is empty
    """
    gyro_y = np.asarray(gyro_y)

    if len(gyro_y) == 0:
        raise ValueError("Input gyro_y array cannot be empty")

    # Compute fluke stroke as the absolute value of gyro_y
    # (representing the magnitude of rotation around the Y axis)
    fluke_stroke = np.abs(gyro_y)

    return fluke_stroke.tolist()
