import { type ReactNode, useEffect, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { useNavigate, useSearchParams } from 'react-router-dom';
import remarkGfm from 'remark-gfm';
import { useAuth } from '../App';
import OurogenLogo from '../components/OurogenLogo';
import ActionCard from '../coworker/ActionCard';
import { coworkerApi, errorMessage } from '../coworker/api';
import { useCoworker } from '../coworker/CoworkerContext';
import { ConnectionsPanel } from '../coworker/tabs/SettingsTab';
import type { Action, Learned, Suggestion } from '../coworker/types';
import { Card, Pill, RELATIONSHIP_TONE, ghostBtn, inputCls, primaryBtn } from '../coworker/ui';

type Step = 'welcome' | 'connect' | 'learning' | 'learned' | 'delegate' | 'firstwin' | 'twin';
const ORDER: Step[] = ['welcome', 'connect', 'learning', 'learned', 'delegate', 'firstwin', 'twin'];

function Bubble({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-start gap-3">
      <div className="w-8 h-8 rounded-full bg-gray-100 dark:bg-[#2F2F2F] flex items-center justify-center flex-shrink-0">
        <OurogenLogo className="w-5 h-5" />
      </div>
      <div className="flex-1 min-w-0 text-[15px] leading-relaxed space-y-3">{children}</div>
    </div>
  );
}

export default function OnboardingPage() {
  const { token, user } = useAuth();
  const { coworker, capabilities, refresh, refreshStatus, loaded, tick } = useCoworker();
  const api = coworkerApi(token);
  const nav = useNavigate();
  const [params, setParams] = useSearchParams();
  const [step, setStepState] = useState<Step>('welcome');
  const [learned, setLearned] = useState<Learned | null>(null);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [firstActions, setFirstActions] = useState<Action[]>([]);
  const [firstResults, setFirstResults] = useState<string[]>([]);
  const [briefs, setBriefs] = useState<string[]>([]);
  const [progress, setProgress] = useState<string[]>([]);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const [rule, setRule] = useState('');
  const { actionCache } = useCoworker();
  const first = (user?.name || '').split(' ')[0];

  const setStep = (s: Step) => {
    setStepState(s);
    if (coworker) api.patch('', { onboarding: { step: s } }).catch(() => {});
  };

  // Resume where the user left off, and handle OAuth returns.
  useEffect(() => {
    if (!loaded) return;
    const connected = params.get('connected');
    const connectError = params.get('connect_error');
    const returnTo = localStorage.getItem('coworker_return_to');
    if ((connected || connectError) && returnTo && returnTo !== '/app/onboarding') {
      localStorage.removeItem('coworker_return_to');
      nav(`${returnTo}?${params.toString()}`, { replace: true });
      return;
    }
    if (connectError) setErr(`Couldn't connect ${connectError}: ${params.get('message') || 'unknown error'}`);
    if (connected) {
      setParams({}, { replace: true });
      refresh();
      setStepState('learning');
      return;
    }
    const saved = coworker?.onboarding?.step as Step | undefined;
    if (coworker?.onboarding?.completed) return;
    if (saved && ORDER.includes(saved)) setStepState(saved === 'learning' ? 'learned' : saved);
  }, [loaded]);

  // Learning: sync (live) and build memory, with a visible progress feed.
  useEffect(() => {
    if (step !== 'learning') return;
    let cancelled = false;
    (async () => {
      setProgress(['Reading your recent email, Slack, calendar, and docs…']);
      try {
        if (coworker?.mode === 'live') await api.post('/sync?rebuild=1');
        else await api.post('/memory/rebuild', { enrich: false });
        const l: Learned = await api.get('/memory/learned');
        if (cancelled) return;
        const lines = [
          `Found ${l.counts.emails} emails, ${l.counts.slack_messages} Slack messages, ${l.counts.meetings} meetings, and ${l.counts.docs} docs.`,
          `Mapped ${l.counts.people} people and ${l.counts.active_threads} active conversations.`,
          `Spotted ${l.counts.decisions} decisions you made, and learned how you write.`,
        ];
        for (const line of lines) {
          await new Promise((r) => setTimeout(r, 700));
          if (cancelled) return;
          setProgress((p) => [...p, line]);
        }
        setLearned(l);
        await new Promise((r) => setTimeout(r, 600));
        if (!cancelled) setStep('learned');
      } catch (e) {
        setErr(errorMessage(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [step]);

  useEffect(() => {
    if (step === 'learned' && !learned) api.get('/memory/learned').then(setLearned).catch(() => {});
    if (step === 'delegate') api.get('/onboarding/suggestions').then((d) => setSuggestions(d.suggestions || []));
    if (step === 'firstwin' && !firstActions.length) {
      api.get('/actions', { status: 'proposed' }).then((d) => setFirstActions((d.actions || []).slice(0, 3)));
    }
  }, [step]);

  const startDemo = async () => {
    setBusy(true);
    setErr('');
    try {
      await api.post('', { mode: 'demo', name: user?.name, email: user?.email });
      await refresh();
      setStepState('learning');
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const startLive = async () => {
    setBusy(true);
    setErr('');
    try {
      if (!coworker) await api.post('', { mode: 'live', name: user?.name, email: user?.email });
      localStorage.setItem('coworker_return_to', '/app/onboarding');
      const d = await api.post('/connections/google/start', { level: 'read' });
      window.location.href = d.url;
    } catch (e) {
      setErr(errorMessage(e));
      setBusy(false);
    }
  };

  const takeOn = async (template: string) => {
    setBusy(true);
    try {
      const created = await api.post('/responsibilities', { template });
      setFirstResults(created.results || []);
      const d = await api.get('/actions', { status: 'proposed' });
      setFirstActions((d.actions || []).slice(0, 3));
      const act = await api.get('/activity', { limit: 20 });
      setBriefs((act.activity || []).filter((r: any) => r.kind === 'brief').map((r: any) => r.detail?.brief?.markdown).filter(Boolean).slice(0, 2));
      refreshStatus();
      setStep('firstwin');
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const editPerson = async (id: number, relationship: string) => {
    await api.patch(`/memory/people/${id}`, { relationship });
    setLearned(await api.get('/memory/learned'));
  };
  const forgetPerson = async (id: number) => {
    await api.del(`/memory/people/${id}`);
    setLearned(await api.get('/memory/learned'));
  };
  const addRule = async () => {
    if (!rule.trim()) return;
    await api.post('/style/rules', { rule });
    setRule('');
    setLearned(await api.get('/memory/learned'));
  };

  const finish = async () => {
    await api.patch('', { onboarding: { step: 'done', completed: true } });
    localStorage.removeItem('ourogen_show_onboarding');
    await refresh();
    tick(true);
    nav('/app');
  };

  const approvedOne = useMemo(
    () => firstActions.some((a) => ['executed', 'approved'].includes((actionCache[a.id] || a).status)),
    [firstActions, actionCache],
  );
  const stepIndex = ORDER.indexOf(step);

  return (
    <div className="min-h-dvh bg-white dark:bg-[#212121] text-gray-900 dark:text-white">
      <header className="flex items-center justify-between px-5 py-4 max-w-3xl mx-auto">
        <div className="flex items-center gap-2">
          <OurogenLogo className="w-7 h-7" />
          <span className="font-semibold text-sm">Ourogen Coworker</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex gap-1" aria-label={`Step ${stepIndex + 1} of ${ORDER.length}`}>
            {ORDER.map((s, i) => (
              <span key={s} className={`h-1.5 w-6 rounded-full ${i <= stepIndex ? 'bg-black dark:bg-white' : 'bg-gray-200 dark:bg-gray-700'}`} />
            ))}
          </div>
          <button className="text-xs text-gray-500 hover:underline" onClick={coworker ? finish : () => nav('/app')}>Skip for now</button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-5 pb-16 space-y-6">
        {err && <p className="text-sm rounded-lg bg-red-50 dark:bg-red-500/10 text-red-700 dark:text-red-300 px-3 py-2">{err}</p>}

        {step === 'welcome' && (
          <Bubble>
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight">Hi{first ? ` ${first}` : ''}, let's set up your AI coworker.</h1>
            <p>I learn how you work from your email, Slack, and calendar. Then I take things off your plate: replying to leads, scheduling, prepping you for meetings, following up. I can even join calls for you.</p>
            <ul className="text-sm text-gray-600 dark:text-gray-300 space-y-1.5">
              <li>✋ Nothing goes out without your approval until you say otherwise.</li>
              <li>🤖 I always say I'm your AI. I never pretend to be you.</li>
              <li>⏸️ One click pauses everything. You can see every action I take.</li>
            </ul>
            <button className={primaryBtn} onClick={() => setStep('connect')}>Let's go · about 5 minutes</button>
          </Bubble>
        )}

        {step === 'connect' && (
          <Bubble>
            <h2 className="text-xl font-semibold">First, connect your work.</h2>
            <p>Read access is all I need to start. I'll ask before sending anything, and you can disconnect anytime. I'll delete what I synced when you do.</p>
            {!coworker || coworker.mode === 'live' ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <Card className="p-4 flex flex-col">
                  <p className="font-medium">Continue with Google</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 flex-1">Gmail, Calendar, and Drive with your real data. Slack is next.</p>
                  <button className={`${primaryBtn} mt-3`} disabled={busy || !capabilities?.google} onClick={startLive}>
                    {capabilities?.google ? 'Connect Google' : 'Not configured on this server'}
                  </button>
                </Card>
                <Card className="p-4 flex flex-col">
                  <p className="font-medium">Try the Anote demo workspace</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 flex-1">A realistic, fictional inbox, Slack, and calendar. Nothing real gets touched.</p>
                  <button className={`${ghostBtn} mt-3`} disabled={busy} onClick={startDemo}>{busy ? 'Setting up…' : 'Use demo data'}</button>
                </Card>
              </div>
            ) : (
              <button className={primaryBtn} onClick={() => setStep('learning')}>Continue with the demo workspace</button>
            )}
            {coworker?.mode === 'live' && (
              <div className="pt-2">
                <p className="text-sm font-medium mb-2">Add Slack (optional)</p>
                <ConnectionsPanel returnTo="/app/onboarding" />
                <button className={`${primaryBtn} mt-3`} onClick={() => setStep('learning')}>Continue</button>
              </div>
            )}
          </Bubble>
        )}

        {step === 'learning' && (
          <Bubble>
            <h2 className="text-xl font-semibold">Getting to know your work…</h2>
            <ul className="space-y-2 text-sm">
              {progress.map((p, i) => (
                <li key={i} className="flex gap-2">
                  <span>{i === progress.length - 1 ? <span className="inline-block animate-spin">◌</span> : '✓'}</span>
                  {p}
                </li>
              ))}
            </ul>
          </Bubble>
        )}

        {step === 'learned' && learned && (
          <Bubble>
            <h2 className="text-xl font-semibold">Here's what I learned about you.</h2>
            <p className="text-sm text-gray-600 dark:text-gray-300">
              Looks like you're a <strong>{learned.role_guess}</strong>
              {learned.focus_areas.length ? `, focused on ${learned.focus_areas.join(', ')}` : ''}. Fix anything I got wrong. Your edits stick.
            </p>
            <Card className="divide-y divide-gray-100 dark:divide-gray-700/70">
              {learned.key_people.map((p) => (
                <div key={p.id} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{p.name}</p>
                    <p className="text-xs text-gray-500 truncate">{[p.role, p.company].filter(Boolean).join(', ') || p.email}</p>
                  </div>
                  <select className="bg-transparent text-xs border border-gray-200 dark:border-gray-600 rounded px-1.5 py-1" value={p.relationship}
                    onChange={(e) => editPerson(p.id, e.target.value)}>
                    {['prospect', 'customer', 'investor', 'teammate', 'candidate', 'partner', 'vendor', 'contact'].map((r) => <option key={r}>{r}</option>)}
                  </select>
                  <button className="text-gray-400 hover:text-red-500 text-xs" title="Forget" onClick={() => forgetPerson(p.id)}>✕</button>
                </div>
              ))}
            </Card>
            {learned.deals.length > 0 && (
              <div>
                <p className="text-sm font-medium mb-2">What's in flight</p>
                <div className="flex flex-wrap gap-2">
                  {learned.deals.map((d) => (
                    <span key={d.company} className="text-xs rounded-lg border border-gray-200 dark:border-gray-600 px-2.5 py-1.5">
                      <Pill tone={RELATIONSHIP_TONE[d.relationship]}>{d.relationship}</Pill> <strong>{d.company}</strong>
                      {d.waiting_on ? ` · waiting on ${d.waiting_on}` : ''}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {learned.decisions.length > 0 && (
              <div>
                <p className="text-sm font-medium mb-1">Decisions I'll remember</p>
                <ul className="text-sm text-gray-600 dark:text-gray-300 list-disc pl-5">
                  {learned.decisions.slice(0, 3).map((d) => <li key={d.id}>{d.title}</li>)}
                </ul>
              </div>
            )}
            <Card className="p-4">
              <p className="text-sm font-medium">How you write</p>
              <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">{learned.style?.summary}</p>
              <div className="flex gap-2 mt-3">
                <input className={inputCls} placeholder="Anything to add? e.g. “Never use exclamation points”" value={rule}
                  onChange={(e) => setRule(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && addRule()} />
                <button className={ghostBtn} onClick={addRule}>Add</button>
              </div>
            </Card>
            <button className={primaryBtn} onClick={() => setStep('delegate')}>Looks right</button>
          </Bubble>
        )}

        {step === 'delegate' && (
          <Bubble>
            <h2 className="text-xl font-semibold">What should I take off your plate first?</h2>
            <p className="text-sm text-gray-600 dark:text-gray-300">Based on what's waiting on you right now:</p>
            <div className="grid gap-3 sm:grid-cols-2">
              {suggestions.map((s) => (
                <Card key={s.template} className="p-4 flex flex-col">
                  <p className="font-medium text-sm">{s.name}</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 flex-1">{s.why}</p>
                  <button className={`${primaryBtn} mt-3 self-start`} disabled={busy} onClick={() => takeOn(s.template)}>
                    {busy ? 'Working…' : 'Take this on'}
                  </button>
                </Card>
              ))}
              {suggestions.length === 0 && <p className="text-sm text-gray-500">Nothing urgent. You can add responsibilities anytime.</p>}
            </div>
            <button className="text-sm text-gray-500 hover:underline" onClick={() => setStep('twin')}>Skip this</button>
          </Bubble>
        )}

        {step === 'firstwin' && (
          <Bubble>
            <h2 className="text-xl font-semibold">Done. Here's my first pass.</h2>
            <p className="text-sm text-gray-600 dark:text-gray-300">
              Review it like you would a teammate's draft. Edit anything, then approve.
              {coworker?.mode === 'demo' ? ' In the demo, “sending” adds the reply to the fictional thread.' : ''}
            </p>
            {firstResults.length > 0 && (
              <ul className="text-sm space-y-1">
                {firstResults.map((r, i) => <li key={i}>✓ {r}</li>)}
              </ul>
            )}
            {firstActions.length === 0 && briefs.length === 0 && (
              <p className="text-sm text-gray-500">Nothing needed doing yet. I'll keep watching.</p>
            )}
            {firstActions.map((a) => <ActionCard key={a.id} action={a} />)}
            {firstActions.length === 0 &&
              briefs.map((b, i) => (
                <div key={i} className="prose prose-sm dark:prose-invert max-w-none rounded-xl border border-gray-200 dark:border-gray-700 px-4 py-3">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{b}</ReactMarkdown>
                </div>
              ))}
            <button className={approvedOne || firstActions.length === 0 ? primaryBtn : ghostBtn} onClick={() => setStep('twin')}>
              {approvedOne ? 'Nice, continue' : 'Continue'}
            </button>
          </Bubble>
        )}

        {step === 'twin' && (
          <Bubble>
            <h2 className="text-xl font-semibold">Want me to sound like you on calls?</h2>
            <p className="text-sm text-gray-600 dark:text-gray-300">
              Upload a short video of yourself talking and I can join meetings with your voice and face, always introduced as your AI.
              You can set this up anytime from the Coworker page.
            </p>
            <div className="flex gap-2">
              <button className={primaryBtn} onClick={async () => { await finish(); nav('/app/coworker/twin'); }}>Set up my twin</button>
              <button className={ghostBtn} onClick={finish}>Finish setup</button>
            </div>
          </Bubble>
        )}
      </main>
    </div>
  );
}
