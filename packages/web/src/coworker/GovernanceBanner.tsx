import { useEffect, useState } from 'react';
import { useAuth } from '../App';
import { coworkerApi, errorMessage } from './api';
import { useCoworker } from './CoworkerContext';
import { ghostBtn, primaryBtn } from './ui';

/** Shown when the coworker runs on a work account and the user hasn't
 * confirmed they're allowed to use an AI coworker there. Until they do it
 * can read and draft, but nothing is sent. */
export default function GovernanceBanner() {
  const { token } = useAuth();
  const { coworker, version } = useCoworker();
  const api = coworkerApi(token);
  const [gov, setGov] = useState<any>(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    if (coworker?.mode === 'live') api.get('/governance').then(setGov).catch(() => {});
  }, [coworker?.mode, version]);

  if (!gov) return null;
  if (gov.orgDisabled) {
    return (
      <div className="bg-red-50 dark:bg-red-500/10 border-b border-red-200 dark:border-red-500/30 text-sm text-red-900 dark:text-red-200 px-4 py-2 text-center">
        Your organization has turned off AI coworkers for this account. Your coworker is paused.
      </div>
    );
  }
  if (!gov.needsEmployerAuthorization) return null;
  const confirm = async (basis: 'owner' | 'permitted') => {
    try {
      setGov(await api.post('/governance/employer', { confirm: true, basis }));
    } catch (e) {
      setErr(errorMessage(e));
    }
  };
  return (
    <div className="border-b border-gray-200 dark:border-gray-700 bg-[#F7F7F8] dark:bg-[#2F2F2F] px-4 py-3">
      <div className="max-w-4xl mx-auto flex flex-col sm:flex-row sm:items-center gap-3">
        <p className="text-sm flex-1">
          <span className="font-medium">Is an AI coworker allowed at {gov.workDomain}?</span>{' '}
          Until you confirm, I'll read and draft, but I won't send anything for you.
          {err && <span className="block text-red-500 text-xs mt-1">{err}</span>}
        </p>
        <div className="flex gap-2 shrink-0">
          <button className={primaryBtn} onClick={() => confirm('owner')}>I own the company</button>
          <button className={ghostBtn} onClick={() => confirm('permitted')}>My employer allows it</button>
        </div>
      </div>
    </div>
  );
}
