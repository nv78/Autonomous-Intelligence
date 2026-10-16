import { useEffect, useState } from 'react';
import { useAuth } from '../../App';
import { coworkerApi, errorMessage } from '../api';
import { API_BASE_URL } from '../../constants/constants';
import { Card, Empty, Pill, Section, dangerBtn, ghostBtn, inputCls, primaryBtn } from '../ui';

const LEVEL_LABEL: Record<string, string> = {
  suggest: 'Prepare only', approve: 'Ask first', notify: 'Do it, then tell', silent: 'Just do it',
};
const TYPES: Record<string, string> = {
  'email.send': 'Send email', 'slack.post': 'Post on Slack', 'calendar.create': 'Send calendar invites', 'crm.update': 'Update CRM',
};

/** Team plan: your organization, its members, and the rules every member's coworker follows. */
export default function TeamTab() {
  const { token } = useAuth();
  const api = coworkerApi(token);
  const [org, setOrg] = useState<any>(undefined);
  const [models, setModels] = useState<any[]>([]);
  const [form, setForm] = useState({ name: '', domain: '' });
  const [invite, setInvite] = useState({ email: '', role: 'member' });
  const [policies, setPolicies] = useState<any>({});
  const [blocked, setBlocked] = useState('');
  const [domain, setDomain] = useState('');
  const [msg, setMsg] = useState('');
  const [link, setLink] = useState('');
  const [scimToken, setScimToken] = useState('');

  const load = async () => {
    const d = await api.get('/org');
    setOrg(d.org);
    setPolicies(d.org?.policies || {});
    setBlocked((d.org?.policies?.blocked_domains || []).join('\n'));
    setDomain(d.org?.domain || '');
  };
  useEffect(() => {
    load().catch(() => setOrg(null));
    api.get('/models').then((d) => setModels(d.models || [])).catch(() => {});
  }, []);

  const run = async (fn: () => Promise<any>, ok = '') => {
    setMsg('');
    try {
      await fn();
      if (ok) setMsg(ok);
      await load();
    } catch (e) {
      setMsg(errorMessage(e));
    }
  };

  if (org === undefined) return null;

  if (!org) {
    return (
      <Section title="Team" subtitle="Give everyone on your team an AI coworker that follows the same rules.">
        <Card className="p-5 space-y-3 max-w-lg">
          <p className="text-sm text-gray-600 dark:text-gray-300">
            Create an organization, invite teammates, and set rules their coworkers can't override: when to ask first,
            domains never to email, recording consent, and which AI models are allowed.
          </p>
          <input className={inputCls} placeholder="Organization name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input className={inputCls} placeholder="Company domain (e.g. acme.com)" value={form.domain} onChange={(e) => setForm({ ...form, domain: e.target.value })} />
          <button className={primaryBtn} disabled={!form.name.trim()} onClick={() => run(() => api.post('/org', form))}>Create organization</button>
          {msg && <p className="text-sm text-red-500">{msg}</p>}
        </Card>
      </Section>
    );
  }

  const isAdmin = org.role === 'admin';
  const ceiling = policies.autonomy_ceiling || {};
  const allowed: string[] = policies.allowed_models || [];
  const savePolicies = () =>
    run(() => api.patch('/org', {
      domain,
      policies: { ...policies, blocked_domains: blocked.split(/[\n,]/).map((d) => d.trim()).filter(Boolean) },
    }), 'Saved. Every member’s coworker follows these rules now.');

  return (
    <div className="space-y-8">
      <Section title={org.name} subtitle={`${org.domain ? `${org.domain} · ` : ''}${org.seats} seat${org.seats === 1 ? '' : 's'} · you're ${isAdmin ? 'an admin' : 'a member'}`}>
        <Card className="divide-y divide-gray-100 dark:divide-gray-700/70">
          {org.members.map((m: any) => (
            <div key={m.id} className="flex items-center gap-3 px-4 py-3">
              <div className="flex-1 min-w-0">
                <p className="text-sm truncate">{m.email}</p>
                {m.usage && (
                  <p className="text-xs text-gray-500">
                    {m.usage.status} · {m.usage.executed} done · {m.usage.acceptance != null ? `${Math.round(m.usage.acceptance * 100)}% approved unedited · ` : ''}
                    ~{m.usage.hoursSaved}h saved · {m.usage.callMinutes} call min
                    {m.usage.taskSpendUsd ? ` · $${m.usage.taskSpendUsd.toFixed(2)} scheduled-task AI` : ''} (30 days)
                  </p>
                )}
              </div>
              {m.status === 'invited' && <Pill tone="amber">Invited</Pill>}
              <Pill tone={m.role === 'admin' ? 'blue' : 'gray'}>{m.role}</Pill>
              {isAdmin && (
                <>
                  <button className={ghostBtn} onClick={() => run(() => api.patch(`/org/members/${m.id}`, { role: m.role === 'admin' ? 'member' : 'admin' }))}>
                    {m.role === 'admin' ? 'Make member' : 'Make admin'}
                  </button>
                  <button className={ghostBtn}
                    onClick={() => confirm(`Remove ${m.email}? Their coworker is paused and every connection revoked.`) && run(() => api.del(`/org/members/${m.id}`), `Removed ${m.email}.`)}>
                    Remove
                  </button>
                </>
              )}
            </div>
          ))}
          {org.members.length === 0 && <Empty title="No members yet" />}
        </Card>
        {isAdmin && (
          <div className="flex flex-wrap gap-2 mt-3">
            <input className={`${inputCls} flex-1 min-w-[220px]`} placeholder="teammate@company.com" value={invite.email}
              onChange={(e) => setInvite({ ...invite, email: e.target.value })} />
            <select className={`${inputCls} w-auto`} value={invite.role} onChange={(e) => setInvite({ ...invite, role: e.target.value })}>
              <option value="member">Member</option>
              <option value="admin">Admin</option>
            </select>
            <button className={primaryBtn} disabled={!invite.email.includes('@')}
              onClick={() => run(async () => {
                const d = await api.post('/org/invites', invite);
                setLink(d.invite.url);
                setInvite({ email: '', role: 'member' });
              }, 'Invite sent.')}>
              Invite
            </button>
          </div>
        )}
        {link && (
          <p className="text-xs text-gray-500 mt-2 break-all">
            If the email doesn't arrive, share this link (it only works for that address): <span className="font-mono">{link}</span>
          </p>
        )}
      </Section>

      <Section title="Team rules" subtitle={isAdmin ? 'Ceilings: members can be stricter, never looser.' : 'Set by your admins. Your coworker follows them.'}>
        <Card className="p-4 space-y-4">
          <div>
            <p className="text-sm font-medium mb-2">Most autonomy a member's coworker may have</p>
            <div className="grid gap-2 sm:grid-cols-2">
              {Object.entries(TYPES).map(([type, label]) => (
                <label key={type} className="flex items-center justify-between gap-3 text-sm">
                  <span>{label}</span>
                  <select className={`${inputCls} w-auto`} disabled={!isAdmin} value={ceiling[type] || ''}
                    onChange={(e) => setPolicies({ ...policies, autonomy_ceiling: { ...ceiling, [type]: e.target.value || undefined } })}>
                    <option value="">No limit</option>
                    {Object.entries(LEVEL_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                </label>
              ))}
            </div>
          </div>
          <div>
            <p className="text-sm font-medium mb-1">Never send to these domains</p>
            <textarea className={`${inputCls} min-h-[70px] font-mono`} disabled={!isAdmin} placeholder={'competitor.com\nrival.io'}
              value={blocked} onChange={(e) => setBlocked(e.target.value)} />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" disabled={!isAdmin} checked={policies.recording_consent === 'all_party'}
              onChange={(e) => setPolicies({ ...policies, recording_consent: e.target.checked ? 'all_party' : '' })} />
            Always ask everyone on a call for consent before taking notes
          </label>
          <div>
            <p className="text-sm font-medium mb-1">Allowed AI models <span className="text-gray-500 font-normal">(none checked = any)</span></p>
            <div className="flex flex-wrap gap-3">
              {models.map((m) => (
                <label key={m.id} className="flex items-center gap-1.5 text-sm">
                  <input type="checkbox" disabled={!isAdmin} checked={allowed.includes(m.id)}
                    onChange={(e) => setPolicies({ ...policies, allowed_models: e.target.checked ? [...allowed, m.id] : allowed.filter((x) => x !== m.id) })} />
                  {m.label}
                </label>
              ))}
            </div>
          </div>
          <div className="space-y-2 border-t border-gray-100 dark:border-gray-700/70 pt-4">
            <p className="text-sm font-medium">Sign-in</p>
            <input className={`${inputCls} max-w-xs`} disabled={!isAdmin} placeholder="Company domain (e.g. acme.com)"
              value={domain} onChange={(e) => setDomain(e.target.value)} />
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" disabled={!isAdmin} checked={!!policies.sso_required}
                onChange={(e) => setPolicies({ ...policies, sso_required: e.target.checked })} />
              Members must sign in with Google or Microsoft (no passwords)
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" disabled={!isAdmin} checked={!!policies.domain_auto_join}
                onChange={(e) => setPolicies({ ...policies, domain_auto_join: e.target.checked })} />
              Anyone who signs in with Google or Microsoft at {domain ? `@${domain}` : 'your domain'} joins automatically
            </label>
            {isAdmin && (
              <div className="text-sm space-y-2 pt-1">
                <p className="font-medium">Provisioning (SCIM) {org.scim && <span className="text-xs text-green-600 font-normal">on</span>}</p>
                <p className="text-xs text-gray-500">
                  Let Okta, Microsoft Entra, or another identity provider add and remove people. Base URL:{' '}
                  <span className="font-mono">{API_BASE_URL}/api/coworker/scim/v2</span>
                </p>
                <div className="flex gap-2">
                  <button className={ghostBtn} onClick={() => run(async () => setScimToken((await api.post('/org/scim-token')).token))}>
                    {org.scim ? 'Rotate token' : 'Create token'}
                  </button>
                  {org.scim && <button className={ghostBtn} onClick={() => confirm('Turn off SCIM? Your identity provider will stop syncing.') && run(() => api.del('/org/scim-token'))}>Turn off</button>}
                </div>
                {scimToken && (
                  <p className="text-xs break-all">Copy it now; it won't be shown again: <span className="font-mono">{scimToken}</span></p>
                )}
              </div>
            )}
          </div>
          {isAdmin && <button className={primaryBtn} onClick={savePolicies}>Save rules</button>}
        </Card>
      </Section>

      {!isAdmin && (
        <button className={dangerBtn} onClick={() => confirm('Leave this organization?') && run(() => api.post('/org/leave'))}>Leave organization</button>
      )}
      {msg && <p className="text-sm text-gray-600 dark:text-gray-300">{msg}</p>}
    </div>
  );
}
