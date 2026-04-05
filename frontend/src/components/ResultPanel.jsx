export default function ResultPanel({ score, report }) {
  if (score === null || score === undefined) return null;

  const passed = report?.grade_status === 'PASS';
  const pct = Math.round(score * 100);
  const circumference = 2 * Math.PI * 44;
  const strokeDash = (pct / 100) * circumference;

  return (
    <div className={`card result-card ${passed ? 'result-pass' : 'result-fail'}`}>
      <div className="card-header">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
        <span>Review Result</span>
        <span className={`result-status-badge ${passed ? 'badge-pass' : 'badge-fail'}`}>
          {passed ? 'PASSED' : 'FAILED'}
        </span>
      </div>

      <div className="result-body">
        <div className="score-circle-wrap">
          <svg className="score-circle" viewBox="0 0 100 100">
            <circle className="score-track" cx="50" cy="50" r="44" fill="none" strokeWidth="6" />
            <circle
              className={`score-progress ${passed ? 'progress-pass' : 'progress-fail'}`}
              cx="50" cy="50" r="44" fill="none" strokeWidth="6"
              strokeDasharray={`${strokeDash} ${circumference}`}
              strokeLinecap="round"
              transform="rotate(-90 50 50)"
            />
          </svg>
          <div className="score-inner">
            <span className="score-pct">{pct}</span>
            <span className="score-pct-sign">%</span>
          </div>
        </div>

        {report && (
          <div className="result-details">
            <div className="result-detail-row">
              <span className="detail-label">Evidence</span>
              <div className="detail-bar-wrap">
                <div className="detail-bar" style={{width: `${report.evidence_score * 100}%`}} />
              </div>
              <span className="detail-val">{(report.evidence_score * 100).toFixed(0)}%</span>
            </div>
            <div className="result-detail-row">
              <span className="detail-label">Issue ID</span>
              <div className="detail-bar-wrap">
                <div className="detail-bar" style={{width: `${report.issue_identification_score * 100}%`}} />
              </div>
              <span className="detail-val">{(report.issue_identification_score * 100).toFixed(0)}%</span>
            </div>
            <div className="result-detail-row">
              <span className="detail-label">Decision</span>
              <span className={`detail-val ${report.decision_correct ? 'val-pass' : 'val-fail'}`}>
                {report.submitted_decision || 'none'} / {report.correct_decision}
              </span>
            </div>
            <div className="result-detail-row">
              <span className="detail-label">Relevant</span>
              <span className="detail-val detail-val-list">{report.relevant_files?.join(', ')}</span>
            </div>
            <div className="result-detail-row">
              <span className="detail-label">Keywords</span>
              <span className="detail-val detail-val-list">{report.keyword_hits?.length > 0 ? report.keyword_hits.join(', ') : 'None'}</span>
            </div>
            <div className="result-detail-row">
              <span className="detail-label">Penalties</span>
              <span className="detail-val detail-val-list">{report.penalties?.toFixed?.(2) ?? report.penalties}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
