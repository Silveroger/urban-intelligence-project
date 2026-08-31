---
name: gis-frontend
description: Builds and reviews the React GIS dashboard for SIH 26124, including Google Maps, road layers, markers, filters, inspectors, history, and deck.gl visualization.
---
# GIS Frontend
Read `docs/FRONTEND_ARCHITECTURE.md` and `AGENT_CONTEXT.md`.
Keep map rendering separate from scoring/business logic.
Preserve GeoJSON `[lng,lat]` conventions and explicit conversions at rendering boundaries.
Keep data sources behind the service/data-provider layer.
Use existing map/layer components before introducing new ones.
Verify performance for dense map data and preserve existing filters/interactions.
