import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { coworkerApi } from './api';
import { useCoworker } from './CoworkerContext';

const ICON: Record<string, string> = { meeting: '📞', brief: '📋', escalation: '🙋', security: '🛡️', digest: '🗞️' };

/** "Today" in the chat sidebar: the work your coworker did, next to your chats. */
export default function TodaySidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { token } = useAuth();
  const { coworker, version } = useCoworker();
  const nav = useNavigate();
  const [day, setDay] = useState<any>(null);

  useEffect(() => {
    if (!coworker) return;
    const load = () => coworkerApi(token).get('/day').then(setDay).catch(() => {});
    load();
    const t = window.setInterval(load, 60_000);
    return () => window.clearInterval(t);
  }, [coworker?.id, version]);

  if (!coworker || !day) return null;
  const items = day.entries.filter((e: any) => e.kind !== 'digest').slice(0, 6);
  const open = (e: any) => {
    onNavigate?.();
    if (e.chatId) nav(`/app/chat/${e.chatId}`);
    else if (e.kind === 'meeting') nav(`/app/coworker/calls?meeting=${e.id}`);
    else if (e.status === 'proposed') nav('/app/coworker/approvals');
    else nav('/app/coworker/today');
  };
  return (
    <div className="mb-3">
      <button onClick={() => { onNavigate?.(); nav('/app/coworker/today'); }}
        className="w-full flex items-baseline justify-between gap-2 px-1 pb-1 text-xs text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300">
        <span className="font-semibold uppercase tracking-wider whitespace-nowrap">Today</span>
        <span className="truncate">{day.counts.done} done{day.counts.pending ? ` · ${day.counts.pending} waiting` : ''}</span>
      </button>
      {items.length === 0 ? (
        <p className="px-3 py-2 text-xs text-gray-500 dark:text-gray-400">Nothing yet. Ask it to reply to emails or join a meeting.</p>
      ) : (
        items.map((e: any) => (
          <button key={`${e.kind}-${e.id}`} onClick={() => open(e)}
            className="w-full flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm text-left hover:bg-gray-200 dark:hover:bg-[#2F2F2F]">
            <span aria-hidden className="text-xs">{ICON[e.kind] || (e.status === 'executed' ? '✅' : '📝')}</span>
            <span className="truncate flex-1">{e.title}</span>
            {e.status === 'proposed' && <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0" title="Needs you" />}
          </button>
        ))
      )}
    </div>
  );
}
