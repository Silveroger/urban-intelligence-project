# System Architecture

## Canonical flow

Camera/GPS
→ edge processing
→ AI observations/evidence
→ FastAPI/backend ingestion
→ PostgreSQL + PostGIS
→ aggregation / confidence / road state
→ REST + WebSocket
→ React GIS dashboard

## Boundaries

### Edge
Capture, sampling, packaging, local inference when applicable.

### AI
Perception outputs: class, confidence, severity, tracking/plate information, evidence references.

### Backend / Geospatial
Validation, ingestion, road matching, aggregation, road scoring, historical state, API delivery.

### Database
Persistent relational + spatial truth.

### Dashboard
Visualization, filtering, interaction, charts, map rendering. No core AI/scoring/database logic.

## Dependency rule
Consumers depend on stable contracts, not implementation details.
