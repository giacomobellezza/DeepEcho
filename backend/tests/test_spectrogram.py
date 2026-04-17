import pytest
import numpy as np

from src.processing.spectrogram import compute_preview_spectrogram, compute_detailed_spectrogram


@pytest.fixture
def sample_audio():
    """Create sample audio data for testing."""
    sample_rate = 44100
    duration = 2  # 2 seconds
    t = np.linspace(0, duration, sample_rate * duration)
    # Create a simple sine wave at 440 Hz
    audio_data = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    return audio_data, sample_rate


def test_compute_preview_spectrogram_low(sample_audio):
    """Test preview spectrogram computation with low resolution."""
    audio_data, sample_rate = sample_audio
    result = compute_preview_spectrogram(audio_data, sample_rate, resolution="low")

    assert "freqs" in result
    assert "times" in result
    assert "power" in result

    freqs, times, power = result["freqs"], result["times"], result["power"]

    assert isinstance(freqs, np.ndarray)
    assert isinstance(times, np.ndarray)
    assert isinstance(power, np.ndarray)

    assert freqs.ndim == 1
    assert times.ndim == 1
    assert power.ndim == 2

    # Check shape consistency
    assert power.shape[0] == len(freqs)
    assert power.shape[1] == len(times)

    # Check that frequencies are positive
    assert np.all(freqs >= 0)

    # Check that times are increasing
    assert np.all(np.diff(times) > 0)

    # Check that power is in dB scale (should be negative or small positive values)
    assert np.all(power <= 100)  # dB values should be reasonable


def test_compute_preview_spectrogram_medium(sample_audio):
    """Test preview spectrogram computation with medium resolution."""
    audio_data, sample_rate = sample_audio
    result = compute_preview_spectrogram(audio_data, sample_rate, resolution="medium")

    assert "freqs" in result
    assert "times" in result
    assert "power" in result


def test_compute_preview_spectrogram_high(sample_audio):
    """Test preview spectrogram computation with high resolution."""
    audio_data, sample_rate = sample_audio
    result = compute_preview_spectrogram(audio_data, sample_rate, resolution="high")

    assert "freqs" in result
    assert "times" in result
    assert "power" in result


def test_compute_preview_spectrogram_invalid_resolution(sample_audio):
    """Test that invalid resolution raises ValueError."""
    audio_data, sample_rate = sample_audio
    with pytest.raises(ValueError):
        compute_preview_spectrogram(audio_data, sample_rate, resolution="invalid")


def test_compute_detailed_spectrogram(sample_audio):
    """Test detailed spectrogram computation."""
    audio_data, sample_rate = sample_audio
    result = compute_detailed_spectrogram(audio_data, sample_rate)

    assert "freqs" in result
    assert "times" in result
    assert "power" in result

    freqs, times, power = result["freqs"], result["times"], result["power"]

    assert isinstance(freqs, np.ndarray)
    assert isinstance(times, np.ndarray)
    assert isinstance(power, np.ndarray)

    assert freqs.ndim == 1
    assert times.ndim == 1
    assert power.ndim == 2

    # Check shape consistency
    assert power.shape[0] == len(freqs)
    assert power.shape[1] == len(times)

    # Check that frequencies are positive
    assert np.all(freqs >= 0)

    # Check that times are increasing
    assert np.all(np.diff(times) > 0)

    # Check that power is in dB scale
    assert np.all(power <= 100)


def test_resolution_affects_output(sample_audio):
    """Test that different resolutions produce different sized outputs."""
    audio_data, sample_rate = sample_audio

    low_result = compute_preview_spectrogram(audio_data, sample_rate, resolution="low")
    high_result = compute_preview_spectrogram(audio_data, sample_rate, resolution="high")

    # Higher resolution should have more frequency bins
    assert len(high_result["freqs"]) > len(low_result["freqs"])
