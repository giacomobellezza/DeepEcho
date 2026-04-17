"""
Test suite for analyze endpoint.

Tests the analyze endpoint functionality for extracting and returning cached metrics.
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


class TestAnalyzeEndpoint:
    """Test suite for the analyze endpoint."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Clear cache before each test."""
        cache = get_session_cache()
        cache.clear()
        yield
        cache.clear()

    @pytest.fixture
    def test_deployment_id(self):
        """Create a test deployment with cached metrics."""
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

            # Create a PRH CSV file with 200 samples (20 seconds at 10 Hz)
            n_prh_samples = 200
            prh_data = pd.DataFrame({
                "pitch_smoothed": np.linspace(0, 45, n_prh_samples),
                "roll_smoothed_wrapped": np.linspace(-45, 45, n_prh_samples),
                "heading_smoothed_wrapped": np.linspace(0, 360, n_prh_samples),
                "depth_smoothed": np.linspace(0, 100, n_prh_samples),
                "speed_smoothed": np.linspace(0, 2, n_prh_samples),
                "Gy_Filt": np.sin(np.linspace(0, 4*np.pi, n_prh_samples)),
            })
            prh_path = os.path.join(tmpdir, "test_prh.csv")
            prh_data.to_csv(prh_path, index=False)

            # Create an events CSV file
            events_data = pd.DataFrame({
                "Deployment_ID": ["test_deploy_123"],
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

        assert response.status_code == 200
        # Return deployment_id (from events CSV) for use in analyze endpoint
        return response.json()["deployment_id"]

    def test_analyze_returns_metrics(self, test_deployment_id):
        """Test that analyze endpoint returns all cached metrics."""
        client = TestClient(app)

        response = client.post(
            "/api/analyze",
            json={
                "deployment_id": test_deployment_id,
                "start_idx": 0,
                "end_idx": 10,
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Check all new fields exist
        assert "pitch" in data
        assert "roll" in data
        assert "heading" in data
        assert "depth" in data
        assert "speed" in data
        assert "jerk" in data
        assert "gy_filt" in data
        assert "fluke_stroke_normalized" in data

        # Verify array lengths match interval (10 - 0 = 10 samples)
        interval_length = 10 - 0
        assert len(data["pitch"]) == interval_length
        assert len(data["roll"]) == interval_length
        assert len(data["heading"]) == interval_length
        assert len(data["depth"]) == interval_length
        assert len(data["speed"]) == interval_length
        assert len(data["jerk"]) == interval_length
        assert len(data["gy_filt"]) == interval_length
        assert len(data["fluke_stroke_normalized"]) == interval_length

        # Verify data types are lists/floats
        assert isinstance(data["pitch"], list)
        assert isinstance(data["pitch"][0], (int, float))
        assert isinstance(data["gy_filt"], list)
        assert isinstance(data["fluke_stroke_normalized"], list)

    def test_analyze_deployment_not_found(self):
        """Test that analyze returns 404 when deployment not found."""
        client = TestClient(app)

        response = client.post(
            "/api/analyze",
            json={
                "deployment_id": "nonexistent_deploy",
                "start_idx": 50,
                "end_idx": 150,
            }
        )

        assert response.status_code == 404
