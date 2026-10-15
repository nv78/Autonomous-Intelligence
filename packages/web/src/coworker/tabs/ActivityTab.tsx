import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useAuth } from '../../App';
import { coworkerApi, timeAgo } from '../api';
import { useCoworker } from '../CoworkerContext';
import type { ActivityRow } from '../types';
import { Card, Empty, Section, ghostBtn } from '../ui';

const ICON: Record<string, string> = {
  executed: '✅', proposed: '📝', approved: '👍', rejected: '✋', auto_approved: '⚡', failed: '⚠️', brief: '📋',
  security: '🛡️', escalation: '🙋', digest: '🗞️', paused: '⏸️', resumed: '▶️', setup: '🚀', connection: '🔌',
  simulation: '🧪', responsibility: '📌', undone: '↩️', autonomy: '🎚️', meeting: '🎙️', twin: '🪞',
};

export default function ActivityTab() {
  const { token } = useAuth();
  const { version } = useCoworker();
  const api = coworkerApi(token);
  const [rows, setRows] = useState<ActivityRow[]>([]);
  const [digest, setDigest] = useState<any>(null);
  const [open, setOpen] = useState<number | null>(null);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    api.get('/activity', { limit: 300 }).then((d) => setRows(d.activity || []));
    api.get('/digest').then(setDigest);
  }, [version]);

  const exportCsv = async () => {
    const res = await fetch(`${api.base}/activity?format=csv&limit=2000`, { headers: api.headers });
    const url = URL.createObjectURL(await res.blob());
    const a = document.createElement('a');
    a.href = url;
    a.download = 'coworker-activity.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const groups: Record<string, string[]> = {
    all: [], actions: ['executed', 'proposed', 'approved', 'rejected', 'auto_approved', 'failed', 'undone'],
    briefs: ['brief', 'digest'], attention: ['security', 'escalation'],
  };
  const shown = filter === 'all' ? rows : rows.filter((r) => groups[filter].includes(r.kind));

  return (
    <div>
      {digest && (
        <Card className="p-4 mb-6">
          <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-1">Last 24 hours</p>
          <p className="text-sm font-medium">{digest.headline}</p>
          {digest.attention?.length > 0 && (
            <ul className="mt-2 text-sm text-amber-700 dark:text-amber-300 list-disc pl-5">
              {digest.attention.map((a: string, i: number) => <li key={i}>{a}</li>)}
            </ul>
          )}
        </Card>
      )}
      <Section
        title="Everything your coworker did"
        subtitle="Every read, draft, send, and decision, with who approved it."
        action={<button className={ghostBtn} onClick={exportCsv}>Export CSV</button>}
      >
        <div className="flex gap-1.5 mb-3">
          {Object.keys(groups).map((g) => (
            <button key={g} onClick={() => setFilter(g)}
              className={`px-3 py-1 rounded-full text-xs capitalize ${filter === g ? 'bg-black text-white dark:bg-white dark:text-black' : 'bg-gray-100 dark:bg-white/10'}`}>
              {g}
            </button>
          ))}
        </div>
        {shown.length === 0 ? (
          <Empty title="No activity yet" />
        ) : (
          <Card className="divide-y divide-gray-100 dark:divide-gray-700/70">
            {shown.map((r) => {
              const brief = r.detail?.brief;
              const dig = r.detail?.digest;
              return (
                <div key={r.id} className="px-4 py-2.5">
                  <div className="flex items-start gap-3 text-sm">
                    <span aria-hidden className="w-5 text-center">{ICON[r.kind] || '•'}</span>
                    <span className="flex-1 min-w-0">{r.summary}</span>
                    {(brief || dig) && (
                      <button className="text-xs underline text-gray-500" onClick={() => setOpen(open === r.id ? null : r.id)}>
                        {open === r.id ? 'Hide' : 'View'}
                      </button>
                    )}
                    <span className="text-xs text-gray-400 whitespace-nowrap" title={r.created_at}>{timeAgo(r.created_at)}</span>
                  </div>
                  {open === r.id && brief && (
                    <div className="prose prose-sm dark:prose-invert max-w-none mt-2 ml-8 bg-[#F7F7F8] dark:bg-[#1f1f1f] rounded-lg px-4 py-3">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{brief.markdown}</ReactMarkdown>
                    </div>
                  )}
                  {open === r.id && dig && (
                    <div className="mt-2 ml-8 text-sm bg-[#F7F7F8] dark:bg-[#1f1f1f] rounded-lg px-4 py-3 space-y-1">
                      {dig.executed?.map((e: string, i: number) => <p key={i}>✅ {e}</p>)}
                      {dig.pending?.map((e: string, i: number) => <p key={i}>📝 {e}</p>)}
                    </div>
                  )}
                </div>
              );
            })}
          </Card>
        )}
      </Section>
    </div>
  );
}
