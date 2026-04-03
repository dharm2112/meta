import { useState } from 'react';

export default function ActionPanel({ onAction, disabled, done }) {
  const [comment, setComment] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeAction, setActiveAction] = useState(null);

  const handleAction = async (actionType) => {
    if (disabled || loading) return;
    setLoading(true);
    setActiveAction(actionType);
    try {
      await onAction(actionType, actionType === 'comment_issue' ? comment : '');
      if (actionType === 'comment_issue') setComment('');
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
          className={`action-btn action-view ${activeAction === 'view_file' ? 'loading' : ''}`}
          onClick={() => handleAction('view_file')}
          disabled={isDisabled}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          <span>View File</span>
        </button>
        <button
          className={`action-btn action-approve ${activeAction === 'approve_pr' ? 'loading' : ''}`}
          onClick={() => handleAction('approve_pr')}
          disabled={isDisabled}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
          <span>Approve</span>
        </button>
        <button
          className={`action-btn action-request ${activeAction === 'request_changes' ? 'loading' : ''}`}
          onClick={() => handleAction('request_changes')}
          disabled={isDisabled}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
          <span>Request Changes</span>
        </button>
      </div>

      <div className="comment-box">
        <label className="comment-label">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          Comment on Issue
        </label>
        <textarea
          className="comment-textarea"
          rows={3}
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Describe the issue you found in the code..."
          disabled={isDisabled}
        />
        <button
          className={`btn btn-submit-comment ${activeAction === 'comment_issue' ? 'loading' : ''}`}
          onClick={() => handleAction('comment_issue')}
          disabled={isDisabled || !comment.trim()}
        >
          {activeAction === 'comment_issue' ? (
            <><span className="btn-spinner" /> Submitting...</>
          ) : (
            <><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg> Submit Comment</>
          )}
        </button>
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
