import { useEffect, useState } from 'react';
import { useAuth } from '../../App';
import { coworkerApi, errorMessage, timeAgo } from '../api';
import { useCoworker } from '../CoworkerContext';
import { Card, Pill, Section, dangerBtn, ghostBtn, inputCls, primaryBtn } from '../ui';

const LEVEL_HELP: Record<string, string> = {
  suggest: 'Prepare it; I send it myself',
  approve: 'Ask me first',
  notify: 'Do it, then tell me',
  silent: 'Just do it',
};

export function ConnectionsPanel({ returnTo = '/app/coworker/settings' }: { returnTo?: string }) {
  const { token } = useAuth();
  const { connections, capabilities, coworker, refresh } = useCoworker();
  const api = coworkerApi(token);
  const [slackToken, setSlackToken] = useState('');
  const [hubspotToken, setHubspotToken] = useState('');
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);

  const connectGoogle = async (level: 'read' | 'act') => {
    try {
      localStorage.setItem('coworker_return_to', returnTo);
      const d = await api.post('/connections/google/start', { level });
      window.location.href = d.url;
    } catch (e) {
      setMsg(errorMessage(e));
    }
  };
  const connectSlackOAuth = async () => {
    try {
      localStorage.setItem('coworker_return_to', returnTo);
      window.location.href = (await api.post('/connections/slack/start')).url;
    } catch (e) {
      setMsg(errorMessage(e));
    }
  };
  const saveSlackToken = async () => {
    setBusy(true);
    try {
      const d = await api.post('/connections/slack/token', { token: slackToken });
      setMsg(`Connected Slack (${d.team}).`);
      setSlackToken('');
      await refresh();
    } catch (e) {
      setMsg(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  const connectHubspotOAuth = async () => {
    try {
      localStorage.setItem('coworker_return_to', returnTo);
      window.location.href = (await api.post('/connections/hubspot/start')).url;
    } catch (e) {
      setMsg(errorMessage(e));
    }
  };
  const saveHubspotToken = async () => {
    setBusy(true);
    try {
      const d = await api.post('/connections/hubspot/token', { token: hubspotToken });
      setMsg(`Connected HubSpot (${d.portal}).`);
      setHubspotToken('');
      await refresh();
    } catch (e) {
      setMsg(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  const disconnect = async (provider: string) => {
    if (!confirm(`Disconnect ${provider}? I'll revoke access and delete everything I synced from it.`)) return;
    await api.del(`/connections/${provider}`);
    await refresh();
  };
  const syncNow = async () => {
    setBusy(true);
    setMsg('Syncing…');
    try {
      await api.post('/sync?rebuild=1');
      // Sync runs in the background; poll until it finishes (or 2 minutes pass).
      for (let i = 0; i < 80; i++) {
        const st = await api.get('/sync/status');
        if (!st.running) {
          const job = st.job || {};
          if (job.status === 'error') setMsg(`Sync failed: ${job.error}`);
          else setMsg(`Synced: ${Object.entries(job.counts || {}).map(([k, v]) => `${k} +${v}`).join(', ') || 'no new items'}.`);
          break;
        }
        setMsg(`Syncing… ${st.total} items so far.`);
        await new Promise((r) => setTimeout(r, 1500));
      }
      await refresh();
    } catch (e) {
      setMsg(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const conn = (p: string) => connections.find((c) => c.provider === p);
  const google = conn('google');
  const slack = conn('slack');
  const hubspot = conn('hubspot');
  const canSend = google?.scopes?.includes('gmail.send');

  return (
    <div className="space-y-3">
      {coworker?.mode === 'demo' && (
        <Card className="p-4 flex items-center gap-3">
          <span className="text-xl" aria-hidden>🧪</span>
          <div className="flex-1">
            <p className="text-sm font-medium">Anote demo workspace</p>
            <p className="text-xs text-gray-500">Fictional inbox, Slack, calendar, and docs. Connecting a real account replaces it.</p>
          </div>
          <Pill tone="blue">Demo</Pill>
        </Card>
      )}
      <Card className="p-4">
        <div className="flex items-center gap-3">
          <span className="text-xl" aria-hidden>📧</span>
          <div className="flex-1">
            <p className="text-sm font-medium">Google: Gmail, Calendar, Drive</p>
            <p className="text-xs text-gray-500">
              {google
                ? `${google.account || 'Connected'} · ${google.status}${google.lastSyncedAt ? ` · synced ${timeAgo(google.lastSyncedAt)}` : ''}`
                : capabilities?.google ? 'Read access first. I ask for send access when a responsibility needs it.' : 'Not configured on this server (set GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET).'}
            </p>
            {google?.error && <p className="text-xs text-red-500 mt-1">{google.error}</p>}
          </div>
          {google ? (
            <div className="flex gap-2">
              {!canSend && <button className={ghostBtn} onClick={() => connectGoogle('act')}>Allow sending</button>}
              {google.status === 'reauth_required' && <button className={primaryBtn} onClick={() => connectGoogle('read')}>Reconnect</button>}
              <button className={ghostBtn} onClick={() => disconnect('google')}>Disconnect</button>
            </div>
          ) : (
            <button className={primaryBtn} disabled={!capabilities?.google} onClick={() => connectGoogle('read')}>Connect</button>
          )}
        </div>
      </Card>
      <Card className="p-4">
        <div className="flex items-center gap-3">
          <span className="text-xl" aria-hidden>💬</span>
          <div className="flex-1">
            <p className="text-sm font-medium">Slack</p>
            <p className="text-xs text-gray-500">
              {slack ? `${slack.account} · ${slack.status}` : 'Connect with OAuth, or paste a user token (xoxp-…) from a Slack app you installed.'}
            </p>
          </div>
          {slack ? (
            <button className={ghostBtn} onClick={() => disconnect('slack')}>Disconnect</button>
          ) : capabilities?.slack_oauth ? (
            <button className={primaryBtn} onClick={connectSlackOAuth}>Connect</button>
          ) : null}
        </div>
        {!slack && (
          <div className="flex gap-2 mt-3">
            <input className={inputCls} placeholder="xoxp-…" value={slackToken} onChange={(e) => setSlackToken(e.target.value)} />
            <button className={ghostBtn} disabled={busy || !slackToken.startsWith('xoxp-')} onClick={saveSlackToken}>Use token</button>
          </div>
        )}
      </Card>
      <Card className="p-4">
        <div className="flex items-center gap-3">
          <span className="text-xl" aria-hidden>📇</span>
          <div className="flex-1">
            <p className="text-sm font-medium">HubSpot CRM</p>
            <p className="text-xs text-gray-500">
              {hubspot
                ? `${hubspot.account} · ${hubspot.status}. Approved CRM updates log a note on the contact and company.`
                : 'Approved CRM updates from calls go here. Connect with OAuth, or paste a private app token (pat-…).'}
            </p>
            {hubspot?.error && <p className="text-xs text-red-500 mt-1">{hubspot.error}</p>}
          </div>
          {hubspot ? (
            <button className={ghostBtn} onClick={() => disconnect('hubspot')}>Disconnect</button>
          ) : capabilities?.hubspot_oauth ? (
            <button className={primaryBtn} onClick={connectHubspotOAuth}>Connect</button>
          ) : null}
        </div>
        {!hubspot && (
          <div className="flex gap-2 mt-3">
            <input className={inputCls} placeholder="pat-…" value={hubspotToken} onChange={(e) => setHubspotToken(e.target.value)} />
            <button className={ghostBtn} disabled={busy || !hubspotToken.startsWith('pat-')} onClick={saveHubspotToken}>Use token</button>
          </div>
        )}
      </Card>
      {coworker?.mode === 'live' && (
        <button className={ghostBtn} disabled={busy} onClick={syncNow}>Sync now</button>
      )}
      {msg && <p className="text-sm text-gray-600 dark:text-gray-300">{msg}</p>}
    </div>
  );
}

export default function SettingsTab() {
  const { token } = useAuth();
  const { coworker, refresh } = useCoworker();
  const api = coworkerApi(token);
  const [autonomy, setAutonomy] = useState<any>(null);
  const [form, setForm] = useState<Record<string, any>>({});
  const [saved, setSaved] = useState('');

  useEffect(() => {
    api.get('/autonomy').then(setAutonomy);
  }, []);
  useEffect(() => {
    if (!coworker) return;
    const s = coworker.settings || {};
    setForm({
      displayName: coworker.displayName, persona: coworker.persona, company_name: s.company_name || '',
      company_domain: s.company_domain || '', timezone: s.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
      start: s.working_hours?.start ?? 9, end: s.working_hours?.end ?? 17, disclosure_text: s.disclosure_text || '',
      send_delay_seconds: s.send_delay_seconds ?? (coworker.mode === 'demo' ? 0 : 20),
    });
  }, [coworker?.id]);

  if (!coworker) return null;
  const set = (k: string, v: any) => setForm((f) => ({ ...f, [k]: v }));
  const save = async () => {
    await api.patch('', {
      displayName: form.displayName, persona: form.persona,
      settings: {
        company_name: form.company_name, company_domain: form.company_domain, timezone: form.timezone,
        working_hours: { start: Number(form.start), end: Number(form.end), days: [0, 1, 2, 3, 4] },
        disclosure_text: form.disclosure_text, send_delay_seconds: Number(form.send_delay_seconds),
      },
    });
    await refresh();
    setSaved('Saved.');
    setTimeout(() => setSaved(''), 2000);
  };
  const setLevel = async (type: string, level: string) => {
    setAutonomy(await api.put('/autonomy', { [type]: level }));
  };
  const exportData = async () => {
    const data = await api.get('/export');
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = 'ourogen-coworker-export.json';
    a.click();
    URL.revokeObjectURL(url);
  };
  const deleteAll = async () => {
    if (!confirm('Delete your coworker? This revokes Google and Slack access and deletes every email, memory, action, call, and twin file it stored. This cannot be undone.')) return;
    await api.del('/data');
    await refresh();
    window.location.href = '/app';
  };
  const resetDemo = async () => {
    if (!confirm('Reset the demo workspace? This clears actions, activity, and memory and reseeds the demo data.')) return;
    await api.post('/demo/reset');
    await refresh();
  };

  return (
    <div>
      <Section title="Connections" subtitle="Where your coworker reads from and acts through.">
        <ConnectionsPanel />
      </Section>

      {autonomy && (
        <Section title="Autonomy" subtitle="How much I can do on my own, per kind of action.">
          <Card className="divide-y divide-gray-100 dark:divide-gray-700/70">
            {Object.entries(autonomy.types as Record<string, string>).map(([type, label]) => (
              <div key={type} className="flex items-center gap-3 px-4 py-3">
                <span className="text-sm flex-1">{label}</span>
                <select className={`${inputCls} w-auto`} value={autonomy.levels[type]} onChange={(e) => setLevel(type, e.target.value)}>
                  {autonomy.options.map((o: string) => <option key={o} value={o}>{o}: {LEVEL_HELP[o]}</option>)}
                </select>
              </div>
            ))}
          </Card>
          <div className="mt-3 rounded-xl bg-[#F7F7F8] dark:bg-[#2F2F2F] px-4 py-3">
            <p className="text-xs font-medium mb-1">Always asks first, whatever the setting:</p>
            <ul className="text-xs text-gray-600 dark:text-gray-300 list-disc pl-4 space-y-0.5">
              {autonomy.hardFloors.map((f: string) => <li key={f}>{f}</li>)}
            </ul>
          </div>
        </Section>
      )}

      {form.timezone !== undefined && <Section title="Identity & preferences">
        <Card className="p-4 grid gap-3 sm:grid-cols-2">
          <label className="text-sm">Coworker name<input className={`${inputCls} mt-1`} value={form.displayName || ''} onChange={(e) => set('displayName', e.target.value)} /></label>
          <label className="text-sm">Time zone<input className={`${inputCls} mt-1`} value={form.timezone || ''} onChange={(e) => set('timezone', e.target.value)} /></label>
          <label className="text-sm">Company name<input className={`${inputCls} mt-1`} value={form.company_name || ''} onChange={(e) => set('company_name', e.target.value)} /></label>
          <label className="text-sm">Company email domain<input className={`${inputCls} mt-1`} placeholder="anote.ai" value={form.company_domain || ''} onChange={(e) => set('company_domain', e.target.value)} /></label>
          <label className="text-sm">Working hours start<input type="number" min={0} max={23} className={`${inputCls} mt-1`} value={form.start} onChange={(e) => set('start', e.target.value)} /></label>
          <label className="text-sm">Working hours end<input type="number" min={1} max={24} className={`${inputCls} mt-1`} value={form.end} onChange={(e) => set('end', e.target.value)} /></label>
          <label className="text-sm sm:col-span-2">AI disclosure footer on emails
            <input className={`${inputCls} mt-1`} placeholder={`Sent by ${coworker.ownerName.split(' ')[0] || 'your'}'s AI coworker (Ourogen) on their behalf.`}
              value={form.disclosure_text || ''} onChange={(e) => set('disclosure_text', e.target.value)} />
            <span className="text-xs text-gray-500">You can reword it. Emails I send without your approval always carry it.</span>
          </label>
          <label className="text-sm">Undo window for emails (seconds)<input type="number" min={0} max={300} className={`${inputCls} mt-1`} value={form.send_delay_seconds} onChange={(e) => set('send_delay_seconds', e.target.value)} /></label>
          <label className="text-sm sm:col-span-2">Extra instructions for your coworker
            <textarea className={`${inputCls} mt-1 min-h-[80px]`} placeholder="e.g. Our ICP is 20–200 person funds. Never offer discounts."
              value={form.persona || ''} onChange={(e) => set('persona', e.target.value)} />
          </label>
          <div className="sm:col-span-2 flex items-center gap-3">
            <button className={primaryBtn} onClick={save}>Save</button>
            {saved && <span className="text-sm text-gray-500">{saved}</span>}
          </div>
        </Card>
      </Section>}

      <Section title="Notifications" subtitle="Emails to you, sent from your own Gmail when I have send access.">
        <Card className="divide-y divide-gray-100 dark:divide-gray-700/70">
          {[
            ['notify_approvals', 'Email me when actions are waiting for approval', 'At most one email every 30 minutes, batched.', true],
            ['digest_email', 'Email me the daily digest', 'What I did, what is waiting, and what needs you, around 5pm.', false],
          ].map(([key, label, help, dflt]) => {
            const on = (coworker.settings || {})[key as string] ?? dflt;
            return (
              <label key={key as string} className="flex items-start gap-3 px-4 py-3 cursor-pointer">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={Boolean(on)}
                  onChange={async (e) => {
                    await api.patch('', { settings: { [key as string]: e.target.checked } });
                    await refresh();
                  }}
                />
                <span className="text-sm">
                  {label}
                  <span className="block text-xs text-gray-500">{help}</span>
                </span>
              </label>
            );
          })}
        </Card>
      </Section>

      <PlanSection />

      <Section title="Your data" subtitle="Download everything your coworker stored, or delete it all.">
        <div className="flex flex-wrap gap-2">
          <button className={ghostBtn} onClick={exportData}>Download my data (JSON)</button>
          <button className={dangerBtn} onClick={deleteAll}>Delete my coworker and all its data</button>
        </div>
      </Section>

      {coworker.mode === 'demo' && (
        <Section title="Demo workspace">
          <button className={dangerBtn} onClick={resetDemo}>Reset demo data</button>
        </Section>
      )}
    </div>
  );
}

function PlanSection() {
  const { token } = useAuth();
  const api = coworkerApi(token);
  const [b, setB] = useState<any>(null);
  const [msg, setMsg] = useState('');
  useEffect(() => {
    api.get('/billing').then(setB).catch(() => {});
  }, []);
  if (!b) return null;
  const upgrade = async (plan: string) => {
    try {
      window.location.href = (await api.post('/billing/checkout', { plan })).url;
    } catch (e) {
      setMsg(errorMessage(e));
    }
  };
  return (
    <Section title="Plan & usage" subtitle="Prices are early hypotheses. Pilot users are free.">
      <Card className="p-4 mb-3 grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
        <div><p className="text-lg font-semibold">{b.planName}</p><p className="text-xs text-gray-500">current plan</p></div>
        <div>
          <p className={`text-lg font-semibold tabular-nums ${b.warn ? 'text-amber-600' : ''}`}>{b.callMinutes}{b.callMinutesIncluded ? ` / ${b.callMinutesIncluded}` : ''}</p>
          <p className="text-xs text-gray-500">call minutes this month</p>
        </div>
        <div><p className="text-lg font-semibold tabular-nums">{b.actionsExecuted}</p><p className="text-xs text-gray-500">actions completed</p></div>
        <div><p className="text-lg font-semibold tabular-nums">${b.estimatedCostUsd}</p><p className="text-xs text-gray-500">est. cost to serve</p></div>
      </Card>
      <div className="grid gap-3 sm:grid-cols-3">
        {b.plans.filter((p: any) => p.id !== 'pilot').map((p: any) => (
          <Card key={p.id} className="p-4 flex flex-col">
            <p className="text-sm font-medium">{p.name}</p>
            <p className="text-xl font-semibold mt-1">${p.priceUsd}<span className="text-xs font-normal text-gray-500">/mo</span></p>
            <p className="text-xs text-gray-500 mt-1 flex-1">{p.features.join(', ').replace(/_/g, ' ')}</p>
            <button className={`${ghostBtn} mt-3`} disabled={!p.available || b.plan === p.id} onClick={() => upgrade(p.id)}>
              {b.plan === p.id ? 'Current' : p.available ? 'Upgrade' : 'Coming soon'}
            </button>
          </Card>
        ))}
      </div>
      {msg && <p className="text-sm text-red-500 mt-2">{msg}</p>}
    </Section>
  );
}
