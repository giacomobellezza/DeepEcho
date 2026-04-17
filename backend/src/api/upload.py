import os
import uuid
import tempfile
import shutil
import pandas as pd
import numpy as np
from fastapi import APIRouter, UploadFile, File
from src.models import UploadResponse
from src.processing.wav_loader import get_wav_info, read_wav_slice
from src.processing.prh_parser import parse_prh_csv
from src.processing.spectrogram import compute_preview_spectrogram, sample_spectrogram
from src.processing.metrics import compute_jerk
from src.cache import get_session_cache, get_cache

router = APIRouter()

# Session data cache — stores paths + metadata, NOT audio arrays
_session_data = {}

# Max bytes to buffer in memory during file save (8 MB chunks)
_CHUNK_SIZE = 8 * 1024 * 1024


async def _save_upload(upload: UploadFile, dest_path: str):
    """Stream uploaded file to disk in chunks instead of reading all at once."""
    with open(dest_path, "wb") as f:
        while True:
            chunk = await upload.read(_CHUNK_SIZE)
            if not chunk:
                break
            f.write(chunk)


@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    wav_file: UploadFile = File(...),
    prh_csv: UploadFile = File(...),
    events_csv: UploadFile = File(...),
):
    """
    Upload audio and CSV files for analysis.

    Streams WAV to disk (never loads full audio into RAM).
    """
    session_id = str(uuid.uuid4())

    # Create temp directory for this session
    temp_dir = os.path.join(tempfile.gettempdir(), f"session_{session_id}")
    os.makedirs(temp_dir, exist_ok=True)

    wav_path = os.path.join(temp_dir, wav_file.filename)
    prh_path = os.path.join(temp_dir, prh_csv.filename)
    events_path = os.path.join(temp_dir, events_csv.filename)

    # Stream files to disk (no full-file RAM load)
    await _save_upload(wav_file, wav_path)
    await _save_upload(prh_csv, prh_path)
    await _save_upload(events_csv, events_path)

    # Get WAV metadata without loading audio
    wav_info = get_wav_info(wav_path)
    sr = wav_info["sample_rate"]
    duration_seconds = wav_info["duration_seconds"]

    # Load PRH (small CSV, fine to keep in memory)
    prh_data = parse_prh_csv(prh_path)

    # Read events CSV
    events_df = pd.read_csv(events_path)

    # Pre-compute and cache metrics
    hz = 10
    accel_cols = ('Ax_Filt', 'Ay_Filt', 'Az_Filt')
    if all(col in prh_data.columns for col in accel_cols):
        ax = prh_data['Ax_Filt'].values.astype(np.float64)
        ay = prh_data['Ay_Filt'].values.astype(np.float64)
        az = prh_data['Az_Filt'].values.astype(np.float64)
    else:
        ax = ay = az = np.zeros(len(prh_data))
    acceleration = np.column_stack([ax, ay, az])

    jerk = compute_jerk(ax, ay, az, hz)

    # Extract deployment_id
    if 'Deployment_ID' in events_df.columns and len(events_df) > 0:
        deployment_id = str(events_df['Deployment_ID'].iloc[0])
    else:
        deployment_id = f"session_{session_id[:8]}"

    # Load metrics into session cache
    cache = get_session_cache()
    cache.load_deployment(
        deployment_id=deployment_id,
        prh_data=prh_data,
        acceleration=acceleration,
        jerk=jerk,
        hz=hz,
    )

    # Compute preview spectrogram from a SHORT slice (first 30s max)
    preview_duration_s = min(30, duration_seconds)
    preview_samples = int(preview_duration_s * sr)
    preview_audio, _ = read_wav_slice(wav_path, 0, preview_samples)

    spec_preview = compute_preview_spectrogram(preview_audio, sr)
    spec_preview_serializable = {
        "freqs": spec_preview["freqs"].tolist(),
        "times": spec_preview["times"].tolist(),
        "power": spec_preview["power"].tolist(),
    }

    # Convert events
    events_list = []
    for _, row in events_df.iterrows():
        events_list.append({
            "type": row.get("Type", "unknown"),
            "start_idx": int(row.get("DN_start_idx", 0)),
            "end_idx": int(row.get("DN_end_idx", 0)),
        })

    # Cache session: paths + metadata only, NO audio arrays
    _session_data[session_id] = {
        "wav_path": wav_path,
        "sr": sr,
        "total_frames": wav_info["frames"],
        "prh_data": prh_data,
        "temp_dir": temp_dir,
        "prh_path": prh_path,
        "events_path": events_path,
        "deployment_id": deployment_id,
        "events": events_list,
    }

    # Cache preview spectrogram (64x64)
    try:
        sampled_preview = sample_spectrogram(
            spec_preview["power"], target_freq_bins=64, target_time_bins=64
        )
        spec_cache = get_cache()
        spec_cache.store(
            deployment_id,
            start_idx=0,
            end_idx=len(prh_data),
            freqs=spec_preview["freqs"],
            times=spec_preview["times"],
            power=sampled_preview,
            resolution=64,
        )
    except Exception as e:
        print(f"Warning: Failed to cache preview spectrogram: {e}")

    return UploadResponse(
        session_id=session_id,
        message=f"Files uploaded successfully. Session ID: {session_id}",
        deployment_id=deployment_id,
        duration_seconds=duration_seconds,
        spectrogram_preview=spec_preview_serializable,
        events=events_list,
    )
