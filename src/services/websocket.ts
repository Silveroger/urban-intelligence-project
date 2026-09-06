/**
 * WebSocket Live Streaming Service for SIH 26124 Urban Intelligence GIS
 * Connects to FastAPI endpoint at /ws/live.
 * Supports:
 * - BUS_TELEMETRY
 * - NEW_EVENT
 * - NEW_INCIDENT
 * - SEGMENT_UPDATE
 * - PING/PONG Keepalive
 * - Exponential backoff auto-reconnection
 */

import type { Bus } from '../types/buses';
import type { Event } from '../types/events';
import type { Incident } from '../types/incidents';

export type WebSocketStatus = 'connecting' | 'connected' | 'disconnected';

export interface LiveBusTelemetryFrame {
  type: 'BUS_TELEMETRY';
  payload: Bus;
}

export interface LiveEventFrame {
  type: 'NEW_EVENT';
  payload: Event;
}

export interface LiveIncidentFrame {
  type: 'NEW_INCIDENT';
  payload: Incident;
}

export interface SegmentUpdatePayload {
  segment_id: string;
  condition_score?: number;
  pothole_count: number;
  waterlogging_count: number;
  observation_count: number;
  last_updated?: string;
}

export interface LiveSegmentUpdateFrame {
  type: 'SEGMENT_UPDATE';
  payload: SegmentUpdatePayload;
}

export interface PongFrame {
  type: 'PONG';
}

export type LiveFrame =
  | LiveBusTelemetryFrame
  | LiveEventFrame
  | LiveIncidentFrame
  | LiveSegmentUpdateFrame
  | PongFrame;

export interface LiveStreamHandlers {
  onBusTelemetry?: (bus: Bus) => void;
  onNewEvent?: (event: Event) => void;
  onNewIncident?: (incident: Incident) => void;
  onSegmentUpdate?: (update: SegmentUpdatePayload) => void;
  onStatusChange?: (status: WebSocketStatus) => void;
}

const WS_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000')
  .replace(/^http/, 'ws');
const WS_URL = `${WS_BASE}/ws/live`;

let socket: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let pingInterval: ReturnType<typeof setInterval> | null = null;
let reconnectDelay = 1000;
let shouldReconnect = true;
let currentHandlers: LiveStreamHandlers = {};

export function connectLiveStream(handlers: LiveStreamHandlers): void {
  currentHandlers = handlers;
  shouldReconnect = true;

  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return;
  }

  initiateConnection();
}

function initiateConnection(): void {
  try {
    currentHandlers.onStatusChange?.('connecting');
    socket = new WebSocket(WS_URL);

    socket.onopen = () => {
      reconnectDelay = 1000;
      currentHandlers.onStatusChange?.('connected');

      // Heartbeat ping every 25s
      if (pingInterval) clearInterval(pingInterval);
      pingInterval = setInterval(() => {
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send('ping');
        }
      }, 25000);
    };

    socket.onmessage = (event: MessageEvent) => {
      try {
        const frame: LiveFrame = JSON.parse(event.data);

        switch (frame.type) {
          case 'BUS_TELEMETRY':
            currentHandlers.onBusTelemetry?.(frame.payload);
            break;
          case 'NEW_EVENT':
            currentHandlers.onNewEvent?.(frame.payload);
            break;
          case 'NEW_INCIDENT':
            currentHandlers.onNewIncident?.(frame.payload);
            break;
          case 'SEGMENT_UPDATE':
            currentHandlers.onSegmentUpdate?.(frame.payload);
            break;
          case 'PONG':
            // Keepalive response acknowledged
            break;
        }
      } catch {
        // Ignore unparseable or malformed frames
      }
    };

    socket.onclose = () => {
      currentHandlers.onStatusChange?.('disconnected');
      cleanupSocket();

      if (shouldReconnect) {
        scheduleReconnect();
      }
    };

    socket.onerror = () => {
      currentHandlers.onStatusChange?.('disconnected');
    };
  } catch {
    currentHandlers.onStatusChange?.('disconnected');
    scheduleReconnect();
  }
}

function scheduleReconnect(): void {
  if (reconnectTimer) clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(() => {
    reconnectDelay = Math.min(reconnectDelay * 1.5, 10000);
    initiateConnection();
  }, reconnectDelay);
}

function cleanupSocket(): void {
  if (pingInterval) {
    clearInterval(pingInterval);
    pingInterval = null;
  }
  socket = null;
}

export function disconnectLiveStream(): void {
  shouldReconnect = false;
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  cleanupSocket();
  if (socket) {
    socket.close();
    socket = null;
  }
  currentHandlers.onStatusChange?.('disconnected');
}
