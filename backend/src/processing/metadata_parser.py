"""Parse deployment metadata from either a JSON file or the plain-text
`--- SECTION ---` format. Both are normalized to one dict shape."""

import json
import re
from typing import Optional


def _num(value: str) -> Optional[float]:
    m = re.search(r"-?\d+\.?\d*", value or "")
    return float(m.group()) if m else None


def _empty() -> dict:
    return {
        "title": None,
        "deployment_id": None,
        "species": None,
        "project": None,
        "notes": None,
        "deployment_start": None,
        "deployment_end": None,
        "timezone": None,
        "gps_track": [],
        "additional_metadata": {
            "tag_model": None,
            "sampling_rate_audio": None,
            "sampling_rate_sensors": None,
        },
    }


def parse_metadata(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    if raw.lstrip().startswith("{"):
        try:
            return _normalize_json(json.loads(raw))
        except json.JSONDecodeError:
            pass
    return _parse_text(raw)


def _normalize_json(d: dict) -> dict:
    # Two shapes are supported: a flat schema (legacy) and a nested schema with
    # `deployment` / `date` / `additional_metadata` objects plus a
    # `gps_track_log` list. Nested values take priority, falling back to flat.
    dep = d.get("deployment") or {}
    date = d.get("date") or {}
    add = d.get("additional_metadata") or {}
    result = _empty()
    result.update({
        "title": d.get("title"),
        "deployment_id": dep.get("id") or d.get("deployment_id") or d.get("animal_id"),
        "species": dep.get("species") or d.get("species"),
        "project": dep.get("project") or d.get("research_group") or d.get("project"),
        "notes": dep.get("notes") or d.get("notes"),
        "deployment_start": date.get("deployment_start") or d.get("deployment_start"),
        "deployment_end": date.get("deployment_end") or d.get("deployment_end"),
        "timezone": date.get("timezone") or d.get("timezone"),
        "gps_track": [
            {
                # nested points use `event`; flat points use `label`
                "label": p.get("label") or p.get("event"),
                "timestamp": p.get("timestamp"),
                "latitude": p.get("latitude"),
                "longitude": p.get("longitude"),
            }
            for p in (d.get("gps_track") or d.get("gps_track_log") or [])
        ],
        "additional_metadata": {
            "tag_model": add.get("tag_model"),
            "sampling_rate_audio": add.get("sampling_rate_audio") or add.get("sampling_rate_audio_hz"),
            "sampling_rate_sensors": add.get("sampling_rate_sensors") or add.get("sampling_rate_sensors_hz"),
        },
    })
    return result


def _parse_text(raw: str) -> dict:
    result = _empty()
    current_point = None
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("---") or set(s) == {"="}:
            continue
        m = re.match(r"Point\s+\d+:\s*(?:\(([^)]*)\))?", s)
        if m:
            current_point = {
                "label": (m.group(1) or "").strip() or None,
                "timestamp": None,
                "latitude": None,
                "longitude": None,
            }
            result["gps_track"].append(current_point)
            continue
        if ":" not in s:
            continue
        key, _, value = s.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if key in ("deployment start", "deployment end"):
            value = re.split(r"\s+\(", value)[0].strip()

        if key == "deployment id":
            result["deployment_id"] = value
        elif key == "species":
            result["species"] = value
        elif key == "project":
            result["project"] = value
        elif key == "notes":
            result["notes"] = value
        elif key == "deployment start":
            result["deployment_start"] = value
        elif key == "deployment end":
            result["deployment_end"] = value
        elif key == "timezone":
            result["timezone"] = value
        elif key == "tag model":
            result["additional_metadata"]["tag_model"] = value
        elif key == "sampling rate audio":
            result["additional_metadata"]["sampling_rate_audio"] = _num(value)
        elif key == "sampling rate sensors":
            result["additional_metadata"]["sampling_rate_sensors"] = _num(value)
        elif key == "timestamp" and current_point is not None:
            current_point["timestamp"] = value
        elif key == "latitude" and current_point is not None:
            current_point["latitude"] = _num(value)
        elif key == "longitude" and current_point is not None:
            current_point["longitude"] = _num(value)
    return result
