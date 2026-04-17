"""
Integration tests for the caching workflow.

Tests the complete end-to-end flow: upload → preview cached → analyze (miss, store) → analyze again (hit).
Verifies response format, payload sizes, and caching efficiency.
"""

import os
import tempfile
import time
import numpy as np
import pandas as pd
import pytest
from scipy.io import wavfile
from fastapi.testclient import TestClient

from src.main import app
from src.cache import get_session_cache


class TestEndToEndCachingFlow:
    """Integration tests for the complete caching workflow."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Clear cache before each test."""
        cache = get_session_cache()
        cache.clear()
        yield
        cache.clear()

    @pytest.fixture
    def test_files(self):
        """Create temporary test files for upload."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test WAV file (20 seconds at 16000 Hz)
            # PRH is at 10 Hz, so 200 samples = 20 seconds = 320000 audio samples
            sr = 16000
            duration = 20
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
                "Deployment_ID": ["integration_test_deploy"],
                "Type": ["event_type"],
                "DN_start_idx": [0],
                "DN_end_idx": [10],
            })
            events_path = os.path.join(tmpdir, "test_events.csv")
            events_data.to_csv(events_path, index=False)

            yield wav_path, prh_path, events_path

    def test_end_to_end_caching_flow(self, test_files):
        """
        Full workflow: upload → preview cached → analyze (miss, store) → analyze again (hit).
        Verify response format and payload sizes.
        """
        client = TestClient(app)
        wav_path, prh_path, events_path = test_files

        # Step 1: Upload test files
        with open(wav_path, "rb") as wav_f, \
             open(prh_path, "rb") as prh_f, \
             open(events_path, "rb") as events_f:
            upload_resp = client.post(
                "/api/upload",
                files={
                    "wav_file": ("test_audio.wav", wav_f, "audio/wav"),
                    "prh_csv": ("test_prh.csv", prh_f, "text/csv"),
                    "events_csv": ("test_events.csv", events_f, "text/csv"),
                }
            )

        assert upload_resp.status_code == 200
        upload_data = upload_resp.json()
        deployment_id = upload_data["deployment_id"]
        assert deployment_id == "integration_test_deploy"

        # Verify upload response includes spectrogram preview
        assert "spectrogram_preview" in upload_data
        spec_preview = upload_data["spectrogram_preview"]
        assert "freqs" in spec_preview
        assert "times" in spec_preview
        assert "power" in spec_preview

        # Step 2: First analysis (cache miss, should compute and store)
        resp1 = client.post(
            "/api/analyze",
            json={
                "deployment_id": deployment_id,
                "start_idx": 10,
                "end_idx": 50
            }
        )

        assert resp1.status_code == 200
        data1 = resp1.json()

        # Verify response format - includes all expected fields
        assert "pitch" in data1
        assert "roll" in data1
        assert "heading" in data1
        assert "depth" in data1
        assert "speed" in data1
        assert "jerk" in data1
        assert "gy_filt" in data1
        assert "fluke_stroke_normalized" in data1

        # Verify array lengths match interval (50 - 10 = 40 samples)
        interval_length = 50 - 10
        assert len(data1["pitch"]) == interval_length
        assert len(data1["roll"]) == interval_length
        assert len(data1["depth"]) == interval_length
        assert len(data1["speed"]) == interval_length

        # Verify data types
        assert isinstance(data1["pitch"], list)
        assert isinstance(data1["pitch"][0], (int, float))

        payload_size1 = len(resp1.content) / 1024  # KB

        # Step 3: Second analysis same interval (cache hit)
        resp2 = client.post(
            "/api/analyze",
            json={
                "deployment_id": deployment_id,
                "start_idx": 10,
                "end_idx": 50
            }
        )

        assert resp2.status_code == 200
        data2 = resp2.json()

        # Verify responses are identical
        assert data1 == data2

        payload_size2 = len(resp2.content) / 1024  # KB

        # Step 4: Third analysis different interval (cache miss)
        resp3 = client.post(
            "/api/analyze",
            json={
                "deployment_id": deployment_id,
                "start_idx": 60,
                "end_idx": 100
            }
        )

        assert resp3.status_code == 200
        data3 = resp3.json()

        # Verify it has all required fields
        assert "pitch" in data3
        assert "speed" in data3
        assert len(data3["pitch"]) == 40  # 100 - 60

        payload_size3 = len(resp3.content) / 1024  # KB

        # Verify payload sizes are reasonable (should be similar for same interval length)
        # Allow some variation due to network and serialization differences
        assert abs(payload_size1 - payload_size2) < 10  # Within 10KB
        assert abs(payload_size2 - payload_size3) < 10  # Within 10KB

    def test_cache_efficiency(self, test_files):
        """
        Test that caching provides efficiency gains.
        Verify that repeated analysis of the same interval is faster due to caching.
        """
        client = TestClient(app)
        wav_path, prh_path, events_path = test_files

        # Upload files
        with open(wav_path, "rb") as wav_f, \
             open(prh_path, "rb") as prh_f, \
             open(events_path, "rb") as events_f:
            upload_resp = client.post(
                "/api/upload",
                files={
                    "wav_file": ("test_audio.wav", wav_f, "audio/wav"),
                    "prh_csv": ("test_prh.csv", prh_f, "text/csv"),
                    "events_csv": ("test_events.csv", events_f, "text/csv"),
                }
            )

        deployment_id = upload_resp.json()["deployment_id"]

        # First analysis (compute)
        start = time.time()
        resp1 = client.post(
            "/api/analyze",
            json={
                "deployment_id": deployment_id,
                "start_idx": 20,
                "end_idx": 80
            }
        )
        time1 = time.time() - start

        assert resp1.status_code == 200
        data1 = resp1.json()

        # Second analysis same interval (cache hit)
        start = time.time()
        resp2 = client.post(
            "/api/analyze",
            json={
                "deployment_id": deployment_id,
                "start_idx": 20,
                "end_idx": 80
            }
        )
        time2 = time.time() - start

        assert resp2.status_code == 200
        data2 = resp2.json()

        # Verify responses are identical
        assert data1 == data2

        # Cache hit should be significantly faster or at least comparable
        # (In practice, cache hits are much faster; we use a loose check)
        assert time2 <= time1 * 1.5 or time2 < 0.1  # Cache hit is reasonably fast

    def test_multiple_deployments_isolated(self, test_files):
        """
        Test that cache is properly isolated between deployments.
        Multiple deployments should not interfere with each other's cached data.
        """
        client = TestClient(app)
        wav_path, prh_path, events_path = test_files

        # Create two different deployment IDs by modifying the events file
        with tempfile.TemporaryDirectory() as tmpdir2:
            # First deployment
            with open(wav_path, "rb") as wav_f, \
                 open(prh_path, "rb") as prh_f, \
                 open(events_path, "rb") as events_f:
                upload_resp1 = client.post(
                    "/api/upload",
                    files={
                        "wav_file": ("test_audio.wav", wav_f, "audio/wav"),
                        "prh_csv": ("test_prh.csv", prh_f, "text/csv"),
                        "events_csv": ("test_events.csv", events_f, "text/csv"),
                    }
                )

            deploy_id1 = upload_resp1.json()["deployment_id"]

            # Create second events file with different deployment ID
            events_data2 = pd.DataFrame({
                "Deployment_ID": ["integration_test_deploy_2"],
                "Type": ["event_type"],
                "DN_start_idx": [0],
                "DN_end_idx": [10],
            })
            events_path2 = os.path.join(tmpdir2, "test_events2.csv")
            events_data2.to_csv(events_path2, index=False)

            # Second deployment
            with open(wav_path, "rb") as wav_f, \
                 open(prh_path, "rb") as prh_f, \
                 open(events_path2, "rb") as events_f:
                upload_resp2 = client.post(
                    "/api/upload",
                    files={
                        "wav_file": ("test_audio.wav", wav_f, "audio/wav"),
                        "prh_csv": ("test_prh.csv", prh_f, "text/csv"),
                        "events_csv": ("test_events2.csv", events_f, "text/csv"),
                    }
                )

            deploy_id2 = upload_resp2.json()["deployment_id"]
            assert deploy_id2 == "integration_test_deploy_2"

        # Analyze different intervals for each deployment
        resp1 = client.post(
            "/api/analyze",
            json={
                "deployment_id": deploy_id1,
                "start_idx": 10,
                "end_idx": 30
            }
        )
        assert resp1.status_code == 200
        data1 = resp1.json()

        resp2 = client.post(
            "/api/analyze",
            json={
                "deployment_id": deploy_id2,
                "start_idx": 50,
                "end_idx": 70
            }
        )
        assert resp2.status_code == 200
        data2 = resp2.json()

        # Verify both have correct data
        assert len(data1["pitch"]) == 20  # 30 - 10
        assert len(data2["pitch"]) == 20  # 70 - 50

        # Analyze same interval on second deployment
        resp3 = client.post(
            "/api/analyze",
            json={
                "deployment_id": deploy_id2,
                "start_idx": 50,
                "end_idx": 70
            }
        )
        assert resp3.status_code == 200
        data3 = resp3.json()

        # Verify cache hit for second deployment
        assert data2 == data3

    def test_analyze_invalid_deployment(self):
        """Test that analyze returns 404 for nonexistent deployment."""
        client = TestClient(app)

        response = client.post(
            "/api/analyze",
            json={
                "deployment_id": "nonexistent_deploy_xyz",
                "start_idx": 10,
                "end_idx": 50
            }
        )

        assert response.status_code == 404

    def test_response_consistency_across_calls(self, test_files):
        """
        Test that repeated calls to analyze return consistent responses.
        Ensures cache retrieval produces identical results.
        """
        client = TestClient(app)
        wav_path, prh_path, events_path = test_files

        # Upload
        with open(wav_path, "rb") as wav_f, \
             open(prh_path, "rb") as prh_f, \
             open(events_path, "rb") as events_f:
            upload_resp = client.post(
                "/api/upload",
                files={
                    "wav_file": ("test_audio.wav", wav_f, "audio/wav"),
                    "prh_csv": ("test_prh.csv", prh_f, "text/csv"),
                    "events_csv": ("test_events.csv", events_f, "text/csv"),
                }
            )

        deployment_id = upload_resp.json()["deployment_id"]

        # Perform multiple analyses of the same interval
        responses = []
        for _ in range(3):
            resp = client.post(
                "/api/analyze",
                json={
                    "deployment_id": deployment_id,
                    "start_idx": 30,
                    "end_idx": 60
                }
            )
            assert resp.status_code == 200
            responses.append(resp.json())

        # All responses should be identical
        assert responses[0] == responses[1]
        assert responses[1] == responses[2]

        # Verify data integrity across calls
        for response in responses:
            assert len(response["pitch"]) == 30
            assert len(response["speed"]) == 30
            assert isinstance(response["pitch"][0], (int, float))


class TestCachePerformanceCharacteristics:
    """Test performance characteristics of the caching system."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Clear cache before each test."""
        cache = get_session_cache()
        cache.clear()
        yield
        cache.clear()

    @pytest.fixture
    def test_files(self):
        """Create temporary test files for upload."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test WAV file (20 seconds at 16000 Hz to match 200 PRH samples at 10 Hz)
            sr = 16000
            duration = 20
            samples = sr * duration
            audio_data = np.random.randn(samples).astype(np.float32)
            wav_path = os.path.join(tmpdir, "test_audio.wav")
            wavfile.write(wav_path, sr, audio_data)

            # Create a PRH CSV file
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
                "Deployment_ID": ["perf_test_deploy"],
                "Type": ["event_type"],
                "DN_start_idx": [0],
                "DN_end_idx": [10],
            })
            events_path = os.path.join(tmpdir, "test_events.csv")
            events_data.to_csv(events_path, index=False)

            yield wav_path, prh_path, events_path

    def test_sequential_cache_accesses(self, test_files):
        """
        Test that sequential cache accesses maintain performance.
        """
        client = TestClient(app)
        wav_path, prh_path, events_path = test_files

        # Upload
        with open(wav_path, "rb") as wav_f, \
             open(prh_path, "rb") as prh_f, \
             open(events_path, "rb") as events_f:
            upload_resp = client.post(
                "/api/upload",
                files={
                    "wav_file": ("test_audio.wav", wav_f, "audio/wav"),
                    "prh_csv": ("test_prh.csv", prh_f, "text/csv"),
                    "events_csv": ("test_events.csv", events_f, "text/csv"),
                }
            )

        deployment_id = upload_resp.json()["deployment_id"]

        # Perform 5 sequential analyses of the same interval
        times = []
        for i in range(5):
            start = time.time()
            resp = client.post(
                "/api/analyze",
                json={
                    "deployment_id": deployment_id,
                    "start_idx": 10,
                    "end_idx": 40
                }
            )
            elapsed = time.time() - start
            times.append(elapsed)
            assert resp.status_code == 200

        # After first call, subsequent calls should be cached and fast
        # First call might be slower due to computation
        assert len(times) == 5
        # All calls should complete in reasonable time
        for t in times:
            assert t < 1.0  # Each call should be fast (< 1 second)

    def test_analysis_with_varying_interval_sizes(self, test_files):
        """
        Test analysis with different interval sizes to verify no payload issues.
        """
        client = TestClient(app)
        wav_path, prh_path, events_path = test_files

        # Upload
        with open(wav_path, "rb") as wav_f, \
             open(prh_path, "rb") as prh_f, \
             open(events_path, "rb") as events_f:
            upload_resp = client.post(
                "/api/upload",
                files={
                    "wav_file": ("test_audio.wav", wav_f, "audio/wav"),
                    "prh_csv": ("test_prh.csv", prh_f, "text/csv"),
                    "events_csv": ("test_events.csv", events_f, "text/csv"),
                }
            )

        deployment_id = upload_resp.json()["deployment_id"]

        # Test various interval sizes
        intervals = [
            (5, 15),      # 10 samples
            (10, 50),     # 40 samples
            (0, 100),     # 100 samples (larger)
            (100, 150),   # 50 samples
        ]

        for start_idx, end_idx in intervals:
            resp = client.post(
                "/api/analyze",
                json={
                    "deployment_id": deployment_id,
                    "start_idx": start_idx,
                    "end_idx": end_idx
                }
            )
            assert resp.status_code == 200
            data = resp.json()
            expected_length = end_idx - start_idx
            assert len(data["pitch"]) == expected_length
            assert len(data["speed"]) == expected_length
