import { useState, useRef } from 'react';
import { uploadCode } from '../services/api';

export default function UploadPanel({ onUploadComplete, disabled }) {
  const [isOpen, setIsOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [files, setFiles] = useState([]);
  const [originalFiles, setOriginalFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  
  const fileInputRef = useRef(null);
  const originalInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    const droppedFiles = [...e.dataTransfer.files];
    setFiles(prev => [...prev, ...droppedFiles]);
  };

  const handleFileSelect = (e) => {
    const selectedFiles = [...e.target.files];
    setFiles(prev => [...prev, ...selectedFiles]);
  };

  const handleOriginalSelect = (e) => {
    const selectedFiles = [...e.target.files];
    setOriginalFiles(prev => [...prev, ...selectedFiles]);
  };

  const removeFile = (index, isOriginal = false) => {
    if (isOriginal) {
      setOriginalFiles(prev => prev.filter((_, i) => i !== index));
    } else {
      setFiles(prev => prev.filter((_, i) => i !== index));
    }
  };

  const handleSubmit = async () => {
    if (!title.trim()) {
      setError('Title is required');
      return;
    }
    if (!description.trim()) {
      setError('Description is required');
      return;
    }
    if (files.length === 0) {
      setError('At least one file is required');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const result = await uploadCode(title, description, files, originalFiles);
      
      // Reset form
      setTitle('');
      setDescription('');
      setFiles([]);
      setOriginalFiles([]);
      setIsOpen(false);
      
      // Notify parent
      if (onUploadComplete) {
        onUploadComplete(result);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleClear = () => {
    setTitle('');
    setDescription('');
    setFiles([]);
    setOriginalFiles([]);
    setError(null);
  };

  const handleClose = () => {
    setIsOpen(false);
    setError(null);
  };

  return (
    <>
      <button
        className="btn btn-upload-toggle"
        onClick={() => setIsOpen(true)}
        disabled={disabled}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
        Upload Code
      </button>

      {isOpen && (
        <div className="upload-modal-overlay" onClick={handleClose}>
          <div className="upload-modal" onClick={(e) => e.stopPropagation()}>
            <div className="upload-modal-header">
              <h3>📤 Upload Custom Code for Review</h3>
              <button className="btn btn-icon" onClick={handleClose} title="Close">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>

            <div className="upload-modal-body">
              <div className="upload-form-row">
                <div className="form-group">
                  <label>PR / Issue Title *</label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g., Fix authentication bug in login handler"
                    disabled={uploading}
                  />
                </div>
              </div>

              <div className="upload-form-row">
                <div className="form-group">
                  <label>Description *</label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Describe what this PR/code change is about..."
                    rows={2}
                    disabled={uploading}
                  />
                </div>
              </div>

              <div className="upload-form-columns">
                <div className="form-group">
                  <label>Modified Files * (drag & drop)</label>
                  <div
                    className={`drop-zone ${dragActive ? 'active' : ''}`}
                    onDragEnter={handleDrag}
                    onDragLeave={handleDrag}
                    onDragOver={handleDrag}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      multiple
                      onChange={handleFileSelect}
                      style={{ display: 'none' }}
                    />
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                      <polyline points="17 8 12 3 7 8"/>
                      <line x1="12" y1="3" x2="12" y2="15"/>
                    </svg>
                    <span>Drop files or click</span>
                  </div>
                  {files.length > 0 && (
                    <div className="file-list">
                      {files.map((file, i) => (
                        <div key={i} className="file-item">
                          <span className="file-name">📄 {file.name}</span>
                          <button className="btn btn-icon-sm" onClick={() => removeFile(i)}>×</button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="form-group">
                  <label>Original Files (optional)</label>
                  <div
                    className="drop-zone drop-zone-secondary"
                    onClick={() => originalInputRef.current?.click()}
                  >
                    <input
                      ref={originalInputRef}
                      type="file"
                      multiple
                      onChange={handleOriginalSelect}
                      style={{ display: 'none' }}
                    />
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14 2 14 8 20 8"/>
                    </svg>
                    <span>For diff generation</span>
                  </div>
                  {originalFiles.length > 0 && (
                    <div className="file-list file-list-original">
                      {originalFiles.map((file, i) => (
                        <div key={i} className="file-item">
                          <span className="file-name">📋 {file.name}</span>
                          <button className="btn btn-icon-sm" onClick={() => removeFile(i, true)}>×</button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {error && <div className="upload-error">{error}</div>}
            </div>

            <div className="upload-modal-footer">
              <button
                className="btn btn-secondary"
                onClick={handleClear}
                disabled={uploading}
              >
                Clear
              </button>
              <button
                className="btn btn-primary"
                onClick={handleSubmit}
                disabled={uploading || files.length === 0}
              >
                {uploading ? (
                  <>
                    <span className="btn-spinner" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                      <polyline points="17 8 12 3 7 8"/>
                      <line x1="12" y1="3" x2="12" y2="15"/>
                    </svg>
                    Upload & Create Task
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
