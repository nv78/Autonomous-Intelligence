import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../App';
import { coworkerApi, errorMessage, timeAgo } from '../api';
import { useCoworker } from '../CoworkerContext';
import type { Responsibility, Suggestion } from '../types';
import { Card, Empty, Pill, Section, ghostBtn, inputCls, primaryBtn } from '../ui';
import ScheduleEditor from '../ScheduleEditor';

function when(iso: string | null) {
  if (!iso) return '';
  return new Date(iso).toLocaleString(undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
}

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
  const [editing, setEditing] = useState<number | null>(null);
  const [newTask, setNewTask] = useState('');
  const [recipes, setRecipes] = useState<any[]>([]);
  const nav = useNavigate();

  const load = async () => {
    const d = await api.get('/responsibilities');
    setItems(d.responsibilities || []);
    setTemplates(d.templates || []);
    setSuggestions(d.suggestions || []);
    api.get('/recipes').then((r) => setRecipes(r.recipes || [])).catch(() => {});
  };
  useEffect(() => {
    load();
  }, [version]);

  const add = async (body: any) => {
    setMsg('');
    try {
      const d = await api.post('/responsibilities', body);
      setMsg(d.results?.length ? `Started: ${d.results.join('; ')}. Check Approvals.`
        : d.responsibility?.schedule ? `Scheduled: ${d.responsibility.schedule.description}. First run ${d.responsibility.schedule.nextRunLabel || when(d.responsibility.schedule.nextRun)}.`
          : 'Added. I’ll act when something matches.');
      setCustom('');
      load();
      tick(true);
    } catch (e) {
      setMsg(errorMessage(e));
    }
  };
  const update = async (id: number, body: any) => {
    setMsg('');
    try {
      await api.patch(`/responsibilities/${id}`, body);
      setEditing(null);
      load();
    } catch (e) {
      setMsg(errorMessage(e));
    }
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
                    {r.schedule ? (
                      <div className="mt-1.5 space-y-1">
                        <p className="text-xs text-gray-600 dark:text-gray-300">
                          ⏰ {r.schedule.description}{r.enabled && r.schedule.nextRun ? ` · next ${r.schedule.nextRunLabel || when(r.schedule.nextRun)}` : ''}
                          {r.schedule.deliver.filter((d) => d !== 'chat').length > 0 && ` · also by ${r.schedule.deliver.filter((d) => d !== 'chat').join(' and ')}`}
                        </p>
                        {r.schedule.usage && r.schedule.usage.runs > 0 && (
                          <p className="text-xs text-gray-500">
                            Last 30 days: {r.schedule.usage.runs} run{r.schedule.usage.runs === 1 ? '' : 's'}
                            {r.schedule.usage.costUsd != null ? ` · $${r.schedule.usage.costUsd.toFixed(2)} in AI usage` : ''}
                            {r.schedule.usage.actions ? ` · ${r.schedule.usage.executed}/${r.schedule.usage.actions} actions sent` : ''}
                            {` · ~${r.schedule.usage.hoursSaved}h saved`}
                          </p>
                        )}
                        {r.schedule.runs.slice(0, 3).map((run, i) => (
                          <p key={i} className="text-xs text-gray-400 truncate">
                            {run.status === 'failed' ? '⚠️' : '✓'} {timeAgo(run.at)}: {run.summary}
                          </p>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-gray-400 mt-1.5">
                        {r.runs} actions so far{r.lastRunAt ? ` · last checked ${timeAgo(r.lastRunAt)}` : ''} · {r.escalation}
                      </p>
                    )}
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
                  {r.schedule && <button className={ghostBtn} onClick={() => setEditing(editing === r.id ? null : r.id)}>Edit schedule</button>}
                  {r.schedule?.chatId && <button className={ghostBtn} onClick={() => nav(`/app/chat/${r.schedule!.chatId}`)}>Open its chat</button>}
                  <button className={`${ghostBtn} text-red-600 dark:text-red-400`} onClick={() => remove(r.id)}>Remove</button>
                </div>
                {editing === r.id && (
                  <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700/70">
                    <ScheduleEditor initial={r.trigger} onSave={(schedule) => update(r.id, { schedule })} onCancel={() => setEditing(null)} />
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}
      </Section>

      <Section title="Scheduled tasks" subtitle="Recurring work I do on a clock, in your time zone. Or just tell me in chat: “Every Monday at 9, post the pipeline in #sales.”">
        <div className="grid gap-3 sm:grid-cols-2 mb-4">
          {recipes.filter((r) => !r.enabled).map((r) => (
            <Card key={r.id} className="p-4 flex flex-col">
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium flex-1">⏰ {r.name}</p>
                <span className="text-xs text-gray-500">{r.when}</span>
              </div>
              {r.why && <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">{r.why}</p>}
              <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">{r.instruction}</p>
              <p className="text-xs text-gray-400 mt-1 flex-1 italic">e.g. “{r.sample}”</p>
              <button className={`${primaryBtn} mt-3 self-start`}
                onClick={() => add({ name: r.name, instruction: r.instruction, schedule: r.schedule, runNow: false })}>Turn on</button>
            </Card>
          ))}
        </div>
        <Card className="p-4 space-y-3">
          <input className={inputCls} placeholder="What should I do each time? e.g. Summarize new support tickets and post them in #support"
            value={newTask} onChange={(e) => setNewTask(e.target.value)} />
          <ScheduleEditor saveLabel="Add scheduled task"
            onSave={(schedule) => newTask.trim() && add({ instruction: newTask, schedule, runNow: false }).then(() => setNewTask(''))} />
        </Card>
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
