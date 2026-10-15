import type { ReactNode } from 'react';

export const btn =
  'inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed';
export const primaryBtn = `${btn} bg-black text-white hover:bg-gray-800 dark:bg-white dark:text-black dark:hover:bg-gray-200`;
export const ghostBtn = `${btn} border border-gray-200 dark:border-gray-600 text-gray-800 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-white/10`;
export const dangerBtn = `${btn} bg-red-600 text-white hover:bg-red-700`;
export const inputCls =
  'w-full bg-white dark:bg-[#212121] border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-gray-400';

export function Section({ title, subtitle, action, children }: { title: string; subtitle?: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="mb-8">
      <div className="flex items-end justify-between gap-3 mb-3">
        <div>
          <h2 className="text-base font-semibold">{title}</h2>
          {subtitle && <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-[#262626] ${className}`}>{children}</div>
  );
}

export function Pill({ children, tone = 'gray' }: { children: ReactNode; tone?: 'gray' | 'green' | 'amber' | 'red' | 'blue' }) {
  const tones = {
    gray: 'bg-gray-100 text-gray-700 dark:bg-white/10 dark:text-gray-300',
    green: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300',
    amber: 'bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300',
    red: 'bg-red-100 text-red-800 dark:bg-red-500/15 dark:text-red-300',
    blue: 'bg-blue-100 text-blue-800 dark:bg-blue-500/15 dark:text-blue-300',
  };
  return <span className={`inline-flex items-center text-[11px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap ${tones[tone]}`}>{children}</span>;
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-600 px-6 py-10 text-center">
      <p className="text-sm font-medium">{title}</p>
      {children && <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">{children}</div>}
    </div>
  );
}

export const RELATIONSHIP_TONE: Record<string, 'gray' | 'green' | 'amber' | 'red' | 'blue'> = {
  prospect: 'amber', customer: 'green', investor: 'blue', teammate: 'gray', candidate: 'blue', partner: 'green', vendor: 'gray', contact: 'gray',
};
