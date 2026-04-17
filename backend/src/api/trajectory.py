from fastapi import APIRouter, HTTPException
from src.models import TrajectoryRequest, TrajectoryResponse
from src.api.upload import _session_data
from src.cache import get_session_cache
from src.processing.metrics import compute_trajectory

router = APIRouter()


@router.post("/trajectory", response_model=TrajectoryResponse)
async def trajectory(request: TrajectoryRequest):
    """Compute 3D trajectory for a time interval."""
    # Find session by deployment_id
    session = None
    for sid, sess_data in _session_data.items():
        if sess_data.get("deployment_id") == request.deployment_id:
            session = sess_data
            break

    if session is None:
        raise HTTPException(status_code=404, detail="Deployment not found")

    # Get cached metrics
    cache = get_session_cache()
    cached_metrics = cache.extract_interval(
        request.deployment_id, request.start_idx, request.end_idx
    )

    if cached_metrics is None:
        raise HTTPException(status_code=400, detail="Metrics not cached")

    prh_slice, accel_slice, jerk_slice = cached_metrics

    # Compute trajectory from PRH data
    traj = compute_trajectory(
        speed_smoothed=prh_slice["speed_smoothed"].values,
        heading_smoothed_wrapped=prh_slice["heading_smoothed_wrapped"].values,
        pitch_smoothed=prh_slice["pitch_smoothed"].values,
        depth_smoothed=prh_slice["depth_smoothed"].values,
        hz=10,
    )

    return TrajectoryResponse(
        dx=traj["dx"].tolist(),
        dy=traj["dy"].tolist(),
        dz=traj["dz"].tolist(),
    )
