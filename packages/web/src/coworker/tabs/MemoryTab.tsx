import { useEffect, useState } from 'react';
import { useAuth } from '../../App';
import { coworkerApi, timeAgo } from '../api';
import { useCoworker } from '../CoworkerContext';
import type { Citation, Learned, Person } from '../types';
import { Card, Pill, RELATIONSHIP_TONE, Section, ghostBtn, inputCls, primaryBtn } from '../ui';

const RELATIONSHIPS = ['prospect', 'customer', 'investor', 'teammate', 'candidate', 'partner', 'vendor', 'contact'];

export default function MemoryTab() {
  const { token } = useAuth();
  const { version } = useCoworker();
  const api = coworkerApi(token);
  const [learned, setLearned] = useState<Learned | null>(null);
  const [people, setPeople] = useState<Person[]>([]);
  const [decisions, setDecisions] = useState<any[]>([]);
  const [q, setQ] = useState('');
  const [results, setResults] = useState<Citation[] | null>(null);
  const [rule, setRule] = useState('');

  const load = async () => {
    const [l, p, d] = await Promise.all([api.get('/memory/learned'), api.get('/memory/people'), api.get('/memory/timeline', { kind: 'decision' })]);
    setLearned(l);
    setPeople(p.people || []);
    setDecisions(d.entries || []);
  };
  useEffect(() => {
    load();
  }, [version]);

  const search = async () => {
    if (!q.trim()) return;
    setResults((await api.get('/memory/recall', { q })).results || []);
  };
  const editPerson = async (id: number, body: any) => {
    await api.patch(`/memory/people/${id}`, body);
    load();
  };
  const forgetPerson = async (id: number) => {
    await api.del(`/memory/people/${id}`);
    load();
  };
  const forget = async (id: number) => {
    await api.del(`/memory/${id}`);
    load();
  };
  const addRule = async () => {
    if (!rule.trim()) return;
    await api.post('/style/rules', { rule });
    setRule('');
    load();
  };
  const clearRules = async () => {
    await api.del('/style/rules');
    load();
  };

  return (
    <div>
      <Section title="Ask my memory" subtitle="Search across email, Slack, meetings, docs, and decisions.">
        <div className="flex gap-2">
          <input className={inputCls} placeholder="e.g. SOC 2, Northwind pricing, Beta Corp" value={q}
            onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && search()} />
          <button className={primaryBtn} onClick={search}>Search</button>
        </div>
        {results && (
          <Card className="mt-3 divide-y divide-gray-100 dark:divide-gray-700/70">
            {results.length === 0 && <p className="px-4 py-3 text-sm text-gray-500">Nothing found.</p>}
            {results.map((r) => (
              <div key={`${r.type}-${r.id}`} className="px-4 py-2.5 text-sm">
                <p className="font-medium">{r.type === 'decision' ? `Decision: ${r.title}` : r.title}</p>
                <p className="text-xs text-gray-500">{r.from ? `${r.from} · ` : ''}{r.date?.slice(0, 10)}</p>
                <p className="text-gray-600 dark:text-gray-300 mt-0.5 line-clamp-2">{r.snippet || r.detail}</p>
              </div>
            ))}
          </Card>
        )}
      </Section>

      {learned && (
        <Section title="Your work at a glance" subtitle={learned.role_guess}>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              ['People', learned.counts.people], ['Active threads', learned.counts.active_threads],
              ['Meetings', learned.counts.meetings], ['Decisions', learned.counts.decisions],
            ].map(([label, n]) => (
              <Card key={label as string} className="px-4 py-3">
                <p className="text-2xl font-semibold tabular-nums">{n}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
              </Card>
            ))}
          </div>
        </Section>
      )}

      <Section title="People" subtitle="Fix anything I got wrong. Edits stick, and forgotten people stay forgotten.">
        <Card className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-gray-500 dark:text-gray-400">
              <tr>
                <th className="px-4 py-2 font-medium">Name</th>
                <th className="px-4 py-2 font-medium">Company & role</th>
                <th className="px-4 py-2 font-medium">Relationship</th>
                <th className="px-4 py-2 font-medium">Last contact</th>
                <th />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700/70">
              {people.map((p) => (
                <tr key={p.id}>
                  <td className="px-4 py-2">
                    <p className="font-medium">{p.name}</p>
                    <p className="text-xs text-gray-500">{p.email}</p>
                  </td>
                  <td className="px-4 py-2 text-gray-600 dark:text-gray-300">
                    {[p.role, p.company].filter(Boolean).join(', ') || '—'}
                  </td>
                  <td className="px-4 py-2">
                    <select className="bg-transparent text-xs border border-gray-200 dark:border-gray-600 rounded px-1.5 py-1" value={p.relationship}
                      onChange={(e) => editPerson(p.id, { relationship: e.target.value })}>
                      {RELATIONSHIPS.map((r) => <option key={r} value={r}>{r}</option>)}
                    </select>
                  </td>
                  <td className="px-4 py-2 text-xs text-gray-500 whitespace-nowrap">{timeAgo(p.last_contact_at)}</td>
                  <td className="px-4 py-2 text-right">
                    <button className="text-xs text-gray-400 hover:text-red-500" title="Forget this person" onClick={() => forgetPerson(p.id)}>✕</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </Section>

      {learned && learned.deals.length > 0 && (
        <Section title="Active relationships">
          <div className="grid gap-3 sm:grid-cols-2">
            {learned.deals.map((d) => (
              <Card key={d.company} className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium">{d.company}</p>
                  <Pill tone={RELATIONSHIP_TONE[d.relationship]}>{d.relationship}</Pill>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {d.waiting_on === 'them' ? 'Waiting on them' : d.waiting_on === 'you' ? 'Waiting on you' : ''}
                  {d.days_since_last != null ? ` · ${d.days_since_last}d since last message` : ''}
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-300 mt-1 truncate">{d.last}</p>
              </Card>
            ))}
          </div>
        </Section>
      )}

      <Section title="Decisions you made" subtitle="I use these to answer questions and to avoid re-opening closed topics.">
        <Card className="divide-y divide-gray-100 dark:divide-gray-700/70">
          {decisions.length === 0 && <p className="px-4 py-3 text-sm text-gray-500">No decisions found yet.</p>}
          {decisions.map((d) => (
            <div key={d.id} className="px-4 py-2.5 flex gap-3 text-sm">
              <div className="flex-1">
                <p>{d.title}</p>
                {d.detail && <p className="text-xs text-gray-500 mt-0.5">{d.detail}</p>}
              </div>
              <span className="text-xs text-gray-400">{d.occurred_at?.slice(0, 10)}</span>
              <button className="text-xs text-gray-400 hover:text-red-500" onClick={() => forget(d.id)}>✕</button>
            </div>
          ))}
        </Card>
      </Section>

      {learned?.style && (
        <Section title="How you write" subtitle={`Learned from ${learned.style.sample_size || 0} messages you sent.`}
          action={learned.style.rules?.length ? <button className={ghostBtn} onClick={clearRules}>Clear rules</button> : undefined}>
          <Card className="p-4">
            <p className="text-sm">{learned.style.summary}</p>
            <div className="flex gap-2 mt-3">
              <input className={inputCls} placeholder="Add a rule, e.g. “Keep emails under 100 words”" value={rule}
                onChange={(e) => setRule(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && addRule()} />
              <button className={primaryBtn} onClick={addRule}>Add</button>
            </div>
          </Card>
        </Section>
      )}
    </div>
  );
}
