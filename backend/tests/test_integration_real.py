"""
Real Database & PostGIS Integration Test Suite
Validates real PostgreSQL connection, PostGIS spatial functions in schema 'gis',
canonical schema entities (including routes, trips, and gps_records view),
real map matching, and data integrity against live Supabase.
"""
import pytest
from sqlalchemy import text
from app.db.database import AsyncSessionLocal
from app.services.map_matching import find_nearest_road_segment
from app.services.scoring import calculate_road_health


@pytest.mark.asyncio
async def test_real_postgres_connection():
    """Verify live connection to PostgreSQL 17 via the pooler."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT version();"))
        version_str = result.scalar()
        assert version_str is not None
        assert "PostgreSQL" in version_str


@pytest.mark.asyncio
async def test_real_postgis_in_gis_schema():
    """Verify PostGIS functions in the 'gis' schema execute properly."""
    async with AsyncSessionLocal() as session:
        # Check PostGIS version
        res_version = await session.execute(text("SELECT gis.postgis_full_version();"))
        pgis_ver = res_version.scalar()
        assert "POSTGIS" in pgis_ver

        # Test distance calculation with explicit gis.geography cast
        distance_query = text(
            "SELECT gis.ST_Distance("
            "  gis.ST_SetSRID(gis.ST_MakePoint(76.7794, 30.7333), 4326)::gis.geography, "
            "  gis.ST_SetSRID(gis.ST_MakePoint(76.7820, 30.7350), 4326)::gis.geography"
            ");"
        )
        res_dist = await session.execute(distance_query)
        dist_meters = res_dist.scalar()
        assert dist_meters is not None
        assert dist_meters > 0.0


@pytest.mark.asyncio
async def test_canonical_tables_and_views_exist():
    """Verify all 9 canonical entities/views exist in public schema."""
    canonical_entities = [
        "buses",
        "gps_points",
        "road_segments",
        "observations",
        "incidents",
        "segment_history",
        "routes",
        "trips",
        "gps_records",
    ]
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public';"
            )
        )
        existing = [row[0] for row in res.fetchall()]
        for entity in canonical_entities:
            assert entity in existing, f"Canonical entity '{entity}' missing from database!"


@pytest.mark.asyncio
async def test_gps_records_compatibility_view():
    """Verify gps_records view maps to gps_points without data loss."""
    async with AsyncSessionLocal() as session:
        res_view = await session.execute(text("SELECT COUNT(*) FROM gps_records;"))
        res_points = await session.execute(text("SELECT COUNT(*) FROM gps_points;"))
        count_view = res_view.scalar()
        count_points = res_points.scalar()
        assert count_view == count_points


@pytest.mark.asyncio
async def test_real_map_matching():
    """Verify map-matching service executes a real spatial query against road_segments."""
    async with AsyncSessionLocal() as session:
        # Coordinates in Chandigarh matching TEST ROAD - SECTOR 1
        match = await find_nearest_road_segment(
            session,
            latitude=30.704,
            longitude=76.717,
            max_distance_meters=500.0,
        )
        # Should match the seeded test road segment
        assert match is not None
        segment_id, distance = match
        assert isinstance(segment_id, str)
        assert distance >= 0.0


def test_confidence_weighting_and_clean_pass_scoring():
    """Verify scoring logic properly computes weighted penalties and recovery."""
    obs = [
        {"observation_type": "road_defect", "severity": 2, "confidence": 0.8},
        {"observation_type": "clean_pass"},
    ]
    # Severity 2 base weight = 5, repeat factor = 0 -> penalty = 5 * 0.8 = 4.0
    # Clean pass bonus = +5.0 -> net bonus = +1.0 -> score capped at 100.0
    score, condition = calculate_road_health(obs, weight_by_confidence=True)
    assert score == 100.0
    assert condition == "good"
