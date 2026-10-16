import axios from 'axios';
import { API_BASE_URL } from '../constants/constants';

const BASE = `${API_BASE_URL}/api/coworker`;

export function coworkerApi(token: string | null) {
  const headers = { Authorization: `Bearer ${token}` };
  const get = async <T = any>(path: string, params?: Record<string, any>): Promise<T> =>
    (await axios.get(`${BASE}${path}`, { headers, params })).data;
  const post = async <T = any>(path: string, body: any = {}): Promise<T> =>
    (await axios.post(`${BASE}${path}`, body, { headers })).data;
  const patch = async <T = any>(path: string, body: any = {}): Promise<T> =>
    (await axios.patch(`${BASE}${path}`, body, { headers })).data;
  const put = async <T = any>(path: string, body: any = {}): Promise<T> =>
    (await axios.put(`${BASE}${path}`, body, { headers })).data;
  const del = async <T = any>(path: string): Promise<T> =>
    (await axios.delete(`${BASE}${path}`, { headers })).data;
  const upload = async <T = any>(path: string, form: FormData): Promise<T> =>
    (await axios.post(`${BASE}${path}`, form, { headers })).data;
  return { get, post, patch, put, del, upload, base: BASE, headers };
}

export function errorMessage(err: any, fallback = 'Something went wrong.'): string {
  return err?.response?.data?.error || err?.message || fallback;
}

/** Stream a coworker chat turn. Calls `onEvent` for each SSE payload. */
export async function streamCoworkerChat(
  token: string | null,
  body: { message: string; session_id?: string },
  onEvent: (event: any) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    let msg = 'Your coworker could not respond.';
    try {
      msg = (await res.json()).error || msg;
    } catch {}
    throw new Error(msg);
  }
  if (!res.body) throw new Error('No response body');
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      let event: any;
      try {
        event = JSON.parse(line.slice(6));
      } catch {
        continue;
      }
      onEvent(event);
    }
  }
}

/** Assistant messages embed tool/action markers as `:::cw {json}` lines. */
export type Segment =
  | { kind: 'text'; text: string }
  | { kind: 'tool'; name: string; summary: string }
  | { kind: 'action'; id: number }
  | { kind: 'brief'; title: string }
  | { kind: 'meeting'; id: number };

export function parseSegments(content: string): Segment[] {
  const segments: Segment[] = [];
  let text: string[] = [];
  const flush = () => {
    const joined = text.join('\n').trim();
    if (joined) segments.push({ kind: 'text', text: joined });
    text = [];
  };
  for (const line of content.split('\n')) {
    if (line.startsWith(':::cw ')) {
      try {
        const data = JSON.parse(line.slice(6));
        flush();
        if (data.t === 'tool') segments.push({ kind: 'tool', name: data.name, summary: data.summary });
        else if (data.t === 'action') segments.push({ kind: 'action', id: Number(data.id) });
        else if (data.t === 'brief') segments.push({ kind: 'brief', title: data.title || '' });
        else if (data.t === 'meeting') segments.push({ kind: 'meeting', id: Number(data.id) });
        continue;
      } catch {}
    }
    text.push(line);
  }
  flush();
  return segments;
}

export function marker(data: Record<string, any>): string {
  return `\n:::cw ${JSON.stringify(data)}\n`;
}

export function timeAgo(iso?: string | null): string {
  if (!iso) return '';
  const then = new Date(iso).getTime();
  const diff = Date.now() - then;
  const future = diff < 0;
  const mins = Math.round(Math.abs(diff) / 60000);
  const fmt = (n: number, unit: string) => (future ? `in ${n}${unit}` : `${n}${unit} ago`);
  if (mins < 1) return 'just now';
  if (mins < 60) return fmt(mins, 'm');
  const hours = Math.round(mins / 60);
  if (hours < 24) return fmt(hours, 'h');
  return fmt(Math.round(hours / 24), 'd');
}
