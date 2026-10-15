import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../../App';
import { coworkerApi, errorMessage, timeAgo } from '../api';
import CallStudio, { type MeetingT } from '../CallStudio';
import { useCoworker } from '../CoworkerContext';
import { Card, Empty, Pill, Section, ghostBtn, inputCls, primaryBtn } from '../ui';

export default function CallsTab() {
  const { token } = useAuth();
  const { capabilities, version } = useCoworker();
  const api = coworkerApi(token);
  const [meetings, setMeetings] = useState<MeetingT[]>([]);
  const [personas, setPersonas] = useState<any[]>([]);
  const [playbook, setPlaybook] = useState<any>(null);
  const [active, setActive] = useState<MeetingT | null>(null);
  const [form, setForm] = useState({ prospectName: '', prospectCompany: '', prospectEmail: '', meetingUrl: '' });
  const [msg, setMsg] = useState('');
  const [saved, setSaved] = useState('');

  const load = async () => {
    const [m, pb] = await Promise.all([api.get('/meetings'), api.get('/playbook')]);
    setMeetings(m.meetings || []);
    setPersonas(pb.personas || []);
    setPlaybook(pb.playbook);
  };
  useEffect(() => {
    load();
  }, [version]);
  // Deep link from a chat card or the Today view: /app/coworker/calls?meeting=12
  const [params, setParams] = useSearchParams();
  useEffect(() => {
    const id = params.get('meeting');
    if (!id) return;
    api.get(`/meetings/${id}`).then((d) => setActive(d.meeting)).catch(() => {});
    setParams({}, { replace: true });
  }, [params.get('meeting')]);

  const start = async (body: any) => {
    setMsg('');
    try {
      const d = await api.post('/meetings', body);
      setActive(d.meeting);
    } catch (e) {
      setMsg(errorMessage(e));
    }
  };
  const savePlaybook = async () => {
    const d = await api.put('/playbook', {
      pitch: playbook.pitch, icp: playbook.icp, goals: playbook.goals, pricing_notes: playbook.pricing_notes,
      escalate: playbook.escalate, self_demo: playbook.self_demo,
    });
    setPlaybook(d.playbook);
    setSaved('Saved.');
    setTimeout(() => setSaved(''), 2000);
  };

  if (active) return <CallStudio meeting={active} onClose={() => { setActive(null); load(); }} />;

  return (
    <div>
      <Section title="Let your coworker take the call" subtitle="It opens every call by saying it's your AI, asks discovery questions, answers from your playbook, escalates anything it shouldn't decide, and follows up.">
        <div className="grid gap-3 sm:grid-cols-3">
          <Card className="p-4 flex flex-col">
            <p className="text-sm font-medium">🎬 Watch a demo call</p>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 flex-1">A scripted prospect talks to your coworker out loud, start to finish.</p>
            <div className="flex flex-col gap-2 mt-3">
              {personas.map((p) => (
                <button key={p.id} className={ghostBtn} onClick={() => start({ mode: 'simulated', persona: p.id })}>
                  {p.id === 'ourogen' ? 'Coworker pitches itself' : `${p.name}, ${p.company}`}
                </button>
              ))}
            </div>
          </Card>
          <Card className="p-4 flex flex-col">
            <p className="text-sm font-medium">🎙️ Practice call</p>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">You play the prospect. Talk out loud (Chrome) and it talks back in real time.</p>
            <div className="space-y-2 mt-3 flex-1">
              <input className={inputCls} placeholder="Prospect name" value={form.prospectName} onChange={(e) => setForm({ ...form, prospectName: e.target.value })} />
              <input className={inputCls} placeholder="Company" value={form.prospectCompany} onChange={(e) => setForm({ ...form, prospectCompany: e.target.value })} />
              <input className={inputCls} placeholder="Email (for the follow-up)" value={form.prospectEmail} onChange={(e) => setForm({ ...form, prospectEmail: e.target.value })} />
            </div>
            <button className={`${primaryBtn} mt-3`} onClick={() => start({ mode: 'live_call', ...form, title: form.prospectCompany ? `Call with ${form.prospectCompany}` : '' })}>
              Start call
            </button>
          </Card>
          <Card className="p-4 flex flex-col">
            <p className="text-sm font-medium">📞 Join a real meeting</p>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 flex-1">
              Paste a Zoom, Google Meet, or Teams link. The bot joins as “your AI coworker (Ourogen)” and posts a disclosure in chat.
            </p>
            <input className={`${inputCls} mt-3`} placeholder="https://zoom.us/j/…" value={form.meetingUrl} onChange={(e) => setForm({ ...form, meetingUrl: e.target.value })} />
            <button className={`${primaryBtn} mt-2`} disabled={!capabilities?.meeting_bot || !form.meetingUrl}
              onClick={() => start({ mode: 'bot', ...form })}>
              {capabilities?.meeting_bot ? 'Send my coworker' : 'Needs RECALL_API_KEY'}
            </button>
          </Card>
        </div>
        {msg && <p className="text-sm text-red-500 mt-3">{msg}</p>}
      </Section>

      <Section title="Past calls">
        {meetings.length === 0 ? (
          <Empty title="No calls yet">Try “Watch a demo call” to see it work.</Empty>
        ) : (
          <Card className="divide-y divide-gray-100 dark:divide-gray-700/70">
            {meetings.map((m) => (
              <button key={m.id} className="w-full text-left px-4 py-3 hover:bg-gray-50 dark:hover:bg-white/5" onClick={() => setActive(m)}>
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium flex-1 truncate">{m.title}</p>
                  {m.summary?.hot && <Pill tone="red">🔥 Hot</Pill>}
                  {m.summary && !m.summary.hot && <Pill>Score {m.summary.score}</Pill>}
                  <Pill tone={m.status === 'active' ? 'green' : 'gray'}>{m.status}</Pill>
                </div>
                <p className="text-xs text-gray-500 mt-0.5">
                  {m.mode.replace('_', ' ')} · {m.transcript.length} turns · {timeAgo(m.startedAt)}
                </p>
              </button>
            ))}
          </Card>
        )}
      </Section>

      {playbook && (
        <Section title="Call playbook" subtitle="What your coworker may say. Anything outside it gets escalated to you."
          action={saved ? <span className="text-sm text-gray-500">{saved}</span> : undefined}>
          <Card className="p-4 grid gap-3">
            <label className="text-sm">Pitch<textarea className={`${inputCls} mt-1 min-h-[70px]`} value={playbook.pitch || ''} onChange={(e) => setPlaybook({ ...playbook, pitch: e.target.value })} /></label>
            <label className="text-sm">Ideal customer<input className={`${inputCls} mt-1`} value={playbook.icp || ''} onChange={(e) => setPlaybook({ ...playbook, icp: e.target.value })} /></label>
            <label className="text-sm">Pricing it may state<textarea className={`${inputCls} mt-1 min-h-[60px]`} value={playbook.pricing_notes || ''} onChange={(e) => setPlaybook({ ...playbook, pricing_notes: e.target.value })} /></label>
            <label className="text-sm">Always escalate (comma-separated)
              <input className={`${inputCls} mt-1`} value={(playbook.escalate || []).join(', ')}
                onChange={(e) => setPlaybook({ ...playbook, escalate: e.target.value.split(',').map((x: string) => x.trim()).filter(Boolean) })} />
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={!!playbook.self_demo} onChange={(e) => setPlaybook({ ...playbook, self_demo: e.target.checked })} />
              Self-demo mode: on Ourogen's own sales calls, the coworker points out what it's doing live
            </label>
            <div><button className={primaryBtn} onClick={savePlaybook}>Save playbook</button></div>
          </Card>
        </Section>
      )}
    </div>
  );
}
