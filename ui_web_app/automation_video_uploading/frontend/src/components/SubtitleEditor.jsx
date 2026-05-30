import React from 'react';

export default function SubtitleEditor({ transcripts, setTranscripts }) {
  const handleWordChange = (filename, index, newWord) => {
    const newTranscripts = { ...transcripts };
    const targetTranscript = [...newTranscripts[filename]];
    targetTranscript[index] = { ...targetTranscript[index], word: newWord };
    newTranscripts[filename] = targetTranscript;
    setTranscripts(newTranscripts);
  };

  const handleExport = () => {
    const dataStr = JSON.stringify(transcripts, null, 2);
    const blob = new Blob([dataStr], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'transcripts_export.txt';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleImport = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const importedData = JSON.parse(event.target.result);
        setTranscripts(importedData);
      } catch (err) {
        alert('Invalid transcript file format. Must be a valid JSON text file.');
      }
    };
    reader.readAsText(file);
    e.target.value = ''; // Reset input
  };

  if (!transcripts || Object.keys(transcripts).length === 0) {
    return null;
  }

  return (
    <div className="card" style={{ marginTop: '1rem' }}>
      <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <div className="card-icon" style={{ background: 'rgba(59,130,246,0.15)' }}>📝</div>
          <div>
            <div className="card-title">Edit Subtitles</div>
            <div className="card-subtitle">Review and correct the generated transcript for each video.</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn btn-secondary btn-sm" onClick={handleExport}>
            📥 Export (.txt)
          </button>
          <label className="btn btn-secondary btn-sm" style={{ cursor: 'pointer', margin: 0 }}>
            📤 Import (.txt)
            <input type="file" accept=".txt,.json" style={{ display: 'none' }} onChange={handleImport} />
          </label>
        </div>
      </div>
      
      {Object.entries(transcripts).map(([filename, transcript]) => (
        <div key={filename} style={{ marginBottom: '1.5rem' }}>
          <div className="section-label" style={{ marginBottom: '0.5rem' }}>🎬 {filename}</div>
          
          {transcript.length === 0 ? (
            <div style={{ padding: '0.5rem', color: 'var(--text-secondary)' }}>No words found.</div>
          ) : (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', maxHeight: '300px', overflowY: 'auto', padding: '0.5rem', background: 'var(--bg-base)', borderRadius: 'var(--radius-md)' }}>
              {transcript.map((item, i) => (
                <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', textAlign: 'center' }}>{item.start.toFixed(1)}s</span>
                  <input
                    type="text"
                    value={item.word}
                    onChange={(e) => handleWordChange(filename, i, e.target.value)}
                    style={{
                      padding: '0.4rem',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-sm)',
                      background: 'var(--bg-card)',
                      color: 'var(--text-primary)',
                      width: `${Math.max(60, (item.word?.length || 0) * 10 + 20)}px`,
                      textAlign: 'center',
                      fontSize: '0.9rem'
                    }}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
