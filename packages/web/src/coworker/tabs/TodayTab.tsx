import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../App';
import { coworkerApi } from '../api';
import { useCoworker } from '../CoworkerContext';
import { Card, Empty, Pill, Section, ghostBtn } from '../ui';

const ICON: Record<string, string> = { meeting: '📞', brief: '📋', escalation: '🙋', security: '🛡️', digest: '🗞️' };

function localDate(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function shift(date: string, days: number) {
  const d = new Date(`${date}T12:00:00`);
  d.setDate(d.getDate() + days);
  return localDate(d);
}
function time(at: string) {
  return new Date(at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}

/** One day of your coworker's work: calls it took, what it sent, what's waiting. */
export default function TodayTab() {
  const { token } = useAuth();
  const { version } = useCoworker();
  const api = coworkerApi(token);
  const nav = useNavigate();
  const today = localDate(new Date());
  const [date, setDate] = useState(today);
  const [day, setDay] = useState<any>(null);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    api.get('/day', { date }).then(setDay).catch(() => setDay(null));
  }, [date, version]);

  const go = (e: any) => {
    if (e.chatId) nav(`/app/chat/${e.chatId}`);
    else if (e.kind === 'meeting') nav(`/app/coworker/calls?meeting=${e.id}`);
    else if (e.kind === 'action' && e.status === 'proposed') nav('/app/coworker/approvals');
    else setOpen(open === `${e.kind}-${e.id}` ? null : `${e.kind}-${e.id}`);
  };
  const delegate = (prompt: string) => nav(`/app?prompt=${encodeURIComponent(prompt)}`);
  const label = date === today ? 'Today' : date === shift(today, -1) ? 'Yesterday'
    : new Date(`${date}T12:00:00`).toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' });

  return (
    <div>
      <div className="flex items-center gap-2 mb-6">
        <button className={ghostBtn} onClick={() => setDate(shift(date, -1))} aria-label="Previous day">←</button>
        <h2 className="text-lg font-semibold flex-1 text-center">{label}</h2>
        <button className={ghostBtn} disabled={date >= today} onClick={() => setDate(shift(date, 1))} aria-label="Next day">→</button>
      </div>

      {day && (
        <Card className="p-4 mb-6">
          <div className="grid grid-cols-3 gap-4 text-center">
            {[[day.counts.done, 'done'], [day.counts.calls, day.counts.calls === 1 ? 'call' : 'calls'], [day.counts.pending, 'waiting for you']].map(([n, l]) => (
              <div key={String(l)}>
                <p className="text-2xl font-semibold tabular-nums">{n}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{l}</p>
              </div>
            ))}
          </div>
          {day.counts.pending > 0 && (
            <button className="mt-3 w-full text-sm underline underline-offset-4" onClick={() => nav('/app/coworker/approvals')}>
              Review what's waiting →
            </button>
          )}
        </Card>
      )}

      {day?.upcoming?.length > 0 && (
        <Section title="Still today" subtitle="Send your coworker instead of going yourself.">
          <Card className="divide-y divide-gray-100 dark:divide-gray-700/70">
            {day.upcoming.map((u: any) => (
              <div key={u.id} className="flex items-center gap-3 px-4 py-3">
                <span className="text-xs text-gray-500 w-16 shrink-0">{time(u.at)}</span>
                <span className="text-sm flex-1 truncate">{u.title}</span>
                <button className={ghostBtn} onClick={() => delegate(`Join ${u.title}, take notes, and send me the summary`)}>
                  Send my coworker
                </button>
              </div>
            ))}
          </Card>
        </Section>
      )}

      <Section title="What your coworker did">
        {!day || day.entries.length === 0 ? (
          <Empty title={date === today ? 'Nothing yet today' : 'Nothing that day'}>
            Tell it what to take on in chat, like “reply to my unanswered emails” or “join my 2pm and pitch the pilot”.
          </Empty>
        ) : (
          <Card className="divide-y divide-gray-100 dark:divide-gray-700/70">
            {day.entries.map((e: any) => {
              const key = `${e.kind}-${e.id}`;
              return (
                <div key={key}>
                  <button onClick={() => go(e)} className="w-full text-left flex items-start gap-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-white/5">
                    <span className="text-xs text-gray-500 w-16 shrink-0 pt-0.5">{e.at ? time(e.at) : ''}</span>
                    <span aria-hidden>{ICON[e.kind] || (e.status === 'executed' ? '✅' : '📝')}</span>
                    <span className="flex-1 min-w-0">
                      <span className="block text-sm truncate">{e.title}</span>
                      {e.to?.length > 0 && <span className="block text-xs text-gray-500 truncate">to {e.to.join(', ')}</span>}
                    </span>
                    {e.kind === 'meeting' && e.score != null && <Pill tone={e.hot ? 'green' : 'gray'}>{e.score}/100</Pill>}
                    {e.status === 'proposed' && <Pill tone="amber">Needs you</Pill>}
                    {e.chatId && <span className="text-xs text-gray-400" title="Opens the chat where you asked for this">💬</span>}
                  </button>
                  {open === key && e.detail && (
                    <p className="px-4 pb-3 pl-[6.5rem] text-sm whitespace-pre-wrap text-gray-600 dark:text-gray-300">{e.detail}</p>
                  )}
                </div>
              );
            })}
          </Card>
        )}
      </Section>
    </div>
  );
}
