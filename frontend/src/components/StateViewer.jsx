export default function StateViewer({ state, done, taskInfo }) {
  return (
    <div className="card session-card">
      <div className="card-header">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
        <span>Session Info</span>
      </div>

      {!state && !taskInfo ? (
        <div className="session-empty">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          <p>Waiting for a review session to start...</p>
        </div>
      ) : (
        <>
          {taskInfo && (
            <div className="session-task-row">
              <span className="session-task-label">Task</span>
              <span className={`diff-badge diff-${taskInfo.difficulty}`}>{taskInfo.difficulty}</span>
              <span className="session-task-desc">{taskInfo.description}</span>
            </div>
          )}

          <div className="stats-row">
            <div className="stat-box">
              <span className="stat-number">{state?.current_step ?? 0}</span>
              <span className="stat-label">Steps</span>
            </div>
            <div className="stat-box">
              <span className="stat-number stat-reward">{state?.total_reward?.toFixed(2) ?? '0.00'}</span>
              <span className="stat-label">Reward</span>
            </div>
            <div className="stat-box">
              <span className={`stat-number ${done ? 'stat-done' : 'stat-active'}`}>
                {done ? 'Done' : state ? 'Active' : '—'}
              </span>
              <span className="stat-label">Status</span>
            </div>
          </div>

          {state?.actions_taken && state.actions_taken.length > 0 && (
            <div className="history-section">
              <div className="history-header">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
                Action Timeline
              </div>
              <div className="history-timeline">
                {state.actions_taken.map((a, i) => (
                  <div key={i} className="timeline-item">
                    <div className={`timeline-dot dot-${a.action_type}`} />
                    <div className="timeline-content">
                      <div className="timeline-top">
                        <span className={`action-chip chip-${a.action_type}`}>
                          {a.action_type.replace(/_/g, ' ')}
                        </span>
                        <span className="timeline-step">Step {a.step}</span>
                      </div>
                      {a.comment && (
                        <p className="timeline-comment">{a.comment}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {state?.actions_taken?.length === 0 && (
            <div className="history-empty">
              <p>No actions taken yet. Use the panel above to start reviewing.</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
