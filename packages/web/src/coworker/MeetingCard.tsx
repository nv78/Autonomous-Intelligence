import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { coworkerApi } from './api';
import { useCoworker } from './CoworkerContext';

/** A call the coworker took, inline in the chat: status, score, and a way in. */
export default function MeetingCard({ id }: { id: number }) {
  const { token } = useAuth();
  const { version } = useCoworker();
  const nav = useNavigate();
  const [m, setM] = useState<any>(null);

  useEffect(() => {
    let stop = false;
    const load = () => coworkerApi(token).get(`/meetings/${id}`).then((d) => !stop && setM(d.meeting)).catch(() => {});
    load();
    // Live calls change while the user watches the chat; refresh until it ends.
    const t = window.setInterval(() => { if (!m || m.status === 'active') load(); }, 5000);
    return () => { stop = true; window.clearInterval(t); };
  }, [id, version]);

  if (!m) return <div className="not-prose my-2 h-16 rounded-xl bg-[#F7F7F8] dark:bg-[#2F2F2F] animate-pulse" />;
  const live = m.status === 'active';
  const summary = m.summary || {};
  return (
    <div className="not-prose my-2 rounded-xl border border-gray-200 dark:border-gray-700 p-3.5">
      <div className="flex items-center gap-2">
        <span aria-hidden>📞</span>
        <p className="text-sm font-medium flex-1 truncate">{m.title}</p>
        <span className={`text-[11px] rounded-full px-2 py-0.5 border ${live ? 'border-emerald-500 text-emerald-600 dark:text-emerald-400' : 'border-gray-300 dark:border-gray-600 text-gray-500'}`}>
          {live ? '● Live' : m.status === 'failed' ? 'Failed' : 'Ended'}
        </span>
      </div>
      {!live && summary.score !== undefined && (
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
          Lead score {summary.score}/100{summary.hot ? ' 🔥' : ''} · {m.transcript?.length || 0} turns
          {(m.metrics?.escalations || []).length > 0 && ` · ${m.metrics.escalations.length} escalated to you`}
        </p>
      )}
      {live && <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Your coworker is on the call. Watch, whisper an instruction, or take over.</p>}
      <button onClick={() => nav(`/app/coworker/calls?meeting=${m.id}`)}
        className="mt-2 text-xs font-medium underline underline-offset-4">
        {live ? 'Open the live call →' : 'Read the transcript →'}
      </button>
    </div>
  );
}
