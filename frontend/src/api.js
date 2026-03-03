import axios from "axios";

const DEFAULT_ORIGIN =
  (typeof window !== "undefined" && window.location.origin.replace(/:\d+$/, ":5000")) ||
  "http://127.0.0.1:5000";
const CONFIG_ORIGIN = (import.meta.env.VITE_API_ORIGIN || DEFAULT_ORIGIN).replace(/\/$/, "");
export const API_ORIGIN = CONFIG_ORIGIN;
export const API_BASE = `${API_ORIGIN}/api`;

const USER_ID_KEY = "access_agent_user_id";

export function getUserId() {
  if (typeof window === "undefined") {
    return null;
  }
  let userId = window.localStorage.getItem(USER_ID_KEY);
  if (!userId) {
    const rand = Math.random().toString(36).slice(2, 8);
    userId = `u_${Date.now()}_${rand}`;
    window.localStorage.setItem(USER_ID_KEY, userId);
  }
  return userId;
}

export async function sendChatMessage(message, sessionId = null) {
  const userId = getUserId();
  const res = await axios.post(`${API_BASE}/chat`, { message, sessionId, userId });
  return res.data;
}

export async function health() {
  const res = await axios.get(`${API_BASE}/health`);
  return res.data;
}

export async function createSession(title = "\u65b0\u5bf9\u8bdd") {
  const res = await axios.post(`${API_BASE}/sessions`, { title });
  return res.data;
}

export async function listSessions() {
  const res = await axios.get(`${API_BASE}/sessions`);
  return res.data.sessions || [];
}

export async function getSessionMessages(sessionId) {
  const res = await axios.get(`${API_BASE}/sessions/${sessionId}/messages`);
  return res.data.messages || [];
}

export async function updateSessionTitle(sessionId, title) {
  const res = await axios.put(`${API_BASE}/sessions/${sessionId}`, { title });
  return res.data;
}

export async function deleteSession(sessionId) {
  const res = await axios.delete(`${API_BASE}/sessions/${sessionId}`);
  return res.data;
}

export default { sendChatMessage, health, createSession, listSessions, getSessionMessages, updateSessionTitle, deleteSession };
