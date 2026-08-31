import { useEffect, useMemo } from 'react';
import { useMap } from '@vis.gl/react-google-maps';
import { GoogleMapsOverlay } from '@deck.gl/google-maps';
import { HeatmapLayer } from '@deck.gl/aggregation-layers';
import type { Event } from '../../types/events';

/** Heatmap configuration — single source of truth for visual tuning */
const HEATMAP_CONFIG = {
  radiusPixels: 40,
  intensity: 1.2,
  threshold: 0.05,
  opacity: 0.55,
  colorRange: [
    [65, 182, 196, 255],   // cool cyan
    [127, 205, 187, 255],  // teal
    [199, 233, 180, 255],  // light green
    [255, 255, 178, 255],  // yellow
    [253, 174, 97, 255],   // orange
    [215, 48, 39, 255],    // red-hot
  ] as [number, number, number, number][],
} as const;

interface DeckHeatmapOverlayProps {
  events: Event[];
  visible: boolean;
}

/**
 * Isolated deck.gl heatmap overlay per AGENT_CONTEXT §12.
 * Uses GoogleMapsOverlay + useMap to attach/detach once.
 * Must be rendered inside <Map> to access the map instance via context.
 */
export function DeckHeatmapOverlay({ events, visible }: DeckHeatmapOverlayProps) {
  const map = useMap();

  const overlay = useMemo(() => new GoogleMapsOverlay({ interleaved: true }), []);

  // Attach/detach overlay to map instance
  useEffect(() => {
    if (map) overlay.setMap(map);
    return () => { overlay.setMap(null); };
  }, [map, overlay]);

  // Update layers when events or visibility changes
  useEffect(() => {
    if (!visible || events.length === 0) {
      overlay.setProps({ layers: [] });
      return;
    }

    const layer = new HeatmapLayer({
      id: 'event-heatmap',
      data: events,
      getPosition: (d: Event) => [d.longitude, d.latitude],
      getWeight: (d: Event) => (d.severity ?? 1) * d.confidence,
      radiusPixels: HEATMAP_CONFIG.radiusPixels,
      intensity: HEATMAP_CONFIG.intensity,
      threshold: HEATMAP_CONFIG.threshold,
      opacity: HEATMAP_CONFIG.opacity,
      colorRange: HEATMAP_CONFIG.colorRange,
    });

    overlay.setProps({ layers: [layer] });
  }, [events, visible, overlay]);

  return null;
}
