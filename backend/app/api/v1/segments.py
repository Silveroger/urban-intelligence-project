import json
from typing import List, Optional, Union
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.db.database import get_db
from app.models.road_segment import RoadSegment
from app.models.segment_history import SegmentHistory
from app.schemas.segments import (
    RoadSegmentFeatureCollection,
    RoadSegmentFeature,
    RoadSegmentProperties,
    GeoJSONGeometry,
    RoadSegmentFlat,
    SegmentHistoryItem,
)
from app.core.errors import ResourceNotFoundError
from app.core.config import settings
from app.utils.timestamps import ensure_iso_timestamp
from app.utils.coordinates import linestring_to_geojson_coords

router = APIRouter()


@router.get(
    "/geojson",
    response_model=Union[RoadSegmentFeatureCollection, List[RoadSegmentFlat]],
    summary="Get road segments in GeoJSON FeatureCollection format",
)
async def get_road_segments_geojson(
    format: Optional[str] = Query(default=None, description="Optional format: 'geojson' or 'flat'"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns complete road network with current aggregate condition metrics.
    By default, returns GeoJSON FeatureCollection according to API_CONTRACT.md.
    Supports ?format=flat for array representation.
    """
    gis_schema = settings.POSTGIS_SCHEMA

    query = text(f"""
        SELECT 
            segment_id,
            name,
            {gis_schema}.ST_AsGeoJSON(geom) AS geojson_geom,
            condition_score,
            confidence,
            pothole_count,
            waterlogging_count,
            observation_count,
            last_updated
        FROM road_segments
        ORDER BY segment_id ASC;
    """)

    try:
        res = await db.execute(query)
        rows = res.fetchall()
    except Exception:
        fallback_query = text("""
            SELECT 
                segment_id,
                name,
                ST_AsGeoJSON(geom) AS geojson_geom,
                condition_score,
                confidence,
                pothole_count,
                waterlogging_count,
                observation_count,
                last_updated
            FROM road_segments
            ORDER BY segment_id ASC;
        """)
        res = await db.execute(fallback_query)
        rows = res.fetchall()

    features: List[RoadSegmentFeature] = []
    flat_list: List[RoadSegmentFlat] = []

    for row in rows:
        seg_id = str(row[0])
        name = row[1] or "Road Segment"
        raw_geom = row[2]
        coords = linestring_to_geojson_coords(raw_geom)
        score = float(row[3]) if row[3] is not None else 100.0
        conf = float(row[4]) if row[4] is not None else 1.0
        potholes = int(row[5]) if row[5] is not None else 0
        waterlogging = int(row[6]) if row[6] is not None else 0
        obs_count = int(row[7]) if row[7] is not None else 0
        last_updated = ensure_iso_timestamp(row[8])

        feature = RoadSegmentFeature(
            type="Feature",
            id=seg_id,
            geometry=GeoJSONGeometry(
                type="LineString",
                coordinates=coords,
            ),
            properties=RoadSegmentProperties(
                segment_id=seg_id,
                name=name,
                condition_score=score,
                confidence=conf,
                pothole_count=potholes,
                waterlogging_count=waterlogging,
                observation_count=obs_count,
                last_updated=last_updated,
            ),
        )
        features.append(feature)

        flat_list.append(
            RoadSegmentFlat(
                segment_id=seg_id,
                name=name,
                geometry=coords,
                condition_score=score,
                confidence=conf,
                pothole_count=potholes,
                waterlogging_count=waterlogging,
                observation_count=obs_count,
                last_updated=last_updated,
            )
        )

    if format == "flat":
        return flat_list

    return RoadSegmentFeatureCollection(
        type="FeatureCollection",
        features=features,
    )


@router.get("/{segment_id}", response_model=RoadSegmentProperties, summary="Get road segment details")
async def get_road_segment(
    segment_id: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(RoadSegment).where(
        (RoadSegment.segment_id == segment_id) | (RoadSegment.name == segment_id)
    )
    res = await db.execute(stmt)
    seg = res.scalar_one_or_none()

    if not seg:
        raise ResourceNotFoundError("Road segment", segment_id)

    return RoadSegmentProperties(
        segment_id=str(seg.segment_id),
        name=seg.name or "Road Segment",
        condition_score=float(seg.condition_score) if seg.condition_score is not None else 100.0,
        confidence=float(seg.confidence) if seg.confidence is not None else 1.0,
        pothole_count=seg.pothole_count or 0,
        waterlogging_count=seg.waterlogging_count or 0,
        observation_count=seg.observation_count or 0,
        last_updated=ensure_iso_timestamp(seg.last_updated),
    )


@router.get(
    "/{segment_id}/history",
    response_model=List[SegmentHistoryItem],
    summary="Get historical condition score timeline for a segment",
)
async def get_segment_history(
    segment_id: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SegmentHistory).where(
        SegmentHistory.segment_id == segment_id
    ).order_by(SegmentHistory.recorded_at.asc())

    res = await db.execute(stmt)
    records = res.scalars().all()

    history_items: List[SegmentHistoryItem] = []
    for r in records:
        ts = ensure_iso_timestamp(r.recorded_at)
        score = float(r.condition_score)
        history_items.append(
            SegmentHistoryItem(
                timestamp=ts,
                date=ts,
                condition_score=score,
                score=score,
                confidence=float(r.confidence) if r.confidence is not None else 1.0,
                pothole_count=r.pothole_count or 0,
                bus_id=str(r.bus_id) if r.bus_id else None,
            )
        )

    return history_items
