import { useEffect, useState } from 'react';
import { useAuth } from '../../App';
import { coworkerApi, errorMessage, timeAgo } from '../api';
import { useCoworker } from '../CoworkerContext';
import { Card, Pill, Section, dangerBtn, ghostBtn, inputCls, primaryBtn } from '../ui';
import TextMessagesCard from '../TextMessagesCard';
import EmailAddressCard from '../EmailAddressCard';

const LEVEL_HELP: Record<string, string> = {
  suggest: 'Prepare it; I send it myself',
  approve: 'Ask me first',
  notify: 'Do it, then tell me',
  silent: 'Just do it',
};

const MAILBOXES = [
  { provider: 'google', label: 'Google: Gmail, Calendar, Drive', icon: '📧', sendScope: 'gmail.send', env: 'GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET' },
  { provider: 'microsoft', label: 'Microsoft 365: Outlook mail and calendar', icon: '📨', sendScope: 'Mail.Send', env: 'MICROSOFT_CLIENT_ID / MICROSOFT_CLIENT_SECRET' },
] as const;

const CRMS = [
  { provider: 'hubspot', label: 'HubSpot CRM', what: 'a note on the contact and company', tokenHint: 'a private app token (pat-…)',
    placeholder: 'pat-…', valid: (t: string) => t.startsWith('pat-') },
  { provider: 'salesforce', label: 'Salesforce', what: 'a completed call task on the contact and account', tokenHint: '',
    placeholder: '', valid: () => false },
  { provider: 'pipedrive', label: 'Pipedrive', what: 'a note on the person and organization',
    tokenHint: 'your API token (Pipedrive → Personal preferences → API)', placeholder: 'Pipedrive API token',
    valid: (t: string) => t.trim().length >= 20 },
] as const;

