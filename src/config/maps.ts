export const MAP_CONFIG = {
  apiKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '',
  mapId: import.meta.env.VITE_GOOGLE_MAPS_MAP_ID || '',
  defaultCenter: { lat: 30.7333, lng: 76.7794 }, // Chandigarh
  defaultZoom: 14,
};
