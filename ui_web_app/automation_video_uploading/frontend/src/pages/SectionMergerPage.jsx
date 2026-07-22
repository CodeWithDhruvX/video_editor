import { useState } from 'react';
import FileDropzone from '../components/shared/FileDropzone';
import ProgressConsole from '../components/shared/ProgressConsole';
import { editorApi } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';

const OUTPUT_MODES = [
  { value: 'both', label: '🌟 Both (Master & Sections)', desc: 'Generates full video and per-section clips' },
  { value: 'master', label: '🎬 Master Video Only', desc: 'Combines all sections into one single video' },
  { value: 'sections', label: '📂 Section Videos Only', desc: 'Renders individual video files per section' },
];

const RESOLUTIONS = [
  { value: '1080p', label: '🖥️ 1080p Full HD (1920x1080)' },
  { value: 'vertical_1080x1920', label: '📱 1080x1920 Vertical (Shorts/Reels)' },
  { value: '720p', label: '📺 720p HD (1280x720)' },
  { value: '4k', label: '✨ 4K Ultra HD (3840x2160)' },
  { value: 'source', label: '⚙️ Native Source Resolution' },
];

const QUALITY_PRESETS = ['ultrafast', 'fast', 'medium', 'slow'];

export default function SectionMergerPage() {
  // Section state
  const [sections, setSections] = useState([
    { id: 'sec-1', title: 'Section 1: Introduction', clips: [] },
    { id: 'sec-2', title: 'Section 2: Main Content', clips: [] },
  ]);

  // Global settings state
  const [outputMode, setOutputMode] = useState('both');
  const [resolution, setResolution] = useState('1080p');
  const [fps, setFps] = useState(30);
  const [quality, setQuality] = useState('fast');
  const [enableGpu, setEnableGpu] = useState(true);
  const [bgMusic, setBgMusic] = useState(null);
  const [musicVolume, setMusicVolume] = useState(0.30);

  // Job state
  const [jobId, setJobId] = useState(null);
  const [outputFiles, setOutputFiles] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const { logs, progress, status, addLog, setStatus, setProgress, reset } = useWebSocket(jobId, 'editor');

  // Helper functions for Section Management
  const addSection = () => {
    const nextNum = sections.length + 1;
    setSections([
      ...sections,
      { id: `sec-${Date.now()}`, title: `Section ${nextNum}: New Section`, clips: [] }
    ]);
  };

  const removeSection = (secId) => {
    if (sections.length <= 1) {
      setError('You must have at least one section.');
      return;
    }
    setError('');
    setSections(sections.filter((s) => s.id !== secId));
  };

  const updateSectionTitle = (secId, title) => {
    setSections(sections.map((s) => (s.id === secId ? { ...s, title } : s)));
  };

  const moveSection = (index, direction) => {
    const targetIdx = index + direction;
    if (targetIdx < 0 || targetIdx >= sections.length) return;
    const updated = [...sections];
    const temp = updated[index];
    updated[index] = updated[targetIdx];
    updated[targetIdx] = temp;
    setSections(updated);
  };

  // Helper functions for Clip Management inside a section
  const addClipsToSection = (secId, files) => {
    const newClips = Array.from(files).map((file) => ({
      id: `clip-${Math.random().toString(36).substring(2, 9)}`,
      file,
      name: file.name,
      sizeMb: (file.size / (1024 * 1024)).toFixed(1),
    }));

    setSections(
      sections.map((s) =>
        s.id === secId ? { ...s, clips: [...s.clips, ...newClips] } : s
      )
    );
  };

  const removeClip = (secId, clipId) => {
    setSections(
      sections.map((s) =>
        s.id === secId
          ? { ...s, clips: s.clips.filter((c) => c.id !== clipId) }
          : s
      )
    );
  };

  const moveClip = (secId, clipIdx, direction) => {
    setSections(
      sections.map((s) => {
        if (s.id !== secId) return s;
        const targetIdx = clipIdx + direction;
        if (targetIdx < 0 || targetIdx >= s.clips.length) return s;
        const updatedClips = [...s.clips];
        const temp = updatedClips[clipIdx];
        updatedClips[clipIdx] = updatedClips[targetIdx];
        updatedClips[targetIdx] = temp;
        return { ...s, clips: updatedClips };
      })
    );
  };

  // Count total clips across all sections
  const totalClips = sections.reduce((acc, s) => acc + s.clips.length, 0);

  // Submit Handler
  const handleSubmit = async () => {
    if (totalClips === 0) {
      setError('Please add at least one video clip to your sections.');
      return;
    }
    setError('');
    setIsSubmitting(true);
    reset();
    setOutputFiles([]);
    setStatus('running');
    addLog('STATUS', `📤 Uploading ${totalClips} video clip(s) to server…`);

    // Collect ordered unique video files across all sections
    const allFiles = [];
    const sectionsPayload = [];

    sections.forEach((sec) => {
      const fileIndices = [];
      sec.clips.forEach((clip) => {
        let idx = allFiles.indexOf(clip.file);
        if (idx === -1) {
          allFiles.push(clip.file);
          idx = allFiles.length - 1;
        }
        fileIndices.push(idx);
      });

      sectionsPayload.push({
        id: sec.id,
        title: sec.title,
        file_indices: fileIndices,
      });
    });

    const config = {
      output_mode: outputMode,
      resolution,
      fps: parseInt(fps),
      quality_preset: quality,
      enable_gpu: enableGpu,
      music_volume: musicVolume,
      sections: sectionsPayload,
    };

    const fd = new FormData();
    allFiles.forEach((file) => fd.append('files', file));
    if (bgMusic) fd.append('background_music', bgMusic);
    fd.append('config_json', JSON.stringify(config));

    try {
      const res = await editorApi.startSectionMerge(fd, (evt) => {
        if (evt.total) {
          const pct = Math.round((evt.loaded * 100) / evt.total);
          setProgress(pct);
          if (pct === 100) {
            addLog('STATUS', '⚡ Upload complete. Backend processing initializing…');
          }
        }
      });
      setJobId(res.data.job_id);
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to start section merge job');
      setStatus('failed');
      addLog('ERROR', e.response?.data?.detail || 'Failed to start section merge job');
    } finally {
      setIsSubmitting(false);
    }
  };


  // Check job completion for outputs
  if (status === 'complete' && jobId && outputFiles.length === 0) {
    editorApi.getStatus(jobId).then((r) => {
      setOutputFiles(r.data.output_files || []);
    });
  }

  return (
    <div className="animate-fadeIn">
      <div className="page-hero">
        <h1>🧩 Section Video Merger</h1>
        <p>Organize, sequence, and merge multiple video clips section-by-section into a unified master video or individual section outputs.</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '1.5rem', alignItems: 'start' }}>
        {/* Left Column — Section Builder & Options */}
        <div className="stack">
          {/* Section Manager Header */}
          <div className="card">
            <div className="card-header" style={{ marginBottom: '0.75rem' }}>
              <div className="card-icon" style={{ background: 'rgba(124,58,237,0.15)' }}>📂</div>
              <div style={{ flex: 1 }}>
                <div className="card-title">Sections Builder</div>
                <div className="card-subtitle">Organize video clips into ordered sections ({sections.length} sections, {totalClips} total clips)</div>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={addSection}>
                ➕ Add Section
              </button>
            </div>

            {/* List of Sections */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', marginTop: '1rem' }}>
              {sections.map((sec, secIdx) => (
                <div className="section-block" key={sec.id}>
                  <div className="section-header-bar">
                    <span className="clip-badge">Section {secIdx + 1}</span>
                    <input
                      type="text"
                      className="section-title-input"
                      value={sec.title}
                      onChange={(e) => updateSectionTitle(sec.id, e.target.value)}
                      placeholder="Section Title (e.g. Intro, Part 1)"
                    />
                    <div style={{ display: 'flex', gap: '0.35rem' }}>
                      <button
                        className="btn-icon"
                        onClick={() => moveSection(secIdx, -1)}
                        disabled={secIdx === 0}
                        title="Move Section Up"
                      >
                        ▲
                      </button>
                      <button
                        className="btn-icon"
                        onClick={() => moveSection(secIdx, 1)}
                        disabled={secIdx === sections.length - 1}
                        title="Move Section Down"
                      >
                        ▼
                      </button>
                      <button
                        className="btn-icon"
                        style={{ color: '#f87171' }}
                        onClick={() => removeSection(sec.id)}
                        title="Delete Section"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>

                  {/* Section Clips Dropzone */}
                  <FileDropzone
                    multiple
                    accept="video/*"
                    icon="🎥"
                    title={`Add video clips for ${sec.title}`}
                    hint="Drop MP4/MOV files here"
                    acceptLabel="MP4, MOV, AVI, MKV"
                    onFiles={(files) => addClipsToSection(sec.id, files)}
                  />

                  {/* Clips list in this section */}
                  {sec.clips.length > 0 && (
                    <div className="clip-list">
                      {sec.clips.map((clip, clipIdx) => (
                        <div className="clip-item" key={clip.id}>
                          <span className="clip-badge">Clip {clipIdx + 1}</span>
                          <span className="clip-name" title={clip.name}>
                            🎬 {clip.name} <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>({clip.sizeMb} MB)</span>
                          </span>
                          <div className="clip-actions">
                            <button
                              className="btn-icon"
                              onClick={() => moveClip(sec.id, clipIdx, -1)}
                              disabled={clipIdx === 0}
                              title="Move Clip Up"
                            >
                              ▲
                            </button>
                            <button
                              className="btn-icon"
                              onClick={() => moveClip(sec.id, clipIdx, 1)}
                              disabled={clipIdx === sec.clips.length - 1}
                              title="Move Clip Down"
                            >
                              ▼
                            </button>
                            <button
                              className="btn-icon"
                              style={{ color: '#f87171' }}
                              onClick={() => removeClip(sec.id, clip.id)}
                              title="Remove Clip"
                            >
                              ❌
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Merge & Formatting Options */}
          <div className="card">
            <div className="card-header">
              <div className="card-icon" style={{ background: 'rgba(6,182,212,0.15)' }}>⚙️</div>
              <div>
                <div className="card-title">Merge & Output Options</div>
                <div className="card-subtitle">Output mode, video resolution, quality, and audio mix</div>
              </div>
            </div>

            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <label className="form-label">🎯 Export Mode</label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.75rem' }}>
                {OUTPUT_MODES.map((m) => (
                  <div
                    key={m.value}
                    onClick={() => setOutputMode(m.value)}
                    style={{
                      padding: '0.75rem',
                      borderRadius: 'var(--radius-sm)',
                      border: `1.5px solid ${outputMode === m.value ? 'var(--accent-purple)' : 'var(--border-subtle)'}`,
                      background: outputMode === m.value ? 'rgba(124,58,237,0.1)' : 'transparent',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: '0.85rem', color: outputMode === m.value ? '#c4b5fd' : 'var(--text-primary)' }}>
                      {m.label}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                      {m.desc}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid-2" style={{ gap: '1rem', marginTop: '1rem' }}>
              <div className="form-group">
                <label className="form-label">🖥️ Target Resolution</label>
                <select
                  className="form-select"
                  value={resolution}
                  onChange={(e) => setResolution(e.target.value)}
                >
                  {RESOLUTIONS.map((r) => (
                    <option key={r.value} value={r.value}>{r.label}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">🎞️ Target Frame Rate</label>
                <select
                  className="form-select"
                  value={fps}
                  onChange={(e) => setFps(parseInt(e.target.value))}
                >
                  <option value={30}>30 FPS (Standard)</option>
                  <option value={60}>60 FPS (Smooth)</option>
                  <option value={0}>Source FPS (Native)</option>
                </select>
              </div>
            </div>

            <div className="grid-2" style={{ gap: '1rem', marginTop: '0.75rem' }}>
              <div className="form-group">
                <label className="form-label">⚡ Quality Preset</label>
                <select
                  className="form-select"
                  value={quality}
                  onChange={(e) => setQuality(e.target.value)}
                >
                  {QUALITY_PRESETS.map((q) => (
                    <option key={q} value={q}>{q.charAt(0).toUpperCase() + q.slice(1)}</option>
                  ))}
                </select>
              </div>

              <div className="form-group" style={{ display: 'flex', alignItems: 'center' }}>
                <label className="checkbox-option" style={{ marginTop: '1.25rem' }}>
                  <input
                    type="checkbox"
                    checked={enableGpu}
                    onChange={(e) => setEnableGpu(e.target.checked)}
                  />
                  🚀 GPU Acceleration (NVENC)
                </label>
              </div>
            </div>

            {/* Background Music Option */}
            <div style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid var(--border-subtle)' }}>
              <div className="section-label">🎵 Background Music Track (Optional)</div>
              <FileDropzone
                accept="audio/*"
                icon="🎧"
                title="Drop background music track"
                hint="or click to browse"
                acceptLabel="MP3, WAV, AAC, FLAC"
                onFiles={(arr) => setBgMusic(arr[0] || null)}
              />

              {bgMusic && (
                <div className="form-group" style={{ marginTop: '0.75rem' }}>
                  <label className="form-label">Music Volume: {musicVolume.toFixed(2)}</label>
                  <div className="slider-group">
                    <input
                      type="range"
                      className="form-slider"
                      min={0} max={1.0} step={0.05}
                      value={musicVolume}
                      onChange={(e) => setMusicVolume(parseFloat(e.target.value))}
                    />
                    <span className="slider-value">{musicVolume.toFixed(2)}</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column — Action & Progress Console */}
        <div className="stack" style={{ position: 'sticky', top: '80px' }}>
          <div className="card">
            <div className="card-header">
              <div className="card-icon" style={{ background: 'rgba(16,185,129,0.15)' }}>🚀</div>
              <div>
                <div className="card-title">Start Section Merge</div>
                <div className="card-subtitle">{sections.length} sections &bull; {totalClips} video clip(s)</div>
              </div>
            </div>

            {error && (
              <div style={{
                padding: '0.75rem',
                background: 'rgba(239,68,68,0.1)',
                border: '1px solid rgba(239,68,68,0.25)',
                borderRadius: 'var(--radius-sm)',
                color: '#fca5a5',
                fontSize: '0.85rem',
                marginBottom: '0.75rem',
              }}>
                ⚠️ {error}
              </div>
            )}

            <button
              className="btn btn-primary btn-lg"
              style={{ width: '100%' }}
              onClick={handleSubmit}
              disabled={isSubmitting || status === 'running'}
            >
              {isSubmitting || status === 'running' ? '⏳ Merging Sections…' : '🚀 Start Section Merge'}
            </button>

            {status === 'running' && jobId && (
              <button
                className="btn btn-danger"
                style={{ width: '100%', marginTop: '0.5rem' }}
                onClick={() => editorApi.stopJob(jobId)}
              >
                ⏹ Stop Merge Job
              </button>
            )}

            {/* Output Download List */}
            {status === 'complete' && outputFiles.length > 0 && (
              <div style={{ marginTop: '1rem' }}>
                <div className="section-label">📥 Merged Outputs ({outputFiles.length})</div>
                <div className="file-list">
                  {outputFiles.map((fname) => (
                    <div className="file-item" key={fname}>
                      <span className="file-item-name" title={fname}>
                        {fname.startsWith('Master') ? '🌟' : '🎬'} {fname}
                      </span>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                          className="btn btn-ghost btn-sm"
                          style={{ padding: '0.25rem 0.5rem', color: 'var(--accent-cyan)' }}
                          onClick={() => {
                            editorApi.watchOutput(jobId, fname).catch(e => {
                              alert('Failed to open video: ' + (e.response?.data?.detail || e.message));
                            });
                          }}
                          title="Watch Video Locally"
                        >
                          ▶️ Watch
                        </button>
                        <a
                          href={editorApi.downloadUrl(jobId, fname)}
                          className="btn btn-secondary btn-sm"
                          download
                        >
                          ⬇️ Download
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <ProgressConsole
            logs={logs}
            progress={progress}
            status={status}
            title="Section Merge Console"
          />
        </div>
      </div>
    </div>
  );
}
