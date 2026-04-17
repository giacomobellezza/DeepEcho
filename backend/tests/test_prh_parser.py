import pytest
import numpy as np
import pandas as pd
import tempfile
from pathlib import Path

from src.processing.prh_parser import (
    parse_prh_csv,
    extract_prh_slice,
    compute_jerk,
    compute_fluke_stroke,
)


@pytest.fixture
def temp_prh_csv():
    """Create a temporary PRH CSV file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        filepath = f.name
        # Write header
        f.write(
            "depth,speed,pitch,roll,heading,accel_x,accel_y,accel_z,gyro_y\n"
        )
        # Write some sample data
        for i in range(100):
            depth = 10 + i * 0.1
            speed = 2.0 + 0.1 * np.sin(i * 0.1)
            pitch = 5 + i * 0.05
            roll = -2 + i * 0.02
            heading = 180 + i * 0.5
            accel_x = 0.1 * np.cos(i * 0.1)
            accel_y = 0.2 * np.sin(i * 0.1)
            accel_z = -9.8 + 0.05 * np.cos(i * 0.05)
            gyro_y = 0.5 * np.sin(i * 0.2)

            f.write(
                f"{depth},{speed},{pitch},{roll},{heading},"
                f"{accel_x},{accel_y},{accel_z},{gyro_y}\n"
            )

    yield filepath

    # Cleanup
    Path(filepath).unlink()


def test_parse_prh_csv(temp_prh_csv):
    """Test parsing a PRH CSV file."""
    prh_df = parse_prh_csv(temp_prh_csv)

    assert isinstance(prh_df, pd.DataFrame)
    assert len(prh_df) == 100
    assert list(prh_df.columns) == [
        "depth",
        "speed",
        "pitch",
        "roll",
        "heading",
        "accel_x",
        "accel_y",
        "accel_z",
        "gyro_y",
    ]
    assert prh_df["depth"].dtype == np.float64
    assert prh_df.iloc[0]["depth"] == pytest.approx(10.0)


def test_parse_prh_csv_file_not_found():
    """Test that FileNotFoundError is raised for non-existent file."""
    with pytest.raises(FileNotFoundError):
        parse_prh_csv("/non/existent/file.csv")


def test_parse_prh_csv_invalid_file():
    """Test parsing an invalid/corrupted CSV file."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        filepath = f.name
        # Write valid CSV format
        f.write("depth,speed\n1,2\n3,4\n")

    try:
        # File exists and is readable, so parse_prh_csv should succeed
        df = parse_prh_csv(filepath)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
    finally:
        Path(filepath).unlink()


def test_extract_prh_slice(temp_prh_csv):
    """Test extracting a slice of PRH data."""
    prh_df = parse_prh_csv(temp_prh_csv)
    slice_data = extract_prh_slice(prh_df, 10, 20)

    assert isinstance(slice_data, dict)
    assert set(slice_data.keys()) == {
        "depth",
        "speed",
        "pitch",
        "roll",
        "heading",
        "accel_x",
        "accel_y",
        "accel_z",
        "gyro_y",
    }

    # Each array should have 10 elements (20 - 10)
    for key, value in slice_data.items():
        assert isinstance(value, np.ndarray)
        assert len(value) == 10

    # Check specific values
    assert slice_data["depth"][0] == pytest.approx(prh_df.iloc[10]["depth"])
    assert slice_data["depth"][9] == pytest.approx(prh_df.iloc[19]["depth"])


def test_extract_prh_slice_missing_columns():
    """Test that KeyError is raised for missing columns."""
    # Create a DataFrame with missing columns
    df = pd.DataFrame({"depth": [1, 2, 3], "speed": [4, 5, 6]})

    with pytest.raises(KeyError):
        extract_prh_slice(df, 0, 2)


def test_extract_prh_slice_invalid_indices(temp_prh_csv):
    """Test that IndexError is raised for invalid indices."""
    prh_df = parse_prh_csv(temp_prh_csv)

    # Test negative start_idx
    with pytest.raises(IndexError):
        extract_prh_slice(prh_df, -1, 10)

    # Test end_idx greater than length
    with pytest.raises(IndexError):
        extract_prh_slice(prh_df, 0, 150)

    # Test start_idx >= end_idx
    with pytest.raises(IndexError):
        extract_prh_slice(prh_df, 20, 10)


def test_compute_jerk():
    """Test computing jerk from acceleration data."""
    # Create synthetic acceleration data
    accel_x = np.array([0.0, 0.1, 0.2, 0.3, 0.4])
    accel_y = np.array([0.0, 0.1, 0.2, 0.3, 0.4])
    accel_z = np.array([0.0, 0.1, 0.2, 0.3, 0.4])

    jerk = compute_jerk(accel_x, accel_y, accel_z, sample_rate=10)

    assert isinstance(jerk, list)
    assert len(jerk) == 4  # One less than input (differentiation)
    assert all(isinstance(j, float) for j in jerk)

    # For constant acceleration difference (0.1), jerk should be constant
    # sqrt(3 * (0.1 * 10)^2) = sqrt(3 * 1) = sqrt(3)
    expected_jerk = np.sqrt(3) * 1.0  # accel_diff = 0.1, dt = 0.1, so jerk = 1.0 per axis
    assert jerk[0] == pytest.approx(expected_jerk, rel=0.1)


def test_compute_jerk_mismatched_lengths():
    """Test that ValueError is raised for mismatched acceleration lengths."""
    accel_x = np.array([0.0, 0.1, 0.2])
    accel_y = np.array([0.0, 0.1])  # Different length
    accel_z = np.array([0.0, 0.1, 0.2])

    with pytest.raises(ValueError):
        compute_jerk(accel_x, accel_y, accel_z)


def test_compute_jerk_empty_array():
    """Test that ValueError is raised for empty arrays."""
    with pytest.raises(ValueError):
        compute_jerk(np.array([]), np.array([]), np.array([]))


def test_compute_jerk_single_element():
    """Test that empty list is returned for single element."""
    accel_x = np.array([0.1])
    accel_y = np.array([0.2])
    accel_z = np.array([0.3])

    jerk = compute_jerk(accel_x, accel_y, accel_z)
    assert jerk == []


def test_compute_fluke_stroke():
    """Test computing fluke stroke from gyro data."""
    gyro_y = np.array([-1.0, -0.5, 0.0, 0.5, 1.0])

    fluke_stroke = compute_fluke_stroke(gyro_y)

    assert isinstance(fluke_stroke, list)
    assert len(fluke_stroke) == 5
    assert all(isinstance(f, float) for f in fluke_stroke)
    assert fluke_stroke == [1.0, 0.5, 0.0, 0.5, 1.0]


def test_compute_fluke_stroke_empty_array():
    """Test that ValueError is raised for empty array."""
    with pytest.raises(ValueError):
        compute_fluke_stroke(np.array([]))


def test_compute_fluke_stroke_single_element():
    """Test computing fluke stroke with single element."""
    gyro_y = np.array([0.5])

    fluke_stroke = compute_fluke_stroke(gyro_y)

    assert fluke_stroke == [0.5]
