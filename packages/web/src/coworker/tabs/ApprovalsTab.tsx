import { useEffect, useState } from 'react';
import { useAuth } from '../../App';
import ActionCard from '../ActionCard';
import { coworkerApi } from '../api';
import { useCoworker } from '../CoworkerContext';
import type { Action } from '../types';
import { Empty, Section, ghostBtn } from '../ui';

export default function ApprovalsTab() {
  const { token } = useAuth();
  const { putActions, version, actionCache } = useCoworker();
  const api = coworkerApi(token);
  const [pending, setPending] = useState<Action[]>([]);
  const [recent, setRecent] = useState<Action[]>([]);
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const [p, all, autonomy] = await Promise.all([api.get('/actions', { status: 'proposed' }), api.get('/actions'), api.get('/autonomy')]);
      putActions([...(p.actions || []), ...(all.actions || [])]);
      setPending(p.actions || []);
      setRecent((all.actions || []).filter((a: Action) => a.status !== 'proposed').slice(0, 15));
      setSuggestions(autonomy.suggestions || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [version]);

  const stillPending = pending.filter((a) => (actionCache[a.id] || a).status === 'proposed');

  const raise = async (s: any) => {
    await api.put('/autonomy', { [s.actionType]: s.to });
    load();
  };

  return (
    <div>
      {suggestions.map((s) => (
        <div key={s.actionType} className="mb-4 rounded-xl border border-blue-200 dark:border-blue-500/30 bg-blue-50 dark:bg-blue-500/10 px-4 py-3 flex items-center gap-3">
          <p className="text-sm flex-1">{s.message}</p>
          <button className={ghostBtn} onClick={() => raise(s)}>Move to '{s.to}'</button>
        </div>
      ))}
      <Section title="Waiting for you" subtitle="Nothing leaves without your OK unless you've told me it can.">
        {loading ? (
          <div className="h-24 rounded-xl border border-gray-200 dark:border-gray-700 animate-pulse" />
        ) : stillPending.length === 0 ? (
          <Empty title="You're all caught up">New drafts and proposals show up here and in chat.</Empty>
        ) : (
          stillPending.map((a) => <ActionCard key={a.id} id={a.id} />)
        )}
      </Section>
      {recent.length > 0 && (
        <Section title="Recently handled">
          {recent.map((a) => (
            <ActionCard key={a.id} id={a.id} compact />
          ))}
        </Section>
      )}
    </div>
  );
}
