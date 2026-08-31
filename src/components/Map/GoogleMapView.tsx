import { APIProvider, Map, AdvancedMarker, Pin, Polyline } from '@vis.gl/react-google-maps';
import { MAP_CONFIG } from '../../config/maps';
import type { RoadSegment } from '../../types/roadSegments';
import type { Event } from '../../types/events';
import type { Incident } from '../../types/incidents';
import type { Bus } from '../../types/buses';
import type { FilterState } from '../../types/filters';
import { geoJsonToGooglePath } from '../../utils/coordinates';
import { getRoadColor } from '../../utils/roadColor';
import { getEventTypeColor } from '../../utils/formatters';
import { DeckHeatmapOverlay } from './DeckHeatmapOverlay';

interface GoogleMapViewProps {
  roadSegments: RoadSegment[];
  events: Event[];
  incidents: Incident[];
  buses: Bus[];
  filters: FilterState;
  selectedRoad: RoadSegment | null;
  selectedEvent: Event | null;
  selectedIncident: Incident | null;
  onSelectRoad: (road: RoadSegment) => void;
  onSelectEvent: (event: Event) => void;
  onSelectIncident: (incident: Incident) => void;
}

export function GoogleMapView({
  roadSegments,
  events,
  incidents,
  buses,
  filters,
  selectedRoad,
  selectedEvent,
  selectedIncident,
  onSelectRoad,
  onSelectEvent,
  onSelectIncident,
}: GoogleMapViewProps) {
  if (!MAP_CONFIG.apiKey) {
    return (
      <div style={{ padding: '24px', color: '#ef4444', textAlign: 'center' }}>
        <strong>Configuration Error:</strong> Google Maps API key is missing.
      </div>
    );
  }

  return (
    <APIProvider apiKey={MAP_CONFIG.apiKey}>
      <div style={{ width: '100%', height: '100%', position: 'relative' }}>
        <Map
          mapId={MAP_CONFIG.mapId}
          defaultCenter={MAP_CONFIG.defaultCenter}
          defaultZoom={MAP_CONFIG.defaultZoom}
          gestureHandling="greedy"
          disableDefaultUI={false}
          style={{ width: '100%', height: '100%' }}
        >
          {/* Road Segment Polylines */}
          {filters.layers.roads &&
            roadSegments.map((segment) => {
              const isSelected = selectedRoad?.segment_id === segment.segment_id;
              return (
                <Polyline
                  key={segment.segment_id}
                  path={geoJsonToGooglePath(segment.geometry)}
                  strokeColor={isSelected ? '#38bdf8' : getRoadColor(segment.condition_score)}
                  strokeOpacity={0.9}
                  strokeWeight={isSelected ? 8 : 6}
                  clickable={true}
                  onClick={() => onSelectRoad(segment)}
                />
              );
            })}

          {/* Event Markers */}
          {filters.layers.events &&
            events.map((event) => {
              const isSelected = selectedEvent?.event_id === event.event_id;
              const color = getEventTypeColor(event.event_type);
              return (
                <AdvancedMarker
                  key={event.event_id}
                  position={{ lat: event.latitude, lng: event.longitude }}
                  onClick={() => onSelectEvent(event)}
                  title={event.class_name || event.event_type}
                >
                  <Pin
                    background={isSelected ? '#38bdf8' : color}
                    glyphColor="#ffffff"
                    borderColor={isSelected ? '#0284c7' : color}
                    scale={isSelected ? 1.2 : 1.0}
                  />
                </AdvancedMarker>
              );
            })}

          {/* Incident Markers */}
          {filters.layers.incidents &&
            incidents.map((inc) => {
              const isSelected = selectedIncident?.incident_id === inc.incident_id;
              return (
                <AdvancedMarker
                  key={inc.incident_id}
                  position={{ lat: inc.latitude, lng: inc.longitude }}
                  onClick={() => onSelectIncident(inc)}
                  title={inc.incident_type}
                >
                  <Pin
                    background={isSelected ? '#38bdf8' : '#f43f5e'}
                    glyphColor="#ffffff"
                    borderColor={isSelected ? '#0284c7' : '#be123c'}
                    scale={isSelected ? 1.2 : 1.0}
                  />
                </AdvancedMarker>
              );
            })}

          {/* Bus Markers */}
          {filters.layers.buses &&
            buses.map((bus) => (
              <AdvancedMarker
                key={bus.bus_id}
                position={{ lat: bus.latitude, lng: bus.longitude }}
                title={bus.bus_id}
              >
                <div
                  className="bus-marker"
                  style={{
                    transform: bus.heading_deg != null ? `rotate(${bus.heading_deg}deg)` : undefined,
                  }}
                >
                  🚌
                </div>
              </AdvancedMarker>
            ))}

          {/* deck.gl Heatmap Overlay */}
          <DeckHeatmapOverlay events={events} visible={filters.layers.heatmap} />
        </Map>
      </div>
    </APIProvider>
  );
}
