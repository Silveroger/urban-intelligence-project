# API Contract

## Principles
- Version APIs under `/api/v1`.
- JSON over REST.
- ISO-8601 timestamps with timezone.
- Stable string IDs.
- Document nullability.
- GeoJSON geometry uses `[lng, lat]`.
- Frontend converts coordinates only at rendering boundaries.
- Errors have stable machine-readable codes.

## Current frontend expectations

GET `/api/v1/segments/geojson`
GET `/api/v1/segments/{segment_id}`
GET `/api/v1/segments/{segment_id}/history`
GET `/api/v1/events`
GET `/api/v1/events/{event_id}`
GET `/api/v1/incidents`
GET `/api/v1/incidents/{incident_id}`
GET `/api/v1/buses`

Future live channel:
WS `/ws/live`

## Contract change rule
Any breaking change requires this file and affected consumers to be updated in the same change.
