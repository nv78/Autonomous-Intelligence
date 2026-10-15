import { type ComponentType, useEffect } from 'react';
import { Navigate, useNavigate, useParams } from 'react-router-dom';
import OurogenLogo from '../components/OurogenLogo';
import { useCoworker } from '../coworker/CoworkerContext';
import HeaderControls from '../coworker/HeaderControls';
import ActivityTab from '../coworker/tabs/ActivityTab';
import ApprovalsTab from '../coworker/tabs/ApprovalsTab';
import MemoryTab from '../coworker/tabs/MemoryTab';
import ResponsibilitiesTab from '../coworker/tabs/ResponsibilitiesTab';
import SettingsTab from '../coworker/tabs/SettingsTab';
import { Pill } from '../coworker/ui';

export interface CoworkerTab {
  id: string;
  label: string;
  icon: string;
  component: ComponentType;
}

export const TABS: CoworkerTab[] = [
  { id: 'approvals', label: 'Approvals', icon: '📥', component: ApprovalsTab },
  { id: 'responsibilities', label: 'Responsibilities', icon: '📌', component: ResponsibilitiesTab },
  { id: 'activity', label: 'Activity', icon: '🗒️', component: ActivityTab },
  { id: 'memory', label: 'Memory', icon: '🧠', component: MemoryTab },
  { id: 'settings', label: 'Settings', icon: '⚙️', component: SettingsTab },
];

export default function CoworkerPage() {
  const { tab = 'approvals' } = useParams<{ tab: string }>();
  const nav = useNavigate();
  const { coworker, loaded, status } = useCoworker();

  useEffect(() => {
    document.title = 'Coworker · Ourogen';
  }, []);

  if (loaded && !coworker) return <Navigate to="/app/onboarding" replace />;
  const active = TABS.find((t) => t.id === tab) || TABS[0];
  const Active = active.component;

  return (
    <div className="min-h-dvh bg-white dark:bg-[#212121] text-gray-900 dark:text-white">
      <header className="sticky top-0 z-30 bg-white/90 dark:bg-[#212121]/90 backdrop-blur border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-6xl mx-auto flex items-center gap-3 px-4 py-3">
          <button onClick={() => nav('/app')} className="flex items-center gap-2 text-sm hover:opacity-80" title="Back to chat">
            <OurogenLogo className="w-7 h-7" />
            <span className="hidden sm:inline text-gray-500 dark:text-gray-400">← Chat</span>
          </button>
          <div className="min-w-0 flex-1 flex items-center gap-2">
            <h1 className="text-base font-semibold truncate">{coworker?.displayName || 'Your AI coworker'}</h1>
            <span className="hidden sm:inline-flex">
              {coworker?.mode === 'demo' && <Pill tone="blue">Demo workspace</Pill>}
              {coworker?.mode === 'live' && <Pill tone="green">Live</Pill>}
            </span>
          </div>
          <HeaderControls />
        </div>
        <nav className="max-w-6xl mx-auto px-2 flex gap-1 overflow-x-auto">
          {TABS.map((t) => (
            <button key={t.id} onClick={() => nav(`/app/coworker/${t.id}`)}
              className={`whitespace-nowrap px-3 py-2 text-sm border-b-2 -mb-px transition-colors ${
                t.id === active.id ? 'border-black dark:border-white font-medium' : 'border-transparent text-gray-500 hover:text-gray-900 dark:hover:text-white'
              }`}>
              <span aria-hidden className="mr-1">{t.icon}</span>
              {t.label}
              {t.id === 'approvals' && (status.pending || 0) > 0 && <span className="ml-1.5 text-xs">({status.pending})</span>}
            </button>
          ))}
        </nav>
      </header>
      {coworker?.status === 'paused' && (
        <div className="bg-amber-50 dark:bg-amber-500/10 border-b border-amber-200 dark:border-amber-500/30 text-sm text-amber-900 dark:text-amber-200 px-4 py-2 text-center">
          Your coworker is paused. Nothing will be sent and no responsibilities will run until you resume it.
        </div>
      )}
      <main className="max-w-4xl mx-auto px-4 py-6">{coworker ? <Active /> : <div className="h-40 animate-pulse" />}</main>
    </div>
  );
}
