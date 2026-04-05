import { useState, useCallback } from 'react';
import Header from './components/Header';
import TaskSelector from './components/TaskSelector';
import PRViewer from './components/PRViewer';
import ActionPanel from './components/ActionPanel';
import StateViewer from './components/StateViewer';
import ResultPanel from './components/ResultPanel';
import Toast from './components/Toast';
import { resetTask, stepAction, autoAction } from './services/api';

export default function App() {
  const [selectedTask, setSelectedTask] = useState('');
  const [observation, setObservation] = useState(null);
  const [taskInfo, setTaskInfo] = useState(null);
  const [state, setState] = useState(null);
  const [done, setDone] = useState(false);
  const [score, setScore] = useState(null);
  const [report, setReport] = useState(null);
  const [toast, setToast] = useState(null);
  const [loading, setLoading] = useState(false);
  const [autoPilotRunning, setAutoPilotRunning] = useState(false);

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const handleTaskSelect = (taskName) => {
    setSelectedTask(taskName);
    // Reset display when a new task is chosen
    setObservation(null);
    setTaskInfo(null);
    setState(null);
    setDone(false);
    setScore(null);
    setReport(null);
  };

  const handleStartTask = async () => {
    if (!selectedTask) {
      showToast('Please select a task first', 'error');
      return;
    }
    setLoading(true);
    try {
      const data = await resetTask(selectedTask);
      setObservation(data.observation);
      setTaskInfo({
        task_id: data.task_id,
        difficulty: data.difficulty,
        description: data.description,
        issue_title: data.issue_title,
        issue_body: data.issue_body,
      });
      setDone(false);
      setScore(null);
      setReport(null);
      setState(data.state);
      showToast(`Task "${data.task_id}" loaded — ${data.issue_title}`, 'success');
    } catch (err) {
      const msg = err.response?.data?.error || 'Failed to start task';
      showToast(msg, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleAction = useCallback(async (actionType, payload) => {
    try {
      const data = await stepAction(actionType, payload);
      setObservation(data.observation);
      setState(data.state);
      setDone(data.done);

      if (data.done) {
        setScore(data.score);
        setReport(data.report);
        const status = data.report?.grade_status || '';
        showToast(
          `Episode finished! Score: ${(data.score * 100).toFixed(1)}% — ${status}`,
          status === 'PASS' ? 'success' : 'error'
        );
      } else {
        const suffix = payload?.path || payload?.text || actionType;
        showToast(
          `${suffix} — reward: ${data.reward?.toFixed(4)}`,
          'info'
        );
      }
    } catch (err) {
      const msg = err.response?.data?.error || 'Action failed';
      showToast(msg, 'error');
    }
  }, []);

  const handleAutoPilot = async () => {
    if (done || autoPilotRunning) return;
    setAutoPilotRunning(true);
    showToast('Auto-pilot started...', 'info');

    let episodeDone = false;
    let iterations = 0;
    const maxIterations = 15;

    while (!episodeDone && iterations < maxIterations) {
      iterations++;
      try {
        const data = await autoAction();
        setObservation(data.observation);
        setState(data.state);
        setDone(data.done);
        episodeDone = data.done;

        if (data.done) {
          setScore(data.score);
          setReport(data.report);
          const status = data.report?.grade_status || '';
          showToast(
            `Auto-pilot finished! Score: ${(data.score * 100).toFixed(1)}% — ${status}`,
            status === 'PASS' ? 'success' : 'error'
          );
        }
      } catch (err) {
        const msg = err.response?.data?.error || 'Auto-pilot failed';
        showToast(msg, 'error');
        break;
      }
    }

    setAutoPilotRunning(false);
  };

  return (
    <div className="app">
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}

      <Header taskInfo={taskInfo} done={done} />

      <div className="toolbar">
        <TaskSelector
          onSelect={handleTaskSelect}
          onStart={handleStartTask}
          disabled={loading || autoPilotRunning}
          loading={loading}
          selectedTask={selectedTask}
        />
        {observation && !done && (
          <button
            className={`btn btn-autopilot ${autoPilotRunning ? 'running' : ''}`}
            onClick={handleAutoPilot}
            disabled={autoPilotRunning || done}
          >
            {autoPilotRunning ? (
              <><span className="btn-spinner" /> Auto-Pilot Running...</>
            ) : (
              <><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2a4 4 0 0 1 4 4c0 1.95-1.4 3.57-3.25 3.92A2 2 0 0 0 11 11.91V14"/><circle cx="12" cy="18" r="2"/><path d="M7 10.5A6.5 6.5 0 0 1 12 4"/><path d="M17 10.5A6.5 6.5 0 0 0 12 4"/></svg> Auto-Pilot</>
            )}
          </button>
        )}
        {taskInfo && (
          <div className="toolbar-info">
            <span className="toolbar-issues">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                  {taskInfo.issue_title}
            </span>
          </div>
        )}
      </div>

      <main className="main-content">
        <section className="panel-left">
          <PRViewer observation={observation} loading={loading} />
        </section>
        <section className="panel-right">
          <ActionPanel observation={observation} onAction={handleAction} disabled={!observation || done} done={done} />
          <StateViewer state={state} done={done} taskInfo={taskInfo} />
          <ResultPanel score={score} report={report} />
        </section>
      </main>
    </div>
  );
}
