import { useEffect, useState } from 'react';
import { useAuth } from '../../App';
import { coworkerApi, errorMessage, timeAgo } from '../api';
import { useCoworker } from '../CoworkerContext';
import type { Responsibility, Suggestion } from '../types';
import { Card, Empty, Pill, Section, ghostBtn, inputCls, primaryBtn } from '../ui';

const AUTONOMY_HELP: Record<string, string> = {
  suggest: 'I prepare it, you send it',
  approve: 'I ask before acting',
  notify: 'I act, then tell you',
  silent: 'I act; it shows in the log',
};

export default function ResponsibilitiesTab() {
  const { token } = useAuth();
  const { version, tick } = useCoworker();
  const api = coworkerApi(token);
  const [items, setItems] = useState<Responsibility[]>([]);
  const [templates, setTemplates] = useState<any[]>([]);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [custom, setCustom] = useState('');
  const [msg, setMsg] = useState('');

  const load = async () => {
    const d = await api.get('/responsibilities');
    setItems(d.responsibilities || []);
    setTemplates(d.templates || []);
    setSuggestions(d.suggestions || []);
  };
  useEffect(() => {
    load();
  }, [version]);

  const add = async (body: any) => {
    setMsg('');
    try {
      const d = await api.post('/responsibilities', body);
      setMsg(d.results?.length ? `Started: ${d.results.join('; ')}. Check Approvals.` : 'Added. I’ll act when something matches.');
      setCustom('');
      load();
      tick(true);
    } catch (e) {
      setMsg(errorMessage(e));
    }
  };
  const update = async (id: number, body: any) => {
    await api.patch(`/responsibilities/${id}`, body);
    load();
  };
  const remove = async (id: number) => {
    await api.del(`/responsibilities/${id}`);
    load();
  };
  const runNow = async (id: number) => {
    const d = await api.post(`/responsibilities/${id}/run`);
    setMsg(d.results?.length ? d.results.join('; ') : 'Nothing new to do right now.');
    tick(true);
  };

  const owned = new Set(items.map((i) => i.template));
  return (
    <div>
      {msg && <p className="mb-4 text-sm rounded-lg bg-[#F7F7F8] dark:bg-[#2F2F2F] px-3 py-2">{msg}</p>}
      {suggestions.length > 0 && (
        <Section title="Suggested for you" subtitle="Based on what's in your inbox, calendar, and Slack right now.">
          <div className="grid gap-3 sm:grid-cols-2">
            {suggestions.map((s) => (
              <Card key={s.template} className="p-4 flex flex-col">
                <p className="text-sm font-medium">{s.name}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 flex-1">{s.why}</p>
                <button className={`${primaryBtn} mt-3 self-start`} onClick={() => add({ template: s.template })}>Take this on</button>
              </Card>
            ))}
          </div>
        </Section>
      )}

      <Section title="What I'm responsible for" subtitle="Standing jobs I do without being asked each time.">
        {items.length === 0 ? (
          <Empty title="No responsibilities yet">Pick a suggestion above, or tell me in chat: “From now on, handle inbound leads.”</Empty>
        ) : (
          <div className="space-y-3">
            {items.map((r) => (
              <Card key={r.id} className="p-4">
                <div className="flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium">{r.name}</p>
                      {r.enabled ? <Pill tone="green">On</Pill> : <Pill>Paused</Pill>}
                    </div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{r.instruction}</p>
                    <p className="text-xs text-gray-400 mt-1.5">
                      {r.runs} actions so far{r.lastRunAt ? ` · last checked ${timeAgo(r.lastRunAt)}` : ''} · {r.escalation}
                    </p>
                  </div>
                  <label className="flex items-center gap-2 text-xs">
                    <input type="checkbox" checked={r.enabled} onChange={(e) => update(r.id, { enabled: e.target.checked })} />
                    Enabled
                  </label>
                </div>
                <div className="flex flex-wrap items-center gap-2 mt-3">
                  <select className={`${inputCls} w-auto text-xs py-1.5`} value={r.autonomy} onChange={(e) => update(r.id, { autonomy: e.target.value })}>
                    {Object.entries(AUTONOMY_HELP).map(([k, v]) => <option key={k} value={k}>{k}: {v}</option>)}
                  </select>
                  <button className={ghostBtn} onClick={() => runNow(r.id)}>Run now</button>
                  <button className={`${ghostBtn} text-red-600 dark:text-red-400`} onClick={() => remove(r.id)}>Remove</button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </Section>

      <Section title="Add a responsibility">
        <div className="flex gap-2 mb-3">
          <input className={inputCls} placeholder="e.g. Flag anything about the Series A from investors"
            value={custom} onChange={(e) => setCustom(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && custom.trim() && add({ instruction: custom })} />
          <button className={primaryBtn} disabled={!custom.trim()} onClick={() => add({ instruction: custom })}>Add</button>
        </div>
        <div className="flex flex-wrap gap-2">
          {templates.filter((t) => !owned.has(t.id)).map((t) => (
            <button key={t.id} className={ghostBtn} title={t.description} onClick={() => add({ template: t.id })}>+ {t.name}</button>
          ))}
        </div>
      </Section>
    </div>
  );
}
