import { useState, useEffect } from 'react';
import FileDropzone from '../components/shared/FileDropzone';
import ProgressConsole from '../components/shared/ProgressConsole';
import { uploaderApi } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';

const CATEGORIES = [
  'Film & Animation', 'Autos & Vehicles', 'Music', 'Pets & Animals',
  'Sports', 'Travel & Events', 'Gaming', 'People & Blogs', 'Comedy',
  'Entertainment', 'News & Politics', 'Howto & Style', 'Education',
  'Science & Technology', 'Nonprofits & Activism',
];

// ─── Tag Input Component ───
function TagInput({ tags, onChange }) {
  const [input, setInput] = useState('');

  const addTag = () => {
    const val = input.trim();
    if (val && !tags.includes(val)) {
      onChange([...tags, val]);
    }
    setInput('');
  };

  const removeTag = (i) => onChange(tags.filter((_, idx) => idx !== i));

  return (
    <div
      className="tags-container"
      onClick={(e) => e.currentTarget.querySelector('input')?.focus()}
    >
      {tags.map((t, i) => (
        <span className="tag-pill" key={i}>
          {t}
          <button onClick={() => removeTag(i)}>×</button>
        </span>
      ))}
      <input
        className="tags-input"
        placeholder="Add tag, press Enter…"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addTag(); }
        }}
        onBlur={addTag}
      />
    </div>
  );
}

