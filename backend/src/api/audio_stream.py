import io
import numpy as np
import soundfile as sf
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from src.api.upload import _session_data
from src.processing.wav_loader import read_wav_slice

router = APIRouter()


@router.get("/audio/{deployment_id}")
async def stream_audio_slice(
    deployment_id: str,
    start_idx: int = Query(...),
    end_idx: int = Query(...),
):
    """
    Stream a WAV audio slice for playback.

    Reads only the requested interval from disk and returns it as a WAV file.
    PRH indices (at 10 Hz) are converted to audio samples.
    """
    session = None
    for sid, sess_data in _session_data.items():
        if sess_data.get("deployment_id") == deployment_id:
            session = sess_data
            break

    if session is None:
        raise HTTPException(status_code=404, detail="Deployment not found")

    wav_path = session.get("wav_path")
    sr = session.get("sr")

    if wav_path is None or sr is None:
        raise HTTPException(status_code=400, detail="Session data incomplete")

    # Convert PRH indices (10 Hz) to audio samples
    start_sample = int(start_idx * sr / 10)
    end_sample = int(end_idx * sr / 10)

    audio, _ = read_wav_slice(wav_path, start_sample, end_sample)

    # Write to in-memory WAV buffer
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format='WAV', subtype='PCM_16')
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="audio/wav",
        headers={"Content-Disposition": f"inline; filename=slice_{start_idx}_{end_idx}.wav"},
    )
