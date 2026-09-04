from app.core.config import Settings


def test_settings_cors_parsing():
    s = Settings(CORS_ORIGINS="http://localhost:5173, http://localhost:3000")
    assert "http://localhost:5173" in s.CORS_ORIGINS
    assert "http://localhost:3000" in s.CORS_ORIGINS


def test_settings_db_url_asyncpg_scheme():
    s = Settings(DATABASE_URL="postgresql://user:pass@localhost:5432/db")
    assert s.DATABASE_URL.startswith("postgresql+asyncpg://")

    s2 = Settings(DATABASE_URL="postgres://user:pass@localhost:5432/db")
    assert s2.DATABASE_URL.startswith("postgresql+asyncpg://")


def test_settings_defaults():
    s = Settings()
    assert s.POSTGIS_SCHEMA == "gis"
    assert s.CONFIDENCE_THRESHOLD == 0.50
    assert s.MAP_MATCH_MAX_DISTANCE_METERS == 25.0
