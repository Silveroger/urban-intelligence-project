"""
SIH 26124 — Main FastAPI Server Entrypoint
Integrates REST Endpoints, WebSocket Broadcaster, and Static Evidence File Server.
Conforms strictly to docs/API_CONTRACT.md and docs/TECH_STACK.md.
"""

from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.api.analytics import router as analytics_router
from backend.app.api.buses import router as buses_router
from backend.app.api.events import router as events_router
from backend.app.api.incidents import router as incidents_router
from backend.app.api.ingest import router as ingest_router
from backend.app.api.segments import router as segments_router
from backend.app.core.config import settings
from backend.app.services.websocket_hub import ws_hub

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Centralized Urban Intelligence & Edge Sensing Platform for Public Transport Fleet",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Directories for Defect Keyframe Crops & Incident Clips
static_dir = settings.STATIC_DIR
static_dir.mkdir(parents=True, exist_ok=True)
settings.EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/evidence", StaticFiles(directory=str(settings.EVIDENCE_DIR)), name="evidence")

# Include REST Routers under /api/v1 prefix
app.include_router(segments_router, prefix=settings.API_V1_STR)
app.include_router(events_router, prefix=settings.API_V1_STR)
app.include_router(incidents_router, prefix=settings.API_V1_STR)
app.include_router(buses_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
app.include_router(ingest_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "docs_url": "/docs",
        "api_v1": settings.API_V1_STR
    }


# WebSocket Protocol Endpoint (/ws/live) matching docs/API_CONTRACT.md (§3)
@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await ws_hub.connect(websocket)
    try:
        while True:
            # Keep-alive loop
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_hub.disconnect(websocket)
    except Exception:
        ws_hub.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
