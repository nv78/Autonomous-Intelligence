import { useEffect, useState } from 'react';
import { useAuth } from '../App';
import { coworkerApi, errorMessage } from './api';
import { Card, Pill, Section, ghostBtn, primaryBtn } from './ui';

interface TelegramState {
  configured: boolean;
  linked: boolean;
  username: string;
  notify: string[];
  link?: string;
}

/** Link a Telegram chat: a free way to message your coworker and approve from your phone. */
export default function TelegramCard() {
  const { token } = useAuth();
  const api = coworkerApi(token);
  const [tg, setTg] = useState<TelegramState | null>(null);
  const [link, setLink] = useState('');
  const [msg, setMsg] = useState('');

  const load = () => api.get('/telegram').then(setTg).catch(() => setTg(null));
  useEffect(() => {
    load();
  }, []);

  const run = async (fn: () => Promise<TelegramState>, ok = '') => {
    setMsg('');
    try {
      const next = await fn();
      setTg(next);
      if (next.link) setLink(next.link);
      if (ok) setMsg(ok);
    } catch (e) {
      setMsg(errorMessage(e));
    }
  };

  if (!tg?.configured) return null;
  const approvals = tg.notify.includes('approvals');

  return (
    <Section title="Telegram" subtitle="Message your coworker from Telegram: ask questions, hand off work, approve with a tap.">
      <Card className="p-4 space-y-3">
        {tg.linked ? (
          <>
            <div className="flex items-center gap-2 text-sm">
              {tg.username && <span>@{tg.username}</span>}
              <Pill tone="green">Linked</Pill>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={approvals}
                onChange={() => run(() => api.patch('/telegram', { notify: approvals ? [] : ['approvals'] }))} />
              Message me when something needs my approval
            </label>
            <p className="text-xs text-gray-500">Scheduled tasks set to “Text me” also message you here.</p>
            <button className={ghostBtn} onClick={() => run(() => api.del('/telegram'), 'Unlinked.')}>Unlink Telegram</button>
          </>
        ) : link ? (
          <div className="space-y-2 text-sm">
            <p>Open this link on the phone or computer where you use Telegram, then press <b>Start</b>. It works once, for 15 minutes.</p>
            <a className={primaryBtn} href={link} target="_blank" rel="noreferrer">Open Telegram</a>
            <div className="flex gap-2">
              <button className={ghostBtn} onClick={() => { setLink(''); load(); }}>I pressed Start</button>
              <button className={ghostBtn} onClick={() => run(() => api.post('/telegram'))}>New link</button>
            </div>
          </div>
        ) : (
          <button className={primaryBtn} onClick={() => run(() => api.post('/telegram'))}>Connect Telegram</button>
        )}
        {msg && <p className="text-sm text-gray-600 dark:text-gray-300">{msg}</p>}
      </Card>
    </Section>
  );
}
