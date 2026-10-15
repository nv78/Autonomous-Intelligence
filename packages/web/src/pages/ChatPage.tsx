import axios from 'axios';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import remarkGfm from 'remark-gfm';
import { useAuth, useModel } from '../App';
import DocThumbnail from '../components/DocThumbnail';
import FileViewerModal from '../components/FileViewerModal';
import OnboardingTour from '../components/OnboardingTour';
import OurogenLogo from '../components/OurogenLogo';
import UserMenu from '../components/UserMenu';
import { API_BASE_URL } from '../constants/constants';
import { marker, streamCoworkerChat } from '../coworker/api';
import CoworkerMessage from '../coworker/CoworkerMessage';
import { useCoworker } from '../coworker/CoworkerContext';
import HeaderControls from '../coworker/HeaderControls';
import TodaySidebar from '../coworker/TodaySidebar';

const DELEGATE_PROMPTS = [
  { title: 'Reply to my unanswered emails', prompt: 'Reply to my unanswered emails' },
  { title: 'Take my call with Dana', prompt: 'Join my call with Dana and pitch the pilot, then send me the summary' },
  { title: 'What did you do today?', prompt: 'What did you do today?' },
  { title: "What's going on with Acme?", prompt: "What's going on with Acme?" },
  { title: 'Prep me for my next meeting', prompt: 'Prep me for my next meeting' },
  { title: 'Handle inbound leads', prompt: 'From now on, handle first replies to inbound sales leads' },
];

const LIVE_PROMPTS = [
  { title: 'Reply to my unanswered emails', prompt: 'Reply to my unanswered emails' },
  { title: 'Join my next meeting', prompt: 'Join my next meeting, take notes, and send me the summary' },
  { title: 'What did you do today?', prompt: 'What did you do today?' },
  { title: 'Prep me for my next meeting', prompt: 'Prep me for my next meeting' },
  { title: "What's on my calendar?", prompt: "What's on my calendar this week?" },
  { title: 'Handle inbound leads', prompt: 'From now on, handle first replies to inbound sales leads' },
];

interface Message {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt?: string;
  variants?: string[];
  activeVariantIndex?: number;
}

interface Session {
  id: string;
  title: string;
  createdAt: string;
}

interface UploadItem {
  id: string;
  file: File;
  name: string;
  step: 'uploading' | 'extracting' | 'indexing' | 'done' | 'error';
  pct: number;
  error?: string;
}

interface AttachedDoc {
  id: string;
  filename: string;
}

interface ChatSearchResult {
  id: string;
  title: string;
  snippet: string | null;
}

const ACCEPTED_TYPES = [
  'application/pdf',
  'text/plain',
  'text/markdown',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
];
const ACCEPTED_LABEL = 'PDF, DOCX, TXT, MD';
const ACCEPTED_EXT = '.pdf,.docx,.txt,.md';
const MAX_FILES = 10;
const MAX_SIZE_MB = 50;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

function UploadRing({ step, pct }: { step: UploadItem['step']; pct: number }) {
  if (step === 'error') {
    return (
      <span className="w-5 h-5 rounded-full bg-red-100 dark:bg-red-950/40 text-red-500 text-xs font-bold flex items-center justify-center flex-shrink-0">
        !
      </span>
    );
  }
  if (step === 'done') {
    return (
      <span className="w-5 h-5 rounded-full bg-green-500 text-white flex items-center justify-center flex-shrink-0">
        <svg
          className="w-3 h-3"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={3}
            d="M5 13l4 4L19 7"
          />
        </svg>
      </span>
    );
  }
  const size = 20;
  const stroke = 2.5;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.min(100, Math.max(0, pct));
  const offset = circumference * (1 - clamped / 100);
  return (
    <svg width={size} height={size} className="flex-shrink-0 -rotate-90">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={stroke}
        className="text-gray-200 dark:text-gray-600"
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={stroke}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        className="text-gray-900 dark:text-white transition-all duration-300"
      />
    </svg>
  );
}

