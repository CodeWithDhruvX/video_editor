import { useState, useEffect, useRef, useCallback } from 'react';

const WS_BASE = 'ws://localhost:8000';

// Types that change job status
const TERMINAL_TYPES = new Set(['COMPLETE', 'ERROR', 'FAILED', 'STOPPED']);

/**
 * useWebSocket — connects to a backend WebSocket and streams progress messages.
 * @param {string|null} jobId - job ID to connect to (editor or uploader)
 * @param {string} prefix - route prefix: 'editor' or 'uploader'
 */
export function useWebSocket(jobId, prefix = 'editor') {
  const [logs, setLogs] = useState([]);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('idle'); // idle | running | complete | failed | stopped
  const [isConnected, setIsConnected] = useState(false);

  const wsRef = useRef(null);

  const connect = useCallback((id) => {
    if (!id) return;
    const url = `${WS_BASE}/${prefix}/ws/${id}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setStatus('running');
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        const { type, message, progress: pct } = msg;

        // Always append to log (even FFMPEG/WARN/PROGRESS)
        setLogs((prev) => [...prev, { type: type || 'LOG', message, ts: Date.now() }]);

        // Update progress bar
        if (pct != null) setProgress(pct);

        // Update status for terminal events only
        if (type === 'COMPLETE') setStatus('complete');
        else if (type === 'ERROR' || type === 'FAILED') setStatus('failed');
        else if (type === 'STOPPED') setStatus('stopped');
      } catch (err) {
        console.warn('WS parse error:', err);
      }
    };

    ws.onerror = () => {
      setIsConnected(false);
      setStatus('failed');
    };

    ws.onclose = () => {
      setIsConnected(false);
    };
  }, [prefix]);

  useEffect(() => {
    if (jobId) {
      setLogs([]);
      setProgress(0);
      setStatus('idle');
      connect(jobId);
    }
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, [jobId, connect]);

  const reset = useCallback(() => {
    if (wsRef.current) wsRef.current.close();
    setLogs([]);
    setProgress(0);
    setStatus('idle');
    setIsConnected(false);
  }, []);

  return { logs, progress, status, isConnected, reset };
}

