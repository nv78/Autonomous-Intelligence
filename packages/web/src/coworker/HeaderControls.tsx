import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { coworkerApi } from './api';
import { useCoworker } from './CoworkerContext';

/** Status pill, approvals badge, demo simulator, and the kill switch. */
export default function HeaderControls({ showSimulate = true }: { showSimulate?: boolean }) {
  const { token } = useAuth();
  const { coworker, status, pause, resume, scenarios, tick } = useCoworker();
  const nav = useNavigate();
  const [simOpen, setSimOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState('');
  if (!coworker) return null;
  const paused = coworker.status === 'paused';
  const pending = status.pending || 0;

  const simulate = async (scenario: string, label: string) => {
    setSimOpen(false);
    setBusy(true);
    try {
      await coworkerApi(token).post('/demo/simulate', { scenario });
      const result = await tick(true);
      const did = result?.results?.length ? ` · ${result.results.join('; ')}` : '';
      setToast(`Simulated: ${label}${did}`);
      setTimeout(() => setToast(''), 5000);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex items-center gap-2 relative">
      {coworker.mode === 'demo' && showSimulate && scenarios.length > 0 && (
        <div className="relative">
          <button onClick={() => setSimOpen((o) => !o)} disabled={busy}
            className="hidden sm:inline-flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg border border-gray-200 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-white/10"
            title="Drop a scripted event into the demo workspace">
            🧪 Simulate
          </button>
          {simOpen && (
            <div className="absolute right-0 mt-1 z-50 w-64 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#2F2F2F] shadow-lg py-1">
              {scenarios.map((s) => (
                <button key={s.id} onClick={() => simulate(s.id, s.label)}
                  className="block w-full text-left px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-white/10">
                  {s.label}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
      <button onClick={() => nav('/app/coworker/approvals')} title="Approvals"
        className="relative inline-flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-white/10">
        <span aria-hidden>📥</span>
        <span className="hidden sm:inline">Approvals</span>
        {pending > 0 && (
          <span className="min-w-[18px] h-[18px] px-1 rounded-full bg-black text-white dark:bg-white dark:text-black text-[10px] font-semibold flex items-center justify-center">
            {pending}
          </span>
        )}
      </button>
      <button
        onClick={() => (paused ? resume() : pause())}
        title={paused ? 'Resume your coworker' : 'Kill switch: stop everything now'}
        className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg border ${
          paused
            ? 'border-amber-300 bg-amber-50 text-amber-800 dark:bg-amber-500/10 dark:text-amber-300 dark:border-amber-500/40'
            : 'border-gray-200 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-white/10'
        }`}
      >
        <span className={`w-2 h-2 rounded-full ${paused ? 'bg-amber-500' : 'bg-emerald-500'}`} />
        {paused ? 'Paused · Resume' : 'Active · Pause'}
      </button>
      {toast && (
        <div className="absolute right-0 top-10 z-50 w-72 text-xs rounded-lg bg-black text-white dark:bg-white dark:text-black px-3 py-2 shadow-lg">
          {toast}
        </div>
      )}
    </div>
  );
}
