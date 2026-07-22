import { useState, useEffect, useRef, useCallback } from 'react';
import { editorApi, uploaderApi } from '../services/api';

const WS_BASE = 'ws://localhost:8000';

/**
 * useWebSocket — connects to a backend WebSocket and streams progress messages
 * with built-in HTTP polling fallback for maximum reliability.
 * @param {string|null} jobId - job ID to connect to
 * @param {string} prefix - route prefix: 'editor' or 'uploader'
 */
export function useWebSocket(jobId, prefix = 'editor') {
  const [logs, setLogs] = useState([]);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('idle'); // idle | running | complete | failed | stopped
  const [isConnected, setIsConnected] = useState(false);

  const wsRef = useRef(null);
  const pollIntervalRef = useRef(null);

  const addLog = useCallback((type, message) => {
    setLogs((prev) => {
      // Avoid duplicate log messages if received via both WS and HTTP poll
      const exists = prev.some((l) => l.type === type && l.message === message);
      if (exists) return prev;
      return [...prev, { type: type || 'LOG', message, ts: Date.now() }];
    });
  }, []);

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

        addLog(type || 'LOG', message);

        if (pct != null) setProgress(pct);

        if (type === 'COMPLETE') setStatus('complete');
        else if (type === 'ERROR' || type === 'FAILED') setStatus('failed');
        else if (type === 'STOPPED') setStatus('stopped');
      } catch (err) {
        console.warn('WS parse error:', err);
      }
    };

    ws.onerror = () => {
      setIsConnected(false);
    };

    ws.onclose = () => {
      setIsConnected(false);
    };
  }, [prefix, addLog]);

  // HTTP Polling fallback when running
  useEffect(() => {
    if (!jobId || status === 'complete' || status === 'failed' || status === 'stopped') {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      return;
    }

    const apiService = prefix === 'uploader' ? uploaderApi : editorApi;

    pollIntervalRef.current = setInterval(async () => {
      try {
        const res = await apiService.getStatus(jobId);
        const data = res.data;

        if (data.status) setStatus(data.status);
        if (data.progress != null) setProgress(data.progress);

        if (Array.isArray(data.logs)) {
          data.logs.forEach((logEntry) => {
            let mtype = 'LOG';
            let mtext = logEntry;
            if (logEntry.startsWith('[') && logEntry.includes(']')) {
              const idx = logEntry.indexOf(']');
              mtype = logEntry.substring(1, idx).trim();
              mtext = logEntry.substring(idx + 1).trim();
            }
            addLog(mtype, mtext);
          });
        }
      } catch (e) {
        // Silent catch for poll
      }
    }, 1500);

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [jobId, status, prefix, addLog]);

  useEffect(() => {
    if (jobId) {
      setStatus('running');
      connect(jobId);
    }
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [jobId, connect]);

  const reset = useCallback(() => {
    if (wsRef.current) wsRef.current.close();
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    setLogs([]);
    setProgress(0);
    setStatus('idle');
    setIsConnected(false);
  }, []);

  return { logs, progress, status, isConnected, addLog, setStatus, setProgress, reset };
}
