import { useEffect, useState } from 'react';
import { useAuth } from '../App';
import { coworkerApi, errorMessage } from './api';
import { Card, Pill, Section, ghostBtn, inputCls, primaryBtn } from './ui';

interface PhoneState {
  configured: boolean;
  serviceNumber: string;
  whatsappAvailable: boolean;
  number: string;
  verified: boolean;
  whatsapp: boolean;
  notify: string[];
  optedOut: boolean;
}

/** Link a phone so the owner can text the coworker, approve by text, and get texts. */
export default function TextMessagesCard() {
  const { token } = useAuth();
  const api = coworkerApi(token);
  const [phone, setPhone] = useState<PhoneState | null>(null);
  const [number, setNumber] = useState('');
  const [whatsapp, setWhatsapp] = useState(false);
  const [code, setCode] = useState('');
  const [msg, setMsg] = useState('');

  useEffect(() => {
    api.get('/phone').then(setPhone).catch(() => setPhone(null));
  }, []);

  const run = async (fn: () => Promise<PhoneState>, ok = '') => {
    setMsg('');
    try {
      setPhone(await fn());
      if (ok) setMsg(ok);
    } catch (e) {
      setMsg(errorMessage(e));
    }
  };

  if (!phone?.configured) return null;
  const toggle = (kind: string) =>
    run(() => api.patch('/phone', { notify: phone.notify.includes(kind) ? phone.notify.filter((k) => k !== kind) : [...phone.notify, kind] }));

  return (
    <Section title="Text messages" subtitle="Text your coworker like a person: ask questions, hand off work, and approve with YES.">
      <Card className="p-4 space-y-3">
        {phone.verified ? (
          <>
            <div className="flex items-center gap-2 text-sm">
              <span>{phone.number}</span>
              <Pill tone="green">Linked{phone.whatsapp ? ' · WhatsApp' : ''}</Pill>
              {phone.optedOut && <Pill tone="amber">Texts off (you sent STOP)</Pill>}
            </div>
            <p className="text-sm">
              Text <span className="font-mono">{phone.serviceNumber}</span> anytime. Try “what's my next meeting?”. Reply{' '}
              <span className="font-mono">YES 12</span> to approve action 12, <span className="font-mono">PAUSE</span> to stop everything.
            </p>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={phone.notify.includes('approvals')} onChange={() => toggle('approvals')} /> Text me when something needs my approval
            </label>
            <p className="text-xs text-gray-500">Scheduled tasks set to “Text me” text their results here. No texts between 9pm and 8am your time.</p>
            <button className={ghostBtn} onClick={() => run(() => api.del('/phone'), 'Unlinked.')}>Unlink this number</button>
          </>
        ) : phone.number ? (
          <div className="flex flex-wrap gap-2 items-center">
            <span className="text-sm">We texted a code to {phone.number}.</span>
            <input className={`${inputCls} w-32`} inputMode="numeric" placeholder="6-digit code" value={code} onChange={(e) => setCode(e.target.value)} />
            <button className={primaryBtn} disabled={code.trim().length < 6} onClick={() => run(() => api.post('/phone/verify', { code }), 'Linked. Text your coworker anytime.')}>Verify</button>
            <button className={ghostBtn} onClick={() => run(() => api.post('/phone', { number: phone.number, whatsapp: phone.whatsapp }), 'Sent a new code.')}>Resend</button>
          </div>
        ) : (
          <div className="flex flex-wrap gap-2 items-center">
            <input className={`${inputCls} flex-1 min-w-[200px]`} type="tel" placeholder="+1 555 123 4567" value={number} onChange={(e) => setNumber(e.target.value)} />
            {phone.whatsappAvailable && (
              <label className="flex items-center gap-1.5 text-sm"><input type="checkbox" checked={whatsapp} onChange={(e) => setWhatsapp(e.target.checked)} /> Use WhatsApp</label>
            )}
            <button className={primaryBtn} disabled={number.replace(/\D/g, '').length < 8} onClick={() => run(() => api.post('/phone', { number, whatsapp }))}>Send code</button>
          </div>
        )}
        {msg && <p className="text-sm text-gray-600 dark:text-gray-300">{msg}</p>}
      </Card>
    </Section>
  );
}
