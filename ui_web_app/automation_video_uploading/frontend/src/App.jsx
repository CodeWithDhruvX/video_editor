import { useState } from 'react';
import { BrowserRouter, Routes, Route, NavLink, useLocation, Navigate } from 'react-router-dom';
import EditorPage from './pages/EditorPage';
import UploaderPage from './pages/UploaderPage';
import './index.css';

function Header() {
  const location = useLocation();

  const navItems = [
    { path: '/editor', label: '🎬 Video Editor' },
    { path: '/uploader', label: '📺 YouTube Uploader' },
  ];

  return (
    <header className="app-header">
      <NavLink to="/editor" className="app-logo">
        <div className="app-logo-icon">⚡</div>
        <span className="app-logo-text">VideoFlow</span>
      </NavLink>

      <nav className="nav-tabs">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => `nav-tab ${isActive ? 'active' : ''}`}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          FastAPI Backend
        </span>
        <div
          style={{
            width: 8, height: 8, borderRadius: '50%',
            background: 'var(--accent-green)',
            boxShadow: '0 0 8px var(--accent-green)',
          }}
        />
      </div>
    </header>
  );
}

function AppLayout() {
  const location = useLocation();
  const isEditor = location.pathname === '/editor' || location.pathname === '/';
  const isUploader = location.pathname === '/uploader';

  return (
    <div className="app-layout">
      <Header />
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Navigate to="/editor" replace />} />
        </Routes>
        
        <div style={{ display: isEditor ? 'block' : 'none' }}>
          <EditorPage />
        </div>
        
        <div style={{ display: isUploader ? 'block' : 'none' }}>
          <UploaderPage />
        </div>
      </main>

      <footer style={{
        textAlign: 'center',
        padding: '1.5rem',
        color: 'var(--text-muted)',
        fontSize: '0.75rem',
        borderTop: '1px solid var(--border-subtle)',
      }}>
        VideoFlow — Automation Video Editor & YouTube Uploader &nbsp;•&nbsp;
        Backend: <code style={{ color: 'var(--accent-cyan)', fontFamily: 'monospace' }}>localhost:8000</code>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
}
