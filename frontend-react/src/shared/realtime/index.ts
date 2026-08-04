/**
 * Real-Time Messaging & Notification Infrastructure Stub
 * Ready for future WebSocket or Server-Sent Events (SSE) connections.
 */
export type RealtimeEventCallback = (payload: unknown) => void;

class RealtimeManager {
  private listeners: Map<string, Set<RealtimeEventCallback>> = new Map();
  private isConnected = false;

  public connect(): void {
    if (this.isConnected) return;
    this.isConnected = true;
    console.log('[Realtime] Stub connection established.');
  }

  public disconnect(): void {
    this.isConnected = false;
    console.log('[Realtime] Stub disconnected.');
  }

  public subscribe(event: string, callback: RealtimeEventCallback): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);

    return () => {
      const callbacks = this.listeners.get(event);
      if (callbacks) {
        callbacks.delete(callback);
      }
    };
  }

  public emit(event: string, payload: unknown): void {
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      callbacks.forEach((cb) => cb(payload));
    }
  }
}

export const realtime = new RealtimeManager();
