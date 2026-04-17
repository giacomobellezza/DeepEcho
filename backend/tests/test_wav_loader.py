import pytest
import numpy as np
import scipy.io.wavfile as wavfile
from pathlib import Path
import tempfile

from src.processing.wav_loader import load_wav


@pytest.fixture
def temp_wav_mono():
    """Create a temporary mono WAV file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        filepath = f.name

    # Create mono audio data
    sample_rate = 44100
    duration = 1  # 1 second
    t = np.linspace(0, duration, sample_rate * duration)
    audio_data = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave
    audio_data_int16 = (audio_data * 32767).astype(np.int16)

    wavfile.write(filepath, sample_rate, audio_data_int16)
    yield filepath

    # Cleanup
    Path(filepath).unlink()


@pytest.fixture
def temp_wav_stereo():
    """Create a temporary stereo WAV file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        filepath = f.name

    # Create stereo audio data
    sample_rate = 44100
    duration = 1  # 1 second
    t = np.linspace(0, duration, sample_rate * duration)
    left_channel = np.sin(2 * np.pi * 440 * t)  # 440 Hz
    right_channel = np.sin(2 * np.pi * 880 * t)  # 880 Hz
    audio_data = np.column_stack([left_channel, right_channel])
    audio_data_int16 = (audio_data * 32767).astype(np.int16)

    wavfile.write(filepath, sample_rate, audio_data_int16)
    yield filepath

    # Cleanup
    Path(filepath).unlink()


def test_load_wav_mono(temp_wav_mono):
    """Test loading a mono WAV file."""
    audio_data, sample_rate = load_wav(temp_wav_mono)

    assert sample_rate == 44100
    assert audio_data.dtype == np.float32
    assert len(audio_data.shape) == 1  # 1D array
    assert len(audio_data) == 44100  # 1 second at 44100 Hz
    assert np.max(np.abs(audio_data)) <= 1.0  # Normalized


def test_load_wav_stereo(temp_wav_stereo):
    """Test loading a stereo WAV file and converting to mono."""
    audio_data, sample_rate = load_wav(temp_wav_stereo)

    assert sample_rate == 44100
    assert audio_data.dtype == np.float32
    assert len(audio_data.shape) == 1  # 1D array (converted to mono)
    assert len(audio_data) == 44100  # 1 second at 44100 Hz
    assert np.max(np.abs(audio_data)) <= 1.0  # Normalized


def test_load_wav_file_not_found():
    """Test that FileNotFoundError is raised for non-existent file."""
    with pytest.raises(FileNotFoundError):
        load_wav("/non/existent/file.wav")


def test_load_wav_invalid_file():
    """Test that ValueError is raised for invalid WAV file."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        filepath = f.name
        f.write(b"This is not a valid WAV file")

    try:
        with pytest.raises(ValueError):
            load_wav(filepath)
    finally:
        Path(filepath).unlink()
