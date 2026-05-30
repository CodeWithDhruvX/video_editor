import { useEffect, useRef, useState, useCallback } from 'react';

// ─── Log-type metadata ───────────────────────────────────────────────────────
const LINE_META = {
  LOG:      { cls: 'cl-log',      icon: '›',   prefix: '' },
  STATUS:   { cls: 'cl-status',   icon: '◆',   prefix: '[STATUS]' },
  PROGRESS: { cls: 'cl-progress', icon: '↑',   prefix: '[PROGRESS]' },
  COMPLETE: { cls: 'cl-complete', icon: '✓',   prefix: '[DONE]' },
  ERROR:    { cls: 'cl-error',    icon: '✕',   prefix: '[ERROR]' },
  FAILED:   { cls: 'cl-error',    icon: '✕',   prefix: '[FAILED]' },
  STOPPED:  { cls: 'cl-stopped',  icon: '■',   prefix: '[STOPPED]' },
  FFMPEG:   { cls: 'cl-ffmpeg',   icon: '⚙',   prefix: '[ffmpeg]' },
  WARN:     { cls: 'cl-warn',     icon: '⚠',   prefix: '[WARN]' },
};

const STATUS_LABEL = {
  idle:     'Idle',
  running:  'Processing…',
  complete: 'Complete',
  failed:   'Failed',
  stopped:  'Stopped',
};

const STATUS_DOT_CLS = {
  idle:     'dot-idle',
  running:  'dot-running',
  complete: 'dot-complete',
  failed:   'dot-failed',
  stopped:  'dot-stopped',
};

function fmt(ts) {
  const d = new Date(ts);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}.${String(d.getMilliseconds()).padStart(3, '0')}`;
}

// ─── Single log line ─────────────────────────────────────────────────────────
function LogLine({ entry, index }) {
  const meta = LINE_META[entry.type] || LINE_META.LOG;
  return (
    <div
      className={`console-line ${meta.cls}`}
      style={{ animationDelay: `${Math.min(index * 15, 300)}ms` }}
    >
      <span className="cl-time">{fmt(entry.ts)}</span>
      <span className="cl-icon">{meta.icon}</span>
      {meta.prefix && <span className="cl-prefix">{meta.prefix}</span>}
      <span className="cl-msg">{entry.message}</span>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function ProgressConsole({
  logs,
  progress,
  status,
  title = 'Processing Logs',
}) {
  const bodyRef   = useRef(null);
  const [pinned, setPinned] = useState(true);   // auto-scroll toggle
  const [filter, setFilter] = useState('ALL');   // log type filter
  const [search, setSearch] = useState('');

  // Auto-scroll when pinned
  useEffect(() => {
    if (pinned && bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
    }
  }, [logs, pinned]);

  // Detect manual scroll-up → unpin
  const onScroll = useCallback(() => {
    if (!bodyRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = bodyRef.current;
    setPinned(scrollHeight - scrollTop - clientHeight < 40);
  }, []);

  const scrollToBottom = useCallback(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
    setPinned(true);
  }, []);

  // Filter log types
  const FILTERS = ['ALL', 'LOG', 'STATUS', 'FFMPEG', 'ERROR', 'COMPLETE'];
  const visibleLogs = logs.filter((e) => {
    const typeOk   = filter === 'ALL' || e.type === filter || (filter === 'ERROR' && e.type === 'FAILED');
    const searchOk = !search || e.message.toLowerCase().includes(search.toLowerCase());
    return typeOk && searchOk;
  });

  const isRunning = status === 'running';
  const pct = Math.min(Math.round(progress), 100);

  return (
    <div className="progress-console">

      {/* ── Terminal chrome ──────────────────────────── */}
      <div className="console-header">
        <div className="console-dots">
          <span className="console-dot console-dot-red" />
          <span className="console-dot console-dot-yellow" />
          <span className="console-dot console-dot-green" />
        </div>
        <span className="console-title">{title}</span>
        <span className={`status-badge ${status === 'idle' ? 'pending' : status}`} style={{ fontSize: '0.7rem', padding: '0.15rem 0.6rem' }}>
          <span className={`status-badge-dot ${STATUS_DOT_CLS[status] || ''}`} />
          {STATUS_LABEL[status] || status}
        </span>
      </div>

      {/* ── Toolbar ──────────────────────────────────── */}
      <div className="console-toolbar">
        {/* Filter chips */}
        <div className="console-filters">
          {FILTERS.map((f) => (
            <button
              key={f}
              className={`filter-chip ${filter === f ? 'active' : ''}`}
              onClick={() => setFilter(f)}
            >
              {f}
              {f !== 'ALL' && (
                <span className="filter-count">
                  {logs.filter((e) => {
                    if (f === 'ERROR') return e.type === 'ERROR' || e.type === 'FAILED';
                    return e.type === f;
                  }).length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Search */}
        <input
          className="console-search"
          placeholder="Search logs…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        {/* Actions */}
        <div style={{ display: 'flex', gap: '0.4rem', marginLeft: 'auto' }}>
          {!pinned && (
            <button className="console-action-btn" onClick={scrollToBottom} title="Scroll to bottom">
              ↓
            </button>
          )}
          <span className="console-count">{visibleLogs.length} lines</span>
        </div>
      </div>

      {/* ── Log body ─────────────────────────────────── */}
      <div className="console-body" ref={bodyRef} onScroll={onScroll}>
        {/* Running indicator */}
        {isRunning && (
          <div className="console-running-banner">
            <span className="console-spinner" /> Processing — streaming live output…
          </div>
        )}

        {visibleLogs.length === 0 ? (
          <div className="console-empty">
            {search ? `No logs matching "${search}"` : 'Waiting for output…'}
          </div>
        ) : (
          visibleLogs.map((entry, i) => (
            <LogLine key={`${entry.ts}-${i}`} entry={entry} index={i} />
          ))
        )}

        {/* Blinking cursor when running */}
        {isRunning && <span className="console-cursor">█</span>}
      </div>

      {/* ── Progress bar ─────────────────────────────── */}
      <div className="progress-bar-wrapper">
        <div className="progress-bar-track">
          <div
            className={`progress-bar-fill ${isRunning ? 'animated' : ''}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="progress-text">
          <span>
            {status === 'complete' && '✅ Finished'}
            {status === 'running' && '⏳ In progress'}
            {status === 'failed' && '❌ Failed'}
            {status === 'stopped' && '⏹ Stopped'}
            {status === 'idle' && '—'}
          </span>
          <span className="progress-pct">{pct}%</span>
        </div>
      </div>
    </div>
  );
}
