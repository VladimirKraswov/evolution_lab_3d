import { useCallback, useEffect, useRef, useState } from 'preact/hooks';

export function useSocket() {
  const [connected, setConnected] = useState(false);
  const [data, setData] = useState(null);
  const [log, setLog] = useState('init');

  const wsRef = useRef(null);
  const latestPayloadRef = useRef(null);
  const rafRef = useRef(null);

  const send = useCallback((msg) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
    }
  }, []);

  useEffect(() => {
    let stopped = false;
    let retry = 350;

    const flush = () => {
      if (latestPayloadRef.current) {
        setData(latestPayloadRef.current);
        latestPayloadRef.current = null;
      }
      rafRef.current = null;
    };

    const scheduleFlush = () => {
      if (!rafRef.current) {
        rafRef.current = requestAnimationFrame(flush);
      }
    };

    const connect = () => {
      const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
      const ws = new WebSocket(`${proto}//${location.host}/ws`);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setLog('websocket connected');
        retry = 350;
      };

      const environmentStatic = { terrain: null, algae: null };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);

          if (payload.type === 'init' || payload.type === 'snapshot') {
            if (payload.environment) {
              if (payload.environment.terrain) {
                environmentStatic.terrain = payload.environment.terrain;
              } else {
                payload.environment.terrain = environmentStatic.terrain;
              }
              if (payload.environment.algae) {
                environmentStatic.algae = payload.environment.algae;
              } else {
                payload.environment.algae = environmentStatic.algae;
              }
            }
            latestPayloadRef.current = payload;
            scheduleFlush();
          } else if (payload.status) {
            setLog(payload.message || payload.status);
          }
        } catch (err) {
          setLog(`bad json: ${err.message}`);
        }
      };

      ws.onclose = () => {
        setConnected(false);
        setLog('websocket reconnecting...');
        if (!stopped) setTimeout(connect, retry);
        retry = Math.min(4000, retry * 1.5);
      };

      ws.onerror = () => {
        setConnected(false);
        setLog('websocket error');
        ws.close();
      };
    };

    connect();

    return () => {
      stopped = true;
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      wsRef.current?.close();
    };
  }, []);

  return { connected, data, log, send };
}