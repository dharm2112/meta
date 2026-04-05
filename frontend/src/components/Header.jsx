export default function Header({ taskInfo, done }) {
  return (
    <header className="header">
      <div className="header-left">
        <div className="header-logo">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
            <polyline points="10 9 9 9 8 9" />
          </svg>
        </div>
        <div>
          <h1 className="header-title">Code Review Assistant</h1>
          <p className="header-sub">Deterministic Offline PR Review Environment</p>
        </div>
      </div>
      <div className="header-right">
        {taskInfo && (
          <div className="header-task-info">
            <span className={`diff-badge diff-${taskInfo.difficulty}`}>
              {taskInfo.difficulty.toUpperCase()}
            </span>
            <span className="header-task-name">{taskInfo.issue_title}</span>
            <span className={`status-dot ${done ? 'completed' : 'active'}`} />
            <span className="header-status-text">{done ? 'Completed' : 'Active'}</span>
          </div>
        )}
        {!taskInfo && (
          <span className="header-no-session">No active session</span>
        )}
      </div>
    </header>
  );
}
