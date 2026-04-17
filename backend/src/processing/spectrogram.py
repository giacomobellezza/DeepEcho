import numpy as np
from scipy import signal


def compute_preview_spectrogram(
    audio: np.ndarray, sample_rate: int, resolution: str = "low"
) -> dict:
    """
    Compute a preview spectrogram with reduced resolution for quick viewing.

    Args:
        audio: Audio data as numpy array (float32)
        sample_rate: Sample rate in Hz
        resolution: Resolution level ('low', 'medium', 'high')

    Returns:
        Dictionary containing:
        - 'freqs': Array of frequency values in Hz (decimated)
        - 'times': Array of time values in seconds (decimated)
        - 'power': 2D array of power values (log scale, decimated)
    """
    # Parameters based on resolution - use very coarse settings for preview
    if resolution == "low":
        nperseg = 1024
        noverlap = 512
    elif resolution == "medium":
        nperseg = 2048
        noverlap = 1024
    elif resolution == "high":
        nperseg = 4096
        noverlap = 2048
    else:
        raise ValueError(f"Invalid resolution: {resolution}")

    # Compute spectrogram
    freqs, times, Sxx = signal.spectrogram(
        audio, fs=sample_rate, nperseg=nperseg, noverlap=noverlap
    )

    # Convert to dB scale
    power = 10 * np.log10(Sxx + 1e-10)

    # Decimate for preview: keep every Nth sample in both dimensions
    # Target: ~50-100 time bins and ~50 frequency bins for preview
    freq_decimate = max(1, len(freqs) // 50)
    time_decimate = max(1, power.shape[1] // 100)

    freqs_decimated = freqs[::freq_decimate]
    times_decimated = times[::time_decimate]
    power_decimated = power[::freq_decimate, ::time_decimate]

    return {
        "freqs": freqs_decimated,
        "times": times_decimated,
        "power": power_decimated,
    }


def sample_spectrogram(
    power: np.ndarray,
    target_freq_bins: int = 64,
    target_time_bins: int = 64
) -> np.ndarray:
    """
    Downsample a spectrogram to a target resolution using binning.

    Args:
        power: 2D array of power values (freq_bins x time_bins)
        target_freq_bins: Target number of frequency bins
        target_time_bins: Target number of time bins

    Returns:
        Downsampled 2D array of power values with shape (target_freq_bins, target_time_bins)
    """
    freq_bins, time_bins = power.shape

    # Use scipy's interpolation via binning to get exact target size
    # Reshape and average to target resolution
    sampled_freq = []

    for i in range(target_freq_bins):
        # Calculate which rows to include for this output bin
        start_row = (i * freq_bins) // target_freq_bins
        end_row = ((i + 1) * freq_bins) // target_freq_bins
        if end_row <= start_row:
            end_row = start_row + 1

        sampled_time = []
        for j in range(target_time_bins):
            # Calculate which columns to include for this output bin
            start_col = (j * time_bins) // target_time_bins
            end_col = ((j + 1) * time_bins) // target_time_bins
            if end_col <= start_col:
                end_col = start_col + 1

            # Average over this bin
            bin_data = power[start_row:end_row, start_col:end_col]
            sampled_time.append(np.mean(bin_data))

        sampled_freq.append(sampled_time)

    return np.array(sampled_freq)


def compute_detailed_spectrogram(audio: np.ndarray, sample_rate: int) -> dict:
    """
    Compute a detailed spectrogram with high resolution for analysis.

    Args:
        audio: Audio data as numpy array (float32)
        sample_rate: Sample rate in Hz

    Returns:
        Dictionary containing:
        - 'freqs': Array of frequency values in Hz
        - 'times': Array of time values in seconds
        - 'power': 2D array of power values (log scale)
    """
    # High resolution parameters
    nperseg = 4096
    noverlap = 2048

    # Compute spectrogram
    freqs, times, Sxx = signal.spectrogram(
        audio, fs=sample_rate, nperseg=nperseg, noverlap=noverlap
    )

    # Convert to dB scale
    power = 10 * np.log10(Sxx + 1e-10)

    return {"freqs": freqs, "times": times, "power": power}
