---
name: api-contract
description: Designs and reviews REST/WebSocket contracts so frontend, backend, and AI outputs remain compatible.
---
# API Contract
Read `docs/API_CONTRACT.md`.
Use stable IDs, ISO-8601 timestamps, explicit nullability, documented errors, and versioned endpoints.
For every breaking change, update consumers and contract docs in the same change.
Prefer machine-readable schemas where practical.
