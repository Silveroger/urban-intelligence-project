# Database Schema

## Target persistent database
PostgreSQL + PostGIS.

## Core entities
- buses
- routes
- trips
- gps_points
- road_segments
- observations
- incidents
- vehicles/tracks
- infrastructure
- evidence
- road condition history

## Responsibility
Backend/geospatial owner maintains schema, migrations, spatial indexes, and persistence logic.

## Rule
Do not create frontend-specific database assumptions. Dashboard consumes API responses.
