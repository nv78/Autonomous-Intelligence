import { type ReactNode, useEffect, useState } from 'react';
import { useAuth } from '../App';
import { coworkerApi, errorMessage, timeAgo } from './api';
import { useCoworker } from './CoworkerContext';
import type { Action } from './types';

const ICON: Record<string, string> = {
  'email.send': '✉️',
  'slack.post': '💬',
  'calendar.create': '📅',
  'crm.update': '🗂️',
  'responsibility.create': '📌',
};

const STATUS: Record<string, { text: string; cls: string }> = {
  proposed: { text: 'Needs your approval', cls: 'bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300' },
  approved: { text: 'Queued', cls: 'bg-blue-100 text-blue-800 dark:bg-blue-500/15 dark:text-blue-300' },
  executing: { text: 'Working…', cls: 'bg-blue-100 text-blue-800 dark:bg-blue-500/15 dark:text-blue-300' },
  executed: { text: 'Done', cls: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300' },
  rejected: { text: 'Rejected', cls: 'bg-gray-200 text-gray-700 dark:bg-white/10 dark:text-gray-300' },
  cancelled: { text: 'Cancelled', cls: 'bg-gray-200 text-gray-700 dark:bg-white/10 dark:text-gray-300' },
  undone: { text: 'Undone', cls: 'bg-gray-200 text-gray-700 dark:bg-white/10 dark:text-gray-300' },
  expired: { text: 'Expired', cls: 'bg-gray-200 text-gray-700 dark:bg-white/10 dark:text-gray-300' },
  failed: { text: 'Failed', cls: 'bg-red-100 text-red-800 dark:bg-red-500/15 dark:text-red-300' },
};

const btn = 'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed';
const primary = `${btn} bg-black text-white hover:bg-gray-800 dark:bg-white dark:text-black dark:hover:bg-gray-200`;
const ghost = `${btn} text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-white/10 border border-gray-200 dark:border-gray-600`;
const input =
  'w-full bg-white dark:bg-[#212121] border border-gray-200 dark:border-gray-600 rounded-lg px-2.5 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-gray-400';

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex gap-2 text-sm">
      <span className="w-16 flex-shrink-0 text-gray-500 dark:text-gray-400">{label}</span>
      <div className="min-w-0 flex-1 break-words">{children}</div>
    </div>
  );
}

