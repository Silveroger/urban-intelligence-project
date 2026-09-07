import logging
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.config import settings

logger = logging.getLogger("urban_intel.map_matching")


async def find_nearest_road_segment(
    db: AsyncSession,
    latitude: float,
    longitude: float,
    max_distance_meters: Optional[float] = None,
) -> Optional[Tuple[str, float]]:
    """
    Finds the nearest road segment to the given GPS coordinates using PostGIS.
    Uses the configured `gis` schema for PostGIS spatial functions and documented columns (segment_id, geom).

    Returns:
        (segment_id_str, distance_meters) or None if no segment is within max_distance_meters.
    """
    max_dist = max_distance_meters or settings.MAP_MATCH_MAX_DISTANCE_METERS
    gis_schema = settings.POSTGIS_SCHEMA

    query_str = f"""
        SELECT 
            segment_id,
            name,
            {gis_schema}.ST_Distance(
                geom::{gis_schema}.geography,
                {gis_schema}.ST_SetSRID({gis_schema}.ST_MakePoint(:lng, :lat), 4326)::{gis_schema}.geography
            ) AS distance_meters
        FROM road_segments
        WHERE {gis_schema}.ST_DWithin(
            geom::{gis_schema}.geography,
            {gis_schema}.ST_SetSRID({gis_schema}.ST_MakePoint(:lng, :lat), 4326)::{gis_schema}.geography,
            :max_dist
        )
        ORDER BY distance_meters ASC
        LIMIT 1;
    """

    try:
        result = await db.execute(
            text(query_str),
            {"lng": longitude, "lat": latitude, "max_dist": max_dist},
        )
        row = result.fetchone()
        if row:
            segment_id = str(row[0])
            distance = float(row[2])
            return (segment_id, distance)
    except Exception as e:
        logger.warning(
            f"PostGIS map matching primary query failed: {e}. Attempting fallback with session search_path."
        )
        try:
            # Explicitly ensure search_path covers gis schema in fallback
            await db.execute(text(f"SET LOCAL search_path TO public, {gis_schema};"))
            fallback_query = f"""
                SELECT 
                    segment_id,
                    name,
                    {gis_schema}.ST_Distance(
                        geom::{gis_schema}.geography,
                        {gis_schema}.ST_SetSRID({gis_schema}.ST_MakePoint(:lng, :lat), 4326)::{gis_schema}.geography
                    ) AS distance_meters
                FROM road_segments
                WHERE {gis_schema}.ST_DWithin(
                    geom::{gis_schema}.geography,
                    {gis_schema}.ST_SetSRID({gis_schema}.ST_MakePoint(:lng, :lat), 4326)::{gis_schema}.geography,
                    :max_dist
                )
                ORDER BY distance_meters ASC
                LIMIT 1;
            """
            result = await db.execute(
                text(fallback_query),
                {"lng": longitude, "lat": latitude, "max_dist": max_dist},
            )
            row = result.fetchone()
            if row:
                return (str(row[0]), float(row[2]))
        except Exception as e2:
            logger.error(f"Fallback map matching also failed: {e2}")

    return None
