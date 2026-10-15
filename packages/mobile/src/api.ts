import axios from "axios";
import { API_BASE } from "./constants";

export const api = axios.create({ baseURL: API_BASE });

export function setAuthToken(token: string | null) {
  if (token) api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  else delete api.defaults.headers.common["Authorization"];
}

export interface Session {
  id: string;
  title: string;
  createdAt: string;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
}

export async function login(email: string, password: string) {
  const res = await api.post("/auth/login", { email, password });
  return res.data.token as string;
}

export async function register(email: string, password: string, name: string) {
  const res = await api.post("/auth/register", { email, password, name });
  return res.data.token as string;
}

export async function getSessions(): Promise<Session[]> {
  const res = await api.get("/api/chat/sessions");
  return res.data.sessions ?? [];
}

export async function getSession(id: string): Promise<Message[]> {
  const res = await api.get(`/api/chat/sessions/${id}`);
  return res.data.messages ?? [];
}

export async function deleteSession(id: string): Promise<void> {
  await api.delete(`/api/chat/sessions/${id}`);
}

// ── Coworker ────────────────────────────────────────────────────────────────

export interface CoworkerAction {
  id: number;
  type: string;
  label: string;
  status: string;
  title: string;
  payload: Record<string, any>;
  reasoning: string;
  approvalReason: string;
  risks: { code: string; message: string }[];
  createdAt: string;
}

export async function getCoworkerStatus(): Promise<{ exists: boolean; status?: string; pending?: number; attention?: number }> {
  return (await api.get("/api/coworker/status")).data;
}

export async function getPendingActions(): Promise<CoworkerAction[]> {
  return (await api.get("/api/coworker/actions", { params: { status: "proposed" } })).data.actions ?? [];
}

export async function approveAction(id: number, payload?: Record<string, any>): Promise<CoworkerAction> {
  return (await api.post(`/api/coworker/actions/${id}/approve`, payload ? { payload } : {})).data.action;
}

export async function rejectAction(id: number, feedback = ""): Promise<CoworkerAction> {
  return (await api.post(`/api/coworker/actions/${id}/reject`, { feedback })).data.action;
}

export async function setCoworkerPaused(paused: boolean): Promise<void> {
  await api.post(paused ? "/api/coworker/pause" : "/api/coworker/resume", { reason: "Kill switch (mobile)" });
}

export async function tickCoworker(): Promise<void> {
  await api.post("/api/coworker/tick", {});
}

export async function getDigest(): Promise<{ headline: string; attention: string[] }> {
  return (await api.get("/api/coworker/digest")).data;
}
