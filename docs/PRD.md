# Product Requirements Document (PRD)

## 1. Problem Statement
**SIH 26124 — AI-Powered Mobile Urban Intelligence Platform Using Public Transport Fleet.**

Traditional municipal road and traffic monitoring relies on manual surveys, citizen complaints, or static, expensive sensor infrastructure. This results in stale data, delayed defect remediation, and reactive urban governance.

Public transport vehicles (city buses and test fleet vehicles) traverse urban road networks continuously. By transforming these vehicles into mobile sensing nodes equipped with cameras and GPS, municipalities can continuously capture road surface condition, traffic flow, and urban incidents at low incremental cost.

## 2. Core Value Proposition & Differentiators
- **Repeated Geospatial Observations:** Unlike single-image detection tools or generic chat-based LLMs, this platform aggregates repeated observations over space and time to produce high-confidence, persistent road state.
- **Decision-Support for Authorities:** Provides actionable GIS intelligence to municipal administrators, public works departments, and traffic management centers.

## 3. Target Users & Personas
1. **Municipal Road & Public Works Engineers:** Prioritize road resurfacing, track defect progression over time, and export maintenance work orders.
2. **City Traffic Operations Officers:** Monitor live fleet movement, identify localized congestion choke points, and inspect incident alerts.
3. **Urban Governance Executives:** Review high-level city health KPIs, fleet sensing coverage, and road-quality trends across sectors.

## 4. Product Goals
- Provide real-time and historical visibility into road health across urban sectors.
- Automatically classify road defects (potholes, cracks, surface degradation) and waterlogging events.
- Aggregate repeated observations from multiple bus passes into a canonical road segment condition score.
- Visualize dense traffic flow and fleet positions on an interactive, hardware-accelerated GIS map.
- Enable drill-down inspection of individual road segments, events, and evidence media.
- Support live edge camera stream ingestion, video uploads, and hardware telemetry processing.

## 5. Scope & Feature Priorities

### P0 — Core MVP (Current Baseline)
- **Road-Health Polylines:** Vector-rendered road segments colored by aggregate condition score (Green/Yellow/Orange/Red).
- **Defect & Event Markers:** Geospatial markers for potholes, road defects, waterlogging, and traffic incidents.
- **Bus & Fleet Telemetry:** Real-time bus positions with heading indicators.
- **Segment Inspector:** Detailed slide-over panel showing segment condition score, confidence, defect counts, observation count, and historical pass trend chart.
- **Event Inspector:** Panel showing event type, severity, confidence, timestamp, road segment association, and evidence media link.
- **Incident Inspector:** Panel showing incident classification, vehicle tracking IDs, plate text confidence, and incident timestamps.
- **KPI Summary Cards:** High-level dashboard metrics (Total Road Segments, Critical Issues, Monitored Buses, Active Incidents).
- **Layer & Severity Filters:** Multi-criteria filtering by event type, road condition tier, severity threshold, and bus fleet.
- **Edge AI Video Ingestion Hub:** Ingestion modal supporting hardware video uploads, sample test runs, and selective detector toggles.
- **GPS Telemetry Pipeline:** Streaming drawer for validating and transmitting live GPS batches directly into Supabase.

### P1 — Advanced Analytics & Operational Tools
- **Dense Heatmap Overlay:** GPU-accelerated traffic density and defect concentration heatmaps powered by deck.gl.
- **Live Desktop Scanner Window:** Real-time visual HUD window (`run_live_scanner.py`) displaying bounding boxes, telemetry, and detection feeds.
- **Maintenance Priority Ranking:** Algorithmic work-order prioritization based on road condition degradation and traffic volume.
- **Work-Order Export:** Export actionable defect reports (CSV/GeoJSON/PDF) for municipal field crews.
- **Fleet Analytics:** Coverage metrics showing which city routes have been surveyed within the last 24/48 hours.

### P2 — Future Extensions
- **Missing Infrastructure Inference:** Automated detection of missing zebra crossings, faded lane markings, and obstructed traffic signage.
- **Route Delay & Origin-Destination Analysis:** Correlating road defects with bus schedule deviations and transit corridor delays.

## 6. Functional Requirements
- **FR-1:** The dashboard must render road health status using canonical condition scores ($0-100$) delivered by the backend.
- **FR-2:** The frontend must support both mock data mode (`VITE_USE_MOCK=true`) for standalone operation and live REST/WebSocket ingestion (`VITE_USE_MOCK=false`).
- **FR-3:** All geospatial coordinates must conform strictly to GeoJSON format (`[longitude, latitude]`) at data boundaries and transform to Google Maps (`{lat, lng}`) only at rendering boundaries.
- **FR-4:** Optical Character Recognition (OCR) plate detections must always display confidence scores alongside detected text; plate text must never be presented as absolute ground truth without confidence indicators.
- **FR-5:** Inspecting any road segment, event, or incident must highlight the respective element on the map and open its dedicated inspector view.
- **FR-6:** Video processing uploads must support selective detector configuration and report live progress back to the operator.

## 7. Non-Functional Requirements
- **Performance:** Initial map view render under $1.5\text{s}$; smooth 60 FPS panning and zooming with $\ge 500$ road segments and $\ge 1,000$ active markers.
- **Reliability:** The UI must maintain full usability via REST caching if the real-time WebSocket connection drops.
- **Security:** API keys and environment secrets must never be exposed to public version control; browser keys must enforce strict HTTP referrer restrictions.
- **Responsiveness:** Fluid command-and-control layout optimized for desktop and operations-center displays ($\ge 1280\text{px}$ width).

## 8. Telemetry Constraints
- **Vehicle Speed:** Vehicle speed is **NOT** required for the prototype telemetry. Bus telemetry requires only `bus_id`, `timestamp`, `latitude`, `longitude`, and optional `heading_deg`. Functionality must never fail if speed is omitted.

## 9. Explicit Non-Goals ("What NOT to do")
- **No Generic Chatbots:** Do not implement conversational AI or chatbot interfaces.
- **No Client-Side Model Training:** Do not train machine learning models in the frontend application.
- **No Client-Side AI Inference:** Computer vision inference is executed on edge/backend services; the frontend only consumes structured metadata.
- **No Client-Side Road Truth Calculation:** The backend owns spatial map-matching and multi-observation score aggregation; the frontend strictly visualizes backend scores.
- **No Continuous Raw Video Streaming:** The pipeline operates on structured event metadata and sampled evidence keyframes, not continuous raw video streams.

## 10. Acceptance Criteria & Demo Target
**End-to-End Demonstration Scenario:**
1. A fleet vehicle equipped with camera and GPS traverses a test route in Chandigarh.
2. Edge/AI pipeline detects a road defect (pothole), captures a keyframe, and transmits structured event metadata.
3. Backend ingests the event, matches it to the road segment, recalculates segment condition score and confidence, and emits a live update.
4. The dashboard reflects the updated road health color on the map, updates KPI counters, and allows the operator to click the segment to view defect history and inspect the evidence frame.
