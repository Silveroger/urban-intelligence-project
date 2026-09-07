export interface Bus {
  bus_id: string;
  vehicle_number?: string;
  latitude: number;
  longitude: number;
  speed_kmh?: number;
  heading_deg?: number;
  timestamp: string;
  status?: string;
}

