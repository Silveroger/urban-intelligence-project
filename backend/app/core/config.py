"""
SIH 26124 — Backend Application Configuration
Conforms to docs/SECURITY.md and docs/ENVIRONMENT.md
"""

from pathlib import Path


class Settings:
    PROJECT_NAME: str = "SIH 26124 Urban Intelligence Platform"
    API_V1_STR: str = "/api/v1"
    CORS_ORIGINS: list = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "*"
    ]
    
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    STATIC_DIR: Path = BASE_DIR / "static"
    EVIDENCE_DIR: Path = STATIC_DIR / "evidence"
    DATA_DIR: Path = BASE_DIR / "data"
    ROADS_GEOJSON: Path = DATA_DIR / "chandigarh_roads.geojson"


settings = Settings()
settings.EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
