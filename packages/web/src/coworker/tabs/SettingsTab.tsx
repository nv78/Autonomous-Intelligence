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
  const disconnect = async (provider: string) => {
    if (!confirm(`Disconnect ${provider}? I'll revoke access and delete everything I synced from it.`)) return;
    await api.del(`/connections/${provider}`);
    await refresh();
  };
  const syncNow = async () => {
    setBusy(true);
    setMsg('Syncing…');
    try {
      const d = await api.post('/sync?rebuild=1');
      setMsg(`Synced: ${Object.entries(d.synced || {}).map(([k, v]) => `${k} +${v}`).join(', ') || 'no new items'}.`);
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

      {coworker.mode === 'demo' && (
        <Section title="Demo workspace">
          <button className={dangerBtn} onClick={resetDemo}>Reset demo data</button>
        </Section>
      )}
    </div>
  );
}