// ─── Auth Panel ───
function AuthPanel({ authStatus, onStatusChange }) {
  const [secretFile, setSecretFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [msg, setMsg] = useState('');

  const uploadSecret = async () => {
    if (!secretFile) return;
    setUploading(true);
    try {
      await uploaderApi.uploadSecret(secretFile);
      setMsg('✅ client_secret.json uploaded');
    } catch (e) {
      setMsg('❌ ' + (e.response?.data?.detail || 'Upload failed'));
    }
    setUploading(false);
  };

  const startAuth = async () => {
    try {
      const res = await uploaderApi.startAuth();
      window.open(res.data.auth_url, '_blank');
      setMsg('🔐 Opened Google auth in new tab. After approving, refresh auth status.');
    } catch (e) {
      setMsg('❌ ' + (e.response?.data?.detail || 'Auth start failed'));
    }
  };

  const refreshStatus = async () => {
    try {
      const res = await uploaderApi.getAuthStatus();
      onStatusChange(res.data);
    } catch {
      onStatusChange({ authenticated: false, message: 'Error checking status' });
    }
  };

  const logout = async (channelId) => {
    await uploaderApi.logout(channelId);
    refreshStatus();
  };

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-icon" style={{ background: 'rgba(245,158,11,0.15)' }}>🔐</div>
        <div>
          <div className="card-title">YouTube Authentication</div>
          <div className="card-subtitle">Manage your connected Google accounts</div>
        </div>
      </div>

      <div
        className={`auth-status ${authStatus?.authenticated ? 'authenticated' : 'unauthenticated'}`}
        style={{ marginBottom: '1rem' }}
      >
        {authStatus?.authenticated ? '✅' : '❌'}
        {authStatus?.authenticated
          ? ` Connected Channels: ${authStatus.channels?.length || 0}`
          : ` Not connected — ${authStatus?.message || ''}`}
      </div>

      {authStatus?.authenticated && authStatus.channels && authStatus.channels.length > 0 && (
        <div style={{ marginBottom: '1rem' }}>
          <label className="form-label">Connected Channels</label>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {authStatus.channels.map((channel) => (
              <div key={channel.channel_id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.75rem', background: 'rgba(255,255,255,0.05)', borderRadius: 'var(--radius-sm)' }}>
                <div>
                  <strong>{channel.channel_name}</strong>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>ID: {channel.channel_id}</div>
                </div>
                <button className="btn btn-ghost btn-sm" onClick={() => logout(channel.channel_id)}>🚪 Logout</button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="form-group">
        <label className="form-label">{authStatus?.authenticated ? "Connect Another Account (Requires client_secret.json)" : "Step 1: Upload client_secret.json"}</label>
        <FileDropzone
          accept=".json"
          icon="🔑"
          title="Drop client_secret.json here"
          hint="or click to browse"
          acceptLabel="JSON files only"
          showList
          onFiles={(arr) => setSecretFile(arr[0] || null)}
        />
      </div>
      <div className="row" style={{ marginTop: '0.5rem' }}>
        <button
          className="btn btn-secondary"
          onClick={uploadSecret}
          disabled={!secretFile || uploading}
        >
          {uploading ? '⏳ Uploading…' : '📤 Upload Secret'}
        </button>
        <button className="btn btn-primary" onClick={startAuth}>
          🔗 Connect to YouTube
        </button>
      </div>

      <div className="row" style={{ marginTop: '0.75rem' }}>
        <button className="btn btn-ghost btn-sm" onClick={refreshStatus}>🔄 Refresh Status</button>
      </div>

      {msg && (
        <div style={{ marginTop: '0.75rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          {msg}
        </div>
      )}
    </div>
  );
}

// ─── Single Upload Form ───
function SingleUploadTab({ authStatus, activeChannelId, setActiveChannelId }) {
  const [videoFile, setVideoFile] = useState(null);
  const [thumbnail, setThumbnail] = useState(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState([]);
  const [category, setCategory] = useState('Entertainment');
  const [privacy, setPrivacy] = useState('public');
  const [madeForKids, setMadeForKids] = useState(false);
  const [playlists, setPlaylists] = useState([]);
  const [playlistInput, setPlaylistInput] = useState('');
  const [scheduleEnabled, setScheduleEnabled] = useState(false);
  const [publishAt, setPublishAt] = useState('');
  const [publishTime, setPublishTime] = useState('09:00:00');

  const [jobId, setJobId] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const { logs, progress, status, reset } = useWebSocket(jobId, 'uploader');

  const submit = async () => {
    if (!activeChannelId) return setError('Please select a YouTube channel');
    if (!videoFile) return setError('Please select a video file');
    if (!title.trim()) return setError('Title is required');
    setError('');
    setIsSubmitting(true);
    reset();

    const metadata = {
      title: title.trim(),
      description,
      tags,
      category_name: category,
      privacy_status: privacy,
      made_for_kids: madeForKids,
      playlist_names: playlists,
      publish_at: scheduleEnabled && publishAt ? `${publishAt} ${publishTime}` : null,
    };

    const fd = new FormData();
    fd.append('channel_id', activeChannelId);
    fd.append('video_file', videoFile);
    if (thumbnail) fd.append('thumbnail', thumbnail);
    fd.append('metadata_json', JSON.stringify(metadata));

    try {
      const res = await uploaderApi.uploadSingle(fd);
      setJobId(res.data.job_id);
    } catch (e) {
      setError(e.response?.data?.detail || 'Upload failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: '1.5rem', alignItems: 'start' }}>
      <div className="stack">
        {/* Files */}
        <div className="card">
          <div className="card-header">
            <div className="card-icon" style={{ background: 'rgba(239,68,68,0.12)' }}>🎬</div>
            <div><div className="card-title">Video & Thumbnail</div></div>
          </div>
          <div className="form-group">
            <label className="form-label">Video File *</label>
            <FileDropzone
              accept="video/*"
              icon="🎬"
              title="Drop video file here"
              hint="or click to browse"
              acceptLabel="MP4, MOV, AVI, MKV"
              onFiles={(arr) => setVideoFile(arr[0] || null)}
            />
          </div>
          <div className="form-group">
            <label className="form-label">Thumbnail (Optional)</label>
            <FileDropzone
              accept="image/*"
              icon="🖼️"
              title="Drop thumbnail here"
              hint="or click to browse"
              acceptLabel="JPG, PNG"
              onFiles={(arr) => setThumbnail(arr[0] || null)}
            />
          </div>
        </div>

        {/* Metadata */}
        <div className="card">
          <div className="card-header">
            <div className="card-icon" style={{ background: 'rgba(6,182,212,0.12)' }}>📝</div>
            <div><div className="card-title">Video Details</div></div>
          </div>

          <div className="form-group">
            <label className="form-label">Title *</label>
            <input
              className="form-input"
              placeholder="Enter video title…"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={100}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea
              className="form-textarea"
              placeholder="Video description…"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
            />
          </div>

          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">Category</label>
              <select className="form-select" value={category} onChange={(e) => setCategory(e.target.value)}>
                {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Privacy</label>
              <div className="radio-group">
                {['public', 'unlisted', 'private'].map((p) => (
                  <label key={p} className="radio-option">
                    <input type="radio" name="privacy" value={p} checked={privacy === p} onChange={() => setPrivacy(p)} />
                    {p.charAt(0).toUpperCase() + p.slice(1)}
                  </label>
                ))}
              </div>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Tags</label>
            <TagInput tags={tags} onChange={setTags} />
          </div>

          <div className="form-group">
            <label className="form-label">Playlists (press Enter to add)</label>
            <TagInput tags={playlists} onChange={setPlaylists} />
          </div>

          <label className="checkbox-option">
            <input type="checkbox" checked={madeForKids} onChange={(e) => setMadeForKids(e.target.checked)} />
            Made for Kids (COPPA)
          </label>
        </div>

        {/* Schedule */}
        <div className="card">
          <div className="card-header">
            <div className="card-icon" style={{ background: 'rgba(124,58,237,0.12)' }}>📅</div>
            <div><div className="card-title">Schedule Publishing</div></div>
          </div>
          <label className="checkbox-option" style={{ marginBottom: '0.75rem' }}>
            <input type="checkbox" checked={scheduleEnabled} onChange={(e) => setScheduleEnabled(e.target.checked)} />
            Schedule for later (IST timezone)
          </label>
          {scheduleEnabled && (
            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Date</label>
                <input
                  type="date"
                  className="form-input"
                  value={publishAt}
                  onChange={(e) => setPublishAt(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Time (HH:MM:SS)</label>
                <input
                  type="time"
                  className="form-input"
                  value={publishTime}
                  onChange={(e) => setPublishTime(e.target.value + ':00')}
                  step={1}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right panel */}
      <div className="stack" style={{ position: 'sticky', top: '80px' }}>
        <div className="card">
          <div className="card-header">
            <div className="card-icon" style={{ background: 'rgba(16,185,129,0.12)' }}>🚀</div>
            <div><div className="card-title">Upload to YouTube</div></div>
          </div>
          {!authStatus?.authenticated && (
            <div style={{ padding: '0.75rem', background: 'rgba(239,68,68,0.08)', borderRadius: 'var(--radius-sm)', color: '#fca5a5', fontSize: '0.85rem', marginBottom: '0.75rem', border: '1px solid rgba(239,68,68,0.2)' }}>
              ⚠️ Please authenticate with YouTube first (Auth tab)
            </div>
          )}
          {authStatus?.authenticated && (
            <div className="form-group">
              <label className="form-label">Target Channel</label>
              <select 
                className="form-select" 
                value={activeChannelId} 
                onChange={(e) => setActiveChannelId(e.target.value)}
              >
                <option value="">-- Select Channel --</option>
                {authStatus?.channels?.map(c => (
                  <option key={c.channel_id} value={c.channel_id}>{c.channel_name}</option>
                ))}
              </select>
            </div>
          )}
          {error && (
            <div style={{ padding: '0.75rem', background: 'rgba(239,68,68,0.08)', borderRadius: 'var(--radius-sm)', color: '#fca5a5', fontSize: '0.85rem', marginBottom: '0.75rem', border: '1px solid rgba(239,68,68,0.2)' }}>
              ⚠️ {error}
            </div>
          )}
          <button
            className="btn btn-primary btn-lg"
            style={{ width: '100%' }}
            onClick={submit}
            disabled={isSubmitting || status === 'running' || !authStatus?.authenticated || !activeChannelId}
          >
            {isSubmitting || status === 'running' ? '⏳ Uploading…' : '🚀 Upload Video'}
          </button>
        </div>
        <ProgressConsole logs={logs} progress={progress} status={status} title="Upload Log" />
      </div>
    </div>
  );
}

// ─── Batch Upload Tab ───
function BatchUploadTab({ authStatus, activeChannelId, setActiveChannelId }) {
  const [videos, setVideos] = useState([]);
  const [metadataFile, setMetadataFile] = useState(null);
  const [metadataPreview, setMetadataPreview] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const { logs, progress, status, reset } = useWebSocket(jobId, 'uploader');

  const loadMetadata = async (file) => {
    setMetadataFile(file);
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      setMetadataPreview(data);
    } catch {
      setError('Invalid JSON metadata file');
    }
  };

  const submit = async () => {
    if (!activeChannelId) return setError('Select a YouTube channel');
    if (videos.length === 0) return setError('Select at least one video');
    if (!metadataFile) return setError('Select a metadata JSON file');
    setError('');
    setIsSubmitting(true);
    reset();

    const fd = new FormData();
    fd.append('channel_id', activeChannelId);
    videos.forEach((v) => fd.append('videos', v));
    fd.append('metadata_json', await metadataFile.text());

    try {
      const res = await uploaderApi.uploadBatchWithFiles(fd);
      setJobId(res.data.job_id);
    } catch (e) {
      setError(e.response?.data?.detail || 'Batch upload failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: '1.5rem', alignItems: 'start' }}>
      <div className="stack">
        <div className="card">
          <div className="card-header">
            <div className="card-icon" style={{ background: 'rgba(6,182,212,0.12)' }}>📦</div>
            <div>
              <div className="card-title">Batch Upload</div>
              <div className="card-subtitle">Upload multiple videos at once using a JSON metadata file</div>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Video Files</label>
            <FileDropzone
              multiple
              accept="video/*"
              icon="🎬"
              title="Drop all video files here"
              hint="or click to browse (select multiple)"
              acceptLabel="MP4, MOV, AVI, MKV"
              onFiles={setVideos}
            />
          </div>

          <div className="form-group" style={{ marginTop: '0.5rem' }}>
            <label className="form-label">Metadata JSON</label>
            <FileDropzone
              accept=".json"
              icon="📋"
              title="Drop metadata.json here"
              hint="or click to browse"
              acceptLabel="JSON file"
              onFiles={(arr) => arr[0] && loadMetadata(arr[0])}
            />
            <div className="tooltip-text" style={{ marginTop: '0.5rem' }}>
              JSON format: <code style={{ color: 'var(--accent-cyan)', fontFamily: 'monospace' }}>{'{"videos": [{title, description, tags, ...}]}'}</code>
            </div>
          </div>

          {metadataPreview && (
            <div style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(6,182,212,0.06)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(6,182,212,0.15)' }}>
              <div className="section-label" style={{ marginBottom: '0.5rem' }}>📋 Metadata Preview</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Found <strong style={{ color: 'var(--accent-cyan)' }}>{metadataPreview.videos?.length || 0} videos</strong> in metadata
              </div>
              {metadataPreview.videos?.slice(0, 5).map((v, i) => (
                <div key={i} style={{ padding: '0.4rem 0.6rem', marginTop: '0.4rem', background: 'rgba(255,255,255,0.04)', borderRadius: 'var(--radius-sm)', fontSize: '0.8rem', color: 'var(--text-primary)' }}>
                  <strong>{i + 1}.</strong> {v.title}
                  {v.privacy_status && <span style={{ marginLeft: '0.5rem', color: 'var(--text-muted)' }}>({v.privacy_status})</span>}
                </div>
              ))}
              {(metadataPreview.videos?.length || 0) > 5 && (
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.4rem' }}>
                  …and {metadataPreview.videos.length - 5} more
                </div>
              )}
            </div>
          )}
        </div>

        {/* JSON Format Guide */}
        <div className="card">
          <div className="card-header">
            <div className="card-icon" style={{ background: 'rgba(245,158,11,0.12)' }}>📖</div>
            <div><div className="card-title">Metadata Format Guide</div></div>
          </div>
          <pre style={{ background: 'rgba(0,0,0,0.3)', borderRadius: 'var(--radius-sm)', padding: '1rem', fontSize: '0.75rem', color: '#a3e635', fontFamily: 'JetBrains Mono, monospace', overflow: 'auto' }}>
{`{
  "videos": [
    {
      "title": "My Video Title",
      "description": "Video description",
      "tags": ["tag1", "tag2"],
      "category_name": "Entertainment",
      "privacy_status": "public",
      "made_for_kids": false,
      "playlist_names": ["My Playlist"],
      "publish_at": "2024-12-25 10:00:00",
      "video_file_path": "video1.mp4",
      "thumbnail_path": "thumb1.jpg"
    }
  ]
}`}
          </pre>
        </div>
      </div>

      {/* Right panel */}
      <div className="stack" style={{ position: 'sticky', top: '80px' }}>
        <div className="card">
          <div className="card-header">
            <div className="card-icon" style={{ background: 'rgba(16,185,129,0.12)' }}>📦</div>
            <div>
              <div className="card-title">Batch Upload</div>
              <div className="card-subtitle">{videos.length} video(s) selected</div>
            </div>
          </div>
          {!authStatus?.authenticated && (
            <div style={{ padding: '0.75rem', background: 'rgba(239,68,68,0.08)', borderRadius: 'var(--radius-sm)', color: '#fca5a5', fontSize: '0.85rem', marginBottom: '0.75rem', border: '1px solid rgba(239,68,68,0.2)' }}>
              ⚠️ Please authenticate with YouTube first
            </div>
          )}
          {authStatus?.authenticated && (
            <div className="form-group">
              <label className="form-label">Target Channel</label>
              <select 
                className="form-select" 
                value={activeChannelId} 
                onChange={(e) => setActiveChannelId(e.target.value)}
              >
                <option value="">-- Select Channel --</option>
                {authStatus?.channels?.map(c => (
                  <option key={c.channel_id} value={c.channel_id}>{c.channel_name}</option>
                ))}
              </select>
            </div>
          )}
          {error && (
            <div style={{ padding: '0.75rem', background: 'rgba(239,68,68,0.08)', borderRadius: 'var(--radius-sm)', color: '#fca5a5', fontSize: '0.85rem', marginBottom: '0.75rem', border: '1px solid rgba(239,68,68,0.2)' }}>
              ⚠️ {error}
            </div>
          )}
          <button
            className="btn btn-primary btn-lg"
            style={{ width: '100%' }}
            onClick={submit}
            disabled={isSubmitting || status === 'running' || !authStatus?.authenticated || !activeChannelId}
          >
            {isSubmitting || status === 'running'
              ? `⏳ Uploading… (${Math.round(progress)}%)`
              : `🚀 Upload ${videos.length || 0} Videos`}
          </button>
        </div>
        <ProgressConsole logs={logs} progress={progress} status={status} title="Batch Upload Log" />
      </div>
    </div>
  );
}

// ─── Main Uploader Page ───
export default function UploaderPage() {
  const [activeTab, setActiveTab] = useState('single');
  const [authStatus, setAuthStatus] = useState(null);
  const [activeChannelId, setActiveChannelId] = useState('');

  useEffect(() => {
    uploaderApi.getAuthStatus()
      .then((res) => {
        setAuthStatus(res.data);
        if (res.data.channels && res.data.channels.length > 0) {
          setActiveChannelId(res.data.channels[0].channel_id);
        }
      })
      .catch(() => setAuthStatus({ authenticated: false, message: 'Cannot reach backend' }));
  }, []);

  const tabs = [
    { id: 'auth', label: '🔐 Authentication' },
    { id: 'single', label: '📤 Single Upload' },
    { id: 'batch', label: '📦 Batch Upload' },
  ];

  return (
    <div className="animate-fadeIn">
      <div className="page-hero">
        <h1>📺 YouTube Uploader</h1>
        <p>Upload videos with full metadata, thumbnails, scheduled publishing, and playlist management.</p>
      </div>

      <div className="page-tabs">
        {tabs.map((t) => (
          <button
            key={t.id}
            className={`page-tab ${activeTab === t.id ? 'active' : ''}`}
            onClick={() => setActiveTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === 'auth' && (
        <div style={{ maxWidth: '600px' }}>
          <AuthPanel authStatus={authStatus} onStatusChange={setAuthStatus} />
        </div>
      )}
      {activeTab === 'single' && <SingleUploadTab authStatus={authStatus} activeChannelId={activeChannelId} setActiveChannelId={setActiveChannelId} />}
      {activeTab === 'batch' && <BatchUploadTab authStatus={authStatus} activeChannelId={activeChannelId} setActiveChannelId={setActiveChannelId} />}
    </div>
  );
}
