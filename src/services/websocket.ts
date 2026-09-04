/**
 * SIH 26124 — WebSocket Live Stream Client
 * Manages persistent /ws/live connection and broadcasts incremental updates.
 * Conforms to docs/API_CONTRACT.md (§3).
 */

const WS_URL = `${(import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/^http/, 'ws')}/ws/live`;

let socket: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

export interface WSMessage<T = unknown> {
  type: 'BUS_TELEMETRY' | 'NEW_EVENT' | 'NEW_INCIDENT' | 'SEGMENT_UPDATE';
  payload: T;
}

export function connectWebSocket(onMessage: (data: WSMessage) => void): void {
  if (socket && socket.readyState === WebSocket.OPEN) return;

  try {
    socket = new WebSocket(WS_URL);

    socket.onopen = () => {
      console.log('[WebSocket] Connected to /ws/live');
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
    };

    socket.onmessage = (ev) => {
      try {
        const parsed = JSON.parse(ev.data) as WSMessage;
        onMessage(parsed);
      } catch {
        /* ignore malformed frames */
      }
    };

    socket.onclose = () => {
      socket = null;
      // Attempt reconnect every 4 seconds
      if (!reconnectTimer) {
        reconnectTimer = setTimeout(() => {
          reconnectTimer = null;
          connectWebSocket(onMessage);
        }, 4000);
      }
    };

    socket.onerror = () => {
      socket?.close();
    };
  } catch {
    /* Silent failure in offline/mock mode */
  }
}

export function disconnectWebSocket(): void {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  socket?.close();
  socket = null;
}
