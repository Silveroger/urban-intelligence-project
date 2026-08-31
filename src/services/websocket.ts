/**
 * WebSocket service stub — §7 project structure requirement.
 * Will be implemented in step 17 (WebSocket live updates).
 * Initial state loads through REST (§13); WebSocket is for incremental live updates.
 */

const WS_URL = `${(import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/^http/, 'ws')}/ws/live`;

let socket: WebSocket | null = null;

export function connectWebSocket(onMessage: (data: unknown) => void): void {
  if (socket) return;
  socket = new WebSocket(WS_URL);
  socket.onmessage = (ev) => {
    try {
      onMessage(JSON.parse(ev.data));
    } catch { /* ignore malformed frames */ }
  };
  socket.onclose = () => { socket = null; };
}

export function disconnectWebSocket(): void {
  socket?.close();
  socket = null;
}
