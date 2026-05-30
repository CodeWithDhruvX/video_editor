import { useState, useRef } from 'react';
import FileDropzone from '../components/shared/FileDropzone';
import ProgressConsole from '../components/shared/ProgressConsole';
import SubtitleEditor from '../components/SubtitleEditor';
import { editorApi } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';

const QUALITY_PRESETS = ['ultrafast', 'fast', 'medium', 'slow'];
const SUBTITLE_MODES = [
  { value: 'single', label: '📝 Single Word', desc: 'One word at a time' },
  { value: 'multiple', label: '📄 Multiple Words', desc: 'Group of words per subtitle' },
  { value: 'mixed', label: '🎨 Mixed Styles', desc: 'Creative random fonts & colors' },
];
const COLOR_PRESETS = ['#FFFFFF', '#FFFF00', '#FF6B6B', '#06FFA5', '#06B6D4', '#FF69B4', '#FFA500', '#C4B5FD'];
const FONT_FAMILIES = [
  'Arial', 'Arial Black', 'Verdana', 'Tahoma', 'Trebuchet MS', 'Impact', 
  'Times New Roman', 'Georgia', 'Courier New', 'Comic Sans MS', 
  'Lucida Console', 'Lucida Sans Unicode', 'Palatino Linotype', 
  'Garamond', 'Book Antiqua', 'Consolas', 'Segoe UI', 'Calibri', 
  'Cambria', 'Candara', 'Franklin Gothic Medium', 'Corbel', 'Constantia'
];

