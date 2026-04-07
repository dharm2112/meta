import { useState, useEffect } from 'react';
import { fetchTasks } from '../services/api';

export default function TaskSelector({ onSelect, onStart, disabled, loading, selectedTask, refreshKey = 0 }) {
  const [tasks, setTasks] = useState([]);
  const [fetchLoading, setFetchLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setFetchLoading(true);
    fetchTasks()
      .then((data) => {
        setTasks(data.tasks || []);
        setFetchLoading(false);
      })
      .catch(() => {
        setError('Failed to load tasks');
        setFetchLoading(false);
      });
  }, [refreshKey]);

  const handleSelect = (e) => {
    const val = e.target.value;
    if (val && onSelect) onSelect(val);
  };

  return (
    <div className="task-bar">
      <div className="task-bar-group">
        <label className="task-bar-label">Task</label>
        {fetchLoading ? (
          <div className="task-loading-pill">
            <span className="loading-dot" />
            Loading tasks...
          </div>
        ) : error ? (
          <div className="task-error-pill">{error}</div>
        ) : (
          <select
            className="task-select"
            value={selectedTask}
            onChange={handleSelect}
            disabled={disabled}
          >
            <option value="">Select difficulty...</option>
            {tasks.map((t) => (
              <option key={t.id} value={t.id}>
                {t.icon} {t.label} — {t.issue_title}
              </option>
            ))}
          </select>
        )}
      </div>
      <button
        className="btn btn-primary btn-start"
        onClick={onStart}
        disabled={!selectedTask || loading || disabled}
      >
        {loading ? (
          <>
            <span className="btn-spinner" />
            Starting...
          </>
        ) : (
          <>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            Start Review
          </>
        )}
      </button>
    </div>
  );
}
