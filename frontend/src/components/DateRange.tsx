import { Calendar } from 'lucide-react'
import { prettyDate } from '../lib/format'

export const PRESETS = [
  { label: 'Last 7 days', days: 7 },
  { label: 'Last 30 days', days: 30 },
  { label: 'Last 90 days', days: 90 },
  { label: 'Last 12 months', days: 365 },
]

export function DateRange({
  start, end, days, onChangeDays,
}: {
  start: string
  end: string
  days: number
  onChangeDays: (d: number) => void
}) {
  return (
    <div
      className="flex items-center gap-2 rounded-[11px] border px-3 py-2"
      style={{ backgroundColor: 'var(--c-surface)', borderColor: 'var(--c-border)' }}
    >
      <Calendar size={15} style={{ color: 'var(--c-ink-mute)' }} />
      <span className="hidden text-[12.5px] font-medium text-ink sm:inline">
        {prettyDate(start)} – {prettyDate(end)}
      </span>
      <select
        value={days}
        onChange={(e) => onChangeDays(Number(e.target.value))}
        aria-label="Select reporting period"
        className="!w-auto !border-0 !bg-transparent !px-1 !py-0 text-[12.5px] font-medium"
        style={{ color: 'var(--c-brand)' }}
      >
        {PRESETS.map((p) => (
          <option key={p.days} value={p.days}>{p.label}</option>
        ))}
      </select>
    </div>
  )
}
