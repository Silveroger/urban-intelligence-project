from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings


def setup_cors(app: FastAPI) -> None:
    """Configures CORS middleware using settings.CORS_ORIGINS."""
    origins: List[str] = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )


def mask_secret(secret: str) -> str:
    """Masks secret key strings for safe diagnostics output without leaking credentials."""
    if not secret or len(secret) < 8:
        return "***"
    return f"{secret[:4]}...{secret[-4:]}"
