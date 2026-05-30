import { useState, useCallback, useRef } from 'react';

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * FileDropzone — drag-and-drop file selector.
 * @param {function} onFiles - called with FileList on file selection
 * @param {boolean} multiple - allow multiple files
 * @param {string} accept - MIME type filter string
 * @param {string} icon - emoji icon
 * @param {string} title - dropzone title
 * @param {string} hint - secondary hint text
 * @param {string} acceptLabel - human-readable accept hint (e.g. "MP4, MOV, AVI")
 * @param {boolean} showList - show the selected file list below
 */
export default function FileDropzone({
  onFiles,
  multiple = false,
  accept = 'video/*',
  icon = '🎬',
  title = 'Drop files here',
  hint = 'or click to browse',
  acceptLabel = '',
  showList = true,
}) {
  const [dragOver, setDragOver] = useState(false);
  const [files, setFiles] = useState([]);
  const inputRef = useRef(null);

  const handleFiles = useCallback(
    (incoming) => {
      const arr = Array.from(incoming);
      setFiles(arr);
      onFiles && onFiles(arr);
    },
    [onFiles]
  );

  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  };

  const onDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const onDragLeave = () => setDragOver(false);

  const onClick = () => inputRef.current?.click();

  const onInputChange = (e) => {
    if (e.target.files?.length) handleFiles(e.target.files);
  };

  const removeFile = (idx) => {
    const updated = files.filter((_, i) => i !== idx);
    setFiles(updated);
    onFiles && onFiles(updated);
  };

  return (
    <div>
      <div
        className={`dropzone ${dragOver ? 'drag-over' : ''}`}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onClick={onClick}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && onClick()}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          style={{ display: 'none' }}
          onChange={onInputChange}
        />
        <div className="dropzone-icon">{icon}</div>
        <div className="dropzone-title">{title}</div>
        <div className="dropzone-hint">{hint}</div>
        {acceptLabel && <div className="dropzone-accept">Accepted: {acceptLabel}</div>}
      </div>

      {showList && files.length > 0 && (
        <div className="file-list">
          {files.map((file, i) => (
            <div className="file-item" key={`${file.name}-${i}`}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', minWidth: 0 }}>
                <span style={{ flexShrink: 0 }}>📄</span>
                <span className="file-item-name">{file.name}</span>
                <span className="file-item-size">{formatSize(file.size)}</span>
              </div>
              <button className="file-item-remove" onClick={(e) => { e.stopPropagation(); removeFile(i); }}>
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
