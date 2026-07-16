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
  const [secretFiles, setSecretFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [msg, setMsg] = useState('');

  const uploadSecret = async () => {
    if (!secretFiles || secretFiles.length === 0) return;
    setUploading(true);
    try {
      await uploaderApi.uploadSecret(secretFiles);
      setMsg(`✅ ${secretFiles.length} client_secret.json file(s) uploaded`);
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
          multiple
          accept=".json"
          icon="🔑"
          title="Drop client_secret.json here"
          hint="or click to browse (can select multiple)"
          acceptLabel="JSON files only"
          showList
          onFiles={(arr) => setSecretFiles(arr)}
        />
      </div>
      <div className="row" style={{ marginTop: '0.5rem' }}>
        <button
          className="btn btn-secondary"
          onClick={uploadSecret}
          disabled={!secretFiles || secretFiles.length === 0 || uploading}
        >
          {uploading ? '⏳ Uploading…' : `📤 Upload Secret${secretFiles && secretFiles.length > 1 ? 's' : ''}`}
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
  const [metadataText, setMetadataText] = useState('');
  const [metadataPreview, setMetadataPreview] = useState(null);
  const [videoMapping, setVideoMapping] = useState({});
  const [jobId, setJobId] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [playlists, setPlaylists] = useState([]);
  const [processedVideos, setProcessedVideos] = useState([]);
  const [selectedProcessed, setSelectedProcessed] = useState([]);
  const [fetchingProcessed, setFetchingProcessed] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const { logs, progress, status, reset } = useWebSocket(jobId, 'uploader');

  const fetchProcessedVideos = async () => {
    setFetchingProcessed(true);
    try {
      const res = await uploaderApi.getProcessedVideos();
      setProcessedVideos(res.data || []);
      setSelectedProcessed([]);
    } catch (e) {
      console.error("Failed to fetch processed videos", e);
    } finally {
      setFetchingProcessed(false);
    }
  };

  useEffect(() => {
    if (activeChannelId) {
      uploaderApi.getPlaylists(activeChannelId)
        .then(res => setPlaylists(res.data || []))
        .catch(err => console.error("Failed to load playlists", err));
    } else {
      setPlaylists([]);
    }
  }, [activeChannelId]);

  useEffect(() => {
    fetchProcessedVideos();
  }, []);

  const deleteProcessed = async (paths) => {
    if (!window.confirm(`Are you sure you want to delete ${paths.length} video(s)?`)) return;
    try {
      await uploaderApi.deleteProcessedVideos(paths);
      fetchProcessedVideos();
    } catch (e) {
      alert('Failed to delete videos');
    }
  };

  const watchVideo = async (path) => {
    try {
      await uploaderApi.watchVideo(path);
    } catch (e) {
      alert('Failed to open video: ' + (e.response?.data?.detail || e.message));
    }
  };

  const openFilePath = async (path) => {
    try {
      await uploaderApi.openFilePath(path);
    } catch (e) {
      alert('Failed to open file path: ' + (e.response?.data?.detail || e.message));
    }
  };

  const addProcessedToBatch = () => {
    const toAdd = processedVideos.filter(v => selectedProcessed.includes(v.path));
    if (toAdd.length === 0) return;
    
    // Create virtual file objects for the UI
    const virtualFiles = toAdd.map(v => ({
      name: v.path, // use absolute path as name so it maps correctly
      displayName: v.name,
      size: v.size,
      isServer: true,
    }));
    
    setVideos(prev => {
      // Prevent duplicates based on path
      const existingNames = new Set(prev.map(p => p.name));
      const filteredNew = virtualFiles.filter(vf => !existingNames.has(vf.name));
      return [...prev, ...filteredNew];
    });
    setSelectedProcessed([]);
  };

  const toggleProcessedSelection = (path) => {
    setSelectedProcessed(prev => 
      prev.includes(path) ? prev.filter(p => p !== path) : [...prev, path]
    );
  };


  const loadMetadata = async (file) => {
    setMetadataFile(file);
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      setMetadataText(text);
      setMetadataPreview(data);
      setError('');
    } catch {
      setError('Invalid JSON metadata file');
    }
  };

  const handleMetadataTextChange = (e) => {
    const text = e.target.value;
    setMetadataText(text);
    if (!text.trim()) {
      setMetadataPreview(null);
      setError('');
      return;
    }
    try {
      const data = JSON.parse(text);
      setMetadataPreview(data);
      setError('');
    } catch {
      setError('Invalid JSON format in text area');
    }
  };

  const updateMetadataField = (index, field, value) => {
    const updated = { ...metadataPreview };
    updated.videos[index][field] = value;
    setMetadataPreview(updated);
  };

  const handleDateChange = (index, val) => {
    if (!val) {
      updateMetadataField(index, 'publish_at', null);
      return;
    }
    // Convert "2024-12-25T10:00" to "2024-12-25 10:00:00"
    updateMetadataField(index, 'publish_at', val.replace('T', ' ') + ':00');
  };

  const formatPublishAt = (val) => {
    if (!val) return '';
    // Convert "2024-12-25 10:00:00" to "2024-12-25T10:00"
    return val.replace(' ', 'T').substring(0, 16);
  };

  const submit = async () => {
    if (!activeChannelId) return setError('Select a YouTube channel');
    if (videos.length === 0) return setError('Select at least one video');
    if (!metadataPreview || !metadataPreview.videos) return setError('Provide valid metadata JSON via file or paste');
    setError('');
    setIsSubmitting(true);
    reset();

    const fd = new FormData();
    fd.append('channel_id', activeChannelId);
    videos.forEach((v) => {
      if (!v.isServer) {
        fd.append('videos', v);
      }
    });
    

    // The metadataPreview object is updated live, we use that for submission
    const metadata = { ...metadataPreview };
    if (metadata.videos) {
      metadata.videos.forEach((v, i) => {
        const mappedName = videoMapping[i] !== undefined ? videoMapping[i] : (videos[i] ? videos[i].name : null);
        if (mappedName) {
          v.video_file_path = mappedName;
        }
      });
    }
    fd.append('metadata_json', JSON.stringify(metadata));

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
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: '1.5rem', alignItems: 'start' }}>
        <div className="stack">
          {/* Server Processed Videos */}
          <div className="card">
            <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <div className="card-icon" style={{ background: 'rgba(139,92,246,0.12)' }}>☁️</div>
                <div>
                  <div className="card-title">Server Processed Videos</div>
                  <div className="card-subtitle">Videos generated by the editor in backend/outputs</div>
                </div>
              </div>
              <button className="btn btn-ghost btn-sm" onClick={fetchProcessedVideos} disabled={fetchingProcessed}>
                {fetchingProcessed ? '🔄 Loading...' : '🔄 Refresh'}
              </button>
            </div>
            
            <div style={{ display: 'grid', gap: '1rem', marginTop: '0.5rem' }}>
              {/* Available Server Videos */}
              <div>
                <div style={{ marginBottom: '0.5rem', fontWeight: '500', fontSize: '0.9rem', color: 'var(--text-secondary)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>Available Server Videos</span>
                  <input
                    type="text"
                    placeholder="Search videos..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    style={{
                      padding: '0.4rem 0.6rem',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      background: 'rgba(0,0,0,0.3)',
                      color: 'var(--text-primary)',
                      fontSize: '0.8rem',
                      width: '200px'
                    }}
                  />
                </div>
                <div style={{ maxHeight: '200px', overflowY: 'auto', background: 'rgba(0,0,0,0.2)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(255,255,255,0.05)' }}>
                  {processedVideos
                    .filter(v => !videos.find(sv => sv.isServer && sv.name === v.path))
                    .filter(v => {
                      if (!searchTerm) return true;
                      const searchLower = searchTerm.toLowerCase();
                      return v.name.toLowerCase().includes(searchLower) ||
                             v.job_id.toLowerCase().includes(searchLower) ||
                             v.path.toLowerCase().includes(searchLower);
                    }).length === 0 ? (
                    <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                      {searchTerm ? 'No videos match your search.' : 'No available processed videos found on the server.'}
                    </div>
                  ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                  <thead style={{ position: 'sticky', top: 0, background: '#13131A', zIndex: 1 }}>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', textAlign: 'left', color: 'var(--text-muted)' }}>
                      <th style={{ padding: '0.75rem', width: '40px', textAlign: 'center' }}>
                        <input 
                          type="checkbox" 
                          checked={selectedProcessed.length === processedVideos.filter(v => !videos.find(sv => sv.isServer && sv.name === v.path)).length && processedVideos.filter(v => !videos.find(sv => sv.isServer && sv.name === v.path)).length > 0}
                          onChange={(e) => setSelectedProcessed(e.target.checked ? processedVideos.filter(v => !videos.find(sv => sv.isServer && sv.name === v.path)).map(v => v.path) : [])}
                        />
                      </th>
                      <th style={{ padding: '0.75rem' }}>Filename</th>
                      <th style={{ padding: '0.75rem', width: '120px' }}>Job ID</th>
                      <th style={{ padding: '0.75rem', width: '80px', textAlign: 'right' }}>Size</th>
                    </tr>
                  </thead>
                  <tbody>
                    {processedVideos
                      .filter(v => !videos.find(sv => sv.isServer && sv.name === v.path))
                      .filter(v => {
                        if (!searchTerm) return true;
                        const searchLower = searchTerm.toLowerCase();
                        return v.name.toLowerCase().includes(searchLower) ||
                               v.job_id.toLowerCase().includes(searchLower) ||
                               v.path.toLowerCase().includes(searchLower);
                      })
                      .map(v => (
                      <tr key={v.path} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }} onClick={() => toggleProcessedSelection(v.path)}>
                        <td style={{ padding: '0.75rem', textAlign: 'center' }} onClick={(e) => e.stopPropagation()}>
                          <input 
                            type="checkbox" 
                            checked={selectedProcessed.includes(v.path)}
                            onChange={() => toggleProcessedSelection(v.path)}
                          />
                        </td>
                        <td style={{ padding: '0.75rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <div>
                              <div style={{ wordBreak: 'break-all', fontWeight: '500' }}>{v.name}</div>
                              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{new Date(v.created_at * 1000).toLocaleString()}</div>
                            </div>
                            <div style={{ display: 'flex', gap: '0.25rem' }}>
                              <button 
                                className="btn btn-ghost btn-sm"
                                style={{ padding: '0.25rem 0.5rem' }}
                                onClick={(e) => { e.stopPropagation(); watchVideo(v.path); }}
                                title="Watch Video"
                              >
                                ▶️ Watch
                              </button>
                              <button 
                                className="btn btn-ghost btn-sm"
                                style={{ padding: '0.25rem 0.5rem' }}
                                onClick={(e) => { e.stopPropagation(); openFilePath(v.path); }}
                                title="Open File Path"
                              >
                                📂 Open Path
                              </button>
                            </div>
                          </div>
                        </td>
                        <td style={{ padding: '0.75rem', color: 'var(--text-muted)', fontSize: '0.75rem' }}>{v.job_id.substring(0, 8)}...</td>
                        <td style={{ padding: '0.75rem', textAlign: 'right', color: 'var(--text-muted)' }}>{(v.size / (1024*1024)).toFixed(1)} MB</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            
            {processedVideos.length > 0 && (
              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem', alignItems: 'center' }}>
                <button 
                  className="btn btn-primary btn-sm" 
                  disabled={selectedProcessed.length === 0}
                  onClick={addProcessedToBatch}
                >
                  ➕ Add {selectedProcessed.length} to Batch
                </button>
                <button 
                  className="btn btn-secondary btn-sm" 
                  disabled={selectedProcessed.length === 0}
                  onClick={() => deleteProcessed(selectedProcessed)}
                  style={{ color: '#fca5a5' }}
                >
                  🗑️ Delete Selected
                </button>
                <div style={{ flex: 1 }}></div>
                <button 
                  className="btn btn-ghost btn-sm" 
                  onClick={() => deleteProcessed(processedVideos.filter(v => !videos.find(sv => sv.isServer && sv.name === v.path)).map(v => v.path))}
                  style={{ color: '#f87171' }}
                >
                  ⚠️ Delete All Available
                </button>
              </div>
            )}
            </div>

            {/* Selected Server Videos */}
            {videos.filter(v => v.isServer).length > 0 && (
              <div style={{ marginTop: '1rem' }}>
                <div style={{ marginBottom: '0.5rem', fontWeight: '500', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                  Selected for Batch Upload
                </div>
                <div style={{ maxHeight: '200px', overflowY: 'auto', background: 'rgba(16,185,129,0.05)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(16,185,129,0.2)' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                    <thead style={{ position: 'sticky', top: 0, background: '#13131A', zIndex: 1 }}>
                      <tr style={{ borderBottom: '1px solid rgba(16,185,129,0.2)', textAlign: 'left', color: 'var(--text-muted)' }}>
                        <th style={{ padding: '0.75rem' }}>Filename</th>
                        <th style={{ padding: '0.75rem', width: '80px', textAlign: 'right' }}>Size</th>
                        <th style={{ padding: '0.75rem', width: '160px', textAlign: 'center' }}>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {videos.filter(v => v.isServer).map(v => (
                        <tr key={v.name} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                          <td style={{ padding: '0.75rem' }}>
                            <div style={{ wordBreak: 'break-all', fontWeight: '500', color: 'var(--accent-cyan)' }}>{v.displayName || v.name}</div>
                          </td>
                          <td style={{ padding: '0.75rem', textAlign: 'right', color: 'var(--text-muted)' }}>{(v.size / (1024*1024)).toFixed(1)} MB</td>
                          <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
                              <button 
                                className="btn btn-ghost btn-sm" 
                                style={{ color: 'var(--accent-cyan)', padding: '0.25rem 0.5rem' }}
                                onClick={() => watchVideo(v.name)}
                                title="Watch Video"
                              >
                                ▶️ Watch
                              </button>
                              <button 
                                className="btn btn-ghost btn-sm" 
                                style={{ color: '#fca5a5', padding: '0.25rem 0.5rem' }}
                                onClick={() => setVideos(prev => prev.filter(pv => pv.name !== v.name))}
                              >
                                Remove
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            </div>
          </div>


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
              
              <div style={{ marginTop: '0.75rem', textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                — OR PASTE JSON BELOW —
              </div>
              
              <textarea
                className="form-textarea"
                placeholder='{"videos": [{"title": "My Video", ...}]}'
                value={metadataText}
                onChange={handleMetadataTextChange}
                rows={6}
                style={{ marginTop: '0.5rem', fontFamily: 'monospace', fontSize: '0.8rem' }}
              />
              
              <div className="tooltip-text" style={{ marginTop: '0.5rem' }}>
                JSON format: <code style={{ color: 'var(--accent-cyan)', fontFamily: 'monospace' }}>{'{"videos": [{title, description, tags, ...}]}'}</code>
              </div>
            </div>
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
      "publish_at": "2024-12-25 10:00:00"
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

      {/* NEW Metadata Preview Section - Wide format */}
      {metadataPreview && (
        <div className="card" style={{ marginTop: '1.5rem', overflowX: 'auto' }}>
          <div className="card-header">
            <div className="card-icon" style={{ background: 'rgba(6,182,212,0.12)' }}>📋</div>
            <div>
              <div className="card-title">Metadata Preview & Editor</div>
              <div className="card-subtitle">
                Found <strong style={{ color: 'var(--accent-cyan)' }}>{metadataPreview.videos?.length || 0} videos</strong> in metadata
              </div>
            </div>
          </div>
          
          <table style={{ width: '100%', minWidth: '900px', borderCollapse: 'collapse', marginTop: '1rem', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', textAlign: 'left', color: 'var(--text-muted)' }}>
                <th style={{ padding: '0.75rem', width: '50px' }}>#</th>
                <th style={{ padding: '0.75rem', width: '30%' }}>Title</th>
                <th style={{ padding: '0.75rem', width: '15%' }}>Privacy</th>
                <th style={{ padding: '0.75rem', width: '15%' }}>Schedule (Optional)</th>
                <th style={{ padding: '0.75rem', width: '20%' }}>Playlist</th>
                <th style={{ padding: '0.75rem', width: '20%' }}>Map Video</th>
              </tr>
            </thead>
            <tbody>
              {metadataPreview.videos?.map((v, i) => (
                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', verticalAlign: 'middle' }}>
                  <td style={{ padding: '0.75rem' }}><strong>{i + 1}.</strong></td>
                  
                  {/* Title */}
                  <td style={{ padding: '0.75rem' }}>
                    <div style={{ fontWeight: '500', color: 'var(--text-primary)', marginBottom: '0.2rem' }}>{v.title}</div>
                  </td>
                  
                  {/* Privacy Status */}
                  <td style={{ padding: '0.75rem' }}>
                    <select 
                      className="form-select" 
                      style={{ padding: '4px 8px', fontSize: '0.8rem', height: 'auto', background: 'rgba(255,255,255,0.05)', color: 'var(--text-primary)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 'var(--radius-sm)', width: '100%' }}
                      value={v.privacy_status || 'public'}
                      onChange={(e) => updateMetadataField(i, 'privacy_status', e.target.value)}
                    >
                      <option value="public">Public</option>
                      <option value="unlisted">Unlisted</option>
                      <option value="private">Private</option>
                    </select>
                  </td>
                  
                  {/* Publish At */}
                  <td style={{ padding: '0.75rem' }}>
                    <input 
                      type="datetime-local" 
                      className="form-input"
                      style={{ padding: '4px 8px', fontSize: '0.8rem', height: 'auto', background: 'rgba(255,255,255,0.05)', color: 'var(--text-primary)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 'var(--radius-sm)', width: '100%' }}
                      value={formatPublishAt(v.publish_at)}
                      onChange={(e) => handleDateChange(i, e.target.value)}
                    />
                  </td>
                  
                  {/* Playlist */}
                  <td style={{ padding: '0.75rem' }}>
                    <select 
                      className="form-select" 
                      style={{ padding: '4px 8px', fontSize: '0.8rem', height: 'auto', background: 'rgba(255,255,255,0.05)', color: 'var(--text-primary)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 'var(--radius-sm)', width: '100%' }}
                      value={v.playlist_names?.[0] || ''}
                      onChange={(e) => updateMetadataField(i, 'playlist_names', e.target.value ? [e.target.value] : [])}
                    >
                      <option value="">-- No Playlist --</option>
                      {playlists.map(p => (
                        <option key={p.id} value={p.title}>{p.title}</option>
                      ))}
                    </select>
                  </td>
                  
                  {/* Map Video Dropdown */}
                  <td style={{ padding: '0.75rem' }}>
                    <select 
                      className="form-select" 
                      style={{ padding: '4px 8px', fontSize: '0.8rem', height: 'auto', background: 'rgba(6,182,212,0.1)', color: 'var(--accent-cyan)', border: 'none', width: '100%' }}
                      value={videoMapping[i] !== undefined ? videoMapping[i] : (videos[i] ? videos[i].name : '')}
                      onChange={(e) => setVideoMapping({ ...videoMapping, [i]: e.target.value })}
                    >
                      <option value="">-- Select Video --</option>
                      {videos.map((vid, vidIdx) => (
                        <option key={vidIdx} value={vid.name}>
                          {vid.isServer ? '☁️' : '📎'} {vid.displayName || vid.name}
                        </option>
                      ))}

                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
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
