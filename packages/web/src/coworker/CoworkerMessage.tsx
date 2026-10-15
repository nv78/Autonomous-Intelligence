import { useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ActionCard from './ActionCard';
import MeetingCard from './MeetingCard';
import { parseSegments } from './api';
import { useCoworker } from './CoworkerContext';

export function ToolChip({ summary }: { summary: string }) {
  return (
    <div className="not-prose my-1 inline-flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 bg-[#F7F7F8] dark:bg-[#2F2F2F] rounded-full px-2.5 py-1 mr-1.5">
      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden>
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
      {summary}
    </div>
  );
}

/** Renders an assistant message that may contain tool chips and action cards. */
export default function CoworkerMessage({ content, streaming }: { content: string; streaming?: boolean }) {
  const segments = parseSegments(content);
  const { loadActions, actionCache } = useCoworker();
  const ids = segments.filter((s) => s.kind === 'action').map((s) => (s as { id: number }).id);

  useEffect(() => {
    const missing = ids.filter((id) => !actionCache[id]);
    if (missing.length) loadActions(missing);
  }, [ids.join(',')]);

  if (!segments.length) {
    return <div className="prose prose-sm dark:prose-invert max-w-none">{streaming ? '▋' : ''}</div>;
  }
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      {segments.map((seg, i) => {
        if (seg.kind === 'text') return <ReactMarkdown key={i} remarkPlugins={[remarkGfm]}>{seg.text}</ReactMarkdown>;
        if (seg.kind === 'tool') return <ToolChip key={i} summary={seg.summary} />;
        if (seg.kind === 'action') return <ActionCard key={i} id={seg.id} />;
        if (seg.kind === 'meeting') return <MeetingCard key={i} id={seg.id} />;
        return null;
      })}
      {streaming && <span className="animate-pulse">▋</span>}
    </div>
  );
}