export default function ActionCard({ id, action: initial, compact = false }: { id?: number; action?: Action; compact?: boolean }) {
  const { token } = useAuth();
  const { actionCache, putActions, loadActions, refreshStatus } = useCoworker();
  const api = coworkerApi(token);
  const actionId = id ?? initial?.id;
  const action = (actionId ? actionCache[actionId] : undefined) || initial;
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Record<string, any>>({});
  const [rejecting, setRejecting] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    if (initial) putActions([initial]);
  }, [initial?.id]);

  useEffect(() => {
    if (!action && actionId) loadActions([actionId]);
  }, [actionId, action]);

  useEffect(() => {
    if (action?.status !== 'approved' && action?.status !== 'executing') return;
    const handle = setInterval(async () => {
      setNow(Date.now());
      if (action.executeAfter && new Date(action.executeAfter).getTime() <= Date.now()) {
        const data = await api.get('/actions', { ids: String(action.id) });
        putActions(data.actions || []);
      }
    }, 1000);
    return () => clearInterval(handle);
  }, [action?.status, action?.executeAfter]);

  if (!action) {
    return <div className="my-2 h-24 rounded-xl border border-gray-200 dark:border-gray-700 animate-pulse" />;
  }

  const p = { ...action.payload, ...draft };
  const run = async (fn: () => Promise<any>) => {
    setBusy(true);
    setErr('');
    try {
      const data = await fn();
      if (data?.action) putActions([data.action]);
      setEditing(false);
      setRejecting(false);
      setDraft({});
      refreshStatus();
    } catch (e: any) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  const approve = () => run(() => api.post(`/actions/${action.id}/approve`, Object.keys(draft).length ? { payload: draft } : {}));
  const reject = () => run(() => api.post(`/actions/${action.id}/reject`, { feedback }));
  const undo = () => run(() => api.post(`/actions/${action.id}/undo`));
  const status = STATUS[action.status] || STATUS.proposed;
  const secondsLeft = action.executeAfter ? Math.max(0, Math.ceil((new Date(action.executeAfter).getTime() - now) / 1000)) : 0;
  const set = (k: string, v: any) => setDraft((d) => ({ ...d, [k]: v }));

  const approveLabel =
    action.type === 'responsibility.create'
      ? 'Confirm'
      : action.autonomy === 'suggest' && action.type === 'email.send'
        ? 'Save as draft'
        : action.type === 'email.send'
          ? 'Approve & send'
          : action.type === 'calendar.create'
            ? 'Send invite'
            : 'Approve';

  return (
    <div className="my-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#262626] shadow-sm overflow-hidden not-prose">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-gray-100 dark:border-gray-700/70 bg-[#F7F7F8] dark:bg-[#2F2F2F]">
        <span aria-hidden>{ICON[action.type] || '⚙️'}</span>
        <span className="text-sm font-medium truncate flex-1" title={action.title}>
          {action.title}
        </span>
        <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap ${status.cls}`}>
          {action.status === 'approved' && secondsLeft > 0 ? `Sending in ${secondsLeft}s` : status.text}
        </span>
      </div>

      {!compact && (
        <div className="px-4 py-3 space-y-1.5">
          {action.type === 'email.send' && (
            <>
              <Field label="To">
                {editing ? (
                  <input className={input} value={(p.to || []).join(', ')}
                    onChange={(e) => set('to', e.target.value.split(',').map((x) => x.trim()).filter(Boolean))} />
                ) : (
                  (p.to || []).join(', ')
                )}
              </Field>
              <Field label="Subject">
                {editing ? <input className={input} value={p.subject || ''} onChange={(e) => set('subject', e.target.value)} /> : p.subject}
              </Field>
              <div className="pt-1">
                {editing ? (
                  <textarea className={`${input} min-h-[180px] font-sans`} value={p.body || ''} onChange={(e) => set('body', e.target.value)} />
                ) : (
                  <div className="whitespace-pre-wrap text-sm leading-relaxed text-gray-800 dark:text-gray-200 bg-[#F7F7F8] dark:bg-[#1f1f1f] rounded-lg px-3 py-2.5 max-h-72 overflow-y-auto">
                    {p.body}
                  </div>
                )}
              </div>
            </>
          )}
          {action.type === 'slack.post' && (
            <>
              <Field label="Channel">#{p.channel}</Field>
              {editing ? (
                <textarea className={`${input} min-h-[90px]`} value={p.text || ''} onChange={(e) => set('text', e.target.value)} />
              ) : (
                <div className="whitespace-pre-wrap text-sm bg-[#F7F7F8] dark:bg-[#1f1f1f] rounded-lg px-3 py-2">{p.text}</div>
              )}
            </>
          )}
          {action.type === 'calendar.create' && (
            <>
              <Field label="Title">{p.title}</Field>
              <Field label="When">{p.start ? new Date(p.start).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' }) : ''}</Field>
              <Field label="Guests">{(p.attendees || []).join(', ')}</Field>
            </>
          )}
          {action.type === 'responsibility.create' && (
            <>
              <p className="text-sm font-medium">{p.name}</p>
              <p className="text-sm text-gray-600 dark:text-gray-300">{p.description || p.instruction}</p>
              <Field label="Autonomy">
                <select className={`${input} w-auto`} value={p.autonomy} disabled={action.status !== 'proposed'}
                  onChange={(e) => set('autonomy', e.target.value)}>
                  <option value="suggest">Suggest: I prepare, you send</option>
                  <option value="approve">Approve: I ask before acting</option>
                  <option value="notify">Notify: I act, then tell you</option>
                  <option value="silent">Silent: I act, it's in the log</option>
                </select>
              </Field>
              <Field label="Escalates">{p.escalation}</Field>
            </>
          )}
          {action.type === 'crm.update' && (
            <>
              <Field label="Account">{p.company}</Field>
              <Field label="Update">{p.summary}</Field>
            </>
          )}

          {action.reasoning && (
            <p className="text-xs text-gray-500 dark:text-gray-400 pt-1">
              <span className="font-medium">Why: </span>
              {action.reasoning}
            </p>
          )}
          {action.risks?.length > 0 && action.status === 'proposed' && (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {action.risks.map((r) => (
                <span key={r.code} title={r.message}
                  className="text-[11px] px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200 dark:bg-amber-500/10 dark:text-amber-300 dark:border-amber-500/30">
                  ⚠ {r.message}
                </span>
              ))}
            </div>
          )}
          {action.error && <p className="text-xs text-red-600 dark:text-red-400">{action.error}</p>}
          {action.result?.draft && <p className="text-xs text-gray-500">Saved to your Gmail drafts for you to send.</p>}
        </div>
      )}

      {rejecting && (
        <div className="px-4 pb-3">
          <input autoFocus className={input} placeholder="What should I do differently? (optional, helps me learn)"
            value={feedback} onChange={(e) => setFeedback(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && reject()} />
        </div>
      )}

      <div className="flex items-center gap-2 px-4 py-2.5 border-t border-gray-100 dark:border-gray-700/70">
        {action.status === 'proposed' && !rejecting && (
          <>
            <button className={primary} disabled={busy} onClick={approve}>{approveLabel}</button>
            {action.type !== 'responsibility.create' && action.type !== 'calendar.create' && (
              <button className={ghost} disabled={busy} onClick={() => setEditing((e) => !e)}>{editing ? 'Done editing' : 'Edit'}</button>
            )}
            <button className={ghost} disabled={busy} onClick={() => setRejecting(true)}>
              {action.type === 'responsibility.create' ? 'Not now' : 'Reject'}
            </button>
          </>
        )}
        {rejecting && (
          <>
            <button className={primary} disabled={busy} onClick={reject}>Reject</button>
            <button className={ghost} onClick={() => setRejecting(false)}>Cancel</button>
          </>
        )}
        {action.status === 'approved' && (
          <button className={ghost} disabled={busy} onClick={undo}>Undo</button>
        )}
        {action.status === 'executed' && action.result?.undo && Object.keys(action.result.undo).length > 0 && (
          <button className={ghost} disabled={busy} onClick={undo}>Undo</button>
        )}
        <span className="ml-auto text-[11px] text-gray-400 truncate" title={action.approvalReason}>
          {action.status === 'proposed' ? action.approvalReason : timeAgo(action.executedAt || action.decidedAt || action.createdAt)}
        </span>
      </div>
      {err && <p className="px-4 pb-3 text-xs text-red-600 dark:text-red-400">{err}</p>}
    </div>
  );
}
