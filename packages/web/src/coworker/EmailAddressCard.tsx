import { useEffect, useState } from 'react';
import { useAuth } from '../App';
import { coworkerApi } from './api';
import { Card, Section, ghostBtn } from './ui';

/** The owner's coworker address: CC it on a thread, or forward something with a note. */
export default function EmailAddressCard() {
  const { token } = useAuth();
  const api = coworkerApi(token);
  const [address, setAddress] = useState('');
  const [mailbox, setMailbox] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.get('/inbound-address').then((d) => {
      setAddress(d.address || '');
      setMailbox(!!d.mailbox);
    }).catch(() => {});
  }, []);

  if (!address) return null;
  return (
    <Section title="Email your coworker" subtitle="Works from any email client. Only mail from your own address is acted on.">
      <Card className="p-4 space-y-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm">{address}</span>
          <button className={ghostBtn} onClick={() => navigator.clipboard.writeText(address).then(() => setCopied(true))}>
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
        <ul className="text-sm text-gray-600 dark:text-gray-300 list-disc pl-5 space-y-1">
          <li><b>CC it</b>: “Dana, cc'ing my coworker to find a time next week.” It drafts the reply to Dana for your approval.</li>
          <li><b>Forward with a note</b>: “Summarize this and draft a reply.” The answer comes back to you by email.</li>
        </ul>
        {mailbox && (
          <p className="text-xs text-gray-500">
            This is your own inbox's plus-address: send from your connected mailbox and your coworker picks it up on its next sync
            (within a few minutes). Mail other people send to it is ignored.
          </p>
        )}
      </Card>
    </Section>
  );
}
