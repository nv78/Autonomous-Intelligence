import { API_BASE_URL } from '../constants/constants';

/** Browser speech recognition (Chrome/Edge). Returns null where unsupported. */
export function hasSpeechRecognition(): boolean {
  const w = window as any;
  return !!(w.SpeechRecognition || w.webkitSpeechRecognition);
}

export interface Recognizer {
  start: () => void;
  stop: () => void;
}

export function createRecognizer(handlers: {
  onFinal: (text: string) => void;
  onInterim?: (text: string) => void;
  onSpeechStart?: () => void;
  onError?: (err: string) => void;
}): Recognizer | null {
  const w = window as any;
  const Ctor = w.SpeechRecognition || w.webkitSpeechRecognition;
  if (!Ctor) return null;
  const rec = new Ctor();
  rec.continuous = true;
  rec.interimResults = true;
  rec.lang = navigator.language || 'en-US';
  let active = false;
  rec.onresult = (event: any) => {
    let interim = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i];
      if (result.isFinal) handlers.onFinal(result[0].transcript.trim());
      else interim += result[0].transcript;
    }
    if (interim) handlers.onInterim?.(interim);
  };
  rec.onspeechstart = () => handlers.onSpeechStart?.();
  rec.onerror = (e: any) => {
    if (e.error !== 'no-speech' && e.error !== 'aborted') handlers.onError?.(e.error);
  };
  rec.onend = () => {
    if (active) {
      try {
        rec.start();
      } catch {}
    }
  };
  return {
    start: () => {
      active = true;
      try {
        rec.start();
      } catch {}
    },
    stop: () => {
      active = false;
      try {
        rec.stop();
      } catch {}
    },
  };
}

/** Speaks with the server voice (ElevenLabs / cloned) when available, else the browser voice. */
export class Speaker {
  private audio: HTMLAudioElement | null = null;
  private resolve: (() => void) | null = null;
  speaking = false;
  onChange: (speaking: boolean) => void = () => {};

  constructor(private token: string | null, private serverVoice: boolean) {}

  private set(v: boolean) {
    this.speaking = v;
    this.onChange(v);
  }

  async speak(text: string, opts: { voiceHint?: 'coworker' | 'prospect' } = {}): Promise<{ firstAudioMs: number }> {
    this.stop();
    const started = performance.now();
    if (this.serverVoice && opts.voiceHint !== 'prospect') {
      try {
        const res = await fetch(`${API_BASE_URL}/api/coworker/voice/tts`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${this.token}` },
          body: JSON.stringify({ text }),
        });
        if (res.ok) {
          const url = URL.createObjectURL(await res.blob());
          return await new Promise((resolve) => {
            const audio = new Audio(url);
            this.audio = audio;
            this.resolve = () => resolve({ firstAudioMs: performance.now() - started });
            audio.onplay = () => this.set(true);
            audio.onended = audio.onerror = () => {
              this.set(false);
              URL.revokeObjectURL(url);
              this.resolve?.();
              this.resolve = null;
            };
            audio.play().catch(() => {
              this.set(false);
              this.resolve?.();
            });
          });
        }
      } catch {}
    }
    if (!('speechSynthesis' in window)) return { firstAudioMs: 0 };
    return new Promise((resolve) => {
      const u = new SpeechSynthesisUtterance(text);
      const voices = window.speechSynthesis.getVoices().filter((v) => v.lang.startsWith('en'));
      if (voices.length) u.voice = opts.voiceHint === 'prospect' ? voices[Math.min(1, voices.length - 1)] : voices[0];
      u.rate = 1.03;
      let first = 0;
      u.onstart = () => {
        first = performance.now() - started;
        this.set(true);
      };
      let finished = false;
      // Chrome sometimes never fires onend; never let a call stall on it.
      const safety = setTimeout(() => done(), 2500 + text.split(/\s+/).length * 450);
      const done = () => {
        if (finished) return;
        finished = true;
        clearTimeout(safety);
        this.set(false);
        resolve({ firstAudioMs: first });
      };
      u.onend = done;
      u.onerror = done;
      this.resolve = done;
      window.speechSynthesis.speak(u);
    });
  }

  stop() {
    if (this.audio) {
      this.audio.pause();
      this.audio = null;
    }
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    if (this.speaking) this.set(false);
    const r = this.resolve;
    this.resolve = null;
    r?.();
  }
}

export async function recordMedia(kind: 'audio' | 'video'): Promise<{ stop: () => Promise<Blob>; stream: MediaStream }> {
  const stream = await navigator.mediaDevices.getUserMedia(kind === 'video' ? { audio: true, video: true } : { audio: true });
  const mime = kind === 'video'
    ? (MediaRecorder.isTypeSupported('video/webm') ? 'video/webm' : '')
    : (MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : '');
  const recorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
  const chunks: Blob[] = [];
  recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);
  recorder.start();
  return {
    stream,
    stop: () =>
      new Promise((resolve) => {
        recorder.onstop = () => {
          stream.getTracks().forEach((t) => t.stop());
          resolve(new Blob(chunks, { type: recorder.mimeType || (kind === 'video' ? 'video/webm' : 'audio/webm') }));
        };
        recorder.stop();
      }),
  };
}
