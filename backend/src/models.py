from pydantic import BaseModel
from typing import Optional, Dict, List, Any


class UploadResponse(BaseModel):
    session_id: str
    message: str
    deployment_id: str
    duration_seconds: float
    spectrogram_preview: Dict[str, Any]
    events: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None


class PreviewResponse(BaseModel):
    deployment_id: str
    duration_seconds: float
    events: List[Dict[str, Any]] = []


class AnalyzeRequest(BaseModel):
    deployment_id: str
    start_idx: int
    end_idx: int


class TrajectoryRequest(BaseModel):
    deployment_id: str
    start_idx: int
    end_idx: int


class TrajectoryResponse(BaseModel):
    dx: List[float]
    dy: List[float]
    dz: List[float]


class AnalyzeResponse(BaseModel):
    deployment_id: str
    start_idx: int
    end_idx: int
    audio_slice: List[float]
    sample_rate: int
    spectrogram: Dict[str, Any]
    prh_data: Dict[str, List[float]]
    jerk: List[float]
    fluke_stroke: List[float]
    pitch: List[float]
    roll: List[float]
    heading: List[float]
    depth: List[float]
    speed: List[float]
    gy_filt: List[float]
    fluke_stroke_normalized: List[float]
    odba: List[float]
    vedba: List[float]
    msa: List[float]
