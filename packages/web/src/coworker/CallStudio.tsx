import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../App';
import ActionCard from './ActionCard';
import AvatarStage, { useAssetUrl } from './AvatarStage';
import { coworkerApi, errorMessage } from './api';
import { useCoworker } from './CoworkerContext';
import { Speaker, createRecognizer, hasSpeechRecognition, type Recognizer } from './speech';
import { Card, Pill, ghostBtn, inputCls, primaryBtn } from './ui';

export interface MeetingT {
  id: number;
  title: string;
  mode: 'live_call' | 'simulated' | 'bot';
  platform: string;
  meetingUrl: string;
  prospectName: string;
  prospectCompany: string;
  status: string;
  transcript: { speaker: string; text: string; at: string; kind?: string }[];
  whispers: { text: string }[];
  summary: any;
  answers: Record<string, any>;
  metrics: Record<string, any>;
  startedAt: string;
}

const QUAL_LABELS: Record<string, string> = {
  need: 'Need', current_process: 'Current process', team_size: 'Seats', decision_maker: 'Decision maker',
  timeline: 'Timeline', budget: 'Budget',
};

export default function CallStudio({ meeting: initial, onClose }: { meeting: MeetingT; onClose: () => void }) {
  const { token } = useAuth();
  const { coworker, capabilities, tick } = useCoworker();
  const api = coworkerApi(token);
  const [meeting, setMeeting] = useState<MeetingT>(initial);
  const [speaking, setSpeaking] = useState(false);
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState('');
  const [typed, setTyped] = useState('');
  const [whisper, setWhisper] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [latencies, setLatencies] = useState<{ think: number; voice: number }[]>([]);
  const [autoplay, setAutoplay] = useState(initial.mode === 'simulated');
  const [twinPhoto, setTwinPhoto] = useState<number | null>(null);
  const speaker = useRef<Speaker | null>(null);
  const recognizer = useRef<Recognizer | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const nextLine = useRef<string | null>(null);
  const autoRef = useRef(autoplay);
  const photoUrl = useAssetUrl(twinPhoto);
  autoRef.current = autoplay;

  const ended = meeting.status !== 'active';
  const name = coworker?.displayName || 'AI coworker';

  useEffect(() => {
    api.get('/twin').then((t) => setTwinPhoto(t.photoAssetId)).catch(() => {});
    const sp = new Speaker(token, !!capabilities?.voice);
    sp.onChange = setSpeaking;
    speaker.current = sp;
    const opener = initial.transcript[0]?.text;
    api.get(`/meetings/${initial.id}`).then((d) => {
      nextLine.current = d.nextProspectLine;
      if (opener && initial.mode !== 'bot') {
        sp.speak(opener).then(() => {
          if (initial.mode === 'simulated') runProspect();
        });
      }
    });
    return () => {
      sp.stop();
      recognizer.current?.stop();
    };
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [meeting.transcript.length, interim]);

  // Bot mode: the conversation happens in the real meeting; poll the transcript.
  useEffect(() => {
    if (meeting.mode !== 'bot' || ended) return;
    const h = setInterval(async () => {
      const d = await api.get(`/meetings/${meeting.id}`);
      setMeeting(d.meeting);
    }, 3000);
    return () => clearInterval(h);
  }, [meeting.mode, ended]);

  const send = async (text: string) => {
    if (!text.trim() || ended) return;
    speaker.current?.stop();
    setBusy(true);
    setErr('');
    setMeeting((m) => ({ ...m, transcript: [...m.transcript, { speaker: 'prospect', text, at: new Date().toISOString() }] }));
    const t0 = performance.now();
    try {
      const d = await api.post(`/meetings/${meeting.id}/turn`, { text });
      const think = performance.now() - t0;
      setMeeting(d.meeting);
      nextLine.current = d.nextProspectLine;
      if (d.reply) {
        const { firstAudioMs } = await speakAndMeasure(d.reply, think);
        setLatencies((l) => [...l, { think: Math.round(think), voice: Math.round(think + firstAudioMs) }]);
      }
      if (d.ended) {
        await finish();
        return;
      }
      if (meeting.mode === 'simulated' && autoRef.current) runProspect();
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const speakAndMeasure = async (text: string, _think: number) => {
    const sp = speaker.current;
    if (!sp) return { firstAudioMs: 0 };
    return sp.speak(text);
  };

  const runProspect = async () => {
    const line = nextLine.current;
    if (!line) {
      if (autoRef.current) await finish();
      return;
    }
    await new Promise((r) => setTimeout(r, 400));
    await speaker.current?.speak(line, { voiceHint: 'prospect' });
    if (!autoRef.current) return;
    await send(line);
  };

  const toggleMic = () => {
    if (listening) {
      recognizer.current?.stop();
      setListening(false);
      return;
    }
    const rec = createRecognizer({
      onFinal: (text) => {
        setInterim('');
        if (text) send(text);
      },
      onInterim: setInterim,
      onSpeechStart: () => speaker.current?.speaking && speaker.current.stop(), // barge-in
      onError: (e) => setErr(`Microphone: ${e}`),
    });
    if (!rec) return;
    recognizer.current = rec;
    rec.start();
    setListening(true);
  };

  const sendWhisper = async () => {
    if (!whisper.trim()) return;
    const d = await api.post(`/meetings/${meeting.id}/turn`, { text: whisper, speaker: 'owner' });
    setMeeting(d.meeting);
    setWhisper('');
  };

  const finish = async () => {
    setAutoplay(false);
    recognizer.current?.stop();
    setListening(false);
    speaker.current?.stop();
    const d = await api.post(`/meetings/${meeting.id}/end`);
    setMeeting(d.meeting);
    tick(true);
  };

  const avg = (k: 'think' | 'voice') => (latencies.length ? Math.round(latencies.reduce((a, b) => a + b[k], 0) / latencies.length) : null);
  const s = meeting.summary;

  return (
    <div className="fixed inset-0 z-50 bg-white dark:bg-[#212121] overflow-y-auto">
      <div className="max-w-5xl mx-auto px-4 py-4">
        <div className="flex items-center gap-3 mb-4">
          <button className="text-sm text-gray-500 hover:underline" onClick={onClose}>← Back</button>
          <h2 className="font-semibold flex-1 truncate">{meeting.title}</h2>
          {!ended ? <Pill tone="red">● Live</Pill> : <Pill>Ended</Pill>}
          {!ended && <button className={primaryBtn} onClick={finish}>End call</button>}
        </div>

        <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
          <Card className="p-5 flex flex-col items-center gap-4">
            <AvatarStage name={name} ownerName={coworker?.ownerName} photoUrl={photoUrl} speaking={speaking} listening={listening} />
            <p className="text-xs text-center text-gray-500 dark:text-gray-400">
              {capabilities?.voice ? 'Speaking with your AI voice.' : 'Using the browser voice. Add ElevenLabs for your cloned voice.'}
            </p>
            {meeting.mode === 'live_call' && !ended && (
              hasSpeechRecognition() ? (
                <button className={listening ? `${primaryBtn} bg-red-600 hover:bg-red-700 dark:bg-red-500` : primaryBtn} onClick={toggleMic}>
                  {listening ? '■ Stop listening' : '🎙️ Start talking'}
                </button>
              ) : (
                <p className="text-xs text-amber-700 dark:text-amber-300 text-center">Voice input needs Chrome or Edge. Type below instead.</p>
              )
            )}
            {meeting.mode === 'simulated' && !ended && (
              <div className="flex gap-2">
                <button className={ghostBtn} onClick={() => { setAutoplay((a) => !a); if (!autoplay) runProspect(); }}>
                  {autoplay ? '⏸ Pause' : '▶ Resume'}
                </button>
              </div>
            )}
            {meeting.mode === 'bot' && (
              <p className="text-xs text-center text-gray-500">Bot in {meeting.platform.replace('_', ' ')}: {meeting.meetingUrl}</p>
            )}
            <div className="w-full grid grid-cols-2 gap-2 text-center">
              <div className="rounded-lg bg-[#F7F7F8] dark:bg-[#2F2F2F] py-2">
                <p className="text-lg font-semibold tabular-nums">{avg('think') ?? '—'}<span className="text-xs font-normal"> ms</span></p>
                <p className="text-[11px] text-gray-500">avg think time</p>
              </div>
              <div className="rounded-lg bg-[#F7F7F8] dark:bg-[#2F2F2F] py-2">
                <p className="text-lg font-semibold tabular-nums">{avg('voice') ?? '—'}<span className="text-xs font-normal"> ms</span></p>
                <p className="text-[11px] text-gray-500">avg to first audio</p>
              </div>
            </div>
            {!ended && (
              <div className="w-full">
                <p className="text-xs font-medium mb-1">Whisper to your coworker</p>
                <div className="flex gap-2">
                  <input className={inputCls} placeholder="Only it sees this" value={whisper} onChange={(e) => setWhisper(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && sendWhisper()} />
                  <button className={ghostBtn} onClick={sendWhisper}>Send</button>
                </div>
              </div>
            )}
          </Card>

          <div className="space-y-4">
            <Card className="p-4">
              {meeting.metrics?.consent === 'pending' && (
                <p className="mb-3 rounded-lg bg-[#F7F7F8] dark:bg-[#2F2F2F] px-3 py-2 text-xs text-gray-600 dark:text-gray-300">
                  Notes are off until they agree to them. Their words aren't saved until then.
                </p>
              )}
              {meeting.metrics?.consent === 'granted' && (
                <p className="mb-3 text-xs text-gray-500 dark:text-gray-400">✓ They agreed to notes.</p>
              )}
              <div className="space-y-3 max-h-[55vh] overflow-y-auto pr-1">
                {meeting.transcript.map((t, i) => (
                  <div key={i} className={`flex ${t.speaker === 'coworker' ? '' : 'justify-end'}`}>
                    <div className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-sm ${
                      t.speaker === 'coworker' ? 'bg-[#F7F7F8] dark:bg-[#2F2F2F]' : 'bg-black text-white dark:bg-white dark:text-black'
                    }`}>
                      <p className="text-[11px] opacity-60 mb-0.5">
                        {t.speaker === 'coworker' ? name : meeting.prospectName || 'Them'}
                        {t.kind && t.kind !== 'agent' ? ` · ${t.kind}` : ''}
                      </p>
                      {(t as any).redacted ? <span className="italic opacity-70">Not recorded (no consent yet)</span> : t.text}
                    </div>
                  </div>
                ))}
                {interim && <p className="text-right text-sm text-gray-400 italic">{interim}…</p>}
                {busy && <p className="text-sm text-gray-400">…</p>}
                <div ref={endRef} />
              </div>
              {meeting.mode === 'live_call' && !ended && (
                <div className="flex gap-2 mt-3">
                  <input className={inputCls} placeholder="Or type what the prospect says" value={typed}
                    onChange={(e) => setTyped(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') { send(typed); setTyped(''); } }} />
                  <button className={ghostBtn} onClick={() => { send(typed); setTyped(''); }}>Send</button>
                </div>
              )}
              {err && <p className="text-xs text-red-500 mt-2">{err}</p>}
            </Card>

            {!ended && (
              <Card className="p-4">
                <p className="text-sm font-medium mb-2">Qualification so far</p>
                <div className="grid sm:grid-cols-2 gap-x-4 gap-y-1 text-sm">
                  {Object.entries(QUAL_LABELS).map(([k, label]) => (
                    <p key={k} className="truncate">
                      <span className="text-gray-500">{label}: </span>
                      {meeting.answers[k] ? <span title={meeting.answers[k]}>✓ {String(meeting.answers[k]).slice(0, 60)}</span> : <span className="text-gray-400">—</span>}
                    </p>
                  ))}
                </div>
              </Card>
            )}

            {ended && s && (
              <Card className="p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <p className="font-medium">Call summary</p>
                  <Pill tone={s.hot ? 'red' : s.score >= 40 ? 'amber' : 'gray'}>{s.hot ? '🔥 Hot lead' : `Score ${s.score}/100`}</Pill>
                </div>
                <p className="text-sm whitespace-pre-wrap">{s.text}</p>
                {s.escalations?.length > 0 && (
                  <p className="text-sm text-amber-700 dark:text-amber-300">Escalated to you: {s.escalations.join('; ')}</p>
                )}
                <div>
                  <p className="text-sm font-medium">Action items</p>
                  <ul className="text-sm list-disc pl-5">{s.action_items.map((a: string) => <li key={a}>{a}</li>)}</ul>
                </div>
                {s.followup_action_id && <ActionCard id={s.followup_action_id} />}
                <p className="text-xs text-gray-500">A CRM update is waiting in Approvals, and the transcript is now part of your coworker's memory.</p>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
