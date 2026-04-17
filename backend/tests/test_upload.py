"""
Test suite for upload endpoint.

Tests the file upload functionality and metric pre-computation/caching.
"""

import os
import tempfile
import numpy as np
import pandas as pd
import pytest
from scipy.io import wavfile
from fastapi.testclient import TestClient

from src.main import app
from src.cache import get_session_cache


class TestUploadEndpoint:
    """Test suite for the upload endpoint."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Clear cache before each test."""
        cache = get_session_cache()
        cache.clear()
        yield
        cache.clear()

    def test_upload_precomputes_metrics(self):
        """Test that upload pre-computes and caches metrics."""
        client = TestClient(app)

        # Create temporary test files
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple WAV file (1 second at 16000 Hz)
            sr = 16000
            duration = 1
            samples = sr * duration
            audio_data = np.random.randn(samples).astype(np.float32)
            wav_path = os.path.join(tmpdir, "test_audio.wav")
            wavfile.write(wav_path, sr, audio_data)

            # Create a PRH CSV file with 30 samples (3 seconds at 10 Hz)
            # PRH data has 10 samples per second, so 30 samples = 3 seconds
            n_prh_samples = 30
            prh_data = pd.DataFrame({
                "pitch_smoothed": np.random.randn(n_prh_samples),
                "roll_smoothed_wrapped": np.random.randn(n_prh_samples),
                "heading_smoothed_wrapped": np.random.randn(n_prh_samples),
                "depth_smoothed": np.random.randn(n_prh_samples),
                "speed_smoothed": np.random.randn(n_prh_samples),
                "Gy_Filt": np.random.randn(n_prh_samples),
            })
            prh_path = os.path.join(tmpdir, "test_prh.csv")
            prh_data.to_csv(prh_path, index=False)

            # Create an events CSV file
            events_data = pd.DataFrame({
                "Deployment_ID": ["deploy_test_123"],
                "Type": ["event_type"],
                "DN_start_idx": [0],
                "DN_end_idx": [10],
            })
            events_path = os.path.join(tmpdir, "test_events.csv")
            events_data.to_csv(events_path, index=False)

            # Upload files
            with open(wav_path, "rb") as wav_f, \
                 open(prh_path, "rb") as prh_f, \
                 open(events_path, "rb") as events_f:
                response = client.post(
                    "/api/upload",
                    files={
                        "wav_file": ("test_audio.wav", wav_f, "audio/wav"),
                        "prh_csv": ("test_prh.csv", prh_f, "text/csv"),
                        "events_csv": ("test_events.csv", events_f, "text/csv"),
                    },
                )

        # Verify response
        assert response.status_code == 200
        response_data = response.json()
        deployment_id = response_data["deployment_id"]
        assert deployment_id == "deploy_test_123"

        # Verify metrics are cached
        cache = get_session_cache()
        assert cache.has_deployment(deployment_id)

        # Retrieve cached metrics
        metrics = cache.get_deployment(deployment_id)
        assert metrics is not None

        # Verify PRH data has correct length (30 samples)
        assert len(metrics.prh_data) == n_prh_samples
        assert metrics.prh_data.shape[1] == 6  # 6 columns

        # Verify acceleration is zero array with correct shape
        assert metrics.acceleration.shape == (n_prh_samples, 3)
        np.testing.assert_array_equal(metrics.acceleration, np.zeros((n_prh_samples, 3)))

        # Verify jerk has correct length and first element is 0
        assert len(metrics.jerk) == n_prh_samples
        assert metrics.jerk[0] == 0.0

        # Verify sampling rate is 10 Hz
        assert metrics.hz == 10

    def test_upload_response_structure(self):
        """Test that upload response has correct structure."""
        client = TestClient(app)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create minimal test files
            sr = 16000
            audio_data = np.random.randn(1000).astype(np.float32)
            wav_path = os.path.join(tmpdir, "test_audio.wav")
            wavfile.write(wav_path, sr, audio_data)

            prh_data = pd.DataFrame({
                "pitch_smoothed": [1.0, 2.0],
                "roll_smoothed_wrapped": [10.0, 20.0],
                "heading_smoothed_wrapped": [100.0, 200.0],
                "depth_smoothed": [5.0, 10.0],
                "speed_smoothed": [0.5, 1.0],
                "Gy_Filt": [0.1, 0.2],
            })
            prh_path = os.path.join(tmpdir, "test_prh.csv")
            prh_data.to_csv(prh_path, index=False)

            events_data = pd.DataFrame({
                "Deployment_ID": ["test_deploy"],
                "Type": ["event"],
                "DN_start_idx": [0],
                "DN_end_idx": [1],
            })
            events_path = os.path.join(tmpdir, "test_events.csv")
            events_data.to_csv(events_path, index=False)

            with open(wav_path, "rb") as wav_f, \
                 open(prh_path, "rb") as prh_f, \
                 open(events_path, "rb") as events_f:
                response = client.post(
                    "/api/upload",
                    files={
                        "wav_file": ("test_audio.wav", wav_f, "audio/wav"),
                        "prh_csv": ("test_prh.csv", prh_f, "text/csv"),
                        "events_csv": ("test_events.csv", events_f, "text/csv"),
                    },
                )

        assert response.status_code == 200
        response_data = response.json()

        # Verify required response fields
        assert "session_id" in response_data
        assert "message" in response_data
        assert "deployment_id" in response_data
        assert "duration_seconds" in response_data
        assert "spectrogram_preview" in response_data
        assert "events" in response_data

        # Verify spectrogram preview structure
        spec = response_data["spectrogram_preview"]
        assert "freqs" in spec
        assert "times" in spec
        assert "power" in spec
