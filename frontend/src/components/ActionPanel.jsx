import { useEffect, useState } from 'react';

export default function ActionPanel({ observation, onAction, disabled, done }) {
  const [text, setText] = useState('');
  const [diffPath, setDiffPath] = useState('');
  const [filePath, setFilePath] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeAction, setActiveAction] = useState(null);

  useEffect(() => {
    setDiffPath(observation?.changed_files?.[0] || '');
    setFilePath(observation?.available_files?.[0] || '');
  }, [observation]);

  const handleAction = async (actionType) => {
    if (disabled || loading) return;

    const payload = {};
    if (actionType === 'inspect_diff') payload.path = diffPath;
    if (actionType === 'inspect_file') payload.path = filePath;
    if (['comment', 'approve', 'reject', 'escalate'].includes(actionType)) payload.text = text;

    setLoading(true);
    setActiveAction(actionType);
    try {
      await onAction(actionType, payload);
      if (['comment', 'approve', 'reject', 'escalate'].includes(actionType)) setText('');
    } finally {
      setLoading(false);
      setActiveAction(null);
    }
  };

  const isDisabled = disabled || loading || done;

  return (
    <div className="card actions-card">
      <div className="card-header">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
        <span>Review Actions</span>
      </div>

      <div className="actions-grid">
        <button
          className={`action-btn action-view ${activeAction === 'inspect_diff' ? 'loading' : ''}`}
          onClick={() => handleAction('inspect_diff')}
          disabled={isDisabled || !diffPath}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          <span>Inspect Diff</span>
        </button>
        <button
          className={`action-btn action-view ${activeAction === 'inspect_file' ? 'loading' : ''}`}
          onClick={() => handleAction('inspect_file')}
          disabled={isDisabled || !filePath}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          <span>Inspect File</span>
        </button>
        <button
          className={`action-btn action-approve ${activeAction === 'approve' ? 'loading' : ''}`}
          onClick={() => handleAction('approve')}
          disabled={isDisabled || !text.trim()}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
          <span>Approve</span>
        </button>
        <button
          className={`action-btn action-request ${activeAction === 'reject' ? 'loading' : ''}`}
          onClick={() => handleAction('reject')}
          disabled={isDisabled || !text.trim()}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
          <span>Reject</span>
        </button>
      </div>

      <div className="comment-box">
        <label className="comment-label">Diff path</label>
        <select className="task-select" value={diffPath} onChange={(e) => setDiffPath(e.target.value)} disabled={isDisabled || !observation?.changed_files?.length}>
          {(observation?.changed_files || []).map((path) => (
            <option key={path} value={path}>{path}</option>
          ))}
        </select>
      </div>

      <div className="comment-box">
        <label className="comment-label">File path</label>
        <select className="task-select" value={filePath} onChange={(e) => setFilePath(e.target.value)} disabled={isDisabled || !observation?.available_files?.length}>
          {(observation?.available_files || []).map((path) => (
            <option key={path} value={path}>{path}</option>
          ))}
        </select>
      </div>

      <div className="comment-box">
        <label className="comment-label">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          Comment or Decision Reason
        </label>
        <textarea
          className="comment-textarea"
          rows={3}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Describe the issue, approval reason, rejection reason, or escalation rationale..."
          disabled={isDisabled}
        />
        <div className="actions-grid">
          <button
            className={`btn btn-submit-comment ${activeAction === 'comment' ? 'loading' : ''}`}
            onClick={() => handleAction('comment')}
            disabled={isDisabled || !text.trim()}
          >
            {activeAction === 'comment' ? (
              <><span className="btn-spinner" /> Submitting...</>
            ) : (
              <><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg> Comment</>
            )}
          </button>
          <button
            className={`action-btn action-request ${activeAction === 'escalate' ? 'loading' : ''}`}
            onClick={() => handleAction('escalate')}
            disabled={isDisabled || !text.trim()}
          >
            {activeAction === 'escalate' ? (
            <><span className="btn-spinner" /> Submitting...</>
          ) : (
            <><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 8v4"/><path d="M12 16h.01"/><circle cx="12" cy="12" r="10"/></svg> Escalate</>
          )}
          </button>
        </div>
      </div>

      {done && (
        <div className="actions-done-overlay">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
          Review session completed
        </div>
      )}
    </div>
  );
}
