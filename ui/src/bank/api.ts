import axios from 'axios';

export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const SESSION_KEY = "mnit_bank_session_id";

function randomId(): string {
  return "session_" + Math.random().toString(36).slice(2, 10);
}

// One session_id per browser tab session. Sent as both user_id and
// session_id so /evaluate's history lookup (filtered by user_id) is scoped
// to this demo run instead of the global "ANONYMOUS"/"DEFAULT" bucket.
export function getSessionId(): string {
  let id = sessionStorage.getItem(SESSION_KEY);
  if (!id) {
    id = randomId();
    sessionStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

export function resetSession(): string {
  const id = randomId();
  sessionStorage.setItem(SESSION_KEY, id);
  return id;
}

export async function evaluate(payload: Record<string, any>, sessionId: string) {
  const res = await axios.post(`${API_BASE}/evaluate`, {
    ...payload,
    user_id: sessionId,
    session_id: sessionId,
  });
  return res.data;
}

export async function getTimeline(sessionId: string, limit = 20) {
  const res = await axios.get(`${API_BASE}/timeline`, { params: { user_id: sessionId, limit } });
  return res.data;
}

export async function runJudgeScenario(name: string) {
  const res = await axios.post(`${API_BASE}/demo/scenarios/${name}/run`);
  return res.data;
}

export async function getHealth() {
  const res = await axios.get(`${API_BASE}/health`);
  return res.data;
}
