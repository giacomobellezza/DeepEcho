"""Reconstruct a georeferenced surface→underwater track for a deployment.

GPS only fixes when the animal surfaces, so fixes are sparse. We dead-reckon the
full underwater path from PRH heading+speed (reusing ``compute_trajectory``),
then anchor/correct it to the GPS surface fixes (linear drift removal) and
project the corrected local ENU path back to latitude/longitude.
"""

from datetime import datetime
import numpy as np
from fastapi import APIRouter, HTTPException

from src.models import TrackRequest, TrackResponse
from src.api.upload import _session_data
from src.processing.metrics import compute_trajectory

router = APIRouter()

# Equirectangular projection constant (metres per degree of latitude).
_M_PER_DEG = 111_320.0

# Target number of points to send to the client for the decimated path.
_MAX_PATH_POINTS = 4000


def _parse_ts(value):
    """Parse an ISO-8601 timestamp (with offset) to a datetime, or None."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


@router.post("/track", response_model=TrackResponse)
async def track(request: TrackRequest):
    """Compute the reconstructed geographic track for a deployment."""
    # Find session by deployment_id (mirrors trajectory.py).
    session = None
    for sess_data in _session_data.values():
        if sess_data.get("deployment_id") == request.deployment_id:
            session = sess_data
            break
    if session is None:
        raise HTTPException(status_code=404, detail="Deployment not found")

    metadata = session.get("metadata") or {}
    gps_track = metadata.get("gps_track") or []
    if not gps_track:
        raise HTTPException(status_code=404, detail="No GPS track in deployment metadata")

    prh = session.get("prh_data")
    if prh is None or len(prh) == 0:
        raise HTTPException(status_code=400, detail="No PRH data for deployment")

    hz = 10
    n = len(prh)

    # --- Full-deployment dead reckoning → local ENU metres -------------------
    def col(*names):
        for name in names:
            if name in prh.columns:
                return prh[name].values.astype(np.float64)
        return np.zeros(n)

    traj = compute_trajectory(
        speed_smoothed=col("speed_smoothed", "speed"),
        heading_smoothed_wrapped=col("heading_smoothed_wrapped", "heading_smoothed", "heading"),
        pitch_smoothed=col("pitch_smoothed", "pitch"),
        depth_smoothed=col("depth_smoothed", "depth"),
        hz=hz,
    )
    dx = traj["dx"]  # East (m)
    dy = traj["dy"]  # North (m)
    depth = traj["dz"]  # m

    # --- Map GPS fixes → PRH indices -----------------------------------------
    start_dt = _parse_ts(metadata.get("deployment_start"))
    fixes_out = []
    anchors = []  # (idx, east_target, north_target)

    # Projection origin: the first fix that carries valid coordinates.
    lat0 = lon0 = None
    for fix in gps_track:
        if fix.get("latitude") is not None and fix.get("longitude") is not None:
            lat0 = float(fix["latitude"])
            lon0 = float(fix["longitude"])
            break
    if lat0 is None:
        raise HTTPException(status_code=400, detail="GPS fixes have no coordinates")

    cos_lat0 = np.cos(np.deg2rad(lat0))

    def to_enu(lat, lon):
        east = (lon - lon0) * _M_PER_DEG * cos_lat0
        north = (lat - lat0) * _M_PER_DEG
        return east, north

    def to_latlon(east, north):
        lon = lon0 + east / (_M_PER_DEG * cos_lat0)
        lat = lat0 + north / _M_PER_DEG
        return lat, lon

    for fix in gps_track:
        lat = fix.get("latitude")
        lon = fix.get("longitude")
        if lat is None or lon is None:
            continue
        lat = float(lat)
        lon = float(lon)
        fix_dt = _parse_ts(fix.get("timestamp"))
        idx = None
        in_range = False
        if start_dt is not None and fix_dt is not None:
            idx = int(round((fix_dt - start_dt).total_seconds() * hz))
            if 0 <= idx < n:
                in_range = True
                east, north = to_enu(lat, lon)
                anchors.append((idx, east, north))
        fixes_out.append({
            "label": fix.get("label"),
            "latitude": lat,
            "longitude": lon,
            "timestamp": fix.get("timestamp"),
            "in_range": in_range,
        })

    anchors.sort(key=lambda a: a[0])

    # --- Rubber-sheet / linear drift correction ------------------------------
    # Correct dead-reckoned position so the path passes through each GPS anchor.
    # Offset C_j = anchor_target − P_dr(a_j); interpolate C linearly between
    # consecutive anchors, hold the end offsets beyond the first/last anchor.
    corr_e = np.zeros(n)
    corr_n = np.zeros(n)
    if anchors:
        idxs = np.array([a[0] for a in anchors])
        cj_e = np.array([a[1] - dx[a[0]] for a in anchors])
        cj_n = np.array([a[2] - dy[a[0]] for a in anchors])
        all_i = np.arange(n)
        # np.interp clamps to end values outside the anchor range — exactly the
        # "hold first/last offset" behaviour we want.
        corr_e = np.interp(all_i, idxs, cj_e)
        corr_n = np.interp(all_i, idxs, cj_n)
    else:
        # No in-range anchors: just place the path origin at the first fix.
        corr_e[:] = -dx[0]
        corr_n[:] = -dy[0]

    east_path = dx + corr_e
    north_path = dy + corr_n

    # --- Decimate + project back to lat/lon ----------------------------------
    step = max(1, n // _MAX_PATH_POINTS)
    sel = np.arange(0, n, step)
    lat_arr, lon_arr = to_latlon(east_path[sel], north_path[sel])

    return TrackResponse(
        lat=lat_arr.tolist(),
        lon=lon_arr.tolist(),
        depth=depth[sel].tolist(),
        frames=n,
        fixes=fixes_out,
    )
