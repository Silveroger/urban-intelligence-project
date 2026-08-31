---
name: geospatial-postgis
description: Designs and reviews PostgreSQL/PostGIS schemas and geospatial queries for road matching, road segments, observations, history, and aggregation.
---
# Geospatial/PostGIS
Read `docs/DATABASE_SCHEMA.md` and `docs/ARCHITECTURE.md`.
Keep persistent spatial truth in PostGIS.
Use proper geometry/geography types, SRIDs, spatial indexes, and explicit query semantics.
Keep database logic out of the frontend.
Any schema change requires documentation and migration discipline.
