from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.upload import router as upload_router
from src.api.preview import router as preview_router
from src.api.analyze import router as analyze_router
from src.api.trajectory import router as trajectory_router
from src.api.audio_stream import router as audio_stream_router

app = FastAPI(
    title="Audio Event Detection API",
    description="API for detecting respiratory and other audio events",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload_router, prefix="/api")
app.include_router(preview_router, prefix="/api")
app.include_router(analyze_router, prefix="/api")
app.include_router(trajectory_router, prefix="/api")
app.include_router(audio_stream_router, prefix="/api")


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "ok"}
