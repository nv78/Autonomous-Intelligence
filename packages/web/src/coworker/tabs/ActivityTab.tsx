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
  simulation: '🧪', responsibility: '📌', undone: '↩️', autonomy: '🎚️', meeting: '🎙️', twin: '🪞', edited: '✏️', superseded: '⏭️', notification: '📬', governance: '🏢',
};

export default function ActivityTab() {
  const { token } = useAuth();
  const { version } = useCoworker();
  const api = coworkerApi(token);
  const [rows, setRows] = useState<ActivityRow[]>([]);
  const [digest, setDigest] = useState<any>(null);
  const [record, setRecord] = useState<any>(null);
  const [open, setOpen] = useState<number | null>(null);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    api.get('/activity', { limit: 300 }).then((d) => setRows(d.activity || []));
    api.get('/digest').then(setDigest);
    api.get('/metrics', { days: 30 }).then(setRecord).catch(() => {});
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

  const pct = (v: number | null | undefined) => (v === null || v === undefined ? '—' : `${Math.round(v * 100)}%`);

  return (
    <div>
      {record && record.decided + record.executed + record.calls.count > 0 && (
        <Card className="p-4 mb-4">
          <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-3">Track record · last 30 days</p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              [`~${record.hoursSaved}h`, 'saved', record.hoursSavedNote],
              [pct(record.acceptance), 'approved without edits', 'Of everything you decided on'],
              [String(record.executed), 'actions done', `${record.pending} waiting for you`],
              [String(record.calls.count), 'calls run', `${record.calls.escalations} escalated to you`],
            ].map(([big, label, hint]) => (
              <div key={label} title={hint}>
                <p className="text-2xl font-semibold tabular-nums">{big}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
              </div>
            ))}
          </div>
          {record.edits.count > 0 && (
            <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">
              When you edit a draft you change about {pct(record.edits.avgChanged)} of it.
              {record.rejections.recentReasons.length > 0 && ` Recent feedback: “${record.rejections.recentReasons[0]}”.`}
            </p>
          )}
        </Card>
      )}
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
