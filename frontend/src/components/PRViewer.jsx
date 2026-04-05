export default function PRViewer({ observation, loading }) {
  if (loading) {
    return (
      <div className="pr-viewer">
        <div className="pr-viewer-empty">
          <div className="loading-skeleton">
            <div className="skel-bar skel-bar-header" />
            <div className="skel-bar skel-bar-full" />
            <div className="skel-bar skel-bar-full" />
            <div className="skel-bar skel-bar-mid" />
            <div className="skel-bar skel-bar-full" />
            <div className="skel-bar skel-bar-short" />
          </div>
        </div>
      </div>
    );
  }

  if (!observation) {
    return (
      <div className="pr-viewer">
        <div className="pr-viewer-empty">
          <svg className="empty-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          <h3 className="empty-title">No PR Loaded</h3>
          <p className="empty-desc">Select a task and click "Start Review" to load a pull request for review.</p>
        </div>
      </div>
    );
  }

  const { issue_title, issue_body, summary, changed_files, available_files, latest_event, difficulty } = observation;
  const contentLines = latest_event?.content ? latest_event.content.split('\n') : [];

  return (
    <div className="pr-viewer">
      <div className="pr-file-header">
        <div className="pr-file-name">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          <span>{issue_title}</span>
        </div>
        <div className="pr-file-meta">
          {difficulty && (
            <span className={`diff-badge diff-${difficulty}`}>
              {difficulty}
            </span>
          )}
          {latest_event?.kind && <span className="pr-stat">{latest_event.kind}</span>}
        </div>
      </div>

      <div className="pr-issues-bar">
        <span className="pr-issues-label">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          Review prompt
        </span>
        <div className="pr-issues-tags">
          <span className="issue-chip">{issue_body}</span>
        </div>
      </div>

      <div className="comment-box">
        <label className="comment-label">Episode summary</label>
        <pre className="comment-textarea" style={{ whiteSpace: 'pre-wrap' }}>{summary}</pre>
      </div>

      <div className="pr-issues-bar">
        <span className="pr-issues-label">Changed files</span>
        <div className="pr-issues-tags">
          {changed_files.map((path) => (
            <span key={path} className="issue-chip">{path}</span>
          ))}
        </div>
      </div>

      <div className="pr-issues-bar">
        <span className="pr-issues-label">Available files</span>
        <div className="pr-issues-tags">
          {available_files.map((path) => (
            <span key={path} className="issue-chip">{path}</span>
          ))}
        </div>
      </div>

      <div className="diff-view">
        <table className="diff-table">
          <tbody>
            {contentLines.map((line, i) => {
              let lineClass = 'diff-line';
              if (latest_event?.kind === 'diff' && line.startsWith('+')) lineClass += ' diff-add';
              else if (latest_event?.kind === 'diff' && line.startsWith('-')) lineClass += ' diff-del';
              else if (line.startsWith('@')) lineClass += ' diff-hunk';

              return (
                <tr key={i} className={lineClass}>
                  <td className="diff-ln">{i + 1}</td>
                  <td className="diff-code-cell">
                    <pre>{line || ' '}</pre>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
