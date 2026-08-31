/**
 * Converts GeoJSON [lng, lat] coordinates to Google Maps {lat, lng} paths.
 */
export function geoJsonToGooglePath(
  coords: [number, number][]
): { lat: number; lng: number }[] {
  return coords.map(([lng, lat]) => ({ lat, lng }));
}
