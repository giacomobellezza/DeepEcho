import json
import os
import tempfile
import pytest
from src.processing.metadata_parser import parse_metadata


def _write(tmpdir, name, content):
    path = os.path.join(tmpdir, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def test_parse_json_metadata():
    with tempfile.TemporaryDirectory() as tmp:
        data = {
            "title": "Sperm whale deployment - DP2",
            "animal_id": "SW_001",
            "species": "Physeter macrocephalus",
            "deployment_start": "2026-05-28T14:05:06.860Z",
            "deployment_end": "2026-05-28T18:42:10.120Z",
            "timezone": "UTC+2",
            "gps_track": [
                {"timestamp": "2026-05-28T14:10:00.000Z", "latitude": 43.12345, "longitude": 10.54321}
            ],
            "research_group": "Project Name / Institution",
            "notes": "Optional deployment notes",
            "additional_metadata": {"tag_model": "DTAG-X", "sampling_rate_audio": 192000, "sampling_rate_sensors": 400},
        }
        path = _write(tmp, "meta.json", json.dumps(data))
        result = parse_metadata(path)

    assert result["title"] == "Sperm whale deployment - DP2"
    assert result["species"] == "Physeter macrocephalus"
    assert result["timezone"] == "UTC+2"
    assert result["deployment_start"] == "2026-05-28T14:05:06.860Z"
    assert len(result["gps_track"]) == 1
    assert result["gps_track"][0]["latitude"] == 43.12345
    assert result["additional_metadata"]["sampling_rate_audio"] == 192000


def test_parse_nested_json_metadata():
    """Nested schema: deployment/date/additional_metadata + gps_track_log."""
    with tempfile.TemporaryDirectory() as tmp:
        data = {
            "deployment": {
                "id": "pm20240701-CD3",
                "species": "Physeter macrocephalus",
                "project": "DIVES / SZN",
                "notes": ["Photogrammetry", "Biopsy"],
            },
            "date": {
                "deployment_start": "2024-07-01T13:02:00.820+02:00",
                "deployment_end": "2024-07-01T21:21:48.620+02:00",
                "timezone": "UTC+2",
            },
            "gps_track_log": [
                {"point": 1, "event": "Tag On", "timestamp": "2024-07-01T13:03:01.000+02:00",
                 "latitude": 37.1118, "longitude": 15.3438},
                {"point": 2, "event": "Surface 1", "timestamp": "2024-07-01T13:55:43.000+02:00",
                 "latitude": 37.1228, "longitude": 15.3351},
            ],
            "additional_metadata": {
                "tag_model": "CATS Diary CD3",
                "sampling_rate_audio_hz": 192000,
                "sampling_rate_sensors_hz": 400,
            },
        }
        path = _write(tmp, "nested.json", json.dumps(data))
        result = parse_metadata(path)

    assert result["deployment_id"] == "pm20240701-CD3"
    assert result["species"] == "Physeter macrocephalus"
    assert result["project"] == "DIVES / SZN"
    assert result["deployment_start"] == "2024-07-01T13:02:00.820+02:00"
    assert result["timezone"] == "UTC+2"
    assert len(result["gps_track"]) == 2
    assert result["gps_track"][0]["label"] == "Tag On"
    assert result["gps_track"][0]["latitude"] == pytest.approx(37.1118)
    assert result["additional_metadata"]["tag_model"] == "CATS Diary CD3"
    assert result["additional_metadata"]["sampling_rate_audio"] == 192000
    assert result["additional_metadata"]["sampling_rate_sensors"] == 400


def test_parse_text_metadata_dp1():
    text = """--- GENERAL INFO ---
Deployment ID:    pm20240701-CD3
Species:          Physeter macrocephalus
Project:	  DIVES \\ SZN
Notes:            Photogrammetry\\Biopsy\\Blow

--- DATE ---
Deployment Start: 2024-07-01 13:02:00.820 (YY:MM:DD HH:SS:MM.FFF)
Deployment End:   2024-07-01 21:21:48.620
Timezone:         UTC+2

--- GPS TRACK LOG --- Timestamp in Local Time
Point 1: (Tag On)
  Timestamp: 13:03:01.000
  Latitude:  37.1118
  Longitude: 15.3438
Point 2: (Surface 1)
  Timestamp: 13:55:43.000
  Latitude:  37.1228
  Longitude: 15.3351

--- ADDITIONAL METADATA ---
Tag Model:            CATS Diary CD3
Sampling Rate Audio:  192000 Hz
Sampling Rate Sensors:400 Hz
"""
    with tempfile.TemporaryDirectory() as tmp:
        path = _write(tmp, "DP1.txt", text)
        result = parse_metadata(path)

    assert result["deployment_id"] == "pm20240701-CD3"
    assert result["species"] == "Physeter macrocephalus"
    assert result["timezone"] == "UTC+2"
    assert result["deployment_start"] == "2024-07-01 13:02:00.820"
    assert result["deployment_end"] == "2024-07-01 21:21:48.620"
    assert len(result["gps_track"]) == 2
    assert result["gps_track"][0]["label"] == "Tag On"
    assert result["gps_track"][0]["timestamp"] == "13:03:01.000"
    assert result["gps_track"][0]["latitude"] == pytest.approx(37.1118)
    assert result["gps_track"][1]["longitude"] == pytest.approx(15.3351)
    assert result["additional_metadata"]["tag_model"] == "CATS Diary CD3"
    assert result["additional_metadata"]["sampling_rate_audio"] == 192000
    assert result["additional_metadata"]["sampling_rate_sensors"] == 400


def test_parse_partial_text_does_not_raise():
    with tempfile.TemporaryDirectory() as tmp:
        path = _write(tmp, "partial.txt", "--- GENERAL INFO ---\nSpecies: Orcinus orca\n")
        result = parse_metadata(path)
    assert result["species"] == "Orcinus orca"
    assert result["deployment_start"] is None
    assert result["gps_track"] == []
