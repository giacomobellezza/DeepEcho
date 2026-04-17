import numpy as np
import soundfile as sf
from pathlib import Path


def get_wav_info(filepath: str) -> dict:
    """
    Get WAV file metadata without loading audio into memory.

    Returns:
        Dict with 'sample_rate', 'frames', 'duration_seconds', 'channels'
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    info = sf.info(str(filepath))
    return {
        "sample_rate": info.samplerate,
        "frames": info.frames,
        "duration_seconds": info.duration,
        "channels": info.channels,
    }


def read_wav_slice(filepath: str, start_sample: int, end_sample: int) -> tuple[np.ndarray, int]:
    """
    Read a slice of a WAV file without loading the entire file.

    Uses soundfile seek/read for O(1) memory relative to slice size.

    Args:
        filepath: Path to the WAV file
        start_sample: First sample index
        end_sample: Last sample index (exclusive)

    Returns:
        Tuple of (audio_data_float32, sample_rate)
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    with sf.SoundFile(str(filepath)) as f:
        sr = f.samplerate
        total = f.frames

        start_sample = max(0, min(start_sample, total - 1))
        end_sample = max(start_sample + 1, min(end_sample, total))

        f.seek(start_sample)
        audio = f.read(end_sample - start_sample, dtype='float32')

    # Stereo to mono
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    return audio, sr


def load_wav(filepath: str) -> tuple[np.ndarray, int]:
    """
    Legacy: load entire WAV file. Use read_wav_slice for large files.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    try:
        audio, sr = sf.read(str(filepath), dtype='float32')
    except Exception as e:
        raise ValueError(f"Invalid WAV file: {filepath}") from e

    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    return audio, sr
