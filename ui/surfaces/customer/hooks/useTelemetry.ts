import { useEffect, useRef } from 'react';
import { sendTelemetry } from '../api';

interface TelemetryEvent {
  type: 'keystroke' | 'mouse' | 'session';
  timestamp: number;
  data: any;
}

export const useTelemetry = (
  activeTab: string,
  sessionId: string,
  keyVersion: number,
  aesKey: string
) => {
  const buffer = useRef<TelemetryEvent[]>([]);
  const lastKeyTimestamp = useRef<number | null>(null);
  const keysDown = useRef<Map<string, number>>(new Map());
  const lastMouseMove = useRef<{ x: number; y: number; t: number } | null>(null);

  // Latest crypto state reference to avoid stale closures in listeners
  const cryptoRef = useRef({ sessionId, keyVersion, aesKey });
  useEffect(() => {
    cryptoRef.current = { sessionId, keyVersion, aesKey };
  }, [sessionId, keyVersion, aesKey]);

  const pushEvent = (type: TelemetryEvent['type'], data: any) => {
    buffer.current.push({
      type,
      timestamp: Date.now(),
      data,
    });
  };

  // Track tab changes
  useEffect(() => {
    if (activeTab && cryptoRef.current.sessionId) {
      pushEvent('session', { event: 'tab_change', tab: activeTab });
    }
  }, [activeTab]);

  useEffect(() => {
    if (!sessionId || !aesKey) return;

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

    const flushBuffer = async () => {
      if (buffer.current.length === 0) return;
      const { sessionId: activeSid, keyVersion: activeKv, aesKey: activeKey } = cryptoRef.current;
      if (!activeSid || !activeKey) return;

      const events = [...buffer.current];
      buffer.current = [];

      try {
        await sendTelemetry(activeSid, activeKv, activeKey, events);
      } catch (err) {
        console.warn('[Telemetry] Flush failed', err);
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
  }, [sessionId, aesKey]);
};
