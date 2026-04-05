import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

export async function fetchTasks() {
  const res = await api.get('/api/tasks');
  return res.data;
}

export async function resetTask(taskName) {
  const res = await api.post(`/api/reset/${taskName}`);
  return res.data;
}

export async function stepAction(actionType, payload = {}) {
  const res = await api.post('/api/step', { action_type: actionType, ...payload });
  return res.data;
}

export async function fetchState() {
  const res = await api.get('/api/state');
  return res.data;
}

export async function autoAction() {
  const res = await api.post('/api/auto_action');
  return res.data;
}

export default api;
