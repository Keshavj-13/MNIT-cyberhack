# Telemetry Implementation Audit Report
**Agent:** TELEMETRY_AGENT
**Status:** VERIFIED - LIVE COLLECTION ACTIVE

## 1. Frontend Implementation: `ui/src/hooks/useTelemetry.ts`

The frontend utilizes a custom React hook to attach global event listeners. It captures keystroke dynamics, mouse movements, and session lifecycle events.

### Full Source Code
```typescript
import { useEffect, useRef } from 'react';
import axios from 'axios';
import { getSessionId, API_BASE } from '../bank/api';

/**
 * Telemetry Event Schema
 * 
 * {
 *   type: 'keystroke' | 'mouse' | 'session',
 *   timestamp: number, (ms since epoch)
 *   data: {
 *     // if type === 'keystroke'
 *     event: 'dwell' | 'flight',
 *     key: string,
 *     code: string,
 *     dwellTime?: number, (ms)
 *     flightTime?: number, (ms)
 * 
 *     // if type === 'mouse'
 *     event: 'move' | 'click',
 *     x: number,
 *     y: number,
 *     velocity?: number, (pixels/ms)
 * 
 *     // if type === 'session'
 *     event: 'page_load' | 'idle' | 'visibility' | 'tab_change',
 *     url?: string,
 *     state?: string,
 *     tab?: string,
 *     duration?: number (ms)
 *   }
 * }
 */

interface TelemetryEvent {
  type: 'keystroke' | 'mouse' | 'session';
  timestamp: number;
  data: any;
}

export const useTelemetry = (activeTab?: string) => {
  const buffer = useRef<TelemetryEvent[]>([]);
  const lastKeyTimestamp = useRef<number | null>(null);
  const keysDown = useRef<Map<string, number>>(new Map());
  const lastMouseMove = useRef<{ x: number, y: number, t: number } | null>(null);
  const sessionId = getSessionId();

  // Helper to push to buffer
  const pushEvent = (type: TelemetryEvent['type'], data: any) => {
    buffer.current.push({
      type,
      timestamp: Date.now(),
      data,
    });
  };

  // Track tab changes
  useEffect(() => {
    if (activeTab) {
      pushEvent('session', { event: 'tab_change', tab: activeTab });
    }
  }, [activeTab]);

  useEffect(() => {
    // Keystroke handlers
    const handleKeyDown = (e: KeyboardEvent) => {
      if (keysDown.current.has(e.code)) return; 
      const now = Date.now();
      keysDown.current.set(e.code, now);

      if (lastKeyTimestamp.current) {
        const flightTime = now - lastKeyTimestamp.current;
        pushEvent('keystroke', { event: 'flight', flightTime, key: e.key, code: e.code });
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      const now = Date.now();
      lastKeyTimestamp.current = now;
      const dwellStart = keysDown.current.get(e.code);
      if (dwellStart) {
        const dwellTime = now - dwellStart;
        pushEvent('keystroke', { event: 'dwell', dwellTime, key: e.key, code: e.code });
        keysDown.current.delete(e.code);
      }
    };

    // Mouse handlers
    const handleMouseMove = (e: MouseEvent) => {
      const now = Date.now();
      const { clientX: x, clientY: y } = e;

      if (lastMouseMove.current) {
        const dx = x - lastMouseMove.current.x;
        const dy = y - lastMouseMove.current.y;
        const dt = now - lastMouseMove.current.t;
        
        if (dt > 150) { // Sample mouse every 150ms
          const velocity = Math.sqrt(dx * dx + dy * dy) / dt;
          pushEvent('mouse', { event: 'move', x, y, velocity });
          lastMouseMove.current = { x, y, t: now };
        }
      } else {
        lastMouseMove.current = { x, y, t: now };
      }
    };

    const handleClick = (e: MouseEvent) => {
      pushEvent('mouse', { event: 'click', x: e.clientX, y: e.clientY });
    };

    // Session/Idle handlers
    let idleTimeout: any;
    const resetIdle = () => {
      clearTimeout(idleTimeout);
      idleTimeout = setTimeout(() => {
        pushEvent('session', { event: 'idle', duration: 60000 });
      }, 60000); // 1 minute idle
    };

    const handleVisibilityChange = () => {
      pushEvent('session', { event: 'visibility', state: document.visibilityState });
    };

    pushEvent('session', { event: 'page_load', url: window.location.href });

    // Global listeners
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('click', handleClick);
    window.addEventListener('visibilitychange', handleVisibilityChange);
    
    // Reset idle on activity
    window.addEventListener('keydown', resetIdle);
    window.addEventListener('mousemove', resetIdle);
    window.addEventListener('click', resetIdle);

    resetIdle();

    // Buffering & Flush logic
    const flushBuffer = async () => {
      if (buffer.current.length === 0) return;

      const events = [...buffer.current];
      buffer.current = [];

      try {
        await axios.post(`${API_BASE}/telemetry`, {
          session_id: sessionId,
          events,
        });
        console.log(`[Telemetry] Flushed ${events.length} events`);
      } catch (err) {
        console.warn('[Telemetry] Flush failed', err);
        // Put back in buffer? Not for now to prevent explosion
      }
    };

    const interval = setInterval(flushBuffer, 8000); // 8 seconds batch

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('click', handleClick);
      window.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('keydown', resetIdle);
      window.removeEventListener('mousemove', resetIdle);
      window.removeEventListener('click', resetIdle);
      clearTimeout(idleTimeout);
      clearInterval(interval);
      flushBuffer();
    };
  }, [sessionId]);
};
```

## 2. Buffering Logic Explanation
The telemetry system uses an **interval-based buffering strategy** to optimize network performance and reduce API overhead.
- **In-Memory Buffer:** Events are initially pushed to a `useRef` array (`buffer.current`), which avoids React re-renders while accumulating data.
- **Sampling:** Mouse movements are sampled every **150ms** to prevent flooding the buffer with high-frequency data.
- **Batching:** Every **8 seconds**, the `flushBuffer` function is executed via `setInterval`.
- **Atomic Flush:** When flushing, the buffer is copied and cleared immediately to prevent race conditions. The batch is then sent as a single `POST` request to the backend.

## 3. Example JSON Payload: Keystroke Event
Below is a typical payload for a 'dwell' event (duration a key was held down):

```json
{
  "type": "keystroke",
  "timestamp": 1718112345678,
  "data": {
    "event": "dwell",
    "dwellTime": 85,
    "key": "a",
    "code": "KeyA"
  }
}
```

## 4. Backend Route Verification: `src/api/server.py`
The backend exposes a dedicated endpoint to ingest these telemetry batches.

### Verified Route: `POST /telemetry`
```python
@app.post("/telemetry")
def telemetry(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    session_id = payload.get("session_id", "UNKNOWN")
    events = payload.get("events", [])
    
    for event in events:
        db_telemetry = TelemetryData(
            session_id=session_id,
            type=event.get("type"),
            data=event.get("data")
        )
        db.add(db_telemetry)
    
    db.commit()
    print(f"[TELEMETRY] Stored {len(events)} events for session {session_id}")
    return {"status": "success", "count": len(events)}
```
The endpoint successfully maps incoming events to the `TelemetryData` database model, ensuring persistence for downstream risk analysis.

---
**Audit Complete.**
Telemetric signals are being successfully captured and streamed to the risk engine.
