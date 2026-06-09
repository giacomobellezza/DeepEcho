"""Test suite for the /api/track endpoint (georeferenced track reconstruction)."""

import json
import os
import tempfile

import numpy as np
import pandas as pd
import pytest
from scipy.io import wavfile
from fastapi.testclient import TestClient

from src.main import app
from src.cache import get_session_cache


def _make_deployment(tmpdir, deployment_id, n_prh, with_gps=True):
    """Write a minimal WAV/PRH/events (+metadata) deployment to tmpdir."""
    sr = 16000
    audio = np.random.randn(sr).astype(np.float32)
    wav_path = os.path.join(tmpdir, "a.wav")
    wavfile.write(wav_path, sr, audio)

    # Constant eastward swim at 1 m/s, gentle dive, so dead reckoning moves east.
    prh = pd.DataFrame({
        "pitch_smoothed": np.zeros(n_prh),
        "roll_smoothed_wrapped": np.zeros(n_prh),
        "heading_smoothed_wrapped": np.zeros(n_prh),  # 0° -> due East
        "depth_smoothed": np.linspace(0, 500, n_prh),
        "speed_smoothed": np.ones(n_prh),
        "Gy_Filt": np.zeros(n_prh),
    })
    prh_path = os.path.join(tmpdir, "prh.csv")
    prh.to_csv(prh_path, index=False)

    events = pd.DataFrame({
        "Deployment_ID": [deployment_id],
        "Type": ["click"],
        "DN_start_idx": [0],
        "DN_end_idx": [min(10, n_prh)],
    })
    events_path = os.path.join(tmpdir, "events.csv")
    events.to_csv(events_path, index=False)

    meta_path = None
    if with_gps:
        # n_prh samples at 10 Hz -> covers n_prh/10 seconds. Place two fixes
        # inside the record and one well after it.
        meta = {
            "deployment": {"id": deployment_id, "species": "Physeter macrocephalus"},
            "date": {"deployment_start": "2024-07-01T13:00:00.000+02:00",
                     "timezone": "UTC+2"},
            "gps_track_log": [
                {"point": 1, "event": "Tag On",
                 "timestamp": "2024-07-01T13:00:00.000+02:00",
                 "latitude": 37.10, "longitude": 15.30},
                {"point": 2, "event": "Surface 1",
                 "timestamp": "2024-07-01T13:00:20.000+02:00",
                 "latitude": 37.12, "longitude": 15.33},
                {"point": 3, "event": "Recovery",
                 "timestamp": "2024-07-01T18:00:00.000+02:00",  # far past record
                 "latitude": 37.20, "longitude": 15.40},
            ],
            "additional_metadata": {"tag_model": "CATS"},
        }
        meta_path = os.path.join(tmpdir, "meta.json")
        with open(meta_path, "w") as f:
            json.dump(meta, f)
    return wav_path, prh_path, events_path, meta_path


def _upload(client, wav_path, prh_path, events_path, meta_path=None):
    files = {
        "wav_file": ("a.wav", open(wav_path, "rb"), "audio/wav"),
        "prh_csv": ("prh.csv", open(prh_path, "rb"), "text/csv"),
        "events_csv": ("events.csv", open(events_path, "rb"), "text/csv"),
    }
    if meta_path:
        files["metadata_file"] = ("meta.json", open(meta_path, "rb"), "application/json")
    try:
        return client.post("/api/upload", files=files)
    finally:
        for _, (_, fh, _) in files.items():
            fh.close()


@pytest.fixture(autouse=True)
def _clear_cache():
    get_session_cache().clear()
    yield
    get_session_cache().clear()


def test_track_reconstructs_georeferenced_path():
    client = TestClient(app)
    with tempfile.TemporaryDirectory() as tmp:
        n_prh = 400  # 40 s at 10 Hz
        wav, prh, events, meta = _make_deployment(tmp, "track_test_1", n_prh)
        up = _upload(client, wav, prh, events, meta)
        assert up.status_code == 200

        res = client.post("/api/track", json={"deployment_id": "track_test_1"})
        assert res.status_code == 200
        data = res.json()

    # Parallel arrays of equal length, decimated to <= the source length.
    assert len(data["lat"]) == len(data["lon"]) == len(data["depth"]) > 0
    assert len(data["lat"]) <= n_prh
    # Total source frames reported for timeline-synced position mapping.
    assert data["frames"] == n_prh

    # All 3 fixes returned; exactly 2 fall within the PRH record (anchors).
    assert len(data["fixes"]) == 3
    in_range = [f for f in data["fixes"] if f["in_range"]]
    assert len(in_range) == 2
    assert {f["label"] for f in in_range} == {"Tag On", "Surface 1"}

    # Reconstructed track sits in the Sicilian fix neighbourhood, and the
    # anchored path passes through the two in-range fixes.
    assert 37.0 < min(data["lat"]) and max(data["lat"]) < 37.3
    assert 15.2 < min(data["lon"]) and max(data["lon"]) < 15.45
    assert max(data["depth"]) > 400  # dive recorded


def test_track_without_gps_returns_404():
    client = TestClient(app)
    with tempfile.TemporaryDirectory() as tmp:
        wav, prh, events, _ = _make_deployment(tmp, "track_test_nogps", 200, with_gps=False)
        up = _upload(client, wav, prh, events, None)
        assert up.status_code == 200
        res = client.post("/api/track", json={"deployment_id": "track_test_nogps"})
        assert res.status_code == 404


def test_track_unknown_deployment_returns_404():
    client = TestClient(app)
    res = client.post("/api/track", json={"deployment_id": "does_not_exist"})
    assert res.status_code == 404
