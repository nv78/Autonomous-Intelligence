import { useState } from 'react';
import { ghostBtn, inputCls, primaryBtn } from './ui';

const DAYS: [string, string][] = [['mon', 'Mon'], ['tue', 'Tue'], ['wed', 'Wed'], ['thu', 'Thu'], ['fri', 'Fri'], ['sat', 'Sat'], ['sun', 'Sun']];
const FREQS: [string, string][] = [['daily', 'Every day'], ['weekdays', 'Every weekday'], ['weekly', 'Weekly'], ['monthly', 'Monthly'], ['hourly', 'Every few hours']];

export interface ScheduleSpec {
  freq: string;
  time: string;
  days?: string[];
  day?: number;
  every_hours?: number;
  deliver?: string[];
}

/** Pick when a scheduled task runs and where its results go. */
export default function ScheduleEditor({ initial, onSave, onCancel, saveLabel = 'Save schedule' }: {
  initial?: Partial<ScheduleSpec>; onSave: (spec: ScheduleSpec) => void; onCancel?: () => void; saveLabel?: string;
}) {
  const [spec, setSpec] = useState<ScheduleSpec>({
    freq: initial?.freq || 'weekdays', time: initial?.time || '09:00', days: initial?.days || ['mon'],
    day: initial?.day || 1, every_hours: initial?.every_hours || 4, deliver: initial?.deliver || ['chat'],
  });
  const set = (patch: Partial<ScheduleSpec>) => setSpec({ ...spec, ...patch });
  const toggle = (list: string[] = [], v: string) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <select className={`${inputCls} w-auto`} value={spec.freq} onChange={(e) => set({ freq: e.target.value })}>
          {FREQS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        {spec.freq === 'hourly' ? (
          <label className="text-sm flex items-center gap-2">every
            <input type="number" min={1} max={24} className={`${inputCls} w-20`} value={spec.every_hours}
              onChange={(e) => set({ every_hours: Number(e.target.value) })} /> hours
          </label>
        ) : (
          <label className="text-sm flex items-center gap-2">at
            <input type="time" className={`${inputCls} w-auto`} value={spec.time} onChange={(e) => set({ time: e.target.value })} />
          </label>
        )}
        {spec.freq === 'monthly' && (
          <label className="text-sm flex items-center gap-2">on day
            <input type="number" min={1} max={31} className={`${inputCls} w-20`} value={spec.day} onChange={(e) => set({ day: Number(e.target.value) })} />
          </label>
        )}
      </div>
      {spec.freq === 'weekly' && (
        <div className="flex flex-wrap gap-1.5">
          {DAYS.map(([v, l]) => (
            <button key={v} type="button" onClick={() => set({ days: toggle(spec.days, v) })}
              className={`px-2.5 py-1 rounded-full text-xs border ${spec.days?.includes(v) ? 'bg-black text-white dark:bg-white dark:text-black border-transparent' : 'border-gray-300 dark:border-gray-600'}`}>
              {l}
            </button>
          ))}
        </div>
      )}
      <div className="flex flex-wrap items-center gap-4 text-sm">
        <span className="text-gray-500">Results go to its chat, and:</span>
        {[['email', 'Email me'], ['push', 'Phone notification'], ['sms', 'Text me']].map(([v, l]) => (
          <label key={v} className="flex items-center gap-1.5">
            <input type="checkbox" checked={spec.deliver?.includes(v)} onChange={() => set({ deliver: toggle(spec.deliver, v) })} /> {l}
          </label>
        ))}
      </div>
      <div className="flex gap-2">
        <button className={primaryBtn} onClick={() => onSave(spec)}>{saveLabel}</button>
        {onCancel && <button className={ghostBtn} onClick={onCancel}>Cancel</button>}
      </div>
    </div>
  );
}
