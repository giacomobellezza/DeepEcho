from fastapi import APIRouter, HTTPException
import numpy as np
from src.models import AnalyzeRequest, AnalyzeResponse
from src.api.upload import _session_data
from src.processing.prh_parser import extract_prh_slice, compute_jerk, compute_fluke_stroke
from src.processing.spectrogram import compute_detailed_spectrogram, sample_spectrogram
from src.processing.wav_loader import read_wav_slice
from src.cache import get_cache, get_session_cache

router = APIRouter()

# Max points to send for waveform display (keeps JSON small)
MAX_WAVEFORM_POINTS = 2000


def downsample_waveform(audio: np.ndarray, max_points: int = MAX_WAVEFORM_POINTS) -> list[float]:
    """
    Downsample audio for waveform display using min/max envelope.

    Preserves peaks (critical for seeing acoustic events).
    Returns ~max_points values.
    """
    n = len(audio)
    if n <= max_points:
        return audio.tolist()

    # Each output pair = (min, max) of a chunk → max_points/2 chunks
    chunk_size = n // (max_points // 2)
    result = []
    for i in range(0, n - chunk_size + 1, chunk_size):
        chunk = audio[i:i + chunk_size]
        result.append(float(np.min(chunk)))
        result.append(float(np.max(chunk)))
        if len(result) >= max_points:
            break
    return result


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    """
    Analyze a specific time slice of deployment data.

    Reads audio slice from disk (not RAM), downsamples waveform.
    """
    # Find session by deployment_id
    session = None
    for sid, sess_data in _session_data.items():
        if sess_data.get("deployment_id") == request.deployment_id:
            session = sess_data
            break

    if session is None:
        raise HTTPException(status_code=404, detail="Deployment not found")

    wav_path = session.get("wav_path")
    sr = session.get("sr")
    prh_data = session.get("prh_data")
    deployment_id = session.get("deployment_id")

    if wav_path is None or sr is None or prh_data is None:
        raise HTTPException(status_code=400, detail="Session data incomplete")

    # Get cached PRH metrics
    cache = get_session_cache()
    cached_metrics = cache.extract_interval(
        deployment_id, request.start_idx, request.end_idx
    )

    if cached_metrics is None:
        raise HTTPException(status_code=400, detail="Metrics not cached")

    prh_slice, accel_slice, jerk_slice = cached_metrics

    # Convert PRH indices to audio samples (PRH is at 10 Hz)
    start_sample = int(request.start_idx * sr / 10)
    end_sample = int(request.end_idx * sr / 10)

    # Read audio slice from disk (not from RAM)
    audio_slice_array, _ = read_wav_slice(wav_path, start_sample, end_sample)

    # Downsample for waveform display (max 2000 points instead of millions)
    audio_slice = downsample_waveform(audio_slice_array)

    # Spectrogram: try cache first
    spec_cache = get_cache()
    cached_spectrogram = spec_cache.get(
        deployment_id, request.start_idx, request.end_idx, resolution=256
    )

    if cached_spectrogram is not None:
        spectrogram_result = {
            "freqs": cached_spectrogram.freqs.tolist(),
            "times": cached_spectrogram.times.tolist(),
            "power": cached_spectrogram.power.tolist(),
        }
    else:
        spectrogram_data = compute_detailed_spectrogram(audio_slice_array, sr)
        target_freq = 256
        target_time = 256
        sampled_power = sample_spectrogram(
            spectrogram_data["power"], target_freq_bins=target_freq, target_time_bins=target_time
        )

        # Downsample freq/time axes to match power grid
        raw_freqs = spectrogram_data["freqs"]
        raw_times = spectrogram_data["times"]
        sampled_freqs = np.linspace(raw_freqs[0], raw_freqs[-1], target_freq)
        sampled_times = np.linspace(raw_times[0], raw_times[-1], target_time)

        spec_cache.store(
            deployment_id,
            request.start_idx,
            request.end_idx,
            freqs=sampled_freqs,
            times=sampled_times,
            power=sampled_power,
            resolution=256,
        )

        spectrogram_result = {
            "freqs": sampled_freqs.tolist(),
            "times": sampled_times.tolist(),
            "power": sampled_power.tolist(),
        }

    # Extract metrics from cached PRH slice
    pitch = prh_slice["pitch_smoothed"].tolist()
    roll = prh_slice["roll_smoothed_wrapped"].tolist()
    heading = prh_slice["heading_smoothed_wrapped"].tolist()
    depth = prh_slice["depth_smoothed"].tolist()
    speed = prh_slice["speed_smoothed"].tolist()
    gy_filt = prh_slice["Gy_Filt"].tolist()
    jerk = jerk_slice.tolist()

    # Fluke stroke
    gy_filt_array = prh_slice["Gy_Filt"].values
    fluke_stroke = np.abs(gy_filt_array).tolist()
    gy_mean = np.mean(gy_filt_array)
    fluke_stroke_normalized = (gy_filt_array - gy_mean).tolist()

    # Dynamic body acceleration
    accel_hz = 10
    window = max(1, int(3 * accel_hz))
    ax, ay, az = accel_slice[:, 0], accel_slice[:, 1], accel_slice[:, 2]

    def _running_mean(x, w):
        if len(x) < w:
            return np.full_like(x, np.mean(x)) if len(x) else x
        kernel = np.ones(w) / w
        return np.convolve(x, kernel, mode='same')

    dax = ax - _running_mean(ax, window)
    day = ay - _running_mean(ay, window)
    daz = az - _running_mean(az, window)
    odba = (np.abs(dax) + np.abs(day) + np.abs(daz)).tolist()
    vedba = np.sqrt(dax**2 + day**2 + daz**2).tolist()
    msa = (np.sqrt(ax**2 + ay**2 + az**2) - 1.0).tolist()

    # PRH data for backward compatibility
    prh_result = {
        key: value.tolist() if hasattr(value, "tolist") else list(value)
        for key, value in prh_slice.items()
    }

    return AnalyzeResponse(
        deployment_id=request.deployment_id,
        start_idx=request.start_idx,
        end_idx=request.end_idx,
        audio_slice=audio_slice,
        sample_rate=int(sr),
        spectrogram=spectrogram_result,
        prh_data=prh_result,
        jerk=jerk,
        fluke_stroke=fluke_stroke,
        pitch=pitch,
        roll=roll,
        heading=heading,
        depth=depth,
        speed=speed,
        gy_filt=gy_filt,
        fluke_stroke_normalized=fluke_stroke_normalized,
        odba=odba,
        vedba=vedba,
        msa=msa,
    )
