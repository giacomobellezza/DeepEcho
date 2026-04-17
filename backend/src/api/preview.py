from fastapi import APIRouter, HTTPException
from src.models import PreviewResponse
from src.api.upload import _session_data

router = APIRouter()


@router.get("/preview/{deployment_id}", response_model=PreviewResponse)
async def preview(deployment_id: str):
    """
    Get preview information for a deployment.
    """
    session_key = deployment_id
    if session_key not in _session_data:
        raise HTTPException(status_code=404, detail="Deployment not found")

    session = _session_data[session_key]
    sr = session.get("sr", 0)
    total_frames = session.get("total_frames", 0)

    duration_seconds = total_frames / sr if sr > 0 else 0.0
    events = session.get("events", [])

    return PreviewResponse(
        deployment_id=deployment_id,
        duration_seconds=duration_seconds,
        events=events,
    )
