import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../../App';
import AvatarStage, { useAssetUrl } from '../AvatarStage';
import { coworkerApi, errorMessage } from '../api';
import { useCoworker } from '../CoworkerContext';
import { Speaker, createRecognizer, hasSpeechRecognition, recordMedia } from '../speech';
import { Card, Pill, Section, dangerBtn, ghostBtn, inputCls, primaryBtn } from '../ui';

const SAMPLE_SCRIPT =
  "Hi, it's me. I want to walk you through how our team uses this every day. Honestly, the best part is how much " +
  "time it saves. We used to spend hours digging through documents, and now we just ask. Does that make sense? " +
  "Great. Let's find a time next week, maybe Tuesday or Wednesday afternoon, and I'll show you the rest.";

export default function TwinTab() {
  const { token, user } = useAuth();
  const { coworker, capabilities, refresh } = useCoworker();
  const api = coworkerApi(token);
  const [status, setStatus] = useState<any>(null);
  const [recording, setRecording] = useState<null | 'voice' | 'consent'>(null);
  const [challenge, setChallenge] = useState<{ id: number; phrase: string; code: string } | null>(null);
  const [transcript, setTranscript] = useState('');
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [tavusUrl, setTavusUrl] = useState('');
  const stopRef = useRef<null | (() => Promise<Blob>)>(null);
  const previewRef = useRef<HTMLVideoElement>(null);
  const recRef = useRef<ReturnType<typeof createRecognizer>>(null);
  const photoUrl = useAssetUrl(status?.photoAssetId);
  const videoUrl = useAssetUrl(status?.videoAssetId);

  const load = async () => setStatus(await api.get('/twin'));
  useEffect(() => {
    load();
  }, []);

  const upload = async (kind: string, file: Blob, filename: string) => {
    const form = new FormData();
    form.append('kind', kind);
    form.append('file', file, filename);
    await api.upload('/twin/assets', form);
    await load();
  };

  const recordVoice = async () => {
    setMsg('');
    try {
      const rec = await recordMedia('audio');
      stopRef.current = rec.stop;
      setRecording('voice');
    } catch (e) {
      setMsg(`Microphone unavailable: ${errorMessage(e)}`);
    }
  };
  const stopVoice = async () => {
    const blob = await stopRef.current!();
    setRecording(null);
    await upload('voice_sample', blob, 'voice-sample.webm');
    setMsg('Voice sample saved.');
  };

  const getChallenge = async () => {
    setMsg('');
    const d = await api.post('/twin/consent/challenge', { name: user?.name || coworker?.ownerName });
    setChallenge(d);
    setTranscript('');
  };

  const recordConsent = async () => {
    try {
      const rec = await recordMedia('video');
      stopRef.current = rec.stop;
      if (previewRef.current) {
        previewRef.current.srcObject = rec.stream;
        previewRef.current.play().catch(() => {});
      }
      setRecording('consent');
      const r = createRecognizer({ onFinal: (t) => setTranscript((prev) => `${prev} ${t}`.trim()) });
      recRef.current = r;
      r?.start();
    } catch (e) {
      setMsg(`Camera unavailable: ${errorMessage(e)}`);
    }
  };
  const stopConsent = async () => {
    recRef.current?.stop();
    const blob = await stopRef.current!();
    setRecording(null);
    if (previewRef.current) previewRef.current.srcObject = null;
    setBusy(true);
    try {
      const form = new FormData();
      form.append('consentId', String(challenge!.id));
      form.append('transcript', transcript);
      form.append('recording', blob, 'consent.webm');
      const res = await fetch(`${api.base}/twin/consent`, { method: 'POST', headers: api.headers, body: form });
      const d = await res.json();
      if (d.verified) {
        setMsg('Consent verified. You can now create your AI voice and likeness.');
        setChallenge(null);
      } else {
        const missing = Object.entries(d.checks || {}).filter(([, ok]) => !ok).map(([k]) => k);
        setMsg(`Couldn't verify (${missing.join(', ') || d.error}). Read the statement exactly, including the code, and try again.`);
      }
      await load();
    } finally {
      setBusy(false);
    }
  };

  const createVoice = async () => {
    setBusy(true);
    setMsg('');
    try {
      await api.post('/twin/voice');
      await load();
      await refresh();
      setMsg('Your AI voice is ready. Calls will use it from now on.');
    } catch (e) {
      setMsg(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const preview = async () => {
    const sp = new Speaker(token, !!capabilities?.voice);
    sp.onChange = setSpeaking;
    await sp.speak(`Hi, I'm ${coworker?.displayName}. I'm an AI, not ${coworker?.ownerName.split(' ')[0]}, and I'm here to help get things done.`);
  };

  const startTavus = async () => {
    try {
      setTavusUrl((await api.post('/twin/avatar/session')).url);
    } catch (e) {
      setMsg(errorMessage(e));
    }
  };

  const revoke = async () => {
    if (!confirm('Delete your AI voice, every uploaded file, and revoke consent? This cannot be undone.')) return;
    const d = await api.del('/twin');
    setMsg(`Deleted ${d.deletedFiles} files${d.voiceDeleted ? ' and your cloned voice' : ''}. Consent revoked.`);
    await load();
    await refresh();
  };

  if (!status) return <div className="h-40 animate-pulse" />;
  const samples = status.assets.filter((a: any) => a.kind !== 'photo');
  const consented = status.consent.voice_clone;

  return (
    <div>
      <Card className="p-5 mb-8 flex flex-col sm:flex-row items-center gap-6">
        <AvatarStage name={coworker?.displayName || 'AI coworker'} ownerName={coworker?.ownerName} photoUrl={photoUrl} videoUrl={videoUrl} speaking={speaking} />
        <div className="flex-1 space-y-2 text-sm">
          <p className="font-medium text-base">Your twin, on calls</p>
          <p className="text-gray-600 dark:text-gray-300">Your coworker can join calls with your voice and face. It always opens by saying it's your AI, and the AI badge is part of the frame.</p>
          <div className="flex flex-wrap gap-2">
            <Pill tone={consented ? 'green' : 'amber'}>{consented ? 'Consent verified' : 'Consent needed'}</Pill>
            <Pill tone={status.voiceId ? 'green' : 'gray'}>{status.voiceId ? 'Your voice' : 'Stock voice'}</Pill>
            <Pill tone={status.photoAssetId || status.videoAssetId ? 'green' : 'gray'}>{status.photoAssetId || status.videoAssetId ? 'Your likeness' : 'Initials avatar'}</Pill>
          </div>
          <div className="flex gap-2 pt-1">
            <button className={ghostBtn} onClick={preview}>▶ Preview</button>
            {status.avatarConfigured && consented && <button className={ghostBtn} onClick={startTavus}>Start live video avatar</button>}
          </div>
        </div>
      </Card>
      {tavusUrl && (
        <Card className="mb-8 overflow-hidden">
          <iframe src={tavusUrl} title="Video avatar" allow="camera; microphone; autoplay" className="w-full h-[480px]" />
        </Card>
      )}
      {msg && <p className="mb-6 text-sm rounded-lg bg-[#F7F7F8] dark:bg-[#2F2F2F] px-3 py-2">{msg}</p>}

      <Section title="1. Samples of you" subtitle="A minute or two of you talking. Existing talks or Zoom recordings work too.">
        <Card className="p-4 space-y-3">
          {recording === 'voice' ? (
            <>
              <p className="text-sm bg-[#F7F7F8] dark:bg-[#1f1f1f] rounded-lg px-3 py-2 leading-relaxed">{SAMPLE_SCRIPT}</p>
              <button className={`${primaryBtn} bg-red-600 dark:bg-red-500`} onClick={stopVoice}>■ Stop & save</button>
            </>
          ) : (
            <div className="flex flex-wrap gap-2">
              <button className={primaryBtn} onClick={recordVoice}>🎙️ Record a voice sample</button>
              <label className={`${ghostBtn} cursor-pointer`}>
                Upload audio or video
                <input type="file" accept="audio/*,video/*" className="hidden" onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) upload(f.type.startsWith('video') ? 'video_sample' : 'voice_sample', f, f.name);
                }} />
              </label>
              <label className={`${ghostBtn} cursor-pointer`}>
                Upload a photo
                <input type="file" accept="image/*" className="hidden" onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) upload('photo', f, f.name);
                }} />
              </label>
            </div>
          )}
          {status.assets.length > 0 && (
            <ul className="text-sm divide-y divide-gray-100 dark:divide-gray-700/70">
              {status.assets.map((a: any) => (
                <li key={a.id} className="flex items-center gap-2 py-1.5">
                  <span>{a.kind === 'photo' ? '🖼️' : a.kind === 'video_sample' ? '🎞️' : '🎙️'}</span>
                  <span className="flex-1 truncate">{a.filename}</span>
                  <span className="text-xs text-gray-400">{Math.round(a.size / 1024)} KB</span>
                  <button className="text-xs text-gray-400 hover:text-red-500" onClick={async () => { await api.del(`/twin/assets/${a.id}`); load(); }}>✕</button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </Section>

      <Section title="2. Your consent, on camera" subtitle="Nothing is cloned until you record this. It's how we make sure only you can create your twin.">
        <Card className="p-4 space-y-3">
          {consented ? (
            <p className="text-sm">✅ Consent recorded and verified.</p>
          ) : !challenge ? (
            <button className={primaryBtn} onClick={getChallenge}>Get my consent statement</button>
          ) : (
            <>
              <p className="text-sm">Read this out loud, exactly, while recording:</p>
              <p className="text-base font-medium bg-[#F7F7F8] dark:bg-[#1f1f1f] rounded-lg px-4 py-3">“{challenge.phrase}”</p>
              <video ref={previewRef} muted playsInline className={`w-full max-w-sm rounded-lg bg-black ${recording === 'consent' ? '' : 'hidden'}`} />
              {recording === 'consent' ? (
                <button className={`${primaryBtn} bg-red-600 dark:bg-red-500`} disabled={busy} onClick={stopConsent}>■ Stop & verify</button>
              ) : (
                <button className={primaryBtn} onClick={recordConsent}>⏺ Record statement</button>
              )}
              <label className="block text-sm">
                What we heard {hasSpeechRecognition() ? '(live transcript)' : '(type what you said; your browser has no speech recognition)'}
                <textarea className={`${inputCls} mt-1`} value={transcript} onChange={(e) => setTranscript(e.target.value)} />
              </label>
            </>
          )}
        </Card>
      </Section>

      <Section title="3. Your AI voice">
        <Card className="p-4 space-y-2">
          {status.voiceId ? (
            <p className="text-sm">✅ Your voice is ready and used on calls.</p>
          ) : (
            <>
              <button className={primaryBtn} disabled={!consented || !samples.length || busy} onClick={createVoice}>Create my AI voice</button>
              <p className="text-xs text-gray-500">
                {!status.voiceConfigured
                  ? 'Voice cloning needs ELEVENLABS_API_KEY on the server. Until then, calls use a browser voice.'
                  : !consented ? 'Verify consent first.' : !samples.length ? 'Add a voice sample first.' : ''}
              </p>
            </>
          )}
        </Card>
      </Section>

      <Section title="Delete my twin">
        <button className={dangerBtn} onClick={revoke}>Revoke consent and delete everything</button>
        <p className="text-xs text-gray-500 mt-2">Deletes your cloned voice at the provider, every file you uploaded, and your consent recording.</p>
      </Section>
    </div>
  );
}