export default function ChatPage() {
  const { id: sessionId } = useParams<{ id: string }>();
  const nav = useNavigate();
  const { token } = useAuth();
  const { model } = useModel();
  const { coworker, status: coworkerStatus, putActions, loaded: coworkerLoaded, version: coworkerVersion } = useCoworker();
  const [assistantMode, setAssistantMode] = useState(() => localStorage.getItem('chat_mode') === 'assistant');
  const coworkerMode = !!coworker && !assistantMode;
  const toggleMode = () => {
    const next = !assistantMode;
    setAssistantMode(next);
    localStorage.setItem('chat_mode', next ? 'assistant' : 'coworker');
  };

  const [sessions, setSessions] = useState<Session[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  // Deep link with a prepared delegation, e.g. "Send my coworker" from the Today view.
  const [searchParams, setSearchParams] = useSearchParams();
  useEffect(() => {
    const prompt = searchParams.get('prompt');
    if (!prompt) return;
    setInput(prompt);
    setSearchParams({}, { replace: true });
  }, [searchParams.get('prompt')]);
  const [streaming, setStreaming] = useState(false);
  useEffect(() => { streamingRef.current = streaming; }, [streaming]);
  const [regeneratingIndex, setRegeneratingIndex] = useState<number | null>(
    null,
  );
  const [sidebarOpen, setSidebarOpen] = useState(() => window.innerWidth >= 768);
  const [dragging, setDragging] = useState(false);
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const [deleteTarget, setDeleteTarget] = useState<Session | null>(null);
  const [chatDocs, setChatDocs] = useState<AttachedDoc[]>([]);
  const [docsModalOpen, setDocsModalOpen] = useState(false);
  const [viewingDoc, setViewingDoc] = useState<AttachedDoc | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<ChatSearchResult[]>([]);
  const [showOnboarding, setShowOnboarding] = useState(
    () => localStorage.getItem('ourogen_show_onboarding') === '1',
  );

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const dragCounterRef = useRef(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadAbortRefs = useRef<Map<string, AbortController>>(new Map());
  const skipNextLoadRef = useRef(false);
  const activeChatIdRef = useRef<string | null>(null);
  const ensureChatIdPromiseRef = useRef<Promise<string> | null>(null);

  const headers = { Authorization: `Bearer ${token}` };
  const isUploading = uploads.some(
    (u) =>
      u.step === 'uploading' ||
      u.step === 'extracting' ||
      u.step === 'indexing',
  );
  // Title-only for now — context/content search can layer on top of this later.
  const filteredSessions = sessions.filter((s) =>
    (s.title || 'New chat')
      .toLowerCase()
      .includes(searchQuery.trim().toLowerCase()),
  );

  const loadSessions = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/api/chat/sessions`, { headers });
      setSessions(res.data.sessions || []);
    } catch {}
  }, [token]);

  const loadMessages = useCallback(
    async (id: string) => {
      try {
        const res = await axios.get(`${API_BASE_URL}/api/chat/sessions/${id}`, { headers });
        setMessages(res.data.messages || []);
      } catch {}
    },
    [token],
  );

  const loadChatDocs = useCallback(
    async (id: string) => {
      try {
        const res = await axios.get(`${API_BASE_URL}/api/documents`, {
          headers,
          params: { chat_id: id },
        });
        setChatDocs(
          (res.data.documents || []).map((d: any) => ({
            id: d.id,
            filename: d.filename,
          })),
        );
      } catch {}
    },
    [token],
  );

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);
  // The coworker posts results back into the chat that asked for them (a sent
  // reply, a finished call). Pick those up while the chat is open.
  const streamingRef = useRef(false);
  useEffect(() => {
    if (!coworkerMode || !sessionId) return;
    const t = window.setInterval(() => {
      if (!streamingRef.current && document.visibilityState === 'visible') loadMessages(sessionId);
    }, 15_000);
    return () => window.clearInterval(t);
  }, [coworkerMode, sessionId, loadMessages]);
  useEffect(() => {
    if (coworkerMode && sessionId && !streamingRef.current) loadMessages(sessionId);
  }, [coworkerVersion]);
  useEffect(() => {
    activeChatIdRef.current = sessionId ?? null;
    if (skipNextLoadRef.current) {
      skipNextLoadRef.current = false;
      return;
    }
    if (sessionId) loadMessages(sessionId);
    else setMessages([]);
  }, [sessionId, loadMessages]);
  useEffect(() => {
    if (sessionId) loadChatDocs(sessionId);
    else setChatDocs([]);
  }, [sessionId, loadChatDocs]);

  // Debounced content/title search — empty query falls back to browsing
  // the full chat list client-side (see filteredSessions).
  useEffect(() => {
    const q = searchQuery.trim();
    if (!q) {
      setSearchResults([]);
      return;
    }
    const handle = setTimeout(async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/api/chat/search`, {
          headers: { Authorization: `Bearer ${token}` },
          params: { q },
        });
        setSearchResults(res.data.results || []);
      } catch {
        setSearchResults([]);
      }
    }, 300);
    return () => clearTimeout(handle);
  }, [searchQuery, token]);

  // Creates a chat up front if one doesn't exist yet, so a file dropped
  // before any message has somewhere to attach to. Concurrent calls (e.g.
  // dropping several files at once into a brand-new chat) share one
  // in-flight request instead of each creating their own chat.
  const ensureChatId = useCallback(async (): Promise<string> => {
    if (activeChatIdRef.current) return activeChatIdRef.current;
    if (!ensureChatIdPromiseRef.current) {
      ensureChatIdPromiseRef.current = (async () => {
        const res = await axios.post(`${API_BASE_URL}/api/chat/sessions`, {}, { headers });
        const newId = String(res.data.sessionId);
        activeChatIdRef.current = newId;
        skipNextLoadRef.current = true;
        nav(`/app/chat/${newId}`, { replace: true });
        loadSessions();
        return newId;
      })();
    }
    return ensureChatIdPromiseRef.current;
  }, [headers, nav, loadSessions]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const autoResize = () => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 200) + 'px';
  };

  const newChat = () => nav('/app');

  const uploadFile = async (file: File, existingId?: string) => {
    const id = existingId ?? crypto.randomUUID();
    const upsert = (item: UploadItem) => {
      setUploads((prev) =>
        existingId
          ? prev.map((u) => (u.id === id ? item : u))
          : [...prev, item],
      );
    };

    if (!ACCEPTED_TYPES.includes(file.type)) {
      upsert({
        id,
        file,
        name: file.name,
        step: 'error',
        pct: 0,
        error: `Unsupported type — use ${ACCEPTED_LABEL}`,
      });
      return;
    }

    if (file.size > MAX_SIZE_BYTES) {
      upsert({
        id,
        file,
        name: file.name,
        step: 'error',
        pct: 0,
        error: `File exceeds ${MAX_SIZE_MB}MB limit. Try splitting it into smaller sections.`,
      });
      return;
    }

    upsert({ id, file, name: file.name, step: 'uploading', pct: 0 });

    let chatId: string;
    try {
      chatId = await ensureChatId();
    } catch {
      setUploads((prev) =>
        prev.map((u) =>
          u.id === id
            ? {
                ...u,
                step: 'error',
                error: 'Upload failed — please try again.',
              }
            : u,
        ),
      );
      return;
    }

    const form = new FormData();
    form.append('file', file);
    form.append('chat_id', chatId);

    const controller = new AbortController();
    uploadAbortRefs.current.set(id, controller);

    let simulationInterval: ReturnType<typeof setInterval> | null = null;

    const startSimulation = () => {
      let pct = 34;
      simulationInterval = setInterval(() => {
        pct += 1;
        const step: UploadItem['step'] = pct < 67 ? 'extracting' : 'indexing';
        if (pct >= 99) {
          clearInterval(simulationInterval!);
          return;
        }
        setUploads((prev) =>
          prev.map((u) => (u.id === id ? { ...u, step, pct } : u)),
        );
      }, 200);
    };

    try {
      await axios.post(`${API_BASE_URL}/api/documents/upload`, form, {
        headers: { ...headers, 'Content-Type': 'multipart/form-data' },
        signal: controller.signal,
        onUploadProgress: (e) => {
          const pct = e.total ? Math.round((e.loaded / e.total) * 33) : 0;
          setUploads((prev) =>
            prev.map((u) => (u.id === id ? { ...u, pct } : u)),
          );
          if (e.loaded === e.total) startSimulation();
        },
      });

      if (simulationInterval) clearInterval(simulationInterval);
      setUploads((prev) =>
        prev.map((u) => (u.id === id ? { ...u, step: 'done', pct: 100 } : u)),
      );
      loadChatDocs(chatId);
      setTimeout(
        () => setUploads((prev) => prev.filter((u) => u.id !== id)),
        3000,
      );
    } catch (err: any) {
      if (simulationInterval) clearInterval(simulationInterval);
      if (axios.isCancel(err) || err.code === 'ERR_CANCELED') {
        setUploads((prev) => prev.filter((u) => u.id !== id));
        return;
      }
      const msg =
        err?.response?.data?.error === 'Internal server error'
          ? 'We had trouble reading this file. Try converting it to PDF first.'
          : 'Upload failed — please try again.';
      setUploads((prev) =>
        prev.map((u) =>
          u.id === id ? { ...u, step: 'error', error: msg } : u,
        ),
      );
    } finally {
      uploadAbortRefs.current.delete(id);
    }
  };

  const handleFiles = (files: FileList | null) => {
    if (!files) return;
    Array.from(files)
      .slice(0, MAX_FILES)
      .forEach((file) => uploadFile(file));
  };

  const retryUpload = (id: string) => {
    const item = uploads.find((u) => u.id === id);
    if (item) uploadFile(item.file, id);
  };

  const cancelUpload = (id: string) => {
    const controller = uploadAbortRefs.current.get(id);
    if (controller) controller.abort();
    else setUploads((prev) => prev.filter((u) => u.id !== id));
  };

  const removeAttachedDoc = async (docId: string) => {
    setChatDocs((prev) => prev.filter((d) => d.id !== docId));
    try {
      await axios.delete(`${API_BASE_URL}/api/documents/${docId}`, { headers });
    } catch {}
  };

  const onDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    dragCounterRef.current++;
    setDragging(true);
  };

  const onDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    dragCounterRef.current--;
    if (dragCounterRef.current === 0) setDragging(false);
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    dragCounterRef.current = 0;
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  /** Streams one assistant reply to `userContent`, invoking `onChunk` with the
   * accumulated text as it grows. Shared by first sends and regenerations. */
  const streamAssistantReply = async (
    userContent: string,
    onChunk: (accumulated: string) => void,
  ): Promise<void> => {
    abortRef.current = new AbortController();
    if (coworkerMode) {
      let acc = '';
      await streamCoworkerChat(
        token,
        { message: userContent, session_id: sessionId },
        (ev) => {
          if (ev.type === 'error') throw new Error(ev.message || 'Your coworker hit an error.');
          if (ev.type === 'text' && ev.text) acc += ev.text;
          if (ev.type === 'tool') acc += marker({ t: 'tool', name: ev.name, summary: ev.summary });
          if (ev.type === 'card' && ev.card === 'action' && ev.action) {
            putActions([ev.action]);
            acc += marker({ t: 'action', id: ev.action.id });
          }
          if (ev.type === 'card' && ev.card === 'meeting' && ev.id) acc += marker({ t: 'meeting', id: ev.id });
          if (ev.type === 'session_id' && !sessionId) {
            skipNextLoadRef.current = true;
            nav(`/app/chat/${ev.session_id}`, { replace: true });
            loadSessions();
          }
          if (ev.type === 'title' && ev.session_id) {
            const id = String(ev.session_id);
            setSessions((prev) => prev.map((s) => (s.id === id ? { ...s, title: ev.title } : s)));
          }
          onChunk(acc);
        },
        abortRef.current.signal,
      );
      return;
    }
    const res = await fetch(`${API_BASE_URL}/api/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        message: userContent,
        session_id: sessionId,
        model,
      }),
      signal: abortRef.current.signal,
    });

    if (!res.ok) throw new Error('Stream failed');
    if (!res.body) throw new Error('No body');

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let accumulated = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim();
          if (data === '[DONE]') break;
          let parsed: any;
          try {
            parsed = JSON.parse(data);
          } catch {
            continue;
          }
          if (parsed.type === 'error') {
            throw new Error(
              parsed.message || 'Something went wrong. Please try again.',
            );
          }
          if (parsed.type === 'text' && parsed.text) {
            accumulated += parsed.text;
            onChunk(accumulated);
          }
          if (parsed.type === 'session_id' && !sessionId) {
            skipNextLoadRef.current = true;
            nav(`/app/chat/${parsed.session_id}`, { replace: true });
            loadSessions();
          }
          if (parsed.type === 'title' && parsed.session_id) {
            const id = String(parsed.session_id);
            setSessions((prev) =>
              prev.map((s) =>
                s.id === id ? { ...s, title: parsed.title } : s,
              ),
            );
          }
        }
      }
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || streaming || isUploading) return;
    const userMsg: Message = { role: 'user', content: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
    setStreaming(true);
    setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

    try {
      await streamAssistantReply(userMsg.content, (accumulated) => {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: 'assistant',
            content: accumulated,
          };
          return updated;
        });
      });
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: 'assistant',
            content:
              err.message || 'Sorry, something went wrong. Please try again.',
          };
          return updated;
        });
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
      loadSessions();
    }
  };

  const regenerateMessage = async (index: number) => {
    if (streaming) return;
    const target = messages[index];
    if (!target || target.role !== 'assistant') return;
    const userMsg = messages[index - 1];
    if (!userMsg || userMsg.role !== 'user') return;

    setStreaming(true);
    setRegeneratingIndex(index);

    let newVariantIndex = 0;
    setMessages((prev) => {
      const updated = [...prev];
      const cur = updated[index];
      const variants =
        cur.variants && cur.variants.length ? cur.variants : [cur.content];
      newVariantIndex = variants.length;
      updated[index] = {
        ...cur,
        variants: [...variants, ''],
        activeVariantIndex: newVariantIndex,
        content: '',
      };
      return updated;
    });

    const applyToActiveVariant = (text: string) => {
      setMessages((prev) => {
        const updated = [...prev];
        const cur = updated[index];
        const variants = [...(cur.variants || [''])];
        variants[newVariantIndex] = text;
        updated[index] = { ...cur, variants, content: text };
        return updated;
      });
    };

    try {
      await streamAssistantReply(userMsg.content, applyToActiveVariant);
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        applyToActiveVariant(
          err.message || 'Sorry, something went wrong. Please try again.',
        );
      }
    } finally {
      setStreaming(false);
      setRegeneratingIndex(null);
      abortRef.current = null;
    }
  };

  const setVariant = (index: number, variantIndex: number) => {
    setMessages((prev) => {
      const updated = [...prev];
      const cur = updated[index];
      if (
        !cur.variants ||
        variantIndex < 0 ||
        variantIndex >= cur.variants.length
      )
        return prev;
      updated[index] = {
        ...cur,
        activeVariantIndex: variantIndex,
        content: cur.variants[variantIndex],
      };
      return updated;
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      sendMessage();
    }
  };

  const deleteSession = async (id: string) => {
    try {
      await axios.delete(`${API_BASE_URL}/api/chat/sessions/${id}`, { headers });
      if (sessionId === id) nav('/app');
      loadSessions();
    } catch {}
  };

  const confirmDeleteSession = async () => {
    if (!deleteTarget) return;
    await deleteSession(deleteTarget.id);
    setDeleteTarget(null);
  };

  const uploadsRow = uploads.length > 0 && (
    <div className="px-4 pt-3 max-w-3xl mx-auto w-full flex gap-2 overflow-x-auto pb-1 scrollbar-thin-x">
      {uploads.map((u) => (
        <div
          key={u.id}
          className="group relative w-48 min-w-[160px] flex-shrink-0 bg-[#F7F7F8] dark:bg-[#2F2F2F] rounded-xl px-3 py-2 flex items-center gap-2"
        >
          <span className="text-base flex-shrink-0">📄</span>
          <span
            className="flex-1 min-w-0 text-xs font-medium truncate text-gray-900 dark:text-white"
            title={u.step === 'error' ? u.error : u.name}
          >
            {u.name}
          </span>
          {u.step === 'error' ? (
            <button
              onClick={() => retryUpload(u.id)}
              className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-[#3F3F3F] transition-colors"
              title="Retry upload"
            >
              <svg
                className="w-3.5 h-3.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
            </button>
          ) : (
            <UploadRing step={u.step} pct={u.pct} />
          )}
          <button
            onClick={() => cancelUpload(u.id)}
            className="absolute -top-1.5 -right-1.5 opacity-0 group-hover:opacity-100 w-4 h-4 rounded-full bg-gray-300 dark:bg-gray-600 text-white text-[10px] flex items-center justify-center hover:bg-red-500 transition-colors"
            title={
              u.step === 'done' || u.step === 'error'
                ? 'Dismiss'
                : 'Cancel upload'
            }
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  );

  const composerBox = (
    <div className="max-w-3xl mx-auto w-full">
      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPTED_EXT}
        multiple
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
      <div className="relative flex flex-col bg-[#F7F7F8] dark:bg-[#2F2F2F] rounded-2xl border border-gray-300 dark:border-gray-600">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            autoResize();
          }}
          onKeyDown={handleKeyDown}
          placeholder={coworkerMode ? "Ask or delegate: \u201creply to Dana\u201d, \u201chandle inbound leads from now on\u201d…" : "Message Ourogen..."}
          aria-label="Message Ourogen"
          rows={1}
          className="w-full bg-transparent px-4 pt-3.5 pb-1 text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none min-h-[52px] resize-none"
        />
        <div className="flex items-center justify-between px-2 pb-2">
          <div className="flex items-center gap-1">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="p-2 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-200 dark:hover:bg-[#3F3F3F] transition-colors flex-shrink-0"
              aria-label="Upload file"
              title={`Upload file — ${ACCEPTED_LABEL}`}
            >
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
                />
              </svg>
            </button>
            {chatDocs.length > 0 && (
              <button
                onClick={() => setDocsModalOpen(true)}
                className="relative p-2 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-200 dark:hover:bg-[#3F3F3F] transition-colors flex-shrink-0"
                aria-label="Documents"
                title="Documents attached to this chat"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 rounded-full bg-gray-900 dark:bg-white text-white dark:text-gray-900 text-[10px] font-medium flex items-center justify-center">
                  {chatDocs.length}
                </span>
              </button>
            )}
          </div>
          <button
            onClick={streaming ? () => abortRef.current?.abort() : sendMessage}
            disabled={!streaming && (!input.trim() || isUploading)}
            className="p-2 rounded-lg bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:bg-gray-800 dark:hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors flex-shrink-0"
            aria-label={streaming ? 'Stop' : 'Send'}
            title={
              isUploading && !streaming
                ? 'Waiting for uploads to finish...'
                : undefined
            }
          >
            {streaming ? (
              <span className="w-4 h-4 flex items-center justify-center">
                ■
              </span>
            ) : (
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2 21l21-9L2 3v7l15 2-15 2v7z" />
              </svg>
            )}
          </button>
        </div>
      </div>
      <p className="text-xs text-center text-gray-600 dark:text-gray-400 mt-2">
        Ourogen can make mistakes. Verify important information.
      </p>
    </div>
  );

  return (
    <div
      className="flex h-dvh bg-white dark:bg-[#212121] text-gray-900 dark:text-white relative"
      onDragEnter={onDragEnter}
      onDragLeave={onDragLeave}
      onDragOver={onDragOver}
      onDrop={onDrop}
    >
      {/* Drag overlay */}
      {dragging && (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-white/90 dark:bg-[#212121]/90 border-4 border-dashed border-gray-400 dark:border-gray-500 pointer-events-none">
          <svg
            className="w-16 h-16 text-gray-400 dark:text-gray-500 mb-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
          <p className="text-lg font-medium text-gray-600 dark:text-gray-300">
            Drop to upload
          </p>
          <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
            Supports {ACCEPTED_LABEL}
          </p>
        </div>
      )}

      {/* Delete chat confirmation */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="bg-white dark:bg-[#2F2F2F] rounded-2xl shadow-xl max-w-sm w-full p-6">
            <h2 className="text-base font-semibold mb-2">Delete chat?</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
              Are you sure you want to delete "
              <span className="font-medium text-gray-700 dark:text-gray-300">
                {deleteTarget.title || 'New chat'}
              </span>
              "? This can't be undone.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setDeleteTarget(null)}
                className="px-4 py-2 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-[#3F3F3F] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={confirmDeleteSession}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-red-600 text-white hover:bg-red-700 transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Documents attached to this chat */}
      {docsModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="bg-white dark:bg-[#2F2F2F] rounded-2xl shadow-xl max-w-lg w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold">Documents</h2>
              <button
                onClick={() => setDocsModalOpen(false)}
                className="p-1 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-[#3F3F3F] transition-colors"
                aria-label="Close"
              >
                ✕
              </button>
            </div>
            {chatDocs.length === 0 ? (
              <p className="text-sm text-gray-400 dark:text-gray-500 text-center py-6">
                No files attached to this chat yet.
              </p>
            ) : (
              <div className="grid grid-cols-3 gap-3 max-h-80 overflow-y-auto">
                {chatDocs.map((d) => (
                  <div
                    key={d.id}
                    onClick={() => setViewingDoc(d)}
                    className="group relative flex flex-col rounded-lg p-1.5 cursor-pointer hover:bg-gray-100 dark:hover:bg-[#3a3a3a] transition-colors"
                  >
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        removeAttachedDoc(d.id);
                      }}
                      className="absolute top-1 right-1 z-10 w-5 h-5 rounded-full bg-white/90 dark:bg-black/50 opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 text-xs flex items-center justify-center transition-opacity"
                      title="Remove from this chat"
                    >
                      ✕
                    </button>
                    <div className="aspect-[3/4] w-full rounded-lg overflow-hidden">
                      <DocThumbnail docId={d.id} token={token} size="lg" />
                    </div>
                    <span
                      className="text-xs truncate mt-1.5 px-0.5 text-gray-900 dark:text-white"
                      title={d.filename}
                    >
                      {d.filename}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Search chats */}
      {searchOpen && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 px-4 pt-24"
          onClick={() => {
            setSearchOpen(false);
            setSearchQuery('');
          }}
        >
          <div
            className="bg-white dark:bg-[#2F2F2F] rounded-2xl shadow-xl max-w-md w-full p-4"
            onClick={(e) => e.stopPropagation()}
          >
            <input
              autoFocus
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Escape') {
                  setSearchOpen(false);
                  setSearchQuery('');
                }
              }}
              placeholder="Search chats by title or content..."
              className="w-full bg-[#F7F7F8] dark:bg-[#1a1a1a] border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none"
            />
            <div className="mt-2 max-h-80 overflow-y-auto space-y-0.5">
              {searchQuery.trim() === '' ? (
                filteredSessions.length === 0 ? (
                  <p className="text-sm text-gray-400 dark:text-gray-500 text-center py-6">
                    No chats yet.
                  </p>
                ) : (
                  filteredSessions.map((s) => (
                    <div
                      key={s.id}
                      onClick={() => {
                        nav(`/app/chat/${s.id}`);
                        setSearchOpen(false);
                        setSearchQuery('');
                      }}
                      className={`px-3 py-2 rounded-lg text-sm cursor-pointer truncate transition-colors ${
                        s.id === sessionId
                          ? 'bg-gray-200 dark:bg-[#3F3F3F]'
                          : 'hover:bg-gray-100 dark:hover:bg-[#3a3a3a]'
                      }`}
                    >
                      {s.title || 'New chat'}
                    </div>
                  ))
                )
              ) : searchResults.length === 0 ? (
                <p className="text-sm text-gray-400 dark:text-gray-500 text-center py-6">
                  No chats found.
                </p>
              ) : (
                searchResults.map((r) => (
                  <div
                    key={r.id}
                    onClick={() => {
                      nav(`/app/chat/${r.id}`);
                      setSearchOpen(false);
                      setSearchQuery('');
                    }}
                    className={`px-3 py-2 rounded-lg text-sm cursor-pointer transition-colors ${
                      r.id === sessionId
                        ? 'bg-gray-200 dark:bg-[#3F3F3F]'
                        : 'hover:bg-gray-100 dark:hover:bg-[#3a3a3a]'
                    }`}
                  >
                    <p className="truncate font-medium">{r.title}</p>
                    {r.snippet && (
                      <p className="truncate text-xs text-gray-600 dark:text-gray-400">
                        {r.snippet}
                      </p>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Sidebar */}
      <aside
        className={`${sidebarOpen ? 'w-64 max-md:absolute max-md:inset-y-0 max-md:left-0 max-md:z-40 max-md:shadow-xl' : 'w-14 max-md:hidden'} transition-all duration-200 overflow-hidden flex-shrink-0 bg-[#F7F7F8] dark:bg-[#171717] flex flex-col`}
      >
        <div
          className={`p-3 flex items-center gap-2 ${sidebarOpen ? '' : 'justify-center'}`}
        >
          <OurogenLogo className="w-7 h-7 flex-shrink-0" />
          {sidebarOpen && (
            <span className="font-semibold text-sm truncate">Ourogen</span>
          )}
        </div>
        <div className="px-2 pb-6 space-y-0.5">
          <button
            onClick={newChat}
            title="New Chat"
            className={`w-full rounded-lg text-sm hover:bg-gray-200 dark:hover:bg-[#2F2F2F] transition-colors flex items-center gap-2 ${
              sidebarOpen ? 'text-left px-3 py-2' : 'justify-center py-2'
            }`}
          >
            <svg
              className="w-4 h-4 flex-shrink-0"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
              />
            </svg>
            {sidebarOpen && 'New Chat'}
          </button>
          <button
            onClick={() => nav('/documents')}
            title="Library"
            className={`w-full rounded-lg text-sm hover:bg-gray-200 dark:hover:bg-[#2F2F2F] transition-colors flex items-center gap-2 ${
              sidebarOpen ? 'text-left px-3 py-2' : 'justify-center py-2'
            }`}
          >
            <svg
              className="w-4 h-4 flex-shrink-0"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"
              />
            </svg>
            {sidebarOpen && 'Library'}
          </button>
          <button
            onClick={() => setSearchOpen(true)}
            title="Search chats"
            className={`w-full rounded-lg text-sm hover:bg-gray-200 dark:hover:bg-[#2F2F2F] transition-colors flex items-center gap-2 ${
              sidebarOpen ? 'text-left px-3 py-2' : 'justify-center py-2'
            }`}
          >
            <svg
              className="w-4 h-4 flex-shrink-0"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 105.5 5.5a7.5 7.5 0 0011.15 11.15z"
              />
            </svg>
            {sidebarOpen && 'Search Chats'}
          </button>
          <button
            onClick={() => nav(coworker ? '/app/coworker' : '/app/onboarding')}
            title={coworker ? 'Your AI coworker' : 'Set up your AI coworker'}
            className={`w-full rounded-lg text-sm hover:bg-gray-200 dark:hover:bg-[#2F2F2F] transition-colors flex items-center gap-2 ${
              sidebarOpen ? 'text-left px-3 py-2' : 'justify-center py-2'
            }`}
          >
            <span className="w-4 text-center flex-shrink-0" aria-hidden>🤖</span>
            {sidebarOpen && <span className="flex-1">{coworker ? 'Coworker' : 'Set up your coworker'}</span>}
            {sidebarOpen && coworker && (coworkerStatus.pending || 0) > 0 && (
              <span className="min-w-[18px] h-[18px] px-1 rounded-full bg-black text-white dark:bg-white dark:text-black text-[10px] font-semibold flex items-center justify-center">
                {coworkerStatus.pending}
              </span>
            )}
          </button>
        </div>
        {sidebarOpen && (
          <div className="flex-1 overflow-y-auto px-2 space-y-0.5 flex flex-col">
            <TodaySidebar onNavigate={() => { if (window.innerWidth < 768) setSidebarOpen(false); }} />
            <p className="px-1 pb-1 text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
              Chats
            </p>
            {sessions.map((s) => (
              <div
                key={s.id}
                onClick={() => nav(`/app/chat/${s.id}`)}
                className={`group flex items-center justify-between px-3 py-2 rounded-lg text-sm cursor-pointer transition-colors ${
                  s.id === sessionId
                    ? 'bg-gray-200 dark:bg-[#2F2F2F]'
                    : 'hover:bg-gray-200 dark:hover:bg-[#2F2F2F]'
                }`}
              >
                <span className="truncate">{s.title || 'New chat'}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    e.preventDefault();
                    setDeleteTarget(s);
                  }}
                  className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 text-xs ml-1 flex-shrink-0"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}
        {!sidebarOpen && <div className="flex-1" />}
        <UserMenu sidebarOpen={sidebarOpen} />
      </aside>

      {sidebarOpen && <button className="fixed inset-0 z-30 bg-black/40 md:hidden" aria-label="Close navigation" onClick={() => setSidebarOpen(false)} />}
      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <button
            onClick={() => setSidebarOpen((o) => !o)}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-[#2F2F2F] text-gray-500 dark:text-gray-400"
            aria-label="Toggle sidebar"
            aria-expanded={sidebarOpen}
          >
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>
          <div className="flex items-center gap-2">
            {coworker && (
              <button
                onClick={toggleMode}
                title={coworkerMode ? 'Talking to your AI coworker (can act for you). Click for a plain assistant.' : 'Plain assistant. Click to talk to your coworker.'}
                className="text-xs px-2.5 py-1.5 rounded-lg bg-[#F7F7F8] dark:bg-[#2F2F2F] hover:bg-gray-200 dark:hover:bg-[#3a3a3a]"
              >
                {coworkerMode ? '🤖 Coworker' : '💬 Assistant'}
              </button>
            )}
            {coworkerMode && <HeaderControls />}
          </div>
        </header>
        {coworkerMode && coworker?.status === 'paused' && (
          <div className="bg-amber-50 dark:bg-amber-500/10 border-b border-amber-200 dark:border-amber-500/30 text-xs text-amber-900 dark:text-amber-200 px-4 py-1.5 text-center">
            Your coworker is paused. It can still answer questions, but nothing will be sent and no responsibilities will run.
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center min-h-full gap-4 px-5 py-10 text-center">
              <OurogenLogo className="w-12 h-12" />
              <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">
                {coworkerMode ? 'What should I take off your plate?' : 'What would you like to work on?'}
              </h1>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                {coworkerMode
                  ? `I'm ${coworker?.displayName || 'your AI coworker'}. I can read your work, draft in your voice, and take on ongoing jobs. Anything I send waits for your approval.`
                  : 'Ask a question, explore an idea, or bring a document.'}
              </p>
              {coworkerLoaded && !coworker && (
                <button
                  onClick={() => nav('/app/onboarding')}
                  className="rounded-2xl border border-gray-200 dark:border-gray-700 px-4 py-3 text-sm text-left max-w-xl hover:bg-gray-50 dark:hover:bg-white/5"
                >
                  <span className="font-medium">New: your AI coworker.</span>{' '}
                  <span className="text-gray-600 dark:text-gray-400">It learns from your email, Slack, and calendar, then handles work for you. Set it up in 5 minutes →</span>
                </button>
              )}
              <div className="grid w-full max-w-3xl gap-3 sm:grid-cols-3 my-3 text-left">
                {(coworkerMode ? (coworker?.mode === 'demo' ? DELEGATE_PROMPTS : LIVE_PROMPTS) : [
                  { title: 'Make a plan', prompt: 'Help me turn an idea into a practical plan. Ask me about my goal first.' },
                  { title: 'Improve my writing', prompt: 'Help me make a draft clearer and more concise. Ask me to share it.' },
                  { title: 'Understand some code', prompt: 'Help me understand a piece of code. Ask me to paste it and explain what I want to learn.' },
                ]).map(({ title, prompt }) => (
                  <button key={title} onClick={() => { setInput(prompt); requestAnimationFrame(() => { textareaRef.current?.focus(); autoResize(); }); }}
                    className="rounded-2xl border border-gray-200 dark:border-gray-700 px-4 py-4 text-sm font-medium hover:bg-gray-50 dark:hover:bg-white/5 transition-colors text-left">
                    {title}<span aria-hidden="true" className="float-right text-gray-500">↗</span>
                  </button>
                ))}
              </div>
              <div className="w-full mt-2 text-left">
                {uploadsRow}
                {composerBox}
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
              {messages.map((msg, i) => {
                const isThisStreaming =
                  streaming &&
                  (regeneratingIndex === i ||
                    (regeneratingIndex === null && i === messages.length - 1));
                const activeVariantIndex =
                  msg.activeVariantIndex ??
                  (msg.variants ? msg.variants.length - 1 : 0);
                return (
                  <div
                    key={i}
                    className={`flex items-start gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    {msg.role === 'assistant' && (
                      <div className="w-8 h-8 rounded-full bg-gray-100 dark:bg-[#2F2F2F] flex items-center justify-center flex-shrink-0">
                        <OurogenLogo className="w-5 h-5" />
                      </div>
                    )}
                    <div
                      className={`${msg.role === 'assistant' ? 'max-w-[92%] min-w-0 flex-1' : 'max-w-[85%]'} rounded-2xl px-4 ${
                        msg.role === 'user'
                          ? 'py-3 bg-gray-100 dark:bg-[#2F2F2F] text-gray-900 dark:text-white'
                          : 'py-1.5 bg-transparent text-gray-900 dark:text-white'
                      }`}
                    >
                      {msg.role === 'assistant' ? (
                        msg.content.includes(':::cw ') || (coworkerMode && isThisStreaming) ? (
                          <CoworkerMessage content={msg.content} streaming={isThisStreaming} />
                        ) : (
                          <div className="prose prose-sm dark:prose-invert max-w-none">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                              {msg.content || (isThisStreaming ? '▋' : '')}
                            </ReactMarkdown>
                          </div>
                        )
                      ) : (
                        <p className="whitespace-pre-wrap text-sm">
                          {msg.content}
                        </p>
                      )}
                      {msg.role === 'assistant' &&
                        !isThisStreaming &&
                        msg.content && (
                          <div className="flex items-center gap-1 mt-1 -ml-1 text-gray-400 dark:text-gray-500">
                            <button
                              onClick={() => regenerateMessage(i)}
                              disabled={streaming}
                              className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-[#3F3F3F] hover:text-gray-600 dark:hover:text-gray-300 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                              aria-label="Regenerate response"
                              title="Regenerate response"
                            >
                              <svg
                                className="w-3.5 h-3.5"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth={2}
                                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                                />
                              </svg>
                            </button>
                            {msg.variants && msg.variants.length > 1 && (
                              <div className="flex items-center gap-0.5 text-xs">
                                <button
                                  onClick={() =>
                                    setVariant(i, activeVariantIndex - 1)
                                  }
                                  disabled={activeVariantIndex === 0}
                                  className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-[#3F3F3F] hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                                  aria-label="Previous response"
                                >
                                  <svg
                                    className="w-3 h-3"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                  >
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={2}
                                      d="M15 19l-7-7 7-7"
                                    />
                                  </svg>
                                </button>
                                <span className="tabular-nums">
                                  {activeVariantIndex + 1}/{msg.variants.length}
                                </span>
                                <button
                                  onClick={() =>
                                    setVariant(i, activeVariantIndex + 1)
                                  }
                                  disabled={
                                    activeVariantIndex ===
                                    msg.variants.length - 1
                                  }
                                  className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-[#3F3F3F] hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                                  aria-label="Next response"
                                >
                                  <svg
                                    className="w-3 h-3"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                  >
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={2}
                                      d="M9 5l7 7-7 7"
                                    />
                                  </svg>
                                </button>
                              </div>
                            )}
                          </div>
                        )}
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {messages.length > 0 && (
          <>
            {uploadsRow}
            <div className="border-t border-gray-200 dark:border-gray-700 px-4 py-4 mt-2">
              {composerBox}
            </div>
          </>
        )}
      </div>
      <FileViewerModal
        doc={viewingDoc}
        token={token}
        onClose={() => setViewingDoc(null)}
      />
      {showOnboarding && (
        <OnboardingTour
          onDone={() => {
            localStorage.removeItem('ourogen_show_onboarding');
            setShowOnboarding(false);
          }}
        />
      )}
    </div>
  );
}