export default function EditorPage() {
  // File state
  const [inputVideos, setInputVideos] = useState([]);
  const [extraVideo, setExtraVideo] = useState(null);
  const [bgMusic, setBgMusic] = useState(null);

  // Transcript State
  const [transcripts, setTranscripts] = useState({});
  const [isTranscribing, setIsTranscribing] = useState(false);

  // Config
  const [quality, setQuality] = useState('fast');
  const [musicVolume, setMusicVolume] = useState(0.30);
  const [enableGpu, setEnableGpu] = useState(true);
  const [autoEdit, setAutoEdit] = useState(false);
  const [enableDucking, setEnableDucking] = useState(true);
  const [enableMerge, setEnableMerge] = useState(false);

  // Subtitle settings
  const [subtitleMode, setSubtitleMode] = useState('mixed');
  const [wordsCount, setWordsCount] = useState(3);
  const [subtitleColor, setSubtitleColor] = useState('#FFFFFF');
  const [subtitleFont, setSubtitleFont] = useState('Arial');
  const [subtitleSize, setSubtitleSize] = useState(24);
  const [enableBorders, setEnableBorders] = useState(true);
  const [borderColor, setBorderColor] = useState('#000000');
  const [borderThickness, setBorderThickness] = useState(3);
  const [subtitlePosition, setSubtitlePosition] = useState('bottom');
  const [randomFonts, setRandomFonts] = useState(true);
  const [randomColors, setRandomColors] = useState(true);
  const [randomSizes, setRandomSizes] = useState(true);
  const [enableEffects, setEnableEffects] = useState(true);

  // Job state
  const [jobId, setJobId] = useState(null);
  const [outputFiles, setOutputFiles] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const { logs, progress, status, reset } = useWebSocket(jobId, 'editor');

  const handleTranscribe = async () => {
    if (inputVideos.length === 0) {
      setError('Please select a video file first to transcribe.');
      return;
    }
    setError('');
    setIsTranscribing(true);
    setTranscripts({});
    try {
      const results = {};
      for (const video of inputVideos) {
        const fd = new FormData();
        fd.append('video', video);
        const res = await editorApi.transcribeVideo(fd);
        results[video.name] = res.data.words || [];
      }
      setTranscripts(results);
    } catch (e) {
      setError(e.response?.data?.detail || 'Transcription failed.');
    } finally {
      setIsTranscribing(false);
    }
  };

  const handleSubmit = async () => {
    if (inputVideos.length === 0) {
      setError('Please select at least one video file');
      return;
    }
    setError('');
    setIsSubmitting(true);
    reset();
    setOutputFiles([]);

    const config = {
      quality_preset: quality,
      music_volume: musicVolume,
      enable_gpu: enableGpu,
      enable_auto_edit: autoEdit,
      enable_ducking: enableDucking,
      enable_merge: enableMerge,
      edited_transcripts: transcripts,
      subtitle_settings: {
        color: subtitleColor,
        font_family: subtitleFont,
        mode: subtitleMode,
        size: subtitleSize,
        words_count: wordsCount,
        enable_borders: enableBorders,
        border_color: borderColor,
        border_thickness: borderThickness,
        position: subtitlePosition,
        mixed_font_settings: {
          enable_random_fonts: randomFonts,
          enable_random_colors: randomColors,
          enable_random_sizes: randomSizes,
          enable_effects: enableEffects,
        },
      },
    };

    const fd = new FormData();
    inputVideos.forEach((f) => fd.append('videos', f));
    if (enableMerge && extraVideo) fd.append('extra_video', extraVideo);
    if (bgMusic) fd.append('background_music', bgMusic);
    fd.append('config_json', JSON.stringify(config));

    try {
      const res = await editorApi.startProcessing(fd);
      setJobId(res.data.job_id);
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to start processing');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Poll for output files when job completes
  const pollRef = useRef(null);
  if (status === 'complete' && jobId && outputFiles.length === 0) {
    editorApi.getStatus(jobId).then((r) => {
      setOutputFiles(r.data.output_files || []);
    });
  }

  return (
    <div className="animate-fadeIn">
      <div className="page-hero">
        <h1>🎬 Video Editor</h1>
        <p>Add captions, background music, merge clips, and apply subtitle styles — fully automated.</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '1.5rem', alignItems: 'start' }}>
        {/* Left column */}
        <div className="stack">
          {/* File Selection */}
          <div className="card">
            <div className="card-header">
              <div className="card-icon" style={{ background: 'rgba(124,58,237,0.15)' }}>📁</div>
              <div>
                <div className="card-title">File Selection</div>
                <div className="card-subtitle">Upload your video files to process</div>
              </div>
            </div>

            <div className="section-label">Main Videos *</div>
            <FileDropzone
              multiple
              accept="video/*"
              icon="🎥"
              title="Drop video files here"
              hint="or click to browse"
              acceptLabel="MP4, MOV, AVI, MKV"
              onFiles={(files) => {
                setInputVideos(files);
                setTranscripts({});
              }}
            />

            <div style={{ marginTop: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
                <label className="checkbox-option">
                  <input
                    type="checkbox"
                    checked={enableMerge}
                    onChange={(e) => setEnableMerge(e.target.checked)}
                  />
                  <span style={{ fontWeight: 600 }}>🔗 Enable Video Merging</span>
                </label>
              </div>

              {enableMerge && (
                <FileDropzone
                  accept="video/*"
                  icon="➕"
                  title="Extra video to merge"
                  hint="or click to browse"
                  acceptLabel="MP4, MOV, AVI, MKV"
                  onFiles={(arr) => setExtraVideo(arr[0] || null)}
                />
              )}
            </div>

            <div style={{ marginTop: '1rem' }}>
              <div className="section-label">Background Music (Optional)</div>
              <FileDropzone
                accept="audio/*"
                icon="🎵"
                title="Drop audio file here"
                hint="or click to browse"
                acceptLabel="MP3, WAV, AAC, FLAC"
                onFiles={(arr) => setBgMusic(arr[0] || null)}
              />
            </div>
          </div>

          {/* Transcription & Subtitles */}
          <div className="card">
            <div className="card-header">
              <div className="card-icon" style={{ background: 'rgba(59,130,246,0.15)' }}>🎙️</div>
              <div>
                <div className="card-title">Transcription & Subtitles</div>
                <div className="card-subtitle">Generate and edit subtitles before processing</div>
              </div>
            </div>
            
            <button
              className="btn btn-secondary"
              onClick={handleTranscribe}
              disabled={isTranscribing || inputVideos.length === 0}
              style={{ width: '100%', marginBottom: '1rem' }}
            >
              {isTranscribing ? '⏳ Transcribing...' : '🎙️ Transcribe Video'}
            </button>

            {Object.keys(transcripts).length > 0 && (
              <SubtitleEditor transcripts={transcripts} setTranscripts={setTranscripts} />
            )}
          </div>

          {/* Processing Options */}
          <div className="card">
            <div className="card-header">
              <div className="card-icon" style={{ background: 'rgba(6,182,212,0.15)' }}>⚙️</div>
              <div>
                <div className="card-title">Processing Options</div>
                <div className="card-subtitle">Quality, GPU, and audio settings</div>
              </div>
            </div>

            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Quality Preset</label>
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

              <div className="form-group">
                <label className="form-label">Music Volume: {musicVolume.toFixed(2)}</label>
                <div className="slider-group">
                  <input
                    type="range"
                    className="form-slider"
                    min={0} max={0.5} step={0.05}
                    value={musicVolume}
                    onChange={(e) => setMusicVolume(parseFloat(e.target.value))}
                  />
                  <span className="slider-value">{musicVolume.toFixed(2)}</span>
                </div>
              </div>
            </div>

            <div className="checkbox-group">
              <label className="checkbox-option">
                <input type="checkbox" checked={enableGpu} onChange={(e) => setEnableGpu(e.target.checked)} />
                🚀 GPU Acceleration (NVENC)
              </label>
              <label className="checkbox-option">
                <input type="checkbox" checked={autoEdit} onChange={(e) => setAutoEdit(e.target.checked)} />
                ✂️ Auto-Edit (Remove Silence)
              </label>
              <label className="checkbox-option">
                <input type="checkbox" checked={enableDucking} onChange={(e) => setEnableDucking(e.target.checked)} />
                🎵 Smart Music Ducking
              </label>
            </div>
          </div>

          {/* Subtitle Settings */}
          <div className="card">
            <div className="card-header">
              <div className="card-icon" style={{ background: 'rgba(236,72,153,0.15)' }}>📝</div>
              <div>
                <div className="card-title">Advanced Subtitle Customization</div>
                <div className="card-subtitle">Whisper AI transcription + custom styles</div>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Display Mode</label>
              <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                {SUBTITLE_MODES.map((m) => (
                  <label
                    key={m.value}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      padding: '0.6rem 1rem',
                      borderRadius: 'var(--radius-sm)',
                      border: `1.5px solid ${subtitleMode === m.value ? 'var(--accent-purple)' : 'var(--border-subtle)'}`,
                      background: subtitleMode === m.value ? 'rgba(124,58,237,0.1)' : 'transparent',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                      fontSize: '0.85rem',
                      fontWeight: subtitleMode === m.value ? 600 : 400,
                      color: subtitleMode === m.value ? '#c4b5fd' : 'var(--text-secondary)',
                    }}
                  >
                    <input
                      type="radio"
                      name="subtitle_mode"
                      value={m.value}
                      checked={subtitleMode === m.value}
                      onChange={() => setSubtitleMode(m.value)}
                      style={{ display: 'none' }}
                    />
                    {m.label}
                  </label>
                ))}
              </div>
            </div>

            {(subtitleMode === 'multiple' || subtitleMode === 'mixed') && (
              <div className="form-group">
                <label className="form-label">Words per subtitle group: {wordsCount}</label>
                <div className="slider-group">
                  <input
                    type="range"
                    className="form-slider"
                    min={2} max={10} step={1}
                    value={wordsCount}
                    onChange={(e) => setWordsCount(parseInt(e.target.value))}
                  />
                  <span className="slider-value">{wordsCount}</span>
                </div>
              </div>
            )}

            <div className="grid-2" style={{ gap: '1rem', marginTop: '0.75rem' }}>
              {(subtitleMode === 'single' || subtitleMode === 'multiple') && (
                <div className="form-group">
                  <label className="form-label">Font Family</label>
                  <select
                    className="form-select"
                    value={subtitleFont}
                    onChange={(e) => setSubtitleFont(e.target.value)}
                  >
                    {FONT_FAMILIES.map((font) => (
                      <option key={font} value={font} style={{ fontFamily: font }}>{font}</option>
                    ))}
                  </select>
                </div>
              )}
              <div className="form-group">
                <label className="form-label">Position</label>
                <select
                  className="form-select"
                  value={subtitlePosition}
                  onChange={(e) => setSubtitlePosition(e.target.value)}
                >
                  <option value="bottom">Bottom (Default)</option>
                  <option value="top">Top</option>
                  <option value="center">Center</option>
                </select>
              </div>
            </div>

            <div className="grid-2" style={{ gap: '1rem', marginTop: '0.5rem' }}>
              <div className="form-group">
                <label className="form-label">Base Size (px): {subtitleSize}</label>
                <div className="slider-group">
                  <input
                    type="range"
                    className="form-slider"
                    min={12} max={48} step={2}
                    value={subtitleSize}
                    onChange={(e) => setSubtitleSize(parseInt(e.target.value))}
                  />
                  <span className="slider-value">{subtitleSize}px</span>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Subtitle Color</label>
                <div className="color-swatches">
                  {COLOR_PRESETS.map((c) => (
                    <div
                      key={c}
                      className={`color-swatch ${subtitleColor === c ? 'active' : ''}`}
                      style={{ background: c }}
                      onClick={() => setSubtitleColor(c)}
                    />
                  ))}
                </div>
              </div>
            </div>

            <div style={{ marginTop: '0.75rem' }}>
              <label className="checkbox-option" style={{ marginBottom: '0.5rem' }}>
                <input type="checkbox" checked={enableBorders} onChange={(e) => setEnableBorders(e.target.checked)} />
                📦 Enable Speech Border Boxes
              </label>

              {enableBorders && (
                <div className="form-group" style={{ marginTop: '0.5rem' }}>
                  <label className="form-label">Border Thickness: {borderThickness}</label>
                  <div className="slider-group">
                    <input
                      type="range"
                      className="form-slider"
                      min={1} max={8} step={1}
                      value={borderThickness}
                      onChange={(e) => setBorderThickness(parseInt(e.target.value))}
                    />
                    <span className="slider-value">{borderThickness}</span>
                  </div>
                </div>
              )}
            </div>

            {subtitleMode === 'mixed' && (
              <div style={{ marginTop: '0.75rem', padding: '1rem', background: 'rgba(236,72,153,0.06)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(236,72,153,0.15)' }}>
                <div className="section-label" style={{ marginBottom: '0.75rem' }}>🎨 Mixed Font Style Options</div>
                <div className="checkbox-group">
                  <label className="checkbox-option">
                    <input type="checkbox" checked={randomFonts} onChange={(e) => setRandomFonts(e.target.checked)} />
                    🔀 Random Font Families
                  </label>
                  <label className="checkbox-option">
                    <input type="checkbox" checked={randomColors} onChange={(e) => setRandomColors(e.target.checked)} />
                    🌈 Random Colors
                  </label>
                  <label className="checkbox-option">
                    <input type="checkbox" checked={randomSizes} onChange={(e) => setRandomSizes(e.target.checked)} />
                    📏 Random Sizes
                  </label>
                  <label className="checkbox-option">
                    <input type="checkbox" checked={enableEffects} onChange={(e) => setEnableEffects(e.target.checked)} />
                    ✨ Bold & Italic Effects
                  </label>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right column — controls + console */}
        <div className="stack" style={{ position: 'sticky', top: '80px' }}>
          <div className="card">
            <div className="card-header">
              <div className="card-icon" style={{ background: 'rgba(16,185,129,0.15)' }}>🚀</div>
              <div>
                <div className="card-title">Start Processing</div>
                <div className="card-subtitle">{inputVideos.length} video(s) selected</div>
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
              {isSubmitting || status === 'running' ? '⏳ Processing…' : '🚀 Start Processing'}
            </button>

            {status === 'running' && jobId && (
              <button
                className="btn btn-danger"
                style={{ width: '100%', marginTop: '0.5rem' }}
                onClick={() => editorApi.stopJob(jobId)}
              >
                ⏹ Stop
              </button>
            )}

            {status === 'complete' && outputFiles.length > 0 && (
              <div style={{ marginTop: '0.75rem' }}>
                <div className="section-label">📥 Download Outputs</div>
                <div className="file-list">
                  {outputFiles.map((fname) => (
                    <div className="file-item" key={fname}>
                      <span className="file-item-name">🎬 {fname}</span>
                      <a
                        href={editorApi.downloadUrl(jobId, fname)}
                        className="btn btn-secondary btn-sm"
                        download
                      >
                        ⬇️ Download
                      </a>
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
            title="Processing Log"
          />
        </div>
      </div>
    </div>
  );
}
