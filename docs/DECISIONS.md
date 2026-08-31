# Architecture Decisions

## ADR-001 — PostgreSQL + PostGIS
Use PostgreSQL + PostGIS as the persistent geospatial backend. JSON is the interchange format; structured relational/spatial fields are persisted in the database, with JSONB available for flexible metadata.

## ADR-002 — Frontend data abstraction
The dashboard uses a service/data-provider layer so mock and live API sources can swap without rewriting UI components.

## ADR-003 — GeoJSON convention
GeoJSON and deck.gl geometry use `[lng, lat]`. Google Maps objects use `{lat, lng}`. Conversion occurs at rendering boundaries.

## ADR-004 — REST initial state + WebSocket deltas
REST loads initial state; WebSocket supplies incremental live updates. The dashboard must remain usable if WebSocket disconnects.

## ADR-005 — Specialized CV over generic LLM
Core perception is computer vision; an LLM is optional and non-core.