export function ConnectionsPanel({ returnTo = '/app/coworker/settings' }: { returnTo?: string }) {
  const { token } = useAuth();
  const { connections, capabilities, coworker, refresh } = useCoworker();
  const api = coworkerApi(token);
  const [slackToken, setSlackToken] = useState('');
  const [crmTokens, setCrmTokens] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);

  const connectMailbox = async (provider: 'google' | 'microsoft', level: 'read' | 'act') => {
    try {
      localStorage.setItem('coworker_return_to', returnTo);
      const d = await api.post(`/connections/${provider}/start`, { level });
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
  const connectCrmOAuth = async (provider: string) => {
    try {
      localStorage.setItem('coworker_return_to', returnTo);
      window.location.href = (await api.post(`/connections/${provider}/start`)).url;
    } catch (e) {
      setMsg(errorMessage(e));
    }
  };
  const saveCrmToken = async (c: (typeof CRMS)[number]) => {
    setBusy(true);
    try {
      const d = await api.post(`/connections/${c.provider}/token`, { token: crmTokens[c.provider] || '' });
      setMsg(`Connected ${c.label} (${d.portal || d.company || ''}).`);
      setCrmTokens((t) => ({ ...t, [c.provider]: '' }));
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
  const slack = conn('slack');

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
      {MAILBOXES.map((box) => {
        const c = conn(box.provider);
        const configured = capabilities?.[box.provider];
        const canSend = c?.scopes?.includes(box.sendScope);
        return (
          <Card key={box.provider} className="p-4">
            <div className="flex items-center gap-3">
              <span className="text-xl" aria-hidden>{box.icon}</span>
              <div className="flex-1">
                <p className="text-sm font-medium">{box.label}</p>
                <p className="text-xs text-gray-500">
                  {c
                    ? `${c.account || 'Connected'} · ${c.status === 'reauth_required' ? 'needs reconnecting' : c.status}${c.lastSyncedAt ? ` · synced ${timeAgo(c.lastSyncedAt)}` : ''}`
                    : configured ? 'Read access first. I ask for send access when a responsibility needs it.' : `Not configured on this server (set ${box.env}).`}
                </p>
                {c?.error && <p className="text-xs text-red-500 mt-1">{c.error}</p>}
              </div>
              {c ? (
                <div className="flex gap-2">
                  {c.status === 'reauth_required'
                    ? <button className={primaryBtn} onClick={() => connectMailbox(box.provider, canSend ? 'act' : 'read')}>Reconnect</button>
                    : !canSend && <button className={ghostBtn} onClick={() => connectMailbox(box.provider, 'act')}>Allow sending</button>}
                  <button className={ghostBtn} onClick={() => disconnect(box.provider)}>Disconnect</button>
                </div>
              ) : (
                <button className={primaryBtn} disabled={!configured} onClick={() => connectMailbox(box.provider, 'read')}>Connect</button>
              )}
            </div>
          </Card>
        );
      })}
      <Card className="p-4">
        <div className="flex items-center gap-3">
          <span className="text-xl" aria-hidden>💬</span>
          <div className="flex-1">
            <p className="text-sm font-medium">Slack</p>
            <p className="text-xs text-gray-500">
              {slack ? `${slack.account} · ${slack.status}` : 'Connect with OAuth, or paste a user token (xoxp-…) from a Slack app you installed.'}
            </p>
            {slack?.bot && (
              <p className="text-xs text-gray-500 mt-1">
                Bot is on: @mention it in any channel or DM it. Your messages to it are commands; teammates' are questions it answers for you.
              </p>
            )}
          </div>
          {slack ? (
            <div className="flex gap-2">
              {slack.status === 'reauth_required' && capabilities?.slack_oauth && (
                <button className={primaryBtn} onClick={connectSlackOAuth}>Reconnect</button>
              )}
              {slack.status !== 'reauth_required' && slack.botAvailable && !slack.bot && capabilities?.slack_oauth && (
                <button className={primaryBtn} onClick={connectSlackOAuth} title="Reconnect once to add the @mentionable bot">Add the bot</button>
              )}
              <button className={ghostBtn} onClick={() => disconnect('slack')}>Disconnect</button>
            </div>
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
      {CRMS.map((c) => {
        const row = conn(c.provider);
        const oauth = Boolean(capabilities?.[`${c.provider}_oauth` as 'hubspot_oauth' | 'salesforce_oauth' | 'pipedrive_oauth']);
        const value = crmTokens[c.provider] || '';
        return (
          <Card key={c.provider} className="p-4">
            <div className="flex items-center gap-3">
              <span className="text-xl" aria-hidden>📇</span>
              <div className="flex-1">
                <p className="text-sm font-medium">{c.label}</p>
                <p className="text-xs text-gray-500">
                  {row
                    ? `${row.account} · ${row.status}. Approved CRM updates log ${c.what}.`
                    : `Approved CRM updates from calls go here.${c.tokenHint ? ` Connect with OAuth, or paste ${c.tokenHint}.` : ''}`}
                </p>
                {row?.error && <p className="text-xs text-red-500 mt-1">{row.error}</p>}
              </div>
              {row ? (
                <div className="flex gap-2">
                  {row.status === 'reauth_required' && oauth && (
                    <button className={primaryBtn} onClick={() => connectCrmOAuth(c.provider)}>Reconnect</button>
                  )}
                  <button className={ghostBtn} onClick={() => disconnect(c.provider)}>Disconnect</button>
                </div>
              ) : oauth ? (
                <button className={primaryBtn} onClick={() => connectCrmOAuth(c.provider)}>Connect</button>
              ) : !c.tokenHint ? (
                <span className="text-xs text-gray-400">Not configured on this server</span>
              ) : null}
            </div>
            {!row && c.tokenHint && (
              <div className="flex gap-2 mt-3">
                <input className={inputCls} placeholder={c.placeholder} value={value}
                  onChange={(e) => setCrmTokens((t) => ({ ...t, [c.provider]: e.target.value }))} />
                <button className={ghostBtn} disabled={busy || !c.valid(value)} onClick={() => saveCrmToken(c)}>Use token</button>
              </div>
            )}
          </Card>
        );
      })}
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

      <Section title="Notifications" subtitle="Emails to you, sent from your own mailbox when I have send access.">
        <Card className="divide-y divide-gray-100 dark:divide-gray-700/70">
          {[
            ['notify_approvals', 'Email me when actions are waiting for approval', 'At most one email every 30 minutes, batched.', true],
            ['digest_email', 'Email me the daily digest', 'What I did, what is waiting, and what needs you, around 5pm.', false],
            ['weekly_report', 'Email me a weekly report', 'Monday morning: time saved, what I did, and what I could take on next.', true],
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

      <TextMessagesCard />

      <EmailAddressCard />

      <Section title="Calls" subtitle="How your coworker handles recording on calls.">
        <Card className="p-4">
          <label className="text-sm block">
            Recording consent
            <select
              className={`${inputCls} mt-1`}
              value={(coworker.settings || {}).recording_consent || 'all_party'}
              onChange={async (e) => {
                await api.patch('', { settings: { recording_consent: e.target.value } });
                await refresh();
              }}
            >
              <option value="all_party">Everyone must agree before I take notes (recommended)</option>
              <option value="one_party">Disclose and take notes unless someone objects</option>
            </select>
          </label>
          <p className="mt-2 text-xs text-gray-500">
            California, Illinois, and the EU, among others, require everyone's consent. I always say I'm an AI and leave if asked.
          </p>
        </Card>
      </Section>

      <ModelSection />

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
  const { refresh } = useCoworker();
  const api = coworkerApi(token);
  const [b, setB] = useState<any>(null);
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState('');
  useEffect(() => {
    api.get('/billing').then(setB).catch(() => {});
  }, []);
  if (!b) return null;
  const change = async (plan: string, label: string, dir: string) => {
    if (dir === 'downgrade' && !confirm(plan === 'free'
      ? 'Move to Free at the end of your billing period? Calls and your twin turn off then.'
      : `Switch to ${label}? The difference is prorated on your next invoice.`)) return;
    setBusy(plan);
    setMsg('');
    try {
      const d = await api.post('/billing/change', { plan });
      if (d.status === 'checkout' && d.url) {
        window.location.href = d.url;
        return;
      }
      setB(d.billing);
      setMsg(d.status === 'scheduled' ? `You'll move to Free at the end of this billing period.` : `You're on ${label} now.`);
      await refresh();
    } catch (e) {
      setMsg(errorMessage(e));
    } finally {
      setBusy('');
    }
  };
  const portal = async () => {
    try {
      window.location.href = (await api.post('/billing/portal')).url;
    } catch (e) {
      setMsg(errorMessage(e));
    }
  };
  const pct = b.callMinutesIncluded ? Math.min(100, Math.round((b.callMinutes / b.callMinutesIncluded) * 100)) : 0;
  return (
    <Section title="Plan & usage" subtitle="Change plans anytime. Upgrades take effect now; prorated on your next invoice."
      action={b.hasBillingAccount ? <button className={ghostBtn} onClick={portal}>Invoices & payment</button> : undefined}>
      <Card className="p-4 mb-3">
        <div className="flex items-baseline justify-between gap-3">
          <p className="text-lg font-semibold">{b.planName}</p>
          {b.subscription?.cancel_at_period_end && <Pill tone="amber">Moves to Free at period end</Pill>}
        </div>
        {b.callMinutesIncluded > 0 && (
          <div className="mt-3">
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>Call minutes this month</span>
              <span className={b.warn ? 'text-amber-600 font-medium' : ''}>{b.callMinutes} / {b.callMinutesIncluded}</span>
            </div>
            <div className="h-1.5 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
              <div className={`h-full ${b.warn ? 'bg-amber-500' : 'bg-black dark:bg-white'}`} style={{ width: `${pct}%` }} />
            </div>
            {b.warn && <p className="text-xs text-amber-600 mt-1">You've used over 80% of your call minutes.</p>}
          </div>
        )}
        <p className="text-xs text-gray-500 mt-3">{b.actionsExecuted} actions completed this month.</p>
      </Card>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {b.plans.filter((p: any) => p.id !== 'pilot').map((p: any) => {
          const current = b.plan === p.id && !b.subscription?.cancel_at_period_end;
          const label = current ? 'Current plan' : !p.available ? 'Coming soon'
            : p.direction === 'upgrade' ? 'Upgrade' : p.direction === 'downgrade' ? 'Downgrade' : 'Switch';
          return (
            <Card key={p.id} className={`p-4 flex flex-col ${current ? 'ring-2 ring-black dark:ring-white' : ''}`}>
              <p className="text-sm font-medium">{p.name}</p>
              <p className="text-xl font-semibold mt-1">${p.priceUsd}<span className="text-xs font-normal text-gray-500">/mo</span></p>
              <p className="text-xs text-gray-500 mt-1 flex-1">
                {p.features.join(', ').replace(/_/g, ' ')}{p.callMinutes ? ` · ${p.callMinutes} call min` : ''}
              </p>
              <button className={`${p.direction === 'upgrade' && !current ? primaryBtn : ghostBtn} mt-3`}
                disabled={current || !p.available || !!busy} onClick={() => change(p.id, p.name, p.direction)}>
                {busy === p.id ? '…' : label}
              </button>
            </Card>
          );
        })}
      </div>
      {b.plan === 'pilot' && <p className="text-xs text-gray-500 mt-2">You're in the founder pilot: everything is included and free.</p>}
      {msg && <p className="text-sm mt-2">{msg}</p>}
    </Section>
  );
}

function ModelSection() {
  const { token } = useAuth();
  const { refresh } = useCoworker();
  const api = coworkerApi(token);
  const [models, setModels] = useState<any[]>([]);
  const [msg, setMsg] = useState('');
  useEffect(() => {
    api.get('/models').then((d) => setModels(d.models || [])).catch(() => {});
  }, []);
  if (!models.length) return null;
  const pick = async (id: string) => {
    setMsg('');
    try {
      await api.patch('', { settings: { model: id } });
      setModels((ms) => ms.map((m) => ({ ...m, selected: m.id === id })));
      await refresh();
      setMsg('Saved. New chats and calls use this model.');
    } catch (e) {
      setMsg(errorMessage(e));
    }
  };
  const groups: Record<string, string> = { anthropic: 'Anthropic', openai: 'OpenAI', google: 'Google', ollama: 'Local' };
  return (
    <Section title="Model" subtitle="Pick the AI that powers your coworker. The same guardrails apply to every model.">
      <Card className="divide-y divide-gray-100 dark:divide-gray-700/70">
        {models.map((m) => (
          <label key={m.id} className={`flex items-center gap-3 px-4 py-3 ${m.available ? 'cursor-pointer' : 'opacity-60'}`}>
            <input type="radio" name="model" checked={!!m.selected} disabled={!m.available} onChange={() => pick(m.id)} />
            <span className="flex-1 text-sm">
              {m.label} <span className="text-xs text-gray-500">· {groups[m.provider] || m.provider} · {m.note}</span>
            </span>
            {!m.available && (
              <span className="text-xs text-gray-500">
                {m.provider === 'ollama' ? 'Needs an Ollama server' : `Add ${m.provider === 'openai' ? 'an' : 'a'} ${groups[m.provider] || m.provider} key`}
              </span>
            )}
          </label>
        ))}
      </Card>
      <p className="text-xs text-gray-500 mt-2">
        Add your own OpenAI or Google key under your account settings (API keys) to unlock those models.
        Without any key, the coworker runs its built-in offline planner.
      </p>
      {msg && <p className="text-sm mt-2">{msg}</p>}
    </Section>
  );
}
