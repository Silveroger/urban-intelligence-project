# AI Output Contract

AI services must produce validated structured observations.

Minimum event concepts:
- event_id
- bus_id
- timestamp
- latitude
- longitude
- road_segment_id when already known
- event_type
- class_name when applicable
- confidence
- severity when applicable
- track_id when applicable
- plate_text / plate_confidence when applicable
- evidence_uri when available

The backend is responsible for validating AI output before persistence.
