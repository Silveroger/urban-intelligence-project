# Frontend Architecture

## Data flow

Mock provider OR REST API
→ `src/services/api.ts`
→ dashboard state
→ presentation components
→ Google Maps / deck.gl / charts / inspectors

## Rules
- UI components do not import mock data directly.
- Map components receive data via props/state.
- Backend truth is rendered, not re-derived.
- Keep road, event, bus, and UI-selection state separate.
- Preserve centralized configuration and coordinate utilities.

## Current frontend scope
Map, road colors, markers, heatmap, filters, road detail, historical visualization, API-ready data layer.
