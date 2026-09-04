import logging
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from supabase import create_client, Client
from app.core.config import settings

logger = logging.getLogger("urban_intel.db")

Base = declarative_base()

def create_db_engine():
    db_url = settings.DATABASE_URL
    if "asyncpg" in db_url:
        try:
            import asyncpg  # noqa: F401
        except ImportError:
            logger.warning(
                "asyncpg driver not installed in current environment; using in-memory aiosqlite for tests."
            )
            db_url = "sqlite+aiosqlite:///:memory:"

    kwargs = {"echo": False}
    if not db_url.startswith("sqlite"):
        kwargs["pool_pre_ping"] = True
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 20

    return create_async_engine(db_url, **kwargs)


engine = create_db_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Supabase Client Singleton
_supabase_client: Optional[Client] = None


def get_supabase_client() -> Optional[Client]:
    """Returns initialized Supabase client using service role key, or None if unconfigured."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    if (
        settings.SUPABASE_URL
        and settings.SUPABASE_SERVICE_ROLE_KEY
        and not settings.SUPABASE_URL.startswith("https://your-project-ref")
    ):
        try:
            _supabase_client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY,
            )
        except Exception as e:
            logger.warning(f"Failed to initialize Supabase client: {e}")
            _supabase_client = None

    return _supabase_client


async def check_database_connection() -> dict:
    """
    Validates database connectivity and PostGIS in the configured schema.
    Returns status dict with found tables and postgis version.
    """
    result = {
        "status": "unknown",
        "postgis_version": None,
        "postgis_schema": settings.POSTGIS_SCHEMA,
        "tables_found": [],
    }

    try:
        async with AsyncSessionLocal() as session:
            # 1. Test basic connectivity
            await session.execute(text("SELECT 1;"))
            result["status"] = "connected"

            # 2. Test PostGIS in the specified schema
            try:
                gis_ver = await session.execute(
                    text(f"SELECT {settings.POSTGIS_SCHEMA}.PostGIS_Full_Version();")
                )
                row = gis_ver.fetchone()
                if row:
                    result["postgis_version"] = row[0]
            except Exception:
                # Fall back to standard unqualified call if gis schema function fails
                try:
                    gis_ver = await session.execute(text("SELECT PostGIS_Full_Version();"))
                    row = gis_ver.fetchone()
                    if row:
                        result["postgis_version"] = row[0]
                except Exception:
                    result["postgis_version"] = "unavailable"

            # 3. Check for the 6 existing tables in public schema
            tables_query = await session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' "
                    "AND table_name IN ('buses', 'gps_points', 'road_segments', 'observations', 'incidents', 'segment_history');"
                )
            )
            result["tables_found"] = [r[0] for r in tables_query.fetchall()]

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result
